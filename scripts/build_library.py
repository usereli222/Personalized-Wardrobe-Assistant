"""
Build the FAISS outfit-library cache from images you've already downloaded
locally. Does NOT call gdown / Google Drive — point it at a directory of
outfit photos and it runs SAM + FashionCLIP and writes the cache files
the FastAPI suggester loads at startup:

    data/library_cache/
    ├── images/             your photos (walked recursively)
    ├── embeddings.npy      (N, 512) float32, L2-normalized FashionCLIP vectors
    └── metadata.json       per-item: outfit_id, item_id, category, label, colors

Usage:
    # default — processes data/library_cache/images/
    python scripts/build_library.py

    # source images live somewhere else (script will copy them in)
    python scripts/build_library.py --images-dir ~/Downloads/Wardrobe-Library

    # overwrite an existing cache
    python scripts/build_library.py --rebuild

Time: ~30-90 minutes for ~100 images on CPU. SAM is the slow step.

If a single photo crashes the pipeline (corrupt file, OOM, etc.), the
script logs the failure and keeps going so one bad image doesn't waste
an hour of work.
"""

from __future__ import annotations

import argparse
import json
import logging
import shutil
import sys
from pathlib import Path

import numpy as np


# Make the project root importable when running from anywhere.
_repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_repo_root))


# Categories the FAISS index can store. Anything else (e.g. "unknown") is
# skipped on save. After the wardrobe/config.py vocab unification, "dress"
# already maps to "top" upstream so we don't need to special-case it here.
_VALID_CATEGORIES = {"top", "bottom", "outerwear", "shoes", "accessory"}
_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

_DEFAULT_CACHE = _repo_root / "data" / "library_cache"
_DEFAULT_IMAGES = _DEFAULT_CACHE / "images"


# ---------------------------------------------------------------------------
# JSON encoder for numpy scalars (color extraction returns numpy floats)
# ---------------------------------------------------------------------------


class _NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _collect_images(root: Path) -> list[Path]:
    """Walk `root` recursively and return all image files, sorted."""
    return sorted(
        p for p in root.rglob("*")
        if p.is_file() and p.suffix.lower() in _IMAGE_SUFFIXES
    )


def _stage_images(source: Path, dest: Path, logger: logging.Logger) -> list[Path]:
    """If source != dest, copy source images flat into dest. Returns the
    list of files inside dest after staging. Skips re-copying anything
    already present."""
    if source.resolve() == dest.resolve():
        return _collect_images(dest)

    dest.mkdir(parents=True, exist_ok=True)
    src_files = _collect_images(source)
    if not src_files:
        return []

    logger.info("Staging %d images: %s -> %s", len(src_files), source, dest)
    for p in src_files:
        target = dest / p.name
        if target.exists():
            continue
        shutil.copy2(p, target)
    return _collect_images(dest)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build the outfit library cache from local images."
    )
    parser.add_argument(
        "--images-dir",
        type=str,
        default=str(_DEFAULT_IMAGES),
        help=(
            "Directory of outfit photos to process (recursive). "
            "If different from the default, files are copied flat into "
            "data/library_cache/images/ first so the FastAPI /library "
            "mount can serve them. Default: data/library_cache/images/"
        ),
    )
    parser.add_argument(
        "--cache-dir",
        type=str,
        default=str(_DEFAULT_CACHE),
        help="Where to write embeddings.npy + metadata.json. Default: data/library_cache/",
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Force re-embed even if cache already exists.",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logger = logging.getLogger("build_library")

    cache_dir = Path(args.cache_dir).resolve()
    images_root = cache_dir / "images"
    crops_root = cache_dir / "crops"
    src_dir = Path(args.images_dir).resolve()

    emb_path = cache_dir / "embeddings.npy"
    meta_path = cache_dir / "metadata.json"

    if not args.rebuild and emb_path.exists() and meta_path.exists():
        logger.info(
            "Cache already built at %s — pass --rebuild to overwrite.", cache_dir
        )
        return

    if not src_dir.exists():
        logger.error("Images directory not found: %s", src_dir)
        sys.exit(1)

    # Ensure the canonical images_root exists, then make sure all images
    # the user gave us are there (copying from src_dir if needed).
    images_root.mkdir(parents=True, exist_ok=True)
    image_files = _stage_images(src_dir, images_root, logger)

    if not image_files:
        logger.error("No image files found under %s.", src_dir)
        sys.exit(1)

    # Deduplicate by stem (= outfit_id). If two photos somehow share a
    # filename stem after staging, keep the first and warn.
    by_stem: dict[str, Path] = {}
    dupes: list[Path] = []
    for p in image_files:
        if p.stem in by_stem:
            dupes.append(p)
        else:
            by_stem[p.stem] = p
    if dupes:
        logger.warning(
            "Skipping %d files with duplicate stems (e.g. %s).",
            len(dupes), dupes[0].name,
        )
    image_files = list(by_stem.values())
    logger.info("Processing %d unique images.", len(image_files))

    # Lazy-import so --help is fast and torch/transformers don't load
    # before we actually need them.
    import torch

    from wardrobe.item_processor import WardrobeProcessor

    device = "cuda" if torch.cuda.is_available() else "cpu"
    logger.info(
        "Loading WardrobeProcessor on %s (FashionCLIP + SAM/DINO; "
        "weights download on first run, ~1.5GB)...",
        device,
    )
    if device == "cuda":
        logger.info("  GPU: %s", torch.cuda.get_device_name(0))
    processor = WardrobeProcessor(embedder_device=device)
    logger.info("Models ready. Starting batch...\n")

    all_embeddings: list[np.ndarray] = []
    all_metadata: list[dict] = []
    failures: list[tuple[str, str]] = []

    crops_root.mkdir(parents=True, exist_ok=True)

    for i, img_path in enumerate(image_files, start=1):
        outfit_id = img_path.stem
        logger.info("[%d/%d] %s", i, len(image_files), img_path.name)

        try:
            items = processor.process_wardrobe_photo(img_path)
        except Exception as exc:
            logger.warning("    pipeline failed: %s", exc)
            failures.append((img_path.name, str(exc)))
            continue

        kept = 0
        for idx, item in enumerate(items):
            category = item.get("category", "unknown")
            if category not in _VALID_CATEGORIES:
                continue
            emb = item.get("embedding")
            if emb is None:
                continue

            item_id = f"{outfit_id}_{category}_{idx}"

            # Save the SAM-cropped, alpha-masked region for this item so
            # Find-Similar can show what was actually matched, not the
            # whole outfit photo. RGBA so transparent background renders
            # cleanly in the UI.
            crop_filename = None
            crop = item.get("cropped_image")
            if crop is not None:
                try:
                    crop_filename = f"{item_id}.png"
                    crop.save(crops_root / crop_filename, format="PNG")
                except Exception as exc:
                    logger.warning("    crop save failed (%s): %s", item_id, exc)
                    crop_filename = None

            all_embeddings.append(np.asarray(emb, dtype=np.float32).ravel())
            all_metadata.append({
                "outfit_id": outfit_id,
                "item_id": item_id,
                "category": category,
                "label": item.get("label", "unknown"),
                "dominant_colors": item.get("dominant_colors", {}),
                "crop_filename": crop_filename,
                "bbox": item.get("bbox"),
                "confidence": item.get("confidence"),
            })
            kept += 1
        logger.info("    -> %d items kept", kept)

    if not all_embeddings:
        logger.error("No items were embedded. Cache not written.")
        if failures:
            logger.error("First failure: %s", failures[0])
        sys.exit(1)

    cache_dir.mkdir(parents=True, exist_ok=True)
    np.save(emb_path, np.stack(all_embeddings).astype(np.float32))
    with open(meta_path, "w") as fh:
        json.dump(all_metadata, fh, cls=_NumpyEncoder)

    n_outfits = len({m["outfit_id"] for m in all_metadata})
    by_cat: dict[str, int] = {}
    for m in all_metadata:
        by_cat[m["category"]] = by_cat.get(m["category"], 0) + 1

    logger.info("")
    logger.info("=" * 60)
    logger.info(
        "Done. %d items from %d outfits across %d photos.",
        len(all_embeddings), n_outfits, len(image_files),
    )
    logger.info("Per-category counts: %s", by_cat)
    if failures:
        logger.info("Pipeline failures: %d (see warnings above).", len(failures))
    logger.info("Wrote: %s", emb_path)
    logger.info("Wrote: %s", meta_path)
    logger.info("")
    logger.info("Restart uvicorn so the FAISS index picks up the new cache.")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()