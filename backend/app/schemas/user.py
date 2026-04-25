from pydantic import BaseModel


class HSLColor(BaseModel):
    h: float  # 0-360
    s: float  # 0-100
    l: float  # 0-100


class UserCreate(BaseModel):
    username: str
    name: str
    skin_tone: HSLColor | None = None
    season: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    location_name: str | None = None


class UserLogin(BaseModel):
    username: str


class UserUpdate(BaseModel):
    name: str | None = None
    skin_tone: HSLColor | None = None
    season: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    location_name: str | None = None


class UserResponse(BaseModel):
    id: str
    username: str
    name: str
    skin_tone: HSLColor | None = None
    season: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    location_name: str | None = None

    @classmethod
    def from_db(cls, data: dict):
        skin_tone = None
        if data.get("skin_tone_hue") is not None:
            skin_tone = HSLColor(
                h=data["skin_tone_hue"],
                s=data["skin_tone_saturation"],
                l=data["skin_tone_lightness"],
            )
        return cls(
            id=data["id"],
            username=data["username"],
            name=data["name"],
            skin_tone=skin_tone,
            season=data.get("season"),
            latitude=data.get("latitude"),
            longitude=data.get("longitude"),
            location_name=data.get("location_name"),
        )
