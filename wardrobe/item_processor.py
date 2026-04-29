"""
Pipeline glue combining SAM segmentation with feature extraction.

Takes segmented wardrobe items and enriches them with dense FashionCLIP
embeddings and k-means extracted color palettes, creating final objects
ready for the FAISS database and matching algorithms.
"""

import logging
from typing import Optional, Union
from pathlib import Path

import numpy as np
from PIL import Image

from wardrobe.embeddings import ClothingEmbedder
from wardrobe.colors import extract_dominant_colors

logger = logging.getLogger(__name__)


class WardrobeProcessor:
    """
    Takes Grounded SAM output and produces fully processed wardrobe items
    ready for matching against the outfit library.
    """

    def __init__(self, embedder_device: str = "cpu"):
        """
        Initialize the processor and underlying embedding models.
        """
        logger.info("Initializing WardrobeProcessor...")
        self.embedder = ClothingEmbedder(device=embedder_device)
        self.segmenter = None  # Lazy load later to save VRAM if only embedding

    def process_item(
        self, 
        cropped_image: Image.Image, 
        mask: Optional[np.ndarray] = None, 
        label: Optional[str] = None, 
        category: Optional[str] = None
    ) -> dict:
        """
        Process a single cropped clothing item.
        
        Args:
            cropped_image: RGBA or RGB PIL Image containing the item.
            mask: Optional binary mask tracing the exact item pixels.
                If not provided, and the image is RGBA, the alpha channel
                will be used as the mask for color extraction.
            label: Original label.
            category: Normalized category.
            
        Returns:
            Dictionary with embedding, colors, and metadata.
        """
        # If no mask is given but we have an RGBA image, use alpha channel as mask!
        # This prevents the black/white transparent background from becoming 
        # the "dominant color" during K-Means.
        if mask is None and cropped_image.mode == "RGBA":
            img_arr = np.array(cropped_image)
            mask = img_arr[:, :, 3] > 0

        # Extract features
        embedding = self.embedder.embed(cropped_image)
        dominant_colors = extract_dominant_colors(cropped_image, mask=mask, n_colors=3)

        return {
            "label": label or "unknown",
            "category": category or "unknown",
            "embedding": embedding,
            "dominant_colors": dominant_colors,
            "cropped_image": cropped_image
        }

    def process_segmentation_results(self, seg_results: list[dict]) -> list[dict]:
        """
        Process all items from Grounded SAM output.
        
        Args:
            seg_results: list of dicts from ClothingSegmenter.segment()
        
        Returns:
            List of processed item dicts containing features.
        """
        processed_items = []
        
        for idx, item_data in enumerate(seg_results):
            logger.info(
                f"Extracting features for item {idx + 1} "
                f"({item_data.get('category', 'unknown')})..."
            )
            # The SAM segmenter returns the exact mask covering the original image
            # Wait, the mask from `ClothingSegmenter` is bounding-box scale or full image scale?
            # SAM returns full image scale masks. BUT the `cropped_image` is cropped to the bbox.
            # So the Full image scale mask can't simply be applied to the `cropped_image`.
            # That's why we rely on the RGBA alpha channel of `cropped_image` as the exact local mask!
            
            processed = self.process_item(
                cropped_image=item_data["cropped_image"],
                mask=None,  # Forces reliance on cropped_image alpha channel
                label=item_data.get("label"),
                category=item_data.get("category")
            )
            
            # Carry over spatial data
            processed["confidence"] = item_data.get("confidence")
            processed["bbox"] = item_data.get("bbox")
            
            processed_items.append(processed)
            
        return processed_items

    def process_wardrobe_photo(self, image_input: Union[str, Path, Image.Image], prompt: Optional[str] = None) -> list[dict]:
        """
        Full end-to-end pipeline:
        Raw photo -> Grounded SAM (Segments) -> FashionCLIP & KMeans (Features)

        Args:
            image_input: File path or a PIL Image already in memory (e.g. downloaded
                from Google Drive). ClothingSegmenter.segment() accepts both.
        """
        # Lazy load segmenter to avoid loading heavy SAM into VRAM if this
        # API is just being used for FAISS testing.
        if self.segmenter is None:
            from wardrobe.segmentation import ClothingSegmenter
            self.segmenter = ClothingSegmenter(device=self.embedder.device.type)

        name = getattr(image_input, "filename", None) or (Path(image_input).name if not isinstance(image_input, Image.Image) else "pil_image")
        logger.info(f"\nProcessing full wardrobe photo: {name}")

        # 1. Segment — accepts str | Path | PIL Image
        seg_results = self.segmenter.segment(image_input, prompt=prompt)
        
        if not seg_results:
            logger.warning("No clothing items found in photo.")
            return []
            
        # 2. Extract Features
        logger.info(f"Extracting features for {len(seg_results)} detected items...")
        processed_items = self.process_segmentation_results(seg_results)
        
        logger.info("Successfully processed items.")
        return processed_items
