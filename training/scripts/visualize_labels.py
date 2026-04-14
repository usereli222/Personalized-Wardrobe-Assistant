#!/usr/bin/env python3
from __future__ import annotations

"""
Visualize converted YOLO segmentation labels overlaid on images.

Picks random images from the converted dataset, draws the segmentation
polygons color-coded by class, and saves the visualizations for inspection.

Usage:
    python visualize_labels.py \
        --data-dir ../data/deepfashion2_yolo \
        --split train \
        --num-images 10 \
        --output-dir ../data/visualizations
"""

import argparse
import random
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # non-interactive backend (no display needed)
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from PIL import Image

# Class names and colors (one distinct color per class)
CLASS_NAMES = {
    0: "top",
    1: "outerwear",
    2: "shorts",
    3: "trousers",
    4: "skirt",
    5: "dress",
}

# Visually distinct colors for each class (RGB, 0-1)
CLASS_COLORS = {
    0: (0.12, 0.47, 0.71),   # blue — top
    1: (1.00, 0.50, 0.05),   # orange — outerwear
    2: (0.17, 0.63, 0.17),   # green — shorts
    3: (0.84, 0.15, 0.16),   # red — trousers
    4: (0.58, 0.40, 0.74),   # purple — skirt
    5: (0.55, 0.34, 0.29),   # brown — dress
}


def parse_label_file(label_path: Path) -> list[dict]:
    """
    Parse a YOLO segmentation label file.

    Each line: class_id x1 y1 x2 y2 ... xn yn (all normalized 0-1)

    Returns list of dicts with:
        - class_id (int)
        - polygon (list of (x, y) tuples, normalized)
    """
    items = []
    with open(label_path, "r") as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) < 7:  # class_id + at least 3 points (6 coords)
                continue
            class_id = int(parts[0])
            coords = [float(v) for v in parts[1:]]
            # Group into (x, y) pairs
            polygon = [(coords[i], coords[i + 1]) for i in range(0, len(coords), 2)]
            items.append({"class_id": class_id, "polygon": polygon})
    return items


def visualize_image(
    image_path: Path,
    label_path: Path,
    output_path: Path,
) -> None:
    """
    Draw segmentation polygons on an image and save the result.
    """
    img = Image.open(image_path)
    img_array = np.array(img)
    img_width, img_height = img.size

    items = parse_label_file(label_path)

    fig, axes = plt.subplots(1, 2, figsize=(16, 8))

    # Left: original image
    axes[0].imshow(img_array)
    axes[0].set_title("Original", fontsize=14)
    axes[0].axis("off")

    # Right: image with overlaid segmentation masks
    axes[1].imshow(img_array)
    axes[1].set_title("Segmentation Labels", fontsize=14)
    axes[1].axis("off")

    legend_entries = {}

    for item in items:
        class_id = item["class_id"]
        color = CLASS_COLORS.get(class_id, (0.5, 0.5, 0.5))
        class_name = CLASS_NAMES.get(class_id, f"class_{class_id}")

        # Convert normalized coordinates to pixel coordinates
        pixel_polygon = [
            (x * img_width, y * img_height)
            for x, y in item["polygon"]
        ]

        # Draw filled polygon with transparency
        polygon_np = np.array(pixel_polygon)
        polygon_patch = plt.Polygon(
            polygon_np,
            closed=True,
            facecolor=(*color, 0.35),
            edgecolor=(*color, 1.0),
            linewidth=2,
        )
        axes[1].add_patch(polygon_patch)

        # Track for legend (one entry per class)
        if class_id not in legend_entries:
            legend_entries[class_id] = mpatches.Patch(
                facecolor=(*color, 0.5),
                edgecolor=color,
                label=f"{class_id}: {class_name}",
            )

    # Add legend
    if legend_entries:
        axes[1].legend(
            handles=list(legend_entries.values()),
            loc="upper right",
            fontsize=10,
            framealpha=0.8,
        )

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(
        description="Visualize YOLO segmentation labels overlaid on images.",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        required=True,
        help="Path to YOLO dataset directory (e.g., deepfashion2_yolo/).",
    )
    parser.add_argument(
        "--split",
        choices=["train", "val"],
        default="train",
        help="Which split to visualize.",
    )
    parser.add_argument(
        "--num-images",
        type=int,
        default=10,
        help="Number of random images to visualize.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory to save visualizations. Default: data_dir/../visualizations/",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducible sampling.",
    )

    args = parser.parse_args()

    images_dir = args.data_dir / args.split / "images"
    labels_dir = args.data_dir / args.split / "labels"

    if not images_dir.exists():
        print(f"Error: Images directory not found: {images_dir}")
        return
    if not labels_dir.exists():
        print(f"Error: Labels directory not found: {labels_dir}")
        return

    output_dir = args.output_dir or (args.data_dir.parent / "visualizations")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Find all label files that have a corresponding image
    label_files = sorted(labels_dir.glob("*.txt"))
    valid_pairs = []
    for label_path in label_files:
        stem = label_path.stem
        # Check for matching image
        for ext in [".jpg", ".jpeg", ".png"]:
            img_path = images_dir / f"{stem}{ext}"
            if img_path.exists():
                valid_pairs.append((img_path, label_path))
                break

    if not valid_pairs:
        print("Error: No matching image-label pairs found.")
        return

    print(f"Found {len(valid_pairs):,} image-label pairs in {args.split}/")

    # Sample random images
    random.seed(args.seed)
    num_to_sample = min(args.num_images, len(valid_pairs))
    sampled = random.sample(valid_pairs, num_to_sample)

    print(f"Visualizing {num_to_sample} random images...")

    for i, (img_path, label_path) in enumerate(sampled):
        out_path = output_dir / f"viz_{args.split}_{img_path.stem}.png"
        visualize_image(img_path, label_path, out_path)
        print(f"  [{i + 1}/{num_to_sample}] Saved: {out_path.name}")

    print(f"\nDone! Visualizations saved to: {output_dir}")


if __name__ == "__main__":
    main()
