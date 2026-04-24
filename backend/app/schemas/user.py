from pydantic import BaseModel


class HSLColor(BaseModel):
    h: float  # 0-360
    s: float  # 0-100
    l: float  # 0-100


class UserUpdate(BaseModel):
    name: str | None = None
    skin_tone: HSLColor | None = None


class UserResponse(BaseModel):
    id: int
    email: str
    name: str | None = None
    skin_tone: HSLColor | None = None

    model_config = {"from_attributes": True}

    @classmethod
    def from_db(cls, user):
        skin_tone = None
        if user.skin_tone_hue is not None:
            skin_tone = HSLColor(h=user.skin_tone_hue, s=user.skin_tone_saturation, l=user.skin_tone_lightness)
        return cls(
            id=user.id,
            email=user.email,
            name=user.name,
            skin_tone=skin_tone,
        )
