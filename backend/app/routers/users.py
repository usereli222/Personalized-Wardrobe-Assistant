from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate, UserResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/", response_model=UserResponse)
def create_user(user_in: UserCreate, db: Session = Depends(get_db)):
    user = User(
        name=user_in.name,
        skin_tone_hue=user_in.skin_tone.h if user_in.skin_tone else None,
        skin_tone_saturation=user_in.skin_tone.s if user_in.skin_tone else None,
        skin_tone_lightness=user_in.skin_tone.l if user_in.skin_tone else None,
        season=user_in.season,
        latitude=user_in.latitude,
        longitude=user_in.longitude,
        location_name=user_in.location_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserResponse.from_db(user)


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse.from_db(user)


@router.patch("/{user_id}", response_model=UserResponse)
def update_user(user_id: int, user_in: UserUpdate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user_in.name is not None:
        user.name = user_in.name
    if user_in.skin_tone is not None:
        user.skin_tone_hue = user_in.skin_tone.h
        user.skin_tone_saturation = user_in.skin_tone.s
        user.skin_tone_lightness = user_in.skin_tone.l
    if user_in.season is not None:
        user.season = user_in.season
    if user_in.latitude is not None:
        user.latitude = user_in.latitude
    if user_in.longitude is not None:
        user.longitude = user_in.longitude
    if user_in.location_name is not None:
        user.location_name = user_in.location_name

    db.commit()
    db.refresh(user)
    return UserResponse.from_db(user)
