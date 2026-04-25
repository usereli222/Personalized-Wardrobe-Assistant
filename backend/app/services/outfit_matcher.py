"""
Match wardrobe items to recommended colors using perceptual color distance.

Uses Delta E (CIE76) in CIELAB color space for human-perceptual color matching.
"""

import colorsys
import math

from app.models.wardrobe import doc_to_item


def hsl_to_lab(h: float, s: float, l: float) -> tuple[float, float, float]:
    """Convert HSL (h:0-360, s:0-100, l:0-100) to CIELAB via RGB and XYZ."""
    # HSL to RGB
    r, g, b = colorsys.hls_to_rgb(h / 360.0, l / 100.0, s / 100.0)

    # RGB to linear RGB
    def linearize(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r_lin, g_lin, b_lin = linearize(r), linearize(g), linearize(b)

    # Linear RGB to XYZ (D65)
    x = r_lin * 0.4124564 + g_lin * 0.3575761 + b_lin * 0.1804375
    y = r_lin * 0.2126729 + g_lin * 0.7151522 + b_lin * 0.0721750
    z = r_lin * 0.0193339 + g_lin * 0.1191920 + b_lin * 0.9503041

    # XYZ to CIELAB
    xn, yn, zn = 0.95047, 1.0, 1.08883

    def f(t):
        return t ** (1 / 3) if t > 0.008856 else (7.787 * t) + (16 / 116)

    l_star = 116 * f(y / yn) - 16
    a_star = 500 * (f(x / xn) - f(y / yn))
    b_star = 200 * (f(y / yn) - f(z / zn))

    return l_star, a_star, b_star


def delta_e(color1: dict, color2: dict) -> float:
    """Calculate Delta E (CIE76) between two HSL colors."""
    lab1 = hsl_to_lab(color1["h"], color1["s"], color1["l"])
    lab2 = hsl_to_lab(color2["h"], color2["s"], color2["l"])
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(lab1, lab2)))


def score_item(item: dict, recommended_colors: list[dict]) -> float:
    """
    Score a wardrobe item against recommended colors.

    Lower score = better match. Uses the minimum Delta E between
    the item's dominant colors and any recommended color.
    """
    if not item.get("dominant_colors"):
        return float("inf")

    min_distance = float("inf")
    for item_color in item["dominant_colors"]:
        for rec_color in recommended_colors:
            dist = delta_e(item_color, rec_color)
            min_distance = min(min_distance, dist)

    return min_distance


def get_outfit_recommendation(
    db,
    user_id: str,
    recommended_colors: list[dict],
    top_n: int = 3,
) -> dict[str, list]:
    """
    Match wardrobe items to recommended colors and return top matches per category.

    Returns:
        Dict mapping category -> list of (item_dict, score) tuples, sorted by score
    """
    docs = db.collection("wardrobe_items").where("user_id", "==", user_id).get()
    items = [doc_to_item(doc) for doc in docs]

    # Group by category and score
    categories: dict[str, list] = {}
    for item in items:
        score = score_item(item, recommended_colors)
        if item["category"] not in categories:
            categories[item["category"]] = []
        categories[item["category"]].append((item, score))

    # Sort each category by score and take top N
    result = {}
    for category, scored_items in categories.items():
        scored_items.sort(key=lambda x: x[1])
        result[category] = scored_items[:top_n]

    return result
