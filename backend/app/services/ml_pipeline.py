"""
Lazy singletons that bridge the FastAPI app to the wardrobe/ ML pipeline.

The ML models (FashionCLIP, Grounded SAM, FAISS index over the outfit library)
live in process memory. They are large (~1.5 GB resident on CPU) and slow to
load (~15-30s combined), so we instantiate them on first use and cache the
instances at module level.

Hit POST /api/health/warm at server startup to trigger the cold-start
deliberately instead of blocking the first user request.

Concurrency: a threading.Lock guards each lazy-init so two simultaneous
requests don't load the same model twice. Once loaded, all calls are
read-only forwards to the underlying object, which is itself thread-safe
for inference (PyTorch eval mode + FAISS search).
"""

from __future__ import annotations

import logging
import sys
import threading
from pathlib import Path

logger = logging.getLogger(__name__)

# The wardrobe/ ML package lives at the repo root, not under backend/.
# Add the repo root to sys.path so `import wardrobe.*` works whether
# uvicorn is launched from backend/ or from the repo root.
_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# ---------------------------------------------------------------------------
# Module-level state
# ---------------------------------------------------------------------------

_processor = None  # WardrobeProcessor (FashionCLIP + lazy SAM)
_library_index = None  # FaissIndexManager built from the outfit library cache
_library_meta_by_outfit: dict[str, dict] | None = None  # outfit_id -> first item meta (for thumbnails)
_library_meta_by_item: dict[str, dict] | None = None    # item_id -> per-item metadata (label, category)

_proc_lock = threading.Lock()
_index_lock = threading.Lock()

# Cache directory for the outfit library (built by scripts/build_library.py).
# Resolved relative to the repo root so it works from either backend/ or root cwd.
_LIBRARY_CACHE_DIR = Path(__file__).resolve().parents[3] / "data" / "library_cache"


# ---------------------------------------------------------------------------
# Public accessors
# ---------------------------------------------------------------------------


def _detect_device() -> str:
    """Return 'cuda' if a GPU is available and torch was built with CUDA,
    else 'cpu'. Computed lazily so importing this module doesn't load torch."""
    try:
        import torch

        return "cuda" if torch.cuda.is_available() else "cpu"
    except Exception:
        return "cpu"


def get_processor():
    """Return a singleton WardrobeProcessor (loads FashionCLIP on first call)."""
    global _processor
    if _processor is not None:
        return _processor
    with _proc_lock:
        if _processor is None:
            from wardrobe.item_processor import WardrobeProcessor

            device = _detect_device()
            logger.info(
                "Loading FashionCLIP on %s (first request) — "
                "~5-10s on CPU, ~1-2s on GPU.",
                device,
            )
            _processor = WardrobeProcessor(embedder_device=device)
            logger.info("FashionCLIP loaded on %s.", device)
    return _processor


def get_library_index():
    """Return a singleton FaissIndexManager built from the outfit library cache.

    Raises FileNotFoundError if the cache hasn't been built. The outfits
    router catches this and falls back to a degraded suggester, so the app
    keeps working even before the library is built.
    """
    global _library_index, _library_meta_by_outfit, _library_meta_by_item
    if _library_index is not None:
        return _library_index
    with _index_lock:
        if _library_index is None:
            from wardrobe.faiss_index import FaissIndexManager
            from wardrobe.outfit_library import load_outfit_library

            logger.info("Loading outfit library cache from %s", _LIBRARY_CACHE_DIR)
            outfits = load_outfit_library(str(_LIBRARY_CACHE_DIR))
            idx = FaissIndexManager()
            idx.build_from_outfit_library(outfits)
            _library_index = idx

            # Stash a representative source path per outfit so the API can
            # hand the frontend a real /library/<path> URL. Outfit IDs drop
            # the extension at build time (img_path.stem), so look up the
            # matching file in cache/images/ now. Walk recursively in case
            # the build was run with files nested in subdirectories;
            # paths are stored as POSIX so they work as URL segments on
            # Windows too.
            images_dir = _LIBRARY_CACHE_DIR / "images"
            stem_to_name: dict[str, str] = {}
            if images_dir.exists():
                for p in images_dir.rglob("*"):
                    if p.is_file():
                        stem_to_name.setdefault(p.stem, p.relative_to(images_dir).as_posix())

            # Per-item metadata (crop_filename, bbox, confidence) lives in
            # metadata.json — load_outfit_library doesn't currently surface
            # these extra fields, so re-read the JSON for them.
            import json as _json
            raw_metadata: list[dict] = []
            try:
                with open(_LIBRARY_CACHE_DIR / "metadata.json") as fh:
                    raw_metadata = _json.load(fh)
            except Exception:
                raw_metadata = []
            extra_by_item = {m["item_id"]: m for m in raw_metadata if "item_id" in m}

            meta: dict[str, dict] = {}
            item_meta: dict[str, dict] = {}
            for o in outfits:
                oid = o["outfit_id"]
                if o["items"]:
                    meta[oid] = {
                        "outfit_id": oid,
                        "image_filename": stem_to_name.get(oid),
                    }
                for it in o["items"]:
                    extra = extra_by_item.get(it["item_id"], {})
                    item_meta[it["item_id"]] = {
                        "outfit_id": oid,
                        "category": it.get("category"),
                        "label": it.get("label"),
                        "image_filename": stem_to_name.get(oid),
                        "crop_filename": extra.get("crop_filename"),
                        "bbox": extra.get("bbox"),
                        "confidence": extra.get("confidence"),
                    }
            _library_meta_by_outfit = meta
            _library_meta_by_item = item_meta

            n_items = sum(idx.total_vectors(c) for c in ("top", "bottom", "outerwear", "shoes", "accessory"))
            logger.info(
                "Outfit library loaded — %d outfits, %d indexed items.",
                len(outfits),
                n_items,
            )
    return _library_index


def get_library_outfit_meta(outfit_id: str) -> dict | None:
    """Return the cached metadata for one library outfit, if loaded."""
    if _library_meta_by_outfit is None:
        return None
    return _library_meta_by_outfit.get(outfit_id)


def get_library_item_meta(item_id: str) -> dict | None:
    """Return the cached metadata for one library item (used by /similar)."""
    if _library_meta_by_item is None:
        return None
    return _library_meta_by_item.get(item_id)


def library_is_available() -> bool:
    """Return True if the outfit-library cache files exist on disk."""
    return (
        (_LIBRARY_CACHE_DIR / "embeddings.npy").exists()
        and (_LIBRARY_CACHE_DIR / "metadata.json").exists()
    )


def warm() -> dict:
    """Force-load every model. Call this from /api/health/warm at startup
    so the first user request isn't the one that pays the cold-start cost."""
    status = {"processor": False, "library_index": False, "library_available": library_is_available()}
    try:
        get_processor()
        status["processor"] = True
    except Exception as exc:
        logger.warning("Processor warm failed: %s", exc)
        status["processor_error"] = str(exc)

    if status["library_available"]:
        try:
            get_library_index()
            status["library_index"] = True
        except Exception as exc:
            logger.warning("Library index warm failed: %s", exc)
            status["library_index_error"] = str(exc)
    return status