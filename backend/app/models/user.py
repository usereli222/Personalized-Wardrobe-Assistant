from sqlalchemy import Column, Integer, String, Float
from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    skin_tone_hue = Column(Float, nullable=True)
    skin_tone_saturation = Column(Float, nullable=True)
    skin_tone_lightness = Column(Float, nullable=True)
    season = Column(String, nullable=True)  # warm_spring, cool_summer, warm_autumn, cool_winter
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    location_name = Column(String, nullable=True)
