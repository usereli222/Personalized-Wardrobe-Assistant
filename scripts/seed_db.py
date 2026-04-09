"""Seed the database with a sample user for development."""

import sys
sys.path.insert(0, "backend")

from app.core.database import engine, Base, SessionLocal
from app.models.user import User

Base.metadata.create_all(bind=engine)

db = SessionLocal()

# Check if sample user already exists
existing = db.query(User).filter(User.name == "Demo User").first()
if existing:
    print(f"Sample user already exists (id={existing.id})")
else:
    user = User(
        name="Demo User",
        skin_tone_hue=25,
        skin_tone_saturation=45,
        skin_tone_lightness=65,
        season="warm_spring",
        latitude=40.7128,
        longitude=-74.006,
        location_name="New York, NY",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    print(f"Created sample user (id={user.id})")

db.close()
