from sqlalchemy import Column, Integer, String, Float, JSON, DateTime, func

from app.core.database import Base


class Trend(Base):
    """A scraped outfit/style from Instagram, Pinterest, etc. Global (not per-user)."""
    __tablename__ = "trends"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String, nullable=False, index=True)  # instagram, pinterest
    source_url = Column(String, nullable=False, unique=True)
    image_path = Column(String, nullable=False)
    categories = Column(JSON, nullable=True)  # ["top", "bottom", "shoes"]
    dominant_colors = Column(JSON, nullable=True)  # list of {h, s, l}
    tags = Column(JSON, nullable=True)  # ["minimal", "streetwear", ...]
    popularity = Column(Float, nullable=False, default=0.0)  # engagement-derived score
    scraped_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
