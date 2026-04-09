from pydantic import BaseModel


class HSLColor(BaseModel):
    h: float  # 0-360
    s: float  # 0-100
    l: float  # 0-100


class UserCreate(BaseModel):
    name: str
    skin_tone: HSLColor | None = None
    season: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    location_name: str | None = None


class UserUpdate(BaseModel):
    name: str | None = None
    skin_tone: HSLColor | None = None
    season: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    location_name: str | None = None


class UserResponse(BaseModel):
    id: int
    name: str
    skin_tone: HSLColor | None = None
    season: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    location_name: str | None = None

    model_config = {"from_attributes": True}

    @classmethod
    def from_db(cls, user):
        skin_tone = None
        if user.skin_tone_hue is not None:
            skin_tone = HSLColor(h=user.skin_tone_hue, s=user.skin_tone_saturation, l=user.skin_tone_lightness)
        return cls(
            id=user.id,
            name=user.name,
            skin_tone=skin_tone,
            season=user.season,
            latitude=user.latitude,
            longitude=user.longitude,
            location_name=user.location_name,
        )
