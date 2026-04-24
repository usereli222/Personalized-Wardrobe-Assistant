from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.user import UserUpdate, UserResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
def read_me(current_user: User = Depends(get_current_user)):
    return UserResponse.from_db(current_user)


@router.patch("/me", response_model=UserResponse)
def update_me(
    user_in: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user_in.name is not None:
        current_user.name = user_in.name
    if user_in.skin_tone is not None:
        current_user.skin_tone_hue = user_in.skin_tone.h
        current_user.skin_tone_saturation = user_in.skin_tone.s
        current_user.skin_tone_lightness = user_in.skin_tone.l

    db.commit()
    db.refresh(current_user)
    return UserResponse.from_db(current_user)
