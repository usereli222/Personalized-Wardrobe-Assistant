"""
Outfit suggester — STUB.

Given a user's wardrobe items, returns a list of outfit suggestions. Each
suggestion is just a (top, bottom) pair for now; mentees can extend the
shape to include outerwear/shoes/accessories or a styling rationale.

The stub does an all-pairs cross product and ranks by HSL distance over the
existing `dominant_colors` field, so similar-toned outfits float to the top.
That's not "stylish" in any real sense — it's a placeholder that produces
plausible-looking output during the demo.

Mentees: drop in a real model. Two easy paths:
    1. FashionCLIP embeddings + FAISS over a curated style corpus
       (`wardrobe/faiss_index.py` already exists).
    2. Gemini "stylist" prompt: send the wardrobe + user context, ask for
       N outfit suggestions in JSON.

Keep the return shape stable.
"""

from __future__ import annotations

from typing import Any


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
    # Treat hue as circular (0..360). Saturation/lightness are linear (0..100).
    dh = min(abs(ca[0] - cb[0]), 360 - abs(ca[0] - cb[0]))
    ds = abs(ca[1] - cb[1])
    dl = abs(ca[2] - cb[2])
    return (dh * dh) + (ds * ds) + (dl * dl)


def suggest_outfits(items: list[dict], limit: int = 12) -> list[dict[str, Any]]:
    tops = [i for i in items if i.get("category") == "top"]
    bottoms = [i for i in items if i.get("category") == "bottom"]

    pairs: list[tuple[float, dict, dict]] = []
    for t in tops:
        for b in bottoms:
            pairs.append((_color_distance(t, b), t, b))

    pairs.sort(key=lambda p: p[0])

    return [
        {"top": t, "bottom": b, "score": round(1.0 / (1.0 + dist / 1000.0), 4)}
        for dist, t, b in pairs[:limit]
    ]
