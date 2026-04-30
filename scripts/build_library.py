"""
One-time build of the outfit library cache used by the FAISS-based
suggester.

Reads OUTFIT_FOLDER_URL from .env (a public Google Drive folder of
Pinterest/Instagram outfit photos), downloads every image, runs each
through Grounded SAM + FashionCLIP, and writes the results to
data/library_cache/:

    data/library_cache/
    ├── images/             (raw downloaded photos)
    ├── embeddings.npy      (N, 512) float32, L2-normalized
    └── metadata.json       outfit_id, item_id, category, label, colors

Run:
    python scripts/build_library.py            # build (skip if cache exists)
    python scripts/build_library.py --rebuild  # force re-download + re-embed

Time: ~30-90 minutes depending on corpus size and CPU. SAM is the slow
part. Sit back. Once built, commit the cache so teammates don't have
to rebuild.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Make the project root importable when running from anywhere.
_repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_repo_root))

from wardrobe.outfit_library import build_outfit_library


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the outfit library cache.")
    parser.add_argument(
        "--cache-dir",
        type=str,
        default=str(_repo_root / "data" / "library_cache"),
        help="Where to store images + embeddings (default: data/library_cache).",
    )
    parser.add_argument(
        "--folder-url",
        type=str,
        default=None,
        help="Public Google Drive folder URL. Falls back to OUTFIT_FOLDER_URL in .env.",
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Force re-download and re-embed even if the cache already exists.",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logger = logging.getLogger(__name__)

    logger.info("Building outfit library at %s", args.cache_dir)
    build_outfit_library(
        cache_dir=args.cache_dir,
        folder_url=args.folder_url,
        force_rebuild=args.rebuild,
    )
    logger.info("Done. Restart uvicorn so the FAISS index picks up the new cache.")


if __name__ == "__main__":
    main()
