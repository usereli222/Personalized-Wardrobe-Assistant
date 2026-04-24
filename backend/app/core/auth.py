from pathlib import Path

import firebase_admin
from firebase_admin import auth as fb_auth, credentials
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User


_firebase_initialized = False


def _init_firebase() -> bool:
    global _firebase_initialized
    if _firebase_initialized:
        return True
    if not settings.FIREBASE_CREDENTIALS_PATH:
        return False
    cred_path = Path(settings.FIREBASE_CREDENTIALS_PATH)
    if not cred_path.exists():
        return False
    cred = credentials.Certificate(str(cred_path))
    firebase_admin.initialize_app(cred)
    _firebase_initialized = True
    return True


bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if not _init_firebase():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Firebase auth is not configured. Set FIREBASE_CREDENTIALS_PATH in .env.",
        )
    if creds is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        decoded = fb_auth.verify_id_token(creds.credentials)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired Firebase ID token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    uid = decoded["uid"]
    email = decoded.get("email", "")

    user = db.query(User).filter(User.firebase_uid == uid).first()
    if user is None:
        user = User(firebase_uid=uid, email=email, name=decoded.get("name"))
        db.add(user)
        db.commit()
        db.refresh(user)
    return user
