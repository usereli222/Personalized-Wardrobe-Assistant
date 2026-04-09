"""
Color recommendation engine.

Maps skin tone seasons to color palettes and adjusts for lighting conditions.
Uses established color theory (seasonal color analysis).
"""

# Seasonal color palettes as HSL values
# Each season has a set of recommended clothing colors
SEASONAL_PALETTES: dict[str, list[dict]] = {
    "warm_spring": [
        {"h": 40, "s": 70, "l": 60},    # warm golden
        {"h": 15, "s": 65, "l": 55},     # coral
        {"h": 80, "s": 50, "l": 50},     # warm green
        {"h": 30, "s": 60, "l": 65},     # peach
        {"h": 50, "s": 55, "l": 55},     # warm yellow-green
        {"h": 0, "s": 60, "l": 50},      # warm red
        {"h": 200, "s": 45, "l": 55},    # warm teal
        {"h": 25, "s": 50, "l": 40},     # camel/tan
    ],
    "cool_summer": [
        {"h": 220, "s": 40, "l": 60},    # soft blue
        {"h": 280, "s": 30, "l": 60},    # lavender
        {"h": 330, "s": 35, "l": 60},    # soft rose
        {"h": 180, "s": 30, "l": 55},    # dusty teal
        {"h": 300, "s": 25, "l": 55},    # mauve
        {"h": 0, "s": 25, "l": 50},      # muted raspberry
        {"h": 210, "s": 30, "l": 50},    # slate blue
        {"h": 160, "s": 25, "l": 55},    # sage
    ],
    "warm_autumn": [
        {"h": 20, "s": 70, "l": 40},     # rust
        {"h": 35, "s": 65, "l": 45},     # warm brown
        {"h": 80, "s": 55, "l": 35},     # olive
        {"h": 15, "s": 75, "l": 45},     # burnt orange
        {"h": 50, "s": 60, "l": 45},     # mustard
        {"h": 0, "s": 65, "l": 35},      # deep red
        {"h": 160, "s": 45, "l": 35},    # forest teal
        {"h": 40, "s": 50, "l": 35},     # dark camel
    ],
    "cool_winter": [
        {"h": 240, "s": 60, "l": 45},    # royal blue
        {"h": 340, "s": 70, "l": 45},    # magenta
        {"h": 0, "s": 80, "l": 40},      # true red
        {"h": 270, "s": 50, "l": 40},    # deep purple
        {"h": 180, "s": 60, "l": 35},    # dark teal
        {"h": 0, "s": 0, "l": 10},       # black
        {"h": 0, "s": 0, "l": 95},       # white
        {"h": 210, "s": 50, "l": 50},    # icy blue
    ],
}

# Default palette when no season is set
DEFAULT_PALETTE = [
    {"h": 210, "s": 50, "l": 50},    # medium blue
    {"h": 0, "s": 0, "l": 30},       # charcoal
    {"h": 30, "s": 40, "l": 50},     # tan
    {"h": 0, "s": 0, "l": 95},       # white
    {"h": 120, "s": 30, "l": 40},    # muted green
]


def adjust_for_lighting(colors: list[dict], lighting: str) -> list[dict]:
    """
    Adjust recommended colors based on lighting conditions.

    - Overcast: boost saturation (muted tones get washed out)
    - Bright sun: reduce saturation (vivid colors look harsh)
    - Golden hour: shift hues slightly warm, boost warmth
    - Indoor: no adjustment (neutral lighting assumed)
    """
    adjusted = []
    for color in colors:
        c = color.copy()
        if lighting == "overcast":
            c["s"] = min(100, c["s"] + 15)
            c["l"] = max(20, c["l"] - 5)
        elif lighting == "bright":
            c["s"] = max(10, c["s"] - 10)
            c["l"] = min(80, c["l"] + 5)
        elif lighting == "golden_hour":
            # Shift slightly toward warm tones
            if c["h"] > 180:
                c["h"] = c["h"] - 10
            else:
                c["h"] = c["h"] + 5
            c["s"] = min(100, c["s"] + 5)
        adjusted.append(c)
    return adjusted


def get_recommended_colors(season: str | None, lighting: str) -> list[dict]:
    """
    Get recommended clothing colors for a skin tone season and lighting condition.

    Args:
        season: one of warm_spring, cool_summer, warm_autumn, cool_winter (or None)
        lighting: one of bright, overcast, golden_hour, indoor

    Returns:
        List of HSL color dicts
    """
    palette = SEASONAL_PALETTES.get(season, DEFAULT_PALETTE)
    return adjust_for_lighting(palette, lighting)
