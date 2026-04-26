"""
Dominant color extraction for clothing items.

Uses K-Means clustering on isolated clothing pixels to extract the dominant
color palettes. Maps the extracted colors to a standard set of recognizable
clothing color names.
"""

from typing import Union, Optional

import numpy as np
from PIL import Image
from sklearn.cluster import KMeans
from skimage.color import rgb2lab, deltaE_cie76


CLOTHING_COLORS = {
    "black": (0, 0, 0),
    "white": (255, 255, 255),
    "cream": (255, 253, 208),
    "gray": (128, 128, 128),
    "light gray": (192, 192, 192),
    "charcoal": (54, 69, 79),
    "navy": (0, 0, 128),
    "blue": (0, 0, 255),
    "light blue": (173, 216, 230),
    "denim": (92, 136, 218),
    "red": (255, 0, 0),
    "burgundy": (128, 0, 32),
    "pink": (255, 192, 203),
    "green": (0, 128, 0),
    "olive": (128, 128, 0),
    "yellow": (255, 255, 0),
    "orange": (255, 165, 0),
    "purple": (128, 0, 128),
    "brown": (139, 69, 19),
    "tan": (210, 180, 140),
    "beige": (245, 245, 220),
    "khaki": (195, 176, 145),
    "coral": (255, 127, 80),
    "teal": (0, 128, 128),
}

# Pre-compute LAB conversions for reference colors to speed up lookups
REFERENCE_LAB = {
    name: rgb2lab(np.array([[rgb]], dtype=np.uint8))[0][0].tolist()
    for name, rgb in CLOTHING_COLORS.items()
}


def rgb_to_lab(rgb_color: Union[tuple, list, np.ndarray]) -> tuple:
    """Convert a single RGB color to CIELAB space."""
    rgb_arr = np.array([[rgb_color]], dtype=np.uint8)
    lab_color = rgb2lab(rgb_arr)[0][0]
    return tuple(lab_color)


def closest_color_name(rgb_color: Union[tuple, list, np.ndarray]) -> str:
    """
    Map an RGB color to the visually nearest human-readable color name
    using CIELAB deltaE distance.
    """
    target_lab = rgb_to_lab(rgb_color)
    target_lab_np = np.array([target_lab])
    
    min_dist = float('inf')
    best_name = "unknown"
    
    for name, ref_lab in REFERENCE_LAB.items():
        ref_lab_np = np.array([ref_lab])
        # DeltaE measures human-perceived visual difference
        dist = deltaE_cie76(target_lab_np, ref_lab_np)[0]
        if dist < min_dist:
            min_dist = dist
            best_name = name
            
    return best_name


def extract_dominant_colors(
    image: Union[Image.Image, np.ndarray], 
    mask: Optional[np.ndarray] = None, 
    n_colors: int = 3
) -> dict:
    """
    Extract dominant colors from an image using KMeans clustering.
    
    Args:
        image: PIL Image or numpy array (RGB)
        mask: Optional binary mask (H, W). Only True pixels are analyzed.
        n_colors: Number of color clusters to find.
        
    Returns:
        Dictionary containing sorted lists of RGB tuples, LAB tuples,
        human readable names, and their respective coverage percentages.
    """
    if isinstance(image, Image.Image):
        # Convert to RGB (dropping alpha if present since we only cluster color logic)
        img_arr = np.array(image.convert("RGB"))
    else:
        # Assuming H, W, 3
        img_arr = image

    # Flatten pixels
    if mask is not None:
        # If mask is boolean, just use it.
        if mask.dtype != bool:
            mask = mask > 0
            
        # Ensure mask shape matches image H, W
        if mask.shape[:2] != img_arr.shape[:2]:
            raise ValueError(f"Mask shape {mask.shape} does not match image shape {img_arr.shape}")
            
        pixels = img_arr[mask]
    else:
        pixels = img_arr.reshape(-1, 3)

    if len(pixels) == 0:
        return {
            "colors_rgb": [],
            "colors_lab": [],
            "color_names": [],
            "percentages": []
        }
        
    # Standardize sample size to prevent slow clustering on massive images
    max_pixels = 10000
    if len(pixels) > max_pixels:
        indices = np.random.choice(len(pixels), max_pixels, replace=False)
        pixels = pixels[indices]

    # Handle case where image has fewer unique colors than n_colors
    unique_colors = len(np.unique(pixels, axis=0))
    n_clusters = min(n_colors, unique_colors)

    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init="auto")
    kmeans.fit(pixels)
    
    counts = np.bincount(kmeans.labels_)
    percentages = counts / len(pixels)
    
    # Sort clusters descending by dominance
    sorted_idx = np.argsort(counts)[::-1]
    
    colors_rgb = []
    colors_lab = []
    color_names = []
    sorted_percentages = []
    
    for idx in sorted_idx:
        rgb = tuple(map(int, kmeans.cluster_centers_[idx]))
        colors_rgb.append(rgb)
        
        lab = rgb_to_lab(rgb)
        colors_lab.append(lab)
        
        name = closest_color_name(rgb)
        color_names.append(name)
        
        sorted_percentages.append(float(percentages[idx]))
        
    return {
        "colors_rgb": colors_rgb,
        "colors_lab": colors_lab,
        "color_names": color_names,
        "percentages": sorted_percentages
    }
