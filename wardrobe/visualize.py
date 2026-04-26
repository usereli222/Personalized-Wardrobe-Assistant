"""
Visualization utilities for clothing segmentation results.

Draws annotated images with bounding boxes, segmentation masks,
and category labels color-coded by clothing type.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from wardrobe.config import CATEGORY_COLORS_RGB


def visualize_results(
    image_input: str | Path | Image.Image,
    results: list[dict],
    show_masks: bool = True,
    show_labels: bool = True,
    show_confidence: bool = True,
    mask_alpha: float = 0.4,
) -> Image.Image:
    """
    Draw segmentation results on the original image.

    Args:
        image_input: Path to an image or a PIL Image.
        results: Output from ClothingSegmenter.segment().
        show_masks: Whether to overlay segmentation masks.
        show_labels: Whether to draw labels above bounding boxes.
        show_confidence: Whether to include confidence in labels.
        mask_alpha: Opacity of mask overlay (0-1).

    Returns:
        Annotated PIL Image.
    """
    if isinstance(image_input, (str, Path)):
        image = Image.open(image_input).convert("RGB")
    else:
        image = image_input.convert("RGB")

    # Work in numpy/OpenCV for drawing
    canvas = np.array(image).copy()

    for item in results:
        category = item["category"]
        color = CATEGORY_COLORS_RGB.get(category, CATEGORY_COLORS_RGB["unknown"])
        # OpenCV uses BGR
        color_bgr = (color[2], color[1], color[0])
        bbox = item["bbox"]
        x1, y1, x2, y2 = [int(c) for c in bbox]

        # Draw mask overlay
        if show_masks and "mask" in item:
            mask = item["mask"]
            overlay = canvas.copy()
            overlay[mask] = color
            canvas = cv2.addWeighted(canvas, 1 - mask_alpha, overlay, mask_alpha, 0)

        # Draw bounding box
        cv2.rectangle(canvas, (x1, y1), (x2, y2), color_bgr, 2)

        # Draw label
        if show_labels:
            raw_label = item.get("label", "")
            cat = item.get("category", "")
            conf = item.get("confidence", 0)

            if show_confidence:
                label_text = f"{cat} ({raw_label}) {conf:.2f}"
            else:
                label_text = f"{cat} ({raw_label})"

            # Background rectangle for text
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.6
            thickness = 1
            (text_w, text_h), baseline = cv2.getTextSize(
                label_text, font, font_scale, thickness
            )
            cv2.rectangle(
                canvas,
                (x1, y1 - text_h - baseline - 6),
                (x1 + text_w + 4, y1),
                color_bgr,
                -1,
            )
            cv2.putText(
                canvas,
                label_text,
                (x1 + 2, y1 - baseline - 3),
                font,
                font_scale,
                (255, 255, 255),
                thickness,
                cv2.LINE_AA,
            )

    return Image.fromarray(canvas)
