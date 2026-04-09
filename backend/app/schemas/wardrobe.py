from pydantic import BaseModel


class HSLColor(BaseModel):
    h: float
    s: float
    l: float


class WardrobeItemResponse(BaseModel):
    id: int
    user_id: int
    name: str | None
    category: str
    image_path: str
    dominant_colors: list[dict] | None
    secondary_colors: list[dict] | None

    model_config = {"from_attributes": True}


class OutfitRecommendation(BaseModel):
    recommended_colors: list[HSLColor]
    lighting_condition: str
    weather_description: str
    outfit: dict[str, list[WardrobeItemResponse]]  # category -> items
