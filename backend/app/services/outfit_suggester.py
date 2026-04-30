"""
Outfit suggester — FAISS-backed retrieval against the outfit library.

Each user item embedding is queried against a per-category FAISS index
built from FashionCLIP embeddings of the reference corpus (Pinterest /
Instagram outfit photos in `data/library_cache/`). For each library
outfit, we record the user's best item per slot, average the cosine
similarities, and rank.

The frontend's outfit-card contract is `[{top, bottom, score}]`; we add
`inspired_by_outfit_id` and `rationale` (the frontend ignores unknown
fields, so older builds keep working).

Falls back to the previous color-distance pairing if:
- the library cache hasn't been built yet, or
- the user has no items with embeddings (e.g. uploaded before the ML
  pipeline existed), or
- FAISS retrieval returns nothing usable.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np

from app.services.ml_pipeline import (
    get_library_index,
    get_library_outfit_meta,
    library_is_available,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Fallback: color-distance pairing (the original stub)
# ---------------------------------------------------------------------------


def _first_color(item: dict) -> tuple[float, float, float] | None:
    colors = item.get("dominant_colors") or []
    if not colors:
        return None
    c = colors[0]
    return (float(c.get("h", 0)), float(c.get("s", 0)), float(c.get("l", 0)))


def _color_distance(a: dict, b: dict) -> float:
    ca, cb = _first_color(a), _first_color(b)
    if ca is None or cb is None:
        return 1e9
    dh = min(abs(ca[0] - cb[0]), 360 - abs(ca[0] - cb[0]))
    ds = abs(ca[1] - cb[1])
    dl = abs(ca[2] - cb[2])
    return (dh * dh) + (ds * ds) + (dl * dl)


def _color_pairing(items: list[dict], limit: int) -> list[dict[str, Any]]:
    tops = [i for i in items if i.get("category") == "top"]
    bottoms = [i for i in items if i.get("category") == "bottom"]
    pairs: list[tuple[float, dict, dict]] = []
    for t in tops:
        for b in bottoms:
            pairs.append((_color_distance(t, b), t, b))
    pairs.sort(key=lambda p: p[0])
    return [
        {
            "top": _strip(t),
            "bottom": _strip(b),
            "score": round(1.0 / (1.0 + dist / 1000.0), 4),
            "rationale": "Color-coordinated pairing.",
        }
        for dist, t, b in pairs[:limit]
    ]


def _strip(item: dict) -> dict:
    """Drop the embedding before sending the item to the frontend."""
    return {k: v for k, v in item.items() if k != "embedding"}


# ---------------------------------------------------------------------------
# FAISS-based retrieval (the real path)
# ---------------------------------------------------------------------------


def _items_with_embeddings(items: list[dict]) -> list[dict]:
    out = []
    for it in items:
        emb = it.get("embedding")
        if isinstance(emb, np.ndarray) and emb.any():
            out.append(it)
    return out


def suggest_outfits(items: list[dict], limit: int = 12) -> list[dict[str, Any]]:
    if not library_is_available():
        logger.info("Outfit library not built — using color-pairing fallback.")
        return _color_pairing(items, limit)

    embedded = _items_with_embeddings(items)
    if not embedded:
        logger.info("No items have embeddings — using color-pairing fallback.")
        return _color_pairing(items, limit)

    try:
        index = get_library_index()
    except FileNotFoundError:
        logger.info("Outfit library cache missing on disk — using color-pairing fallback.")
        return _color_pairing(items, limit)
    except Exception as exc:
        logger.warning("FAISS index load failed (%s) — using color-pairing fallback.", exc)
        return _color_pairing(items, limit)

    # Reverse-lookup: for each user item, ask FAISS which library outfits
    # it best fills. Aggregate per outfit, picking the user's best item per
    # slot (highest cosine similarity).
    # best_slot[outfit_id][category] = (score, user_item)
    best_slot: dict[str, dict[str, tuple[float, dict]]] = {}

    for user_item in embedded:
        cat = user_item.get("category")
        if cat is None:
            continue
        n = index.total_vectors(cat)
        if n == 0:
            continue
        emb = np.asarray(user_item["embedding"], dtype=np.float32)
        results = index.query_by_category(cat, emb, k=n)
        for outfit_id, _lib_item_id, score in results:
            slot = best_slot.setdefault(outfit_id, {})
            cur = slot.get(cat)
            if cur is None or score > cur[0]:
                slot[cat] = (float(score), user_item)

    # Now build outfit suggestions. For the Outfits.js contract we need
    # each card to have BOTH a top and a bottom drawn from the user's
    # wardrobe — so only consider library outfits where both slots got
    # filled.
    candidates: list[tuple[float, dict, dict, str]] = []
    for outfit_id, slots in best_slot.items():
        if "top" not in slots or "bottom" not in slots:
            continue
        top_score, top_item = slots["top"]
        bot_score, bot_item = slots["bottom"]
        avg = (top_score + bot_score) / 2.0
        candidates.append((avg, top_item, bot_item, outfit_id))

    if not candidates:
        logger.info("FAISS produced no top+bottom pairs — using color-pairing fallback.")
        return _color_pairing(items, limit)

    candidates.sort(key=lambda c: c[0], reverse=True)

    # De-duplicate near-identical pairs (same top+bottom from different
    # reference outfits) — keep the highest-scoring one.
    seen: set[tuple[str, str]] = set()
    suggestions: list[dict[str, Any]] = []
    for score, top_item, bot_item, outfit_id in candidates:
        key = (top_item["id"], bot_item["id"])
        if key in seen:
            continue
        seen.add(key)
        meta = get_library_outfit_meta(outfit_id) or {}
        suggestions.append(
            {
                "top": _strip(top_item),
                "bottom": _strip(bot_item),
                "score": round(score, 4),
                "inspired_by_outfit_id": outfit_id,
                "inspired_by_image": meta.get("image_filename"),
                "rationale": f"Inspired by reference outfit “{outfit_id}” (cosine {score:.2f}).",
            }
        )
        if len(suggestions) >= limit:
            break

    return suggestions
