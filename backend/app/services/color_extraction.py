"""Extract dominant colors from clothing images using k-means clustering."""

import colorsys
from io import BytesIO

import numpy as np
from PIL import Image
from sklearn.cluster import KMeans


def remove_background(image: Image.Image) -> Image.Image:
    """Remove background from clothing image using rembg."""
    from rembg import remove

    img_bytes = BytesIO()
    image.save(img_bytes, format="PNG")
    img_bytes.seek(0)
    result_bytes = remove(img_bytes.read())
    return Image.open(BytesIO(result_bytes)).convert("RGBA")


def extract_dominant_colors(image: Image.Image, n_colors: int = 3, remove_bg: bool = True) -> list[dict]:
    """
    Extract dominant colors from an image as HSL values.

    Args:
        image: PIL Image
        n_colors: number of dominant colors to extract
        remove_bg: whether to remove background first

    Returns:
        List of dicts with h, s, l keys, sorted by cluster size (most dominant first)
    """
    if remove_bg:
        image = remove_background(image)

    # Convert to RGBA if not already
    image = image.convert("RGBA")
    image = image.resize((150, 150))
    pixels = np.array(image)

    # Filter out transparent/near-transparent pixels
    alpha_mask = pixels[:, :, 3] > 128
    rgb_pixels = pixels[:, :, :3][alpha_mask]

    if len(rgb_pixels) < n_colors:
        return []

    # K-means clustering
    kmeans = KMeans(n_clusters=n_colors, random_state=42, n_init=10)
    kmeans.fit(rgb_pixels)

    # Sort by cluster size (most dominant first)
    labels, counts = np.unique(kmeans.labels_, return_counts=True)
    sorted_indices = np.argsort(-counts)

    colors = []
    for idx in sorted_indices:
        r, g, b = kmeans.cluster_centers_[labels[idx]] / 255.0
        h, l, s = colorsys.rgb_to_hls(r, g, b)
        colors.append({
            "h": round(h * 360, 1),
            "s": round(s * 100, 1),
            "l": round(l * 100, 1),
        })

    return colors
