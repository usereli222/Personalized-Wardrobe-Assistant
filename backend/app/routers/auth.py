"""
Auth routes.

Firebase handles sign-up and sign-in client-side. The backend just
verifies the resulting ID token via `get_current_user` and exposes:

- POST /auth/login-event   — record that the client just signed in
- GET  /auth/me            — return the authed user's profile
- GET  /auth/login-history — recent login events for the authed user
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel

from app.core import store
from app.core.auth import get_current_user


router = APIRouter(prefix="/auth", tags=["auth"])


class UserOut(BaseModel):
    username: str
    email: str
    created_at: str | None
    has_body_photo: bool


class LoginEventOut(BaseModel):
    logged_in_at: str
    ip: str | None = None
    user_agent: str | None = None


def _user_out(user: dict) -> UserOut:
    return UserOut(
        username=user["username"],
        email=user["email"],
        created_at=user["created_at"],
        has_body_photo=bool(user.get("body_photo_path")),
    )


@router.post("/login-event", status_code=status.HTTP_204_NO_CONTENT)
def login_event(request: Request, current_user: dict = Depends(get_current_user)):
    store.record_login(
        current_user["username"],
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.get("/me", response_model=UserOut)
def me(current_user: dict = Depends(get_current_user)):
    return _user_out(current_user)


@router.get("/login-history", response_model=list[LoginEventOut])
def login_history(current_user: dict = Depends(get_current_user)):
    return [LoginEventOut(**e) for e in store.get_login_history(current_user["username"])]
