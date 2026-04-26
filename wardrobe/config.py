"""
Configuration for the clothing segmentation pipeline.

Contains text prompts, category mappings, model identifiers,
and visualization colors.
"""

# ---------------------------------------------------------------------------
# Grounding DINO text prompt
# ---------------------------------------------------------------------------
# Grounding DINO uses periods to separate object classes in the text prompt.
# This prompt covers common clothing items a user would photograph.
DEFAULT_PROMPT = (
    "shirt . t-shirt . pants . trousers . shorts . jacket . "
    "sweater . hoodie . dress . skirt . coat . blazer . jeans"
)

# ---------------------------------------------------------------------------
# Category normalization
# ---------------------------------------------------------------------------
# Grounding DINO returns raw labels like "t-shirt", "trousers", etc.
# We normalize these to a small set of categories that match what the
# Polyvore outfit library uses downstream.
CATEGORY_MAP = {
    "shirt": "top",
    "t-shirt": "top",
    "sweater": "top",
    "hoodie": "top",
    "blazer": "outerwear",
    "jacket": "outerwear",
    "coat": "outerwear",
    "pants": "bottom",
    "trousers": "bottom",
    "jeans": "bottom",
    "shorts": "bottom",
    "skirt": "bottom",
    "dress": "dress",
}

# ---------------------------------------------------------------------------
# Visualization colors (BGR for OpenCV, RGB for PIL)
# ---------------------------------------------------------------------------
# Each normalized category gets a distinct color for annotated outputs.
CATEGORY_COLORS_RGB = {
    "top": (50, 120, 255),
    "bottom": (50, 200, 120),
    "outerwear": (255, 150, 30),
    "dress": (200, 50, 200),
    "unknown": (150, 150, 150),
}

# ---------------------------------------------------------------------------
# Model identifiers (HuggingFace)
# ---------------------------------------------------------------------------
DINO_MODEL_ID = "IDEA-Research/grounding-dino-tiny"
SAM_MODEL_ID = "facebook/sam-vit-base"
# To upgrade mask quality, change SAM_MODEL_ID to:
#   "facebook/sam-vit-large"  (~1.2 GB)
#   "facebook/sam-vit-huge"   (~2.5 GB, best quality)

# ---------------------------------------------------------------------------
# Default thresholds
# ---------------------------------------------------------------------------
DEFAULT_BOX_THRESHOLD = 0.30
DEFAULT_TEXT_THRESHOLD = 0.25
