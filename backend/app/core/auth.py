"""
Auth dependency.

Verifies a Firebase ID token from the `Authorization: Bearer <token>` header,
upserts the corresponding User row in Postgres, and returns a dict that the
existing routers can consume (keyed off `username` for the in-memory store).
"""

from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from firebase_admin import auth as fb_auth
from sqlalchemy.orm import Session

from app.core import store
from app.core.database import SessionLocal
from app.core.firebase import verify_id_token
from app.models.user import User


bearer_scheme = HTTPBearer(auto_error=False)


def _upsert_user(db: Session, decoded: dict) -> User:
    uid = decoded["uid"]
    user = db.query(User).filter(User.firebase_uid == uid).first()
    if user is not None:
        return user

    user = User(
        firebase_uid=uid,
        email=decoded.get("email") or f"{uid}@firebase.local",
        name=decoded.get("name"),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _user_to_dict(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.firebase_uid,
        "email": user.email,
        "name": user.name,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "body_photo_path": store.get_body_photo_path(user.firebase_uid),
    }


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict:
    if creds is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        decoded = verify_id_token(creds.credentials)
    except (fb_auth.InvalidIdTokenError, fb_auth.ExpiredIdTokenError, fb_auth.RevokedIdTokenError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    db = SessionLocal()
    try:
        user = _upsert_user(db, decoded)
        store.ensure_user_buckets(user.firebase_uid)
        return _user_to_dict(user)
    finally:
        db.close()
