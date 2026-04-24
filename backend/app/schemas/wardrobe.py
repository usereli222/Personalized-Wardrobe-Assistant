from datetime import datetime
from pydantic import BaseModel


class WardrobeItemResponse(BaseModel):
    id: int
    user_id: int
    name: str | None
    category: str
    subcategory: str | None
    image_path: str
    dominant_colors: list[dict] | None
    secondary_colors: list[dict] | None
    source: str
    created_at: datetime

    model_config = {"from_attributes": True}


class WardrobeUploadResponse(BaseModel):
    id: int
    user_id: int
    image_path: str
    uploaded_at: datetime

    model_config = {"from_attributes": True}
