#!/usr/bin/env python3
"""
End-to-end test for the Grounded SAM clothing segmentation pipeline.

Runs the segmenter on wardrobe test images and saves:
  - Annotated images (with boxes, masks, labels)
  - Individual cropped items (RGBA PNGs with transparent backgrounds)
  - Summary report to stdout

Usage:
    python tests/test_segmentation.py

    # With custom images:
    python tests/test_segmentation.py --images path/to/img1.jpg path/to/img2.jpg

    # Adjust confidence threshold:
    python tests/test_segmentation.py --threshold 0.3
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

# Add project root to path so we can import wardrobe
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))


def main():
    parser = argparse.ArgumentParser(
        description="Test the Grounded SAM clothing segmentation pipeline."
    )
    parser.add_argument(
        "--images",
        nargs="+",
        type=str,
        default=None,
        help="Image paths to test. Defaults to training/test_images/*.",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.25,
        help="Detection confidence threshold. Default: 0.25.",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="tests/output",
        help="Output directory. Default: tests/output.",
    )
    parser.add_argument(
        "--device",
        type=str,
        default=None,
        help="Device: 'mps', 'cpu', or None for auto-detect.",
    )
    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
    )

    # Resolve output directory
    output_dir = project_root / args.output
    crops_dir = output_dir / "crops"
    output_dir.mkdir(parents=True, exist_ok=True)
    crops_dir.mkdir(parents=True, exist_ok=True)

    # Find test images
    if args.images:
        image_paths = [Path(p) for p in args.images]
    else:
        test_images_dir = project_root / "tests" / "sample_images"
        if not test_images_dir.exists():
            print(f"Test images directory not found: {test_images_dir}")
            print("Use --images to specify image paths.")
            sys.exit(1)
        image_paths = sorted(
            p for p in test_images_dir.iterdir()
            if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".heic"}
        )

    if not image_paths:
        print("No images found to test.")
        sys.exit(1)

    print("=" * 60)
    print("  Grounded SAM Clothing Segmentation Test")
    print("=" * 60)
    print(f"\n  Images:    {len(image_paths)}")
    print(f"  Threshold: {args.threshold}")
    print(f"  Output:    {output_dir}")
    print(f"  Device:    {args.device or 'auto-detect'}")

    # Load models
    print(f"\n{'=' * 60}")
    print("  Loading models (first run downloads ~750MB of weights)...")
    print(f"{'=' * 60}\n")

    t0 = time.time()

    from wardrobe.segmentation import ClothingSegmenter
    from wardrobe.visualize import visualize_results

    segmenter = ClothingSegmenter(
        box_threshold=args.threshold,
        device=args.device,
    )

    load_time = time.time() - t0
    print(f"\n  Models loaded in {load_time:.1f}s\n")

    # Process each image
    total_items = 0

    for img_path in image_paths:
        print(f"\n{'=' * 60}")
        print(f"  Image: {img_path.name}")
        print(f"{'=' * 60}")

        if not img_path.exists():
            print(f"  [SKIP] File not found: {img_path}")
            continue

        t0 = time.time()
        results = segmenter.segment(str(img_path))
        inference_time = time.time() - t0

        print(f"  Detected {len(results)} item(s) in {inference_time:.1f}s:")

        for j, item in enumerate(results):
            label = item["label"]
            category = item["category"]
            conf = item["confidence"]
            bbox = item["bbox"]
            print(
                f"    {j + 1}. {category} ({label}) "
                f"- confidence: {conf:.2f} "
                f"- bbox: [{bbox[0]:.0f}, {bbox[1]:.0f}, {bbox[2]:.0f}, {bbox[3]:.0f}]"
            )

            # Save cropped item
            stem = img_path.stem
            crop_name = f"{stem}_item{j + 1}_{category}.png"
            crop_path = crops_dir / crop_name
            item["cropped_image"].save(crop_path)
            print(f"       Saved crop: {crop_path.name}")

        total_items += len(results)

        # Save annotated image
        if results:
            annotated = visualize_results(str(img_path), results)
            annotated_path = output_dir / f"annotated_{img_path.stem}.jpg"
            annotated.save(annotated_path, quality=95)
            print(f"  Saved annotated: {annotated_path.name}")

    # Summary
    print(f"\n{'=' * 60}")
    print(f"  Summary")
    print(f"{'=' * 60}")
    print(f"  Images processed: {len(image_paths)}")
    print(f"  Total items found: {total_items}")
    print(f"  Annotated images saved to: {output_dir}")
    print(f"  Cropped items saved to: {crops_dir}")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    main()
