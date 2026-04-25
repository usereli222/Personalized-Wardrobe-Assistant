from fastapi import APIRouter, Depends, HTTPException
from google.cloud.firestore_v1.base_client import BaseClient

from app.core.database import get_db
from app.models.user import doc_to_user
from app.schemas.user import HSLColor
from app.schemas.wardrobe import WardrobeItemResponse, OutfitRecommendation
from app.services.weather import get_weather, get_lighting_condition
from app.services.color_recommendation import get_recommended_colors
from app.services.outfit_matcher import get_outfit_recommendation

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.get("/colors", response_model=list[HSLColor])
async def recommend_colors(user_id: str, db: BaseClient = Depends(get_db)):
    """Get recommended clothing colors based on user's skin tone and current weather."""
    doc = db.collection("users").document(user_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="User not found")
    user = doc_to_user(doc)

    # Get weather and lighting
    if user.get("latitude") and user.get("longitude"):
        weather = await get_weather(user["latitude"], user["longitude"])
    else:
        weather = await get_weather(40.7128, -74.0060)  # default NYC

    lighting = get_lighting_condition(weather)
    colors = get_recommended_colors(user.get("season"), lighting)

    return [HSLColor(h=c["h"], s=c["s"], l=c["l"]) for c in colors]


@router.get("/outfit", response_model=OutfitRecommendation)
async def recommend_outfit(user_id: str, db: BaseClient = Depends(get_db)):
    """Get a full outfit recommendation for today."""
    doc = db.collection("users").document(user_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="User not found")
    user = doc_to_user(doc)

    # Get weather and lighting
    if user.get("latitude") and user.get("longitude"):
        weather = await get_weather(user["latitude"], user["longitude"])
    else:
        weather = await get_weather(40.7128, -74.0060)

    lighting = get_lighting_condition(weather)
    recommended_colors = get_recommended_colors(user.get("season"), lighting)

    # Match wardrobe items
    matches = get_outfit_recommendation(db, user["id"], recommended_colors)

    # Format response
    outfit = {}
    for category, scored_items in matches.items():
        outfit[category] = [
            WardrobeItemResponse.model_validate(item) for item, _score in scored_items
        ]

    return OutfitRecommendation(
        recommended_colors=[HSLColor(h=c["h"], s=c["s"], l=c["l"]) for c in recommended_colors],
        lighting_condition=lighting,
        weather_description=weather.get("description", "unknown"),
        outfit=outfit,
    )
