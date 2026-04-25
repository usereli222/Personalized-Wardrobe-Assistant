def user_to_dict(user_in) -> dict:
    """Convert a UserCreate schema to a Firestore-ready dict."""
    return {
        "username": user_in.username,
        "name": user_in.name,
        "skin_tone_hue": user_in.skin_tone.h if user_in.skin_tone else None,
        "skin_tone_saturation": user_in.skin_tone.s if user_in.skin_tone else None,
        "skin_tone_lightness": user_in.skin_tone.l if user_in.skin_tone else None,
        "season": user_in.season,
        "latitude": user_in.latitude,
        "longitude": user_in.longitude,
        "location_name": user_in.location_name,
    }


def doc_to_user(doc) -> dict:
    """Convert a Firestore DocumentSnapshot to a dict with 'id' included."""
    data = doc.to_dict()
    data["id"] = doc.id
    return data
