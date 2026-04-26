"""
Wardrobe item categorizer.

Uses Gemini vision to classify a clothing image into one of CATEGORIES with
a free-form subcategory. If GEMINI_API_KEY is unset (or the call fails),
falls back to "top/shirt" so the upload flow stays unblocked.

Mentees: feel free to swap this for FashionCLIP or any other model — keep
the return shape ({category, subcategory}) since the rest of the app
depends on it.
"""

from __future__ import annotations

import json
import re

from google import genai
from PIL.Image import Image

from app.core.config import settings


CATEGORIES = ("top", "bottom", "outerwear", "shoes", "accessory")

_PROMPT = (
    "Classify this clothing item. Reply with strict JSON ONLY (no prose, no "
    "code fences) of the form: "
    '{"category": "<one of: top, bottom, outerwear, shoes, accessory>", '
    '"subcategory": "<single short noun, e.g. shirt, sweater, jeans, jacket, sneakers>"}. '
    "Use 'top' for shirts/sweaters/t-shirts/blouses, 'bottom' for "
    "pants/shorts/skirts, 'outerwear' for jackets/coats, 'shoes' for any "
    "footwear, 'accessory' for hats/bags/jewelry/scarves."
)


def _parse_response(text: str) -> dict[str, str] | None:
    if not text:
        return None
    # Gemini sometimes wraps JSON in ```json ... ``` despite the instruction.
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.MULTILINE)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        # Try to find the first {...} block
        match = re.search(r"\{[^{}]*\}", cleaned)
        if not match:
            return None
        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
    cat = str(data.get("category", "")).lower().strip()
    sub = str(data.get("subcategory", "")).lower().strip()
    if cat not in CATEGORIES:
        return None
    return {"category": cat, "subcategory": sub or cat}


def categorize_item(image: Image) -> dict[str, str]:
    if not settings.GEMINI_API_KEY:
        return {"category": "top", "subcategory": "shirt"}

    try:
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        response = client.models.generate_content(
            model=settings.GEMINI_VISION_MODEL,
            contents=[_PROMPT, image],
        )
    except Exception:
        return {"category": "top", "subcategory": "shirt"}

    text_parts = []
    for cand in response.candidates or []:
        for part in cand.content.parts or []:
            t = getattr(part, "text", None)
            if t:
                text_parts.append(t)
    parsed = _parse_response("".join(text_parts))
    return parsed or {"category": "top", "subcategory": "shirt"}
