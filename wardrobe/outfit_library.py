"""Build and load the outfit library from a public Google Drive folder.

The folder link goes in .env at the project root:
    OUTFIT_FOLDER_URL=https://drive.google.com/drive/folders/YOUR_FOLDER_ID

Both the outfit library (Drive images) and user wardrobe (uploaded photos) run
through the same WardrobeProcessor pipeline:
    image → Grounded SAM (segment items) → FashionCLIP (embed each item)

build_outfit_library() is a one-time (or on-demand) operation. It downloads
every image in the Drive folder, runs the pipeline, and caches the results
locally. load_outfit_library() then reads that cache — no Drive access needed
at inference time.
"""

import json
import logging
import os
from collections import defaultdict
from pathlib import Path

import numpy as np
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


# ---------------------------------------------------------------------------
# JSON serialization helper — dominant_colors contains numpy scalar types
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
# Public API
# ---------------------------------------------------------------------------

def build_outfit_library(
    cache_dir: str,
    folder_url: str | None = None,
    processor=None,
    force_rebuild: bool = False,
) -> None:
    """Download outfit images from a public Google Drive folder and cache embeddings.

    Each image in the folder is treated as one outfit. Grounded SAM detects the
    clothing items inside it; FashionCLIP embeds each one. This is the same
    WardrobeProcessor pipeline used for user-uploaded wardrobe photos.

    Args:
        cache_dir: Local directory to store downloaded images and computed embeddings.
        folder_url: Public Google Drive folder URL. Reads OUTFIT_FOLDER_URL from
            .env if not passed explicitly.
        processor: WardrobeProcessor instance. Created with CPU defaults if None.
        force_rebuild: Re-download and re-process even if the cache already exists.
    """
    cache = Path(cache_dir)
    images_dir = cache / "images"
    emb_path = cache / "embeddings.npy"
    meta_path = cache / "metadata.json"

    if not force_rebuild and emb_path.exists() and meta_path.exists():
        logger.info(
            "Outfit library cache found at '%s' — skipping build. "
            "Pass force_rebuild=True to reprocess.",
            cache,
        )
        return

    url = folder_url or os.environ.get("OUTFIT_FOLDER_URL")
    if not url:
        raise ValueError(
            "No folder URL provided. Either pass folder_url= or set "
            "OUTFIT_FOLDER_URL in your .env file."
        )

    # --- Download images from the public Drive folder ---
    images_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Downloading outfit images from Google Drive...")

    import gdown
    gdown.download_folder(url=url, output=str(images_dir), quiet=False, use_cookies=False)

    image_files = [p for p in images_dir.iterdir() if p.suffix.lower() in _IMAGE_SUFFIXES]
    if not image_files:
        logger.error("No images found after download — check that the Drive folder URL is correct and public.")
        return

    logger.info("Downloaded %d images — running SAM + FashionCLIP pipeline...", len(image_files))

    # --- Process each image with the same pipeline as user wardrobe photos ---
    if processor is None:
        from wardrobe.item_processor import WardrobeProcessor
        processor = WardrobeProcessor()

    all_embeddings: list[np.ndarray] = []
    all_metadata: list[dict] = []

    for img_path in sorted(image_files):
        outfit_id = img_path.stem  # filename without extension becomes the outfit ID
        logger.info("  [%s] segmenting + embedding...", outfit_id)

        try:
            # process_wardrobe_photo accepts a file path directly
            items = processor.process_wardrobe_photo(img_path)
        except Exception as exc:
            logger.warning("  [%s] failed: %s", outfit_id, exc)
            continue

        if not items:
            logger.warning("  [%s] no clothing items detected — skipping", outfit_id)
            continue

        for idx, item in enumerate(items):
            category = item.get("category", "unknown")
            if category == "unknown":
                continue  # SAM detected something but couldn't map it to a category

            all_embeddings.append(item["embedding"])  # (512,) float32, L2-normalized
            all_metadata.append({
                "outfit_id": outfit_id,
                "item_id": f"{outfit_id}_{category}_{idx}",
                "category": category,
                "label": item.get("label", "unknown"),
                "dominant_colors": item.get("dominant_colors", {}),
            })

        logger.info("  [%s] → %d items kept", outfit_id, sum(1 for m in all_metadata if m["outfit_id"] == outfit_id))

    if not all_embeddings:
        logger.error("No items were successfully embedded. Cache not written.")
        return

    np.save(emb_path, np.stack(all_embeddings).astype(np.float32))
    with open(meta_path, "w") as fh:
        json.dump(all_metadata, fh, cls=_NumpyEncoder)

    n_outfits = len({m["outfit_id"] for m in all_metadata})
    logger.info(
        "Saved %d item embeddings from %d outfits → %s",
        len(all_embeddings), n_outfits, cache,
    )


def load_outfit_library(cache_dir: str) -> list[dict]:
    """Load the pre-computed outfit library from local cache.

    Returns the list[dict] format consumed by FaissIndexManager.build_from_outfit_library().

    Each entry:
        outfit_id (str)
        items (list of dicts):
            item_id         (str)
            category        (str)   — top / bottom / outerwear / shoes / accessory
            embedding       (np.ndarray shape (512,) float32, L2-normalized by FashionCLIP)
            dominant_colors (dict)
    """
    cache = Path(cache_dir)
    emb_path = cache / "embeddings.npy"
    meta_path = cache / "metadata.json"

    if not emb_path.exists() or not meta_path.exists():
        raise FileNotFoundError(
            f"Outfit library cache not found at '{cache_dir}'. "
            "Run build_outfit_library() first."
        )

    embeddings: np.ndarray = np.load(emb_path)   # (N, 512) float32
    with open(meta_path) as fh:
        metadata: list[dict] = json.load(fh)

    if len(embeddings) != len(metadata):
        raise ValueError(
            f"Cache corrupt: {len(embeddings)} embeddings vs {len(metadata)} metadata rows."
        )

    outfits: dict[str, list[dict]] = defaultdict(list)
    for i, meta in enumerate(metadata):
        outfits[meta["outfit_id"]].append({
            "item_id": meta["item_id"],
            "category": meta["category"],
            "embedding": embeddings[i].astype(np.float32),
            "dominant_colors": meta.get("dominant_colors", {}),
        })

    return [{"outfit_id": oid, "items": items} for oid, items in outfits.items()]
