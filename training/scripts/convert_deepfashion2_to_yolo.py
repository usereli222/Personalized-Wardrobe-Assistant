#!/usr/bin/env python3
from __future__ import annotations

"""
Convert DeepFashion2 annotations to YOLO segmentation format.

DeepFashion2 uses per-image JSON files with item-level annotations.
This script converts them to YOLO-seg .txt label files and symlinks
(or copies) the corresponding images.

Usage:
    python convert_deepfashion2_to_yolo.py \
        --raw-dir ../data/deepfashion2_raw \
        --out-dir ../data/deepfashion2_yolo \
        --splits train validation

    # Use --copy to copy images instead of symlinking
    python convert_deepfashion2_to_yolo.py \
        --raw-dir ../data/deepfashion2_raw \
        --out-dir ../data/deepfashion2_yolo \
        --splits train validation \
        --copy
"""

import argparse
import json
import logging
import shutil
import sys
from collections import defaultdict
from pathlib import Path

from PIL import Image
from tqdm import tqdm

# ---------------------------------------------------------------------------
# Category mapping: DeepFashion2 (1-indexed, 13 classes) → merged (0-indexed, 6 classes)
# ---------------------------------------------------------------------------

# DeepFashion2 original categories (1-indexed)
DF2_CATEGORIES = {
    1: "short sleeve top",
    2: "long sleeve top",
    3: "short sleeve outwear",
    4: "long sleeve outwear",
    5: "vest",
    6: "sling",
    7: "shorts",
    8: "trousers",
    9: "skirt",
    10: "short sleeve dress",
    11: "long sleeve dress",
    12: "vest dress",
    13: "sling dress",
}

# Merged YOLO classes (0-indexed)
YOLO_CLASSES = {
    0: "top",
    1: "outerwear",
    2: "shorts",
    3: "trousers",
    4: "skirt",
    5: "dress",
}

# Mapping: DeepFashion2 category_id → YOLO class_id
CATEGORY_MERGE_MAP = {
    1: 0,   # short sleeve top   → top
    2: 0,   # long sleeve top    → top
    3: 1,   # short sleeve outwear → outerwear
    4: 1,   # long sleeve outwear  → outerwear
    5: 0,   # vest               → top
    6: 0,   # sling              → top
    7: 2,   # shorts             → shorts
    8: 3,   # trousers           → trousers
    9: 4,   # skirt              → skirt
    10: 5,  # short sleeve dress → dress
    11: 5,  # long sleeve dress  → dress
    12: 5,  # vest dress         → dress
    13: 5,  # sling dress        → dress
}

# Map DeepFashion2 split names to YOLO split names
SPLIT_NAME_MAP = {
    "train": "train",
    "validation": "val",
}

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Conversion logic
# ---------------------------------------------------------------------------


def parse_annotation(anno_path: Path) -> list[dict]:
    """
    Parse a single DeepFashion2 annotation JSON file.

    Returns a list of items, each with:
        - yolo_class_id (int): merged class index (0-5)
        - polygons (list[list[float]]): list of polygon coordinate lists
          Each polygon is [x1, y1, x2, y2, ...] in absolute pixel coords

    Items with invalid/missing segmentation or unknown category are skipped.
    """
    try:
        with open(anno_path, "r") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"Failed to read {anno_path}: {e}")
        return []

    items = []

    # Items are keyed as "item1", "item2", etc.
    for key, value in data.items():
        if not key.startswith("item"):
            continue

        if not isinstance(value, dict):
            continue

        # Get category
        category_id = value.get("category_id")
        if category_id not in CATEGORY_MERGE_MAP:
            logger.debug(f"Unknown category_id {category_id} in {anno_path}, skipping item")
            continue

        yolo_class_id = CATEGORY_MERGE_MAP[category_id]

        # Get segmentation polygons
        segmentation = value.get("segmentation")
        if not segmentation or not isinstance(segmentation, list):
            continue

        valid_polygons = []
        for polygon in segmentation:
            if not isinstance(polygon, list):
                continue
            # Need at least 3 points (6 values: x1,y1,x2,y2,x3,y3)
            if len(polygon) < 6:
                continue
            # Check that all values are numeric
            if not all(isinstance(v, (int, float)) for v in polygon):
                continue
            valid_polygons.append(polygon)

        if not valid_polygons:
            continue

        items.append({
            "yolo_class_id": yolo_class_id,
            "polygons": valid_polygons,
            "original_category_id": category_id,
        })

    return items


def normalize_polygon(polygon: list[float], img_width: int, img_height: int) -> list[float]:
    """
    Normalize a polygon's coordinates from absolute pixels to [0, 1].

    Input polygon: [x1, y1, x2, y2, x3, y3, ...]
    Output: [x1/w, y1/h, x2/w, y2/h, ...] clamped to [0, 1]
    """
    normalized = []
    for i, val in enumerate(polygon):
        if i % 2 == 0:
            # x coordinate → normalize by width
            normalized.append(max(0.0, min(1.0, val / img_width)))
        else:
            # y coordinate → normalize by height
            normalized.append(max(0.0, min(1.0, val / img_height)))
    return normalized


def format_yolo_line(class_id: int, polygon: list[float]) -> str:
    """
    Format a single YOLO segmentation label line.

    Format: class_id x1 y1 x2 y2 ... xn yn
    Coordinates are rounded to 6 decimal places.
    """
    coords_str = " ".join(f"{v:.6f}" for v in polygon)
    return f"{class_id} {coords_str}"


def get_image_dimensions(image_path: Path) -> tuple[int, int] | None:
    """
    Get image dimensions (width, height) without loading full image into memory.
    Returns None if the image can't be read.
    """
    try:
        with Image.open(image_path) as img:
            return img.size  # (width, height)
    except Exception as e:
        logger.warning(f"Failed to read image {image_path}: {e}")
        return None


def convert_split(
    raw_dir: Path,
    out_dir: Path,
    split: str,
    copy_images: bool = False,
) -> dict:
    """
    Convert one split (train or validation) of DeepFashion2 to YOLO format.

    Args:
        raw_dir: path to deepfashion2_raw/
        out_dir: path to deepfashion2_yolo/
        split: "train" or "validation"
        copy_images: if True, copy images; if False, create symlinks

    Returns:
        Stats dict with counts
    """
    yolo_split = SPLIT_NAME_MAP[split]

    annos_dir = raw_dir / split / "annos"
    images_dir = raw_dir / split / "image"
    out_images_dir = out_dir / yolo_split / "images"
    out_labels_dir = out_dir / yolo_split / "labels"

    # Validate input directories exist
    if not annos_dir.exists():
        logger.error(f"Annotations directory not found: {annos_dir}")
        sys.exit(1)
    if not images_dir.exists():
        logger.error(f"Images directory not found: {images_dir}")
        sys.exit(1)

    # Create output directories
    out_images_dir.mkdir(parents=True, exist_ok=True)
    out_labels_dir.mkdir(parents=True, exist_ok=True)

    # Collect all annotation files
    anno_files = sorted(annos_dir.glob("*.json"))
    if not anno_files:
        logger.error(f"No JSON files found in {annos_dir}")
        sys.exit(1)

    logger.info(f"Converting {split} split: {len(anno_files)} annotation files")

    # Stats tracking
    stats = {
        "total_annotations": len(anno_files),
        "images_converted": 0,
        "images_skipped_no_items": 0,
        "images_skipped_no_image": 0,
        "images_skipped_bad_dims": 0,
        "total_items": 0,
        "items_per_class": defaultdict(int),
        "items_per_original_category": defaultdict(int),
        "polygons_skipped": 0,
    }

    for anno_path in tqdm(anno_files, desc=f"Converting {split}", unit="img"):
        # Determine corresponding image path
        stem = anno_path.stem  # e.g., "000001"
        image_path = None
        for ext in [".jpg", ".jpeg", ".png"]:
            candidate = images_dir / f"{stem}{ext}"
            if candidate.exists():
                image_path = candidate
                break

        if image_path is None:
            stats["images_skipped_no_image"] += 1
            logger.debug(f"No image found for annotation {anno_path.name}")
            continue

        # Parse annotation
        items = parse_annotation(anno_path)
        if not items:
            stats["images_skipped_no_items"] += 1
            continue

        # Get image dimensions for coordinate normalization
        dims = get_image_dimensions(image_path)
        if dims is None:
            stats["images_skipped_bad_dims"] += 1
            continue

        img_width, img_height = dims

        # Build YOLO label lines
        label_lines = []
        for item in items:
            class_id = item["yolo_class_id"]
            original_cat = item["original_category_id"]

            for polygon in item["polygons"]:
                normalized = normalize_polygon(polygon, img_width, img_height)
                line = format_yolo_line(class_id, normalized)
                label_lines.append(line)

                stats["items_per_class"][YOLO_CLASSES[class_id]] += 1
                stats["items_per_original_category"][DF2_CATEGORIES[original_cat]] += 1
                stats["total_items"] += 1

        if not label_lines:
            stats["images_skipped_no_items"] += 1
            continue

        # Write label file
        label_path = out_labels_dir / f"{stem}.txt"
        with open(label_path, "w") as f:
            f.write("\n".join(label_lines) + "\n")

        # Symlink or copy the image
        out_image_path = out_images_dir / image_path.name
        if not out_image_path.exists():
            if copy_images:
                shutil.copy2(image_path, out_image_path)
            else:
                # Use absolute path for symlink to avoid relative path issues
                out_image_path.symlink_to(image_path.resolve())

        stats["images_converted"] += 1

    return stats


def print_stats(stats: dict, split: str) -> None:
    """Print conversion statistics for a split."""
    print(f"\n{'=' * 60}")
    print(f"  Conversion Summary — {split}")
    print(f"{'=' * 60}")
    print(f"  Total annotation files:    {stats['total_annotations']:,}")
    print(f"  Images converted:          {stats['images_converted']:,}")
    print(f"  Skipped (no valid items):   {stats['images_skipped_no_items']:,}")
    print(f"  Skipped (image not found):  {stats['images_skipped_no_image']:,}")
    print(f"  Skipped (bad dimensions):   {stats['images_skipped_bad_dims']:,}")
    print(f"  Total item instances:       {stats['total_items']:,}")
    print()
    print(f"  Merged class distribution (YOLO classes):")
    for class_name in YOLO_CLASSES.values():
        count = stats["items_per_class"].get(class_name, 0)
        bar = "█" * min(50, count // 500)
        print(f"    {class_name:<12s}  {count:>7,}  {bar}")
    print()
    print(f"  Original category distribution:")
    for cat_id, cat_name in DF2_CATEGORIES.items():
        count = stats["items_per_original_category"].get(cat_name, 0)
        print(f"    {cat_id:>2d}. {cat_name:<22s}  {count:>7,}")
    print(f"{'=' * 60}\n")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Convert DeepFashion2 annotations to YOLO segmentation format.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Convert both train and validation splits (symlink images):
  python convert_deepfashion2_to_yolo.py \\
      --raw-dir ../data/deepfashion2_raw \\
      --out-dir ../data/deepfashion2_yolo \\
      --splits train validation

  # Convert only train split, copying images instead of symlinking:
  python convert_deepfashion2_to_yolo.py \\
      --raw-dir ../data/deepfashion2_raw \\
      --out-dir ../data/deepfashion2_yolo \\
      --splits train \\
      --copy
        """,
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        required=True,
        help="Path to deepfashion2_raw/ directory containing train/ and validation/ subdirs.",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        required=True,
        help="Path to output YOLO dataset directory (e.g., deepfashion2_yolo/).",
    )
    parser.add_argument(
        "--splits",
        nargs="+",
        choices=["train", "validation"],
        default=["train", "validation"],
        help="Which splits to convert. Default: both train and validation.",
    )
    parser.add_argument(
        "--copy",
        action="store_true",
        default=False,
        help="Copy images instead of creating symlinks. Uses more disk space but more portable.",
    )

    args = parser.parse_args()

    # Validate raw directory
    if not args.raw_dir.exists():
        logger.error(f"Raw data directory not found: {args.raw_dir}")
        logger.error("Download DeepFashion2 and place it at the specified path.")
        sys.exit(1)

    logger.info(f"Raw data directory: {args.raw_dir}")
    logger.info(f"Output directory:   {args.out_dir}")
    logger.info(f"Splits:             {args.splits}")
    logger.info(f"Image mode:         {'copy' if args.copy else 'symlink'}")
    logger.info(f"Category mapping:   13 DeepFashion2 classes → 6 merged YOLO classes")
    print()

    # Print the merge mapping for reference
    print("Category merge mapping:")
    for df2_id, yolo_id in CATEGORY_MERGE_MAP.items():
        print(f"  {df2_id:>2d}. {DF2_CATEGORIES[df2_id]:<22s} → {yolo_id} ({YOLO_CLASSES[yolo_id]})")
    print()

    # Convert each split
    all_stats = {}
    for split in args.splits:
        stats = convert_split(
            raw_dir=args.raw_dir,
            out_dir=args.out_dir,
            split=split,
            copy_images=args.copy,
        )
        all_stats[split] = stats
        print_stats(stats, split)

    # Final summary
    total_images = sum(s["images_converted"] for s in all_stats.values())
    total_items = sum(s["total_items"] for s in all_stats.values())
    logger.info(f"Done! Converted {total_images:,} images with {total_items:,} item instances total.")
    logger.info(f"Output written to: {args.out_dir}")


if __name__ == "__main__":
    main()
