def item_to_dict(user_id: str, name, category, image_path, dominant_colors, secondary_colors) -> dict:
    """Convert wardrobe item fields to a Firestore-ready dict."""
    return {
        "user_id": user_id,
        "name": name,
        "category": category,
        "image_path": image_path,
        "dominant_colors": dominant_colors,
        "secondary_colors": secondary_colors,
    }


def doc_to_item(doc) -> dict:
    """Convert a Firestore DocumentSnapshot to a dict with 'id' included."""
    data = doc.to_dict()
    data["id"] = doc.id
    return data
