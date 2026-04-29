"""FAISS-based per-category index for the outfit library."""

import pickle
from pathlib import Path

import faiss
import numpy as np

# FashionCLIP (patrickjohncyh/fashion-clip) produces 512-dim float32 embeddings
# that are already L2-normalized by ClothingEmbedder.embed() before they arrive here.
# The normalization steps below are therefore no-ops for pipeline inputs but act as
# a safety guard if embeddings from other sources are ever passed in.
EMBEDDING_DIM = 512
CATEGORIES = ("top", "bottom", "outerwear", "shoes", "accessory")


class FaissIndexManager:
    """
    Maintains one FAISS IndexFlatIP per clothing category.

    All embeddings are L2-normalized on insertion and at query time,
    making inner product equivalent to cosine similarity.
    """

    def __init__(self) -> None:
        self._indexes: dict[str, faiss.IndexFlatIP] = {}
        self._id_maps: dict[str, list[tuple[str, str]]] = {}
        # outfit_id -> set of categories that outfit requires
        self._outfit_categories: dict[str, set[str]] = {}

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def build_from_outfit_library(self, outfits: list[dict]) -> None:
        """Build all category indexes from the outfit library.

        Each vector is L2-normalized before insertion so that IndexFlatIP
        inner products equal cosine similarities.
        """
        self._indexes = {cat: faiss.IndexFlatIP(EMBEDDING_DIM) for cat in CATEGORIES}
        self._id_maps = {cat: [] for cat in CATEGORIES}
        self._outfit_categories = {}

        for outfit in outfits:
            outfit_id: str = outfit["outfit_id"]

            for item in outfit["items"]:
                cat: str = item["category"]
                if cat not in self._indexes:
                    continue

                emb = np.array(item["embedding"], dtype=np.float32).ravel()
                norm = np.linalg.norm(emb)
                if norm > 0:
                    emb = emb / norm
                self._indexes[cat].add(emb.reshape(1, EMBEDDING_DIM))
                self._id_maps[cat].append((outfit_id, item["item_id"]))

                self._outfit_categories.setdefault(outfit_id, set()).add(cat)

    # ------------------------------------------------------------------
    # Persist
    # ------------------------------------------------------------------

    def save(self, path: str) -> None:
        """Save all indexes and ID maps to disk (one subdirectory per category)."""
        base = Path(path)
        base.mkdir(parents=True, exist_ok=True)

        for cat in CATEGORIES:
            if cat not in self._indexes:
                continue
            cat_dir = base / cat
            cat_dir.mkdir(exist_ok=True)
            faiss.write_index(self._indexes[cat], str(cat_dir / "index.faiss"))
            with open(cat_dir / "id_map.pkl", "wb") as fh:
                pickle.dump(self._id_maps[cat], fh)

        with open(base / "outfit_categories.pkl", "wb") as fh:
            pickle.dump(self._outfit_categories, fh)

    def load(self, path: str) -> None:
        """Load indexes and ID maps from disk."""
        base = Path(path)
        self._indexes = {}
        self._id_maps = {}

        for cat in CATEGORIES:
            cat_dir = base / cat
            if not (cat_dir / "index.faiss").exists():
                continue
            self._indexes[cat] = faiss.read_index(str(cat_dir / "index.faiss"))
            with open(cat_dir / "id_map.pkl", "rb") as fh:
                self._id_maps[cat] = pickle.load(fh)

        outfit_cats_path = base / "outfit_categories.pkl"
        if outfit_cats_path.exists():
            with open(outfit_cats_path, "rb") as fh:
                self._outfit_categories = pickle.load(fh)
        else:
            self._outfit_categories = {}

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def query_by_category(
        self,
        category: str,
        embedding: np.ndarray,
        k: int = 10,
    ) -> list[tuple[str, str, float]]:
        """Find the k nearest library items for a given category embedding.

        The query embedding is L2-normalized before searching.

        Returns:
            List of (outfit_id, item_id, cosine_similarity) tuples sorted by
            similarity descending. Returns fewer than k entries when the index
            contains fewer than k vectors.
        """
        if category not in self._indexes:
            return []
        index = self._indexes[category]
        if index.ntotal == 0:
            return []

        emb = np.array(embedding, dtype=np.float32).ravel()
        norm = np.linalg.norm(emb)
        if norm > 0:
            emb = emb / norm
        emb = emb.reshape(1, EMBEDDING_DIM)

        actual_k = min(k, index.ntotal)
        scores, indices = index.search(emb, actual_k)

        results: list[tuple[str, str, float]] = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:
                continue
            outfit_id, item_id = self._id_maps[category][int(idx)]
            results.append((outfit_id, item_id, float(score)))

        return results

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def get_outfit_categories(self, outfit_id: str) -> set[str]:
        """Return the set of categories required by the given outfit."""
        return self._outfit_categories.get(outfit_id, set())

    def total_vectors(self, category: str) -> int:
        """Return the number of indexed vectors for a category."""
        return self._indexes[category].ntotal if category in self._indexes else 0
