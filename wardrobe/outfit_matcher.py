"""FAISS-based wardrobe-to-outfit-library matching.

Note: backend/app/services/outfit_matcher.py is a separate color-based matcher
used by the FastAPI layer. This module handles embedding-similarity matching
against the Polyvore outfit library using the FaissIndexManager.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

import numpy as np

from wardrobe.faiss_index import FaissIndexManager


@dataclass
class OutfitMatch:
    outfit_id: str
    score: float
    matched_items: list[dict] = field(default_factory=list)


def match_wardrobe_to_library(
    user_wardrobe: list[dict],
    faiss_manager: FaissIndexManager,
    top_n: int = 10,
) -> list[OutfitMatch]:
    """Score every outfit in the library against the user's wardrobe.

    Uses FAISS reverse lookup: for each user item, query its category index
    to discover which outfit slots it best fills, then aggregate per outfit.

    Missing category slots (outfit requires a category the user has no item for)
    contribute 0.0 to the average score. A diversity penalty of 0.1 is applied
    for each user item that appears as a best match in more than 3 outfits
    (per additional appearance beyond 3, applied in rank order).

    Args:
        user_wardrobe: Wardrobe item dicts, each requiring at minimum
            "category" (str) and "embedding" (np.ndarray shape (512,)).
            An optional "item_id" key is used for diversity tracking;
            falls back to "wardrobe_{index}" when absent.
        faiss_manager: Pre-built FaissIndexManager.
        top_n: Number of results to return.

    Returns:
        List of OutfitMatch dataclasses sorted by score descending.
    """
    # best_slot[outfit_id][category] = (cosine_score, user_item_id)
    best_slot: dict[str, dict[str, tuple[float, str]]] = defaultdict(dict)

    for i, user_item in enumerate(user_wardrobe):
        category: str | None = user_item.get("category")
        raw_emb = user_item.get("embedding")
        if category is None or raw_emb is None:
            continue

        user_item_id = str(user_item.get("item_id", f"wardrobe_{i}"))

        # Query all indexed vectors in this category so the reverse-lookup
        # covers every outfit, not just the nearest k.
        k = faiss_manager.total_vectors(category)
        if k == 0:
            continue

        emb = np.array(raw_emb, dtype=np.float32)
        results = faiss_manager.query_by_category(category, emb, k=k)

        for outfit_id, _lib_item_id, score in results:
            current = best_slot[outfit_id].get(category)
            if current is None or score > current[0]:
                best_slot[outfit_id][category] = (score, user_item_id)

    # Build OutfitMatch objects, scoring by average per-slot similarity.
    candidates: list[OutfitMatch] = []
    for outfit_id, slot_scores in best_slot.items():
        required_cats = faiss_manager.get_outfit_categories(outfit_id)
        if not required_cats:
            continue

        total = 0.0
        matched_items: list[dict] = []

        for cat in required_cats:
            if cat in slot_scores:
                score, uid = slot_scores[cat]
                total += score
                matched_items.append(
                    {"outfit_slot_category": cat, "user_item_id": uid, "similarity": score}
                )
            else:
                matched_items.append(
                    {"outfit_slot_category": cat, "user_item_id": None, "similarity": 0.0}
                )

        candidates.append(
            OutfitMatch(
                outfit_id=outfit_id,
                score=total / len(required_cats),
                matched_items=matched_items,
            )
        )

    candidates.sort(key=lambda x: x.score, reverse=True)

    # Diversity penalty: penalise re-use of the same user item beyond 3 outfits.
    # Process candidates in rank order so the highest-scoring outfits "consume"
    # the first 3 free appearances.
    item_counts: dict[str, int] = defaultdict(int)
    penalized: list[OutfitMatch] = []

    for match in candidates:
        penalty = 0.0
        for m in match.matched_items:
            uid = m["user_item_id"]
            if uid is not None:
                item_counts[uid] += 1
                if item_counts[uid] > 3:
                    penalty += 0.1

        penalized.append(
            OutfitMatch(
                outfit_id=match.outfit_id,
                score=match.score - penalty,
                matched_items=match.matched_items,
            )
        )

    penalized.sort(key=lambda x: x.score, reverse=True)
    return penalized[:top_n]
