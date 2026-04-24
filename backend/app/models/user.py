from sqlalchemy import Column, Integer, String, Float, DateTime, func
from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    firebase_uid = Column(String, unique=True, nullable=False, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    skin_tone_hue = Column(Float, nullable=True)
    skin_tone_saturation = Column(Float, nullable=True)
    skin_tone_lightness = Column(Float, nullable=True)
