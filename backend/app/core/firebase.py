"""
Firebase Admin SDK initialization.

Call `init_firebase()` once at app startup. The module guards against
double-init so reloads (uvicorn --reload) don't blow up.
"""

from __future__ import annotations

import firebase_admin
from firebase_admin import auth as fb_auth, credentials

from app.core.config import settings


_initialized = False


def init_firebase() -> None:
    global _initialized
    if _initialized or firebase_admin._apps:
        _initialized = True
        return

    if not settings.FIREBASE_CREDENTIALS_PATH:
        raise RuntimeError(
            "FIREBASE_CREDENTIALS_PATH is not set. Download a service-account "
            "JSON from Firebase Console -> Project Settings -> Service Accounts, "
            "save it locally, and point FIREBASE_CREDENTIALS_PATH at it."
        )

    cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
    firebase_admin.initialize_app(cred)
    _initialized = True


def verify_id_token(token: str) -> dict:
    """Verify a Firebase ID token and return the decoded claims."""
    return fb_auth.verify_id_token(token)
