"""
Grounded SAM clothing segmentation pipeline.

Combines Grounding DINO (open-vocabulary object detection) with SAM
(Segment Anything Model) to detect, label, and segment clothing items
from photos. No training required -- both models are pretrained.

Usage:
    from wardrobe.segmentation import ClothingSegmenter

    segmenter = ClothingSegmenter()
    results = segmenter.segment("wardrobe_photo.jpg")

    for item in results:
        print(f"{item['category']} ({item['label']}) - {item['confidence']:.2f}")
        item['cropped_image'].save(f"cropped_{item['category']}.png")
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from transformers import (
    AutoModelForZeroShotObjectDetection,
    AutoProcessor,
    SamModel,
    SamProcessor,
)

from wardrobe.config import (
    CATEGORY_MAP,
    DEFAULT_BOX_THRESHOLD,
    DEFAULT_PROMPT,
    DEFAULT_TEXT_THRESHOLD,
    DINO_MODEL_ID,
    SAM_MODEL_ID,
)

logger = logging.getLogger(__name__)


class ClothingSegmenter:
    """
    End-to-end clothing segmentation pipeline using Grounded SAM.

    Pipeline:
        1. Grounding DINO detects clothing items from a text prompt
        2. SAM generates pixel-level masks for each detection
        3. Each item is cropped with background removed (RGBA)
        4. Labels are normalized to standard categories

    Args:
        box_threshold: Minimum confidence for Grounding DINO detections.
        text_threshold: Minimum text similarity for label assignment.
        sam_model_id: HuggingFace model ID for SAM.
            Options: "facebook/sam-vit-base", "facebook/sam-vit-large",
                     "facebook/sam-vit-huge"
        dino_model_id: HuggingFace model ID for Grounding DINO.
        device: Device to run on ("mps", "cpu", or None for auto-detect).
    """

    def __init__(
        self,
        box_threshold: float = DEFAULT_BOX_THRESHOLD,
        text_threshold: float = DEFAULT_TEXT_THRESHOLD,
        sam_model_id: str = SAM_MODEL_ID,
        dino_model_id: str = DINO_MODEL_ID,
        device: str | None = None,
    ):
        self.box_threshold = box_threshold
        self.text_threshold = text_threshold
        self.device = device or self._detect_device()

        logger.info("Loading Grounding DINO: %s", dino_model_id)
        self.dino_processor = AutoProcessor.from_pretrained(dino_model_id)
        self.dino_model = AutoModelForZeroShotObjectDetection.from_pretrained(
            dino_model_id
        ).to(self.device)
        self.dino_model.eval()

        logger.info("Loading SAM: %s", sam_model_id)
        self.sam_processor = SamProcessor.from_pretrained(sam_model_id)
        self.sam_model = SamModel.from_pretrained(sam_model_id).to(self.device)
        self.sam_model.eval()

        logger.info("Models loaded on device: %s", self.device)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def segment(
        self,
        image_input: str | Path | Image.Image,
        prompt: str | None = None,
    ) -> list[dict]:
        """
        Detect and segment clothing items in an image.

        Args:
            image_input: Path to an image file, or a PIL Image.
            prompt: Text prompt for Grounding DINO. Uses DEFAULT_PROMPT
                if not specified.

        Returns:
            List of dicts, each containing:
                - "label": raw label from Grounding DINO (e.g. "t-shirt")
                - "category": normalized category (e.g. "top")
                - "confidence": detection confidence (0-1)
                - "bbox": bounding box [x1, y1, x2, y2] in pixels
                - "mask": binary mask as numpy array (H, W), dtype bool
                - "cropped_image": PIL Image (RGBA) of just this item
        """
        prompt = prompt or DEFAULT_PROMPT
        image = self._load_image(image_input)

        # Step 1: Detect with Grounding DINO
        boxes, scores, labels = self._detect(image, prompt)

        if len(boxes) == 0:
            logger.info("No clothing items detected.")
            return []

        logger.info(
            "Grounding DINO found %d raw detections, applying NMS...", len(boxes)
        )

        # Step 1b: Apply NMS to remove duplicate/overlapping boxes
        keep = self._nms(boxes, scores, iou_threshold=0.5)
        boxes = boxes[keep]
        scores = scores[keep]
        labels = [labels[i] for i in keep]

        # Step 1c: Filter out detections with empty labels or unknown category
        filtered = []
        for i in range(len(boxes)):
            raw_label = labels[i].strip().lower()
            category = self._normalize_category(raw_label)
            # Keep only detections with a known category
            if category != "unknown" and raw_label:
                filtered.append((i, raw_label, category))

        if not filtered:
            logger.info("No clothing items after filtering.")
            return []

        keep_idx = [f[0] for f in filtered]
        boxes = boxes[keep_idx]
        scores = scores[keep_idx]
        filtered_labels = [f[1] for f in filtered]
        filtered_categories = [f[2] for f in filtered]

        logger.info("%d items after NMS + filtering.", len(boxes))

        # Step 2: Segment with SAM
        masks = self._segment(image, boxes)

        # Step 3: Build results
        results = []
        for i in range(len(boxes)):
            bbox = boxes[i].tolist()
            confidence = float(scores[i])
            mask = masks[i]  # (H, W) bool array

            # Crop the item using the mask
            cropped = self._crop_with_mask(image, mask, bbox)

            results.append(
                {
                    "label": filtered_labels[i],
                    "category": filtered_categories[i],
                    "confidence": confidence,
                    "bbox": [round(c, 1) for c in bbox],
                    "mask": mask,
                    "cropped_image": cropped,
                }
            )

        # Sort by confidence descending
        results.sort(key=lambda r: r["confidence"], reverse=True)
        return results

    # ------------------------------------------------------------------
    # Internal: Detection (Grounding DINO)
    # ------------------------------------------------------------------

    def _detect(
        self,
        image: Image.Image,
        prompt: str,
    ) -> tuple[np.ndarray, np.ndarray, list[str]]:
        """
        Run Grounding DINO to get bounding boxes, scores, and labels.

        Returns:
            boxes: (N, 4) array of [x1, y1, x2, y2] in pixel coords
            scores: (N,) array of confidence scores
            labels: list of N label strings
        """
        # Grounding DINO expects the text prompt as a period-separated string
        # e.g. "shirt. pants. jacket." — the processor tokenizes it internally.
        # Ensure prompt ends with a period for consistent parsing.
        if not prompt.strip().endswith("."):
            prompt = prompt.strip() + "."

        inputs = self.dino_processor(
            images=image,
            text=prompt,
            return_tensors="pt",
        ).to(self.device)

        with torch.no_grad():
            outputs = self.dino_model(**inputs)

        results = self.dino_processor.post_process_grounded_object_detection(
            outputs,
            inputs.input_ids,
            threshold=self.box_threshold,
            text_threshold=self.text_threshold,
            target_sizes=[image.size[::-1]],  # (height, width)
        )

        result = results[0]
        boxes = result["boxes"].cpu().numpy()
        scores = result["scores"].cpu().numpy()
        # Use "text_labels" (string names) instead of "labels" (integer ids)
        raw_labels = result.get("text_labels", result.get("labels", []))
        # Clean up labels: DINO sometimes returns partial prompt substrings
        labels = [self._clean_label(lbl) for lbl in raw_labels]

        return boxes, scores, labels

    # ------------------------------------------------------------------
    # Internal: Segmentation (SAM)
    # ------------------------------------------------------------------

    def _segment(
        self,
        image: Image.Image,
        boxes: np.ndarray,
    ) -> list[np.ndarray]:
        """
        Run SAM to produce masks for each bounding box.

        Args:
            image: PIL Image
            boxes: (N, 4) array of [x1, y1, x2, y2]

        Returns:
            List of N boolean masks, each (H, W).
        """
        # SAM expects input_boxes as [[[x1,y1,x2,y2], [x1,y1,x2,y2], ...]]
        input_boxes = [boxes.tolist()]

        inputs = self.sam_processor(
            images=image,
            input_boxes=input_boxes,
            return_tensors="pt",
        ).to(self.device)

        with torch.no_grad():
            outputs = self.sam_model(**inputs)

        # Post-process masks to original image size
        masks = self.sam_processor.image_processor.post_process_masks(
            outputs.pred_masks.cpu(),
            inputs["original_sizes"].cpu(),
            inputs["reshaped_input_sizes"].cpu(),
        )

        # masks is a list (one per image) of tensors (N_boxes, num_preds, H, W)
        # SAM returns 3 mask predictions per box; take the one with highest IoU
        mask_tensor = masks[0]  # (N_boxes, 3, H, W)
        iou_scores = outputs.iou_scores.cpu()  # (1, N_boxes, 3)

        result_masks = []
        for i in range(mask_tensor.shape[0]):
            # Pick the mask with highest predicted IoU
            best_idx = iou_scores[0, i].argmax().item()
            mask = mask_tensor[i, best_idx].numpy().astype(bool)
            result_masks.append(mask)

        return result_masks

    # ------------------------------------------------------------------
    # Internal: Cropping
    # ------------------------------------------------------------------

    @staticmethod
    def _crop_with_mask(
        image: Image.Image,
        mask: np.ndarray,
        bbox: list[float],
    ) -> Image.Image:
        """
        Crop a clothing item using its segmentation mask.

        Returns an RGBA PIL Image where the background is transparent
        and the item pixels are preserved.
        """
        # Convert image to RGBA
        img_array = np.array(image.convert("RGBA"))

        # Create alpha channel from mask
        alpha = (mask.astype(np.uint8) * 255)

        # Apply mask as alpha channel
        img_array[:, :, 3] = alpha

        # Crop to bounding box with a small padding
        x1, y1, x2, y2 = [int(c) for c in bbox]
        h, w = img_array.shape[:2]
        pad = 5
        x1 = max(0, x1 - pad)
        y1 = max(0, y1 - pad)
        x2 = min(w, x2 + pad)
        y2 = min(h, y2 + pad)

        cropped = img_array[y1:y2, x1:x2]
        return Image.fromarray(cropped, "RGBA")

    # ------------------------------------------------------------------
    # Internal: Category normalization
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_category(raw_label: str) -> str:
        """
        Map a raw Grounding DINO label to a normalized category.

        Falls back to "unknown" if the label isn't in CATEGORY_MAP.
        """
        label = raw_label.strip().lower()

        # Direct lookup
        if label in CATEGORY_MAP:
            return CATEGORY_MAP[label]

        # Fuzzy: check if any key is a substring of the label
        for key, category in CATEGORY_MAP.items():
            if key in label:
                return category

        return "unknown"

    @staticmethod
    def _clean_label(raw: str) -> str:
        """
        Clean a raw Grounding DINO label string.

        DINO sometimes returns partial prompt substrings like
        "shirt t - shirt" or "t - shirt". This method finds the best
        matching clothing term from CATEGORY_MAP.
        """
        raw = raw.strip().lower()

        # Normalize common DINO artifacts: "t - shirt" -> "t-shirt"
        raw = raw.replace(" - ", "-")

        # Try to find the best matching key from CATEGORY_MAP
        best_match = None
        best_len = 0
        for key in CATEGORY_MAP:
            if key in raw and len(key) > best_len:
                best_match = key
                best_len = len(key)

        return best_match or raw

    # ------------------------------------------------------------------
    # Internal: Utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _nms(
        boxes: np.ndarray,
        scores: np.ndarray,
        iou_threshold: float = 0.5,
    ) -> list[int]:
        """
        Non-Maximum Suppression to remove overlapping detections.

        Args:
            boxes: (N, 4) array of [x1, y1, x2, y2]
            scores: (N,) array of confidence scores
            iou_threshold: IoU threshold for suppression

        Returns:
            List of indices to keep.
        """
        if len(boxes) == 0:
            return []

        x1 = boxes[:, 0]
        y1 = boxes[:, 1]
        x2 = boxes[:, 2]
        y2 = boxes[:, 3]
        areas = (x2 - x1) * (y2 - y1)

        order = scores.argsort()[::-1]
        keep = []

        while len(order) > 0:
            i = order[0]
            keep.append(i)

            if len(order) == 1:
                break

            # Compute IoU of i with all remaining boxes
            xx1 = np.maximum(x1[i], x1[order[1:]])
            yy1 = np.maximum(y1[i], y1[order[1:]])
            xx2 = np.minimum(x2[i], x2[order[1:]])
            yy2 = np.minimum(y2[i], y2[order[1:]])

            w = np.maximum(0.0, xx2 - xx1)
            h = np.maximum(0.0, yy2 - yy1)
            intersection = w * h

            iou = intersection / (areas[i] + areas[order[1:]] - intersection)

            # Keep boxes with IoU below threshold
            remaining = np.where(iou <= iou_threshold)[0]
            order = order[remaining + 1]

        return keep

    @staticmethod
    def _load_image(image_input: str | Path | Image.Image) -> Image.Image:
        """Load an image from a path or return it if already a PIL Image."""
        if isinstance(image_input, Image.Image):
            return image_input.convert("RGB")
        return Image.open(image_input).convert("RGB")

    @staticmethod
    def _detect_device() -> str:
        """Auto-detect the best available device."""
        if torch.cuda.is_available():
            return "cuda"
        # MPS can have issues with some HuggingFace models; try it but
        # fall back to CPU if needed.
        if torch.backends.mps.is_available():
            try:
                # Quick smoke test
                _ = torch.zeros(1, device="mps")
                return "mps"
            except Exception:
                logger.warning("MPS available but failed smoke test, using CPU.")
        return "cpu"

