from sqlalchemy import Column, Integer, String, Float, ForeignKey, JSON
from app.core.database import Base


class WardrobeItem(Base):
    __tablename__ = "wardrobe_items"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=True)
    category = Column(String, nullable=False)  # top, bottom, shoes, accessory, outerwear
    image_path = Column(String, nullable=False)
    dominant_colors = Column(JSON, nullable=True)  # list of {h, s, l} dicts
    secondary_colors = Column(JSON, nullable=True)
