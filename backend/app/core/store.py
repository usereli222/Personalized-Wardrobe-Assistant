"""
In-memory data store — STUB.

Everything here lives in process memory and resets when uvicorn restarts.
Mentees: replace each module-level dict with a real database table
(SQLAlchemy models already exist under app/models/). The functions in the
routers should be the only code that touches this module, so swapping it
out is a single-file change in each router.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


# username -> { password_hash, email, created_at, body_photo_path }
_users: dict[str, dict[str, Any]] = {}

# username -> list[{ logged_in_at, ip, user_agent }]
_login_history: dict[str, list[dict[str, Any]]] = {}

# username -> list[wardrobe_item dict]
_wardrobe: dict[str, list[dict[str, Any]]] = {}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---- users ----------------------------------------------------------------

def create_user(username: str, email: str, password_hash: str) -> dict[str, Any]:
    user = {
        "username": username,
        "email": email,
        "password_hash": password_hash,
        "created_at": now(),
        "body_photo_path": None,
    }
    _users[username] = user
    _login_history.setdefault(username, [])
    _wardrobe.setdefault(username, [])
    return user


def get_user(username: str) -> dict[str, Any] | None:
    return _users.get(username)


def set_body_photo(username: str, path: str) -> None:
    if username in _users:
        _users[username]["body_photo_path"] = path


# ---- login history --------------------------------------------------------

def record_login(username: str, ip: str | None, user_agent: str | None) -> None:
    _login_history.setdefault(username, []).append(
        {"logged_in_at": now(), "ip": ip, "user_agent": user_agent}
    )


def get_login_history(username: str) -> list[dict[str, Any]]:
    return list(reversed(_login_history.get(username, [])))


# ---- wardrobe -------------------------------------------------------------

def add_wardrobe_item(username: str, item: dict[str, Any]) -> dict[str, Any]:
    item.setdefault("id", str(uuid4()))
    item.setdefault("created_at", now())
    _wardrobe.setdefault(username, []).append(item)
    return item


def list_wardrobe_items(username: str) -> list[dict[str, Any]]:
    return list(_wardrobe.get(username, []))


def get_wardrobe_item(username: str, item_id: str) -> dict[str, Any] | None:
    for item in _wardrobe.get(username, []):
        if item["id"] == item_id:
            return item
    return None


def delete_wardrobe_item(username: str, item_id: str) -> bool:
    items = _wardrobe.get(username, [])
    for i, item in enumerate(items):
        if item["id"] == item_id:
            items.pop(i)
            return True
    return False
