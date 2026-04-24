from sqlalchemy import Column, Integer, String, Float, ForeignKey, JSON, DateTime, func

from app.core.database import Base


class OutfitRecommendation(Base):
    """An outfit suggested to a user, optionally inspired by a specific trend."""
    __tablename__ = "outfit_recommendations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    trend_id = Column(Integer, ForeignKey("trends.id"), nullable=True, index=True)
    match_score = Column(Float, nullable=False)
    status = Column(String, nullable=False, default="shown")  # shown / accepted / rejected
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class OutfitRecommendationItem(Base):
    """Join row: which wardrobe items compose an outfit recommendation, by role."""
    __tablename__ = "outfit_recommendation_items"

    id = Column(Integer, primary_key=True, index=True)
    recommendation_id = Column(Integer, ForeignKey("outfit_recommendations.id"), nullable=False, index=True)
    wardrobe_item_id = Column(Integer, ForeignKey("wardrobe_items.id"), nullable=False, index=True)
    role = Column(String, nullable=False)  # top / bottom / shoes / outerwear / accessory


class BuyRecommendation(Base):
    """When an outfit can't be built from the wardrobe, suggest a category to buy."""
    __tablename__ = "buy_recommendations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    recommendation_id = Column(Integer, ForeignKey("outfit_recommendations.id"), nullable=True, index=True)
    trend_id = Column(Integer, ForeignKey("trends.id"), nullable=True, index=True)
    category = Column(String, nullable=False)
    desired_colors = Column(JSON, nullable=True)  # list of {h, s, l}
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
