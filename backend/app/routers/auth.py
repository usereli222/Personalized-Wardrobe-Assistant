"""
Auth routes — STUB persistence.

User accounts and login history live in `app/core/store.py` (in-memory).
Mentees: swap the `store` calls for real DB queries against the SQLAlchemy
models in `app/models/user.py`. The route shapes here are the contract —
keep them stable so the frontend doesn't have to change.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr

from app.core import store
from app.core.auth import get_current_user
from app.core.security import create_token, hash_password, verify_password


router = APIRouter(prefix="/auth", tags=["auth"])


class SignupIn(BaseModel):
    username: str
    email: EmailStr
    password: str


class LoginIn(BaseModel):
    username: str
    password: str


class TokenOut(BaseModel):
    token: str
    username: str


class UserOut(BaseModel):
    username: str
    email: str
    created_at: str
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


@router.post("/signup", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def signup(payload: SignupIn, request: Request):
    if store.get_user(payload.username):
        raise HTTPException(status_code=409, detail="Username already taken")

    store.create_user(
        username=payload.username,
        email=payload.email,
        password_hash=hash_password(payload.password),
    )
    store.record_login(
        payload.username,
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return TokenOut(token=create_token(payload.username), username=payload.username)


@router.post("/login", response_model=TokenOut)
def login(payload: LoginIn, request: Request):
    user = store.get_user(payload.username)
    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    store.record_login(
        payload.username,
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return TokenOut(token=create_token(payload.username), username=payload.username)


@router.get("/me", response_model=UserOut)
def me(current_user: dict = Depends(get_current_user)):
    return _user_out(current_user)


@router.get("/login-history", response_model=list[LoginEventOut])
def login_history(current_user: dict = Depends(get_current_user)):
    return [LoginEventOut(**e) for e in store.get_login_history(current_user["username"])]
