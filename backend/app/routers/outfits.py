"""
Outfits routes — pulls suggestions from the in-memory wardrobe store.

Mentees: the suggester stub lives in `app/services/outfit_suggester.py`.
Replace it without changing this router.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core import store
from app.core.auth import get_current_user
from app.services.outfit_suggester import suggest_outfits


router = APIRouter(prefix="/outfits", tags=["outfits"])


@router.get("/suggestions")
def suggestions(current_user: dict = Depends(get_current_user)):
    items = store.list_wardrobe_items(current_user["username"])
    return suggest_outfits(items)
