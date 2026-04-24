from sqlalchemy import Column, Integer, String, ForeignKey, JSON, DateTime, func

from app.core.database import Base


class WardrobeUpload(Base):
    """A closet photo a user submitted. One upload produces many wardrobe items."""
    __tablename__ = "wardrobe_uploads"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    image_path = Column(String, nullable=False)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class WardrobeItem(Base):
    __tablename__ = "wardrobe_items"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    upload_id = Column(Integer, ForeignKey("wardrobe_uploads.id"), nullable=True, index=True)
    name = Column(String, nullable=True)
    category = Column(String, nullable=False)  # top, bottom, shoes, accessory, outerwear
    subcategory = Column(String, nullable=True)  # t-shirt, jeans, sneakers, etc.
    image_path = Column(String, nullable=False)
    dominant_colors = Column(JSON, nullable=True)
    secondary_colors = Column(JSON, nullable=True)
    source = Column(String, nullable=False, default="uploaded")  # uploaded / detected / manual
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
