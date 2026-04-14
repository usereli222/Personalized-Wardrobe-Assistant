#!/usr/bin/env python3
from __future__ import annotations

"""
Sample a balanced subset of the converted DeepFashion2 YOLO dataset.

Reads all label files to determine per-image class distribution, then samples
a balanced subset so underrepresented classes aren't drowned out.

Usage:
    python sample_subset.py \
        --input-dir ../data/deepfashion2_yolo \
        --train-size 15000 \
        --val-size 2000 \
        --seed 42
"""

import argparse
import random
import shutil
from collections import defaultdict
from pathlib import Path

from tqdm import tqdm


CLASS_NAMES = {
    0: "top",
    1: "outerwear",
    2: "shorts",
    3: "trousers",
    4: "skirt",
    5: "dress",
}


def index_labels(labels_dir: Path) -> dict[str, set[int]]:
    """
    Index all label files and return a mapping of filename stem → set of class IDs.

    Example: {"000001": {0, 3}, "000002": {5}}
    """
    index = {}
    label_files = sorted(labels_dir.glob("*.txt"))

    for label_path in tqdm(label_files, desc="Indexing labels", unit="file"):
        classes = set()
        with open(label_path, "r") as f:
            for line in f:
                parts = line.strip().split()
                if parts:
                    try:
                        classes.add(int(parts[0]))
                    except ValueError:
                        continue
        if classes:
            index[label_path.stem] = classes

    return index


def build_class_buckets(index: dict[str, set[int]]) -> dict[int, set[str]]:
    """
    Build a mapping of class_id → set of image stems that contain that class.
    """
    buckets = defaultdict(set)
    for stem, classes in index.items():
        for cls in classes:
            buckets[cls].add(stem)
    return dict(buckets)


def sample_balanced(
    index: dict[str, set[int]],
    target_size: int,
    seed: int = 42,
) -> set[str]:
    """
    Sample a roughly balanced subset of images.

    Strategy:
    1. For each class, calculate how many images we'd ideally want:
       target_per_class = target_size / num_classes
    2. Start with the rarest classes first (so they don't get starved)
    3. For each class, sample images that haven't been selected yet
    4. An image selected for one class counts toward all its classes
    5. If we haven't reached target_size after one round, fill remaining
       slots randomly from unselected images
    """
    rng = random.Random(seed)
    num_classes = len(CLASS_NAMES)
    target_per_class = target_size / num_classes

    # Build class buckets
    buckets = build_class_buckets(index)

    # Sort classes by frequency (rarest first)
    class_counts = {cls: len(stems) for cls, stems in buckets.items()}
    sorted_classes = sorted(class_counts, key=lambda c: class_counts[c])

    selected = set()
    per_class_selected = defaultdict(int)

    # Round 1: Sample proportionally, rarest classes first
    for cls in sorted_classes:
        available = buckets[cls] - selected
        needed = int(target_per_class) - per_class_selected[cls]

        if needed <= 0 or not available:
            continue

        to_sample = min(needed, len(available))
        newly_selected = set(rng.sample(sorted(available), to_sample))
        selected.update(newly_selected)

        # Update per-class counts for all classes these images belong to
        for stem in newly_selected:
            for c in index[stem]:
                per_class_selected[c] += 1

    # Round 2: Fill remaining slots if needed
    if len(selected) < target_size:
        all_stems = set(index.keys())
        remaining = all_stems - selected
        needed = target_size - len(selected)
        if remaining:
            fill = set(rng.sample(sorted(remaining), min(needed, len(remaining))))
            selected.update(fill)

    # Trim if we overshot
    if len(selected) > target_size:
        selected = set(rng.sample(sorted(selected), target_size))

    return selected


def compute_class_distribution(
    index: dict[str, set[int]],
    stems: set[str],
) -> dict[int, int]:
    """Count how many images in `stems` contain each class."""
    counts = defaultdict(int)
    for stem in stems:
        if stem in index:
            for cls in index[stem]:
                counts[cls] += 1
    return dict(counts)


def print_distribution(
    dist: dict[int, int],
    title: str,
    total_images: int,
) -> None:
    """Print a formatted class distribution table."""
    print(f"\n  {title} ({total_images:,} images)")
    print(f"  {'Class':<12s}  {'Count':>7s}  {'%':>6s}  {'Bar'}")
    print(f"  {'─' * 50}")
    max_count = max(dist.values()) if dist else 1
    for cls_id in sorted(CLASS_NAMES.keys()):
        count = dist.get(cls_id, 0)
        pct = (count / total_images * 100) if total_images > 0 else 0
        bar_len = int(count / max_count * 30) if max_count > 0 else 0
        bar = "█" * bar_len
        print(f"  {CLASS_NAMES[cls_id]:<12s}  {count:>7,}  {pct:>5.1f}%  {bar}")


def copy_subset(
    input_dir: Path,
    split: str,
    selected_stems: set[str],
) -> None:
    """
    Copy selected images and labels within the same YOLO directory,
    removing non-selected files.

    Since we're modifying in-place, we delete files that aren't in the subset.
    """
    images_dir = input_dir / split / "images"
    labels_dir = input_dir / split / "labels"

    # Find all existing files
    all_image_files = {f.stem: f for f in images_dir.iterdir() if f.is_file() or f.is_symlink()}
    all_label_files = {f.stem: f for f in labels_dir.iterdir() if f.suffix == ".txt"}

    # Delete non-selected files
    removed_images = 0
    removed_labels = 0

    for stem, img_path in tqdm(all_image_files.items(), desc=f"Filtering {split} images", unit="file"):
        if stem not in selected_stems:
            img_path.unlink()
            removed_images += 1

    for stem, lbl_path in tqdm(all_label_files.items(), desc=f"Filtering {split} labels", unit="file"):
        if stem not in selected_stems:
            lbl_path.unlink()
            removed_labels += 1

    kept = len(all_image_files) - removed_images
    print(f"  {split}: kept {kept:,} / {len(all_image_files):,} images (removed {removed_images:,})")


def copy_subset_to_new_dir(
    input_dir: Path,
    output_dir: Path,
    split: str,
    selected_stems: set[str],
) -> None:
    """
    Copy selected images and labels to a new output directory.
    """
    src_images = input_dir / split / "images"
    src_labels = input_dir / split / "labels"
    dst_images = output_dir / split / "images"
    dst_labels = output_dir / split / "labels"

    dst_images.mkdir(parents=True, exist_ok=True)
    dst_labels.mkdir(parents=True, exist_ok=True)

    copied = 0
    for stem in tqdm(sorted(selected_stems), desc=f"Copying {split}", unit="file"):
        # Copy/symlink image
        for ext in [".jpg", ".jpeg", ".png"]:
            src_img = src_images / f"{stem}{ext}"
            if src_img.exists() or src_img.is_symlink():
                dst_img = dst_images / f"{stem}{ext}"
                if not dst_img.exists():
                    # Resolve symlinks to get the actual file, then symlink to that
                    real_path = src_img.resolve()
                    dst_img.symlink_to(real_path)
                break

        # Copy label
        src_lbl = src_labels / f"{stem}.txt"
        dst_lbl = dst_labels / f"{stem}.txt"
        if src_lbl.exists() and not dst_lbl.exists():
            shutil.copy2(src_lbl, dst_lbl)
            copied += 1

    print(f"  {split}: copied {copied:,} image-label pairs to {output_dir / split}")


def main():
    parser = argparse.ArgumentParser(
        description="Sample a balanced subset of the YOLO-converted DeepFashion2 dataset.",
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        required=True,
        help="Path to the full YOLO dataset directory (e.g., deepfashion2_yolo/).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Path to output the sampled subset. If not specified, modifies input in-place (destructive!).",
    )
    parser.add_argument(
        "--train-size",
        type=int,
        default=15000,
        help="Target number of training images. Default: 15000.",
    )
    parser.add_argument(
        "--val-size",
        type=int,
        default=2000,
        help="Target number of validation images. Default: 2000.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility. Default: 42.",
    )

    args = parser.parse_args()

    print(f"Input directory:  {args.input_dir}")
    print(f"Output directory: {args.output_dir or 'IN-PLACE (will delete non-selected files!)'}")
    print(f"Train target:     {args.train_size:,}")
    print(f"Val target:       {args.val_size:,}")
    print(f"Seed:             {args.seed}")

    splits = {
        "train": args.train_size,
        "val": args.val_size,
    }

    for split, target_size in splits.items():
        labels_dir = args.input_dir / split / "labels"
        if not labels_dir.exists():
            print(f"\nWarning: {labels_dir} not found, skipping {split}")
            continue

        print(f"\n{'=' * 60}")
        print(f"  Processing {split} split")
        print(f"{'=' * 60}")

        # Index all labels
        index = index_labels(labels_dir)
        print(f"  Indexed {len(index):,} images")

        # Print original distribution
        orig_dist = compute_class_distribution(index, set(index.keys()))
        print_distribution(orig_dist, "Original distribution", len(index))

        # Sample balanced subset
        selected = sample_balanced(index, target_size, seed=args.seed)
        print(f"\n  Selected {len(selected):,} images (target: {target_size:,})")

        # Print sampled distribution
        sampled_dist = compute_class_distribution(index, selected)
        print_distribution(sampled_dist, "Sampled distribution", len(selected))

        # Copy or filter
        if args.output_dir:
            copy_subset_to_new_dir(args.input_dir, args.output_dir, split, selected)
        else:
            # In-place mode
            confirm = input(f"\n  WARNING: This will delete {len(index) - len(selected):,} files from {split}/. Continue? [y/N] ")
            if confirm.lower() != "y":
                print("  Skipped.")
                continue
            copy_subset(args.input_dir, split, selected)

    # Copy dataset.yaml to output dir if applicable
    if args.output_dir:
        src_yaml = args.input_dir / "dataset.yaml"
        dst_yaml = args.output_dir / "dataset.yaml"
        if src_yaml.exists() and not dst_yaml.exists():
            shutil.copy2(src_yaml, dst_yaml)
            print(f"\nCopied dataset.yaml to {args.output_dir}")

    print("\nDone!")


if __name__ == "__main__":
    main()
