"""
In-memory data store — STUB.

Everything here lives in process memory and resets when uvicorn restarts.
The User table itself lives in Postgres (see app/models/user.py); this
store is keyed by Firebase UID and holds per-user app data (body photo,
wardrobe items, login history) until those are also moved to the DB.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


# uid -> { body_photo_path }
_users: dict[str, dict[str, Any]] = {}

# uid -> list[{ logged_in_at, ip, user_agent }]
_login_history: dict[str, list[dict[str, Any]]] = {}

# uid -> list[wardrobe_item dict]
_wardrobe: dict[str, list[dict[str, Any]]] = {}

# uid -> list[saved_outfit dict]  (try-on results the user explicitly saved)
_saved_outfits: dict[str, list[dict[str, Any]]] = {}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---- users ----------------------------------------------------------------

def ensure_user_buckets(uid: str) -> None:
    """Make sure the per-user dicts/lists exist for a Firebase UID."""
    _users.setdefault(uid, {"body_photo_path": None})
    _login_history.setdefault(uid, [])
    _wardrobe.setdefault(uid, [])


def get_body_photo_path(uid: str) -> str | None:
    return _users.get(uid, {}).get("body_photo_path")


def set_body_photo(uid: str, path: str) -> None:
    _users.setdefault(uid, {"body_photo_path": None})["body_photo_path"] = path


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


# ---- saved try-on outfits -------------------------------------------------

def add_saved_outfit(username: str, outfit: dict[str, Any]) -> dict[str, Any]:
    outfit.setdefault("id", str(uuid4()))
    outfit.setdefault("created_at", now())
    _saved_outfits.setdefault(username, []).append(outfit)
    return outfit


def list_saved_outfits(username: str) -> list[dict[str, Any]]:
    # Newest first.
    return list(reversed(_saved_outfits.get(username, [])))


def get_saved_outfit(username: str, outfit_id: str) -> dict[str, Any] | None:
    for outfit in _saved_outfits.get(username, []):
        if outfit["id"] == outfit_id:
            return outfit
    return None


def delete_saved_outfit(username: str, outfit_id: str) -> bool:
    outfits = _saved_outfits.get(username, [])
    for i, outfit in enumerate(outfits):
        if outfit["id"] == outfit_id:
            outfits.pop(i)
            return True
    return False
