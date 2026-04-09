"""Tests for the color recommendation engine."""

from app.services.color_recommendation import get_recommended_colors, adjust_for_lighting


def test_get_recommended_colors_with_season():
    colors = get_recommended_colors("warm_spring", "bright")
    assert len(colors) > 0
    for c in colors:
        assert "h" in c and "s" in c and "l" in c


def test_get_recommended_colors_default():
    colors = get_recommended_colors(None, "indoor")
    assert len(colors) > 0


def test_adjust_for_lighting_overcast():
    colors = [{"h": 200, "s": 50, "l": 50}]
    adjusted = adjust_for_lighting(colors, "overcast")
    assert adjusted[0]["s"] > 50  # saturation should increase


def test_adjust_for_lighting_bright():
    colors = [{"h": 200, "s": 50, "l": 50}]
    adjusted = adjust_for_lighting(colors, "bright")
    assert adjusted[0]["s"] < 50  # saturation should decrease


def test_adjust_for_lighting_indoor():
    colors = [{"h": 200, "s": 50, "l": 50}]
    adjusted = adjust_for_lighting(colors, "indoor")
    assert adjusted[0] == {"h": 200, "s": 50, "l": 50}  # no change
