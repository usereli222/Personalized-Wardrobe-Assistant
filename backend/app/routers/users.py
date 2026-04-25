from fastapi import APIRouter, Depends, HTTPException
from google.cloud.firestore_v1.base_client import BaseClient

from app.core.database import get_db
from app.models.user import user_to_dict, doc_to_user
from app.schemas.user import UserCreate, UserLogin, UserUpdate, UserResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/", response_model=UserResponse)
def create_user(user_in: UserCreate, db: BaseClient = Depends(get_db)):
    # Check username uniqueness
    existing = db.collection("users").where("username", "==", user_in.username).limit(1).get()
    if list(existing):
        raise HTTPException(status_code=409, detail="Username already taken")

    doc_data = user_to_dict(user_in)
    _, doc_ref = db.collection("users").add(doc_data)
    doc = doc_ref.get()
    return UserResponse.from_db(doc_to_user(doc))


@router.post("/login", response_model=UserResponse)
def login_user(credentials: UserLogin, db: BaseClient = Depends(get_db)):
    docs = list(db.collection("users").where("username", "==", credentials.username).limit(1).get())
    if not docs:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse.from_db(doc_to_user(docs[0]))


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: str, db: BaseClient = Depends(get_db)):
    doc = db.collection("users").document(user_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse.from_db(doc_to_user(doc))


@router.patch("/{user_id}", response_model=UserResponse)
def update_user(user_id: str, user_in: UserUpdate, db: BaseClient = Depends(get_db)):
    doc_ref = db.collection("users").document(user_id)
    doc = doc_ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="User not found")

    updates = {}
    if user_in.name is not None:
        updates["name"] = user_in.name
    if user_in.skin_tone is not None:
        updates["skin_tone_hue"] = user_in.skin_tone.h
        updates["skin_tone_saturation"] = user_in.skin_tone.s
        updates["skin_tone_lightness"] = user_in.skin_tone.l
    if user_in.season is not None:
        updates["season"] = user_in.season
    if user_in.latitude is not None:
        updates["latitude"] = user_in.latitude
    if user_in.longitude is not None:
        updates["longitude"] = user_in.longitude
    if user_in.location_name is not None:
        updates["location_name"] = user_in.location_name

    if updates:
        doc_ref.update(updates)

    doc = doc_ref.get()
    return UserResponse.from_db(doc_to_user(doc))
