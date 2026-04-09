"""Tests for the outfit matching / color distance logic."""

from app.services.outfit_matcher import delta_e, hsl_to_lab


def test_delta_e_same_color():
    color = {"h": 200, "s": 50, "l": 50}
    assert delta_e(color, color) == 0.0


def test_delta_e_different_colors():
    red = {"h": 0, "s": 100, "l": 50}
    blue = {"h": 240, "s": 100, "l": 50}
    dist = delta_e(red, blue)
    assert dist > 50  # red and blue should be very different


def test_delta_e_similar_colors():
    color1 = {"h": 200, "s": 50, "l": 50}
    color2 = {"h": 205, "s": 52, "l": 48}
    dist = delta_e(color1, color2)
    assert dist < 10  # very similar colors


def test_hsl_to_lab_black():
    l, a, b = hsl_to_lab(0, 0, 0)
    assert l < 1  # L* should be near 0 for black


def test_hsl_to_lab_white():
    l, a, b = hsl_to_lab(0, 0, 100)
    assert l > 99  # L* should be near 100 for white
