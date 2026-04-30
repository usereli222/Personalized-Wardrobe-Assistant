"""
Wardrobe item categorizer — FashionCLIP zero-shot.

Embeds the input image with FashionCLIP, dot-products against pre-computed
text-prompt embeddings (one prompt per category), and returns the argmax.
Also returns the image embedding so the caller can persist it for later
similarity search and FAISS-based outfit retrieval.

Falls back to {"category": "top", "subcategory": "shirt"} with a zero
embedding if the model fails to load — the upload flow stays unblocked.

Replaces the previous Gemini API call. The signature is unchanged from the
caller's perspective except that the returned dict now includes an
"embedding" key (np.ndarray, shape (512,), L2-normalized).
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
from PIL.Image import Image

from app.services.ml_pipeline import get_processor

logger = logging.getLogger(__name__)


CATEGORIES = ("top", "bottom", "outerwear", "shoes", "accessory")

# Per-category text prompts. Tuned for FashionCLIP, which was trained on
# fashion captions — descriptive natural-language prompts work better than
# bare nouns.
_CATEGORY_PROMPTS = {
    "top": "a photo of a shirt, t-shirt, sweater, hoodie, or blouse",
    "bottom": "a photo of pants, jeans, shorts, or a skirt",
    "outerwear": "a photo of a jacket, coat, or blazer",
    "shoes": "a photo of shoes, sneakers, boots, heels, or sandals",
    "accessory": "a photo of a hat, bag, scarf, belt, or sunglasses",
}

# Cached per-category text embeddings, shape (len(CATEGORIES), 512).
_text_embs: np.ndarray | None = None


def _ensure_text_embeddings() -> np.ndarray:
    global _text_embs
    if _text_embs is None:
        proc = get_processor()
        prompts = [_CATEGORY_PROMPTS[c] for c in CATEGORIES]
        _text_embs = proc.embedder.embed_text(prompts)  # (N, 512), L2-normed
    return _text_embs


def _zero_embedding() -> np.ndarray:
    return np.zeros(512, dtype=np.float32)


def categorize_item(image: Image) -> dict[str, Any]:
    """
    Returns:
        {
            "category": one of CATEGORIES,
            "subcategory": str (currently mirrors category — DINO labels
                           would refine this if the segmentation flow runs),
            "embedding": np.ndarray shape (512,) float32, L2-normalized,
        }
    """
    try:
        proc = get_processor()
        text_embs = _ensure_text_embeddings()
    except Exception as exc:
        logger.warning("FashionCLIP failed to load (%s); returning fallback.", exc)
        return {"category": "top", "subcategory": "shirt", "embedding": _zero_embedding()}

    try:
        img_emb = proc.embedder.embed(image)  # (512,)
    except Exception as exc:
        logger.warning("FashionCLIP embed failed (%s); returning fallback.", exc)
        return {"category": "top", "subcategory": "shirt", "embedding": _zero_embedding()}

    # Cosine similarity (vectors are L2-normalized so dot product = cosine).
    sims = img_emb @ text_embs.T  # (N,)
    cat = CATEGORIES[int(np.argmax(sims))]

    return {
        "category": cat,
        "subcategory": cat,
        "embedding": img_emb.astype(np.float32),
    }
