"""Pytest tests for FaissIndexManager and match_wardrobe_to_library."""

import sys
from pathlib import Path

import numpy as np
import pytest

# Make the project root importable when running pytest from anywhere.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from wardrobe.faiss_index import CATEGORIES, EMBEDDING_DIM, FaissIndexManager
from wardrobe.outfit_matcher import OutfitMatch, match_wardrobe_to_library


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_outfit(outfit_id: str, categories: list[str], seed: int | None = None) -> dict:
    rng = np.random.default_rng(seed if seed is not None else abs(hash(outfit_id)) % 2**32)
    return {
        "outfit_id": outfit_id,
        "items": [
            {
                "item_id": f"{outfit_id}_{cat}",
                "category": cat,
                "embedding": rng.standard_normal(EMBEDDING_DIM).astype(np.float32),
                "dominant_colors": {},
            }
            for cat in categories
        ],
    }


def _make_wardrobe_item(item_id: str, category: str, seed: int = 0) -> dict:
    rng = np.random.default_rng(seed)
    return {
        "item_id": item_id,
        "category": category,
        "embedding": rng.standard_normal(EMBEDDING_DIM).astype(np.float32),
    }


# ---------------------------------------------------------------------------
# 1. Build index from 50 synthetic embeddings across 3 categories
# ---------------------------------------------------------------------------

def test_build_populates_indexes():
    cats = ["top", "bottom", "shoes"]
    outfits = [_make_outfit(f"out_{i:03d}", [cats[i % 3]], seed=i) for i in range(50)]

    manager = FaissIndexManager()
    manager.build_from_outfit_library(outfits)

    counts = {cat: manager.total_vectors(cat) for cat in cats}
    # Each category gets roughly 50/3 vectors; at minimum more than zero.
    for cat in cats:
        assert counts[cat] > 0
    # Total across three categories must equal 50 (one item per outfit).
    assert sum(counts.values()) == 50


# ---------------------------------------------------------------------------
# 2. Save / load round-trip
# ---------------------------------------------------------------------------

def test_save_load_roundtrip(tmp_path):
    outfits = [_make_outfit(f"out_{i:02d}", ["top", "bottom"], seed=i) for i in range(10)]
    manager = FaissIndexManager()
    manager.build_from_outfit_library(outfits)

    query_emb = np.random.default_rng(99).standard_normal(EMBEDDING_DIM).astype(np.float32)
    before = manager.query_by_category("top", query_emb, k=5)

    manager.save(str(tmp_path))

    loaded = FaissIndexManager()
    loaded.load(str(tmp_path))
    after = loaded.query_by_category("top", query_emb, k=5)

    assert len(before) == len(after)
    for (oid1, iid1, s1), (oid2, iid2, s2) in zip(before, after):
        assert oid1 == oid2
        assert iid1 == iid2
        assert abs(s1 - s2) < 1e-5


def test_save_load_preserves_outfit_categories(tmp_path):
    outfits = [_make_outfit(f"out_{i:02d}", ["top", "shoes"], seed=i) for i in range(5)]
    manager = FaissIndexManager()
    manager.build_from_outfit_library(outfits)

    manager.save(str(tmp_path))

    loaded = FaissIndexManager()
    loaded.load(str(tmp_path))

    for i in range(5):
        cats = loaded.get_outfit_categories(f"out_{i:02d}")
        assert cats == {"top", "shoes"}


# ---------------------------------------------------------------------------
# 3. Query: correct k results, scores in [-1, 1]
# ---------------------------------------------------------------------------

def test_query_returns_exactly_k():
    outfits = [_make_outfit(f"out_{i:02d}", ["top"], seed=i) for i in range(30)]
    manager = FaissIndexManager()
    manager.build_from_outfit_library(outfits)

    query_emb = np.random.default_rng(7).standard_normal(EMBEDDING_DIM).astype(np.float32)
    results = manager.query_by_category("top", query_emb, k=10)

    assert len(results) == 10


def test_query_scores_in_valid_range():
    outfits = [_make_outfit(f"out_{i:02d}", ["shoes"], seed=i) for i in range(20)]
    manager = FaissIndexManager()
    manager.build_from_outfit_library(outfits)

    query_emb = np.random.default_rng(3).standard_normal(EMBEDDING_DIM).astype(np.float32)
    results = manager.query_by_category("shoes", query_emb, k=20)

    assert len(results) == 20
    for _, _, score in results:
        assert -1.0 - 1e-5 <= score <= 1.0 + 1e-5


def test_query_empty_category_returns_empty():
    manager = FaissIndexManager()
    manager.build_from_outfit_library([])

    query_emb = np.random.default_rng(0).standard_normal(EMBEDDING_DIM).astype(np.float32)
    results = manager.query_by_category("top", query_emb, k=5)

    assert results == []


def test_query_unknown_category_returns_empty():
    outfits = [_make_outfit("out_00", ["top"], seed=0)]
    manager = FaissIndexManager()
    manager.build_from_outfit_library(outfits)

    query_emb = np.random.default_rng(0).standard_normal(EMBEDDING_DIM).astype(np.float32)
    assert manager.query_by_category("dress", query_emb, k=5) == []


# ---------------------------------------------------------------------------
# 4. match_wardrobe_to_library: top_n and diversity penalty
# ---------------------------------------------------------------------------

def test_match_returns_top_n():
    outfits = [_make_outfit(f"out_{i:02d}", ["top", "bottom"], seed=i) for i in range(30)]
    manager = FaissIndexManager()
    manager.build_from_outfit_library(outfits)

    wardrobe = [
        _make_wardrobe_item("my_top", "top", seed=1),
        _make_wardrobe_item("my_bottom", "bottom", seed=2),
    ]
    results = match_wardrobe_to_library(wardrobe, manager, top_n=10)

    assert len(results) == 10
    for r in results:
        assert isinstance(r, OutfitMatch)
        assert isinstance(r.outfit_id, str)
        assert isinstance(r.score, float)
        assert isinstance(r.matched_items, list)


def test_match_scores_sorted_descending():
    outfits = [_make_outfit(f"out_{i:02d}", ["top"], seed=i) for i in range(20)]
    manager = FaissIndexManager()
    manager.build_from_outfit_library(outfits)

    wardrobe = [_make_wardrobe_item("my_top", "top", seed=5)]
    results = match_wardrobe_to_library(wardrobe, manager, top_n=10)

    scores = [r.score for r in results]
    assert scores == sorted(scores, reverse=True)


def test_diversity_penalty_fires():
    # All outfits share the same "top" embedding, so every user query returns
    # cosine similarity 1.0 for all outfits.  With a single user item,
    # appearances 1-3 incur no penalty; appearances 4+ each cost -0.1.
    fixed_emb = np.ones(EMBEDDING_DIM, dtype=np.float32)

    outfits = [
        {
            "outfit_id": f"out_{i:02d}",
            "items": [
                {
                    "item_id": f"out_{i:02d}_top",
                    "category": "top",
                    "embedding": fixed_emb.copy(),
                    "dominant_colors": {},
                }
            ],
        }
        for i in range(10)
    ]
    manager = FaissIndexManager()
    manager.build_from_outfit_library(outfits)

    wardrobe = [{"item_id": "single_top", "category": "top", "embedding": fixed_emb.copy()}]
    results = match_wardrobe_to_library(wardrobe, manager, top_n=10)

    scores = [r.score for r in results]
    # First 3 appearances: raw score 1.0, no penalty.
    # Appearances 4-10: raw score 1.0 - 0.1 penalty = 0.9.
    high = [s for s in scores if s > 0.95]
    low = [s for s in scores if s < 0.95]

    assert len(high) == 3, f"Expected 3 un-penalized outfits, got {len(high)}: {scores}"
    assert len(low) == 7, f"Expected 7 penalized outfits, got {len(low)}: {scores}"
    assert all(abs(s - 1.0) < 1e-5 for s in high)
    assert all(abs(s - 0.9) < 1e-5 for s in low)


# ---------------------------------------------------------------------------
# 5. Edge case: user wardrobe missing a required category
# ---------------------------------------------------------------------------

def test_missing_category_slot_scores_zero():
    # Use the same unit vector for both the library top and the user top so the
    # cosine similarity is exactly 1.0 and the expected score is deterministic.
    lib_top_emb = np.ones(EMBEDDING_DIM, dtype=np.float32)

    outfit = {
        "outfit_id": "full_look",
        "items": [
            {
                "item_id": "lib_top",
                "category": "top",
                "embedding": lib_top_emb.copy(),
                "dominant_colors": {},
            },
            {
                "item_id": "lib_bottom",
                "category": "bottom",
                "embedding": np.random.default_rng(11).standard_normal(EMBEDDING_DIM).astype(np.float32),
                "dominant_colors": {},
            },
            {
                "item_id": "lib_shoes",
                "category": "shoes",
                "embedding": np.random.default_rng(12).standard_normal(EMBEDDING_DIM).astype(np.float32),
                "dominant_colors": {},
            },
        ],
    }
    manager = FaissIndexManager()
    manager.build_from_outfit_library([outfit])

    # User only has a top (same embedding → cosine sim = 1.0).
    # Bottom and shoes slots are missing.
    wardrobe = [{"item_id": "user_top", "category": "top", "embedding": lib_top_emb.copy()}]
    results = match_wardrobe_to_library(wardrobe, manager, top_n=5)

    assert len(results) == 1
    r = results[0]
    assert r.outfit_id == "full_look"

    missing = [m for m in r.matched_items if m["user_item_id"] is None]
    assert len(missing) == 2
    assert all(m["similarity"] == 0.0 for m in missing)

    # Score = (1.0 + 0.0 + 0.0) / 3 ≈ 0.333
    assert r.score > 0.0
    assert abs(r.score - 1.0 / 3) < 1e-5


def test_missing_category_outfit_still_appears_in_results():
    # Ensures outfits with partial matches are not dropped entirely.
    outfits = [_make_outfit(f"out_{i:02d}", ["top", "bottom", "shoes"], seed=i) for i in range(5)]
    manager = FaissIndexManager()
    manager.build_from_outfit_library(outfits)

    # User only has tops.
    wardrobe = [_make_wardrobe_item(f"top_{i}", "top", seed=i) for i in range(3)]
    results = match_wardrobe_to_library(wardrobe, manager, top_n=10)

    assert len(results) == 5
    for r in results:
        # Each outfit has 3 slots; bottom and shoes are always missing.
        missing = [m for m in r.matched_items if m["user_item_id"] is None]
        assert len(missing) == 2
