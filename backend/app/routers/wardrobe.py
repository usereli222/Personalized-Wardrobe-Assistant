"""
Wardrobe routes.

Items live in `app/core/store.py` (in-memory) and uploaded image bytes go
to `settings.UPLOAD_DIR` on disk. Each item carries a FashionCLIP embedding
(np.ndarray, 512 floats) used by /items/{id}/similar and by the FAISS-based
outfit suggester.

The embedding is stored under the "embedding" key in the in-memory dict
but stripped from the JSON response — it's a 512-float vector (not JSON-
serializable as a numpy array, and not interesting to the frontend).
"""

from __future__ import annotations

import io
import uuid
import zipfile
from pathlib import Path
from typing import Any

import numpy as np
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError

from app.core import store
from app.core.auth import get_current_user
from app.core.config import settings
from app.services.categorizer import CATEGORIES, categorize_item
from app.services.color_extraction import extract_dominant_colors


_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}


router = APIRouter(prefix="/wardrobe", tags=["wardrobe"])


def _serialize_item(item: dict) -> dict:
    """Strip the numpy embedding before returning over JSON."""
    return {k: v for k, v in item.items() if k != "embedding"}


def _save_upload(image: UploadFile) -> tuple[Path, str]:
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    ext = Path(image.filename or "").suffix or ".png"
    filename = f"{uuid.uuid4()}{ext}"
    path = upload_dir / filename
    path.write_bytes(image.file.read())
    return path, filename


@router.post("/items")
async def upload_item(
    image: UploadFile = File(...),
    name: str | None = Form(None),
    category: str | None = Form(None),
    current_user: dict = Depends(get_current_user),
):
    """
    Upload one clothing item. The FashionCLIP categorizer assigns a category
    AND produces a 512-dim embedding stored on the item for later similarity
    search and outfit matching.
    """
    path, filename = _save_upload(image)
    img = Image.open(path)

    predicted = categorize_item(img)
    if category is None:
        category = predicted["category"]
        subcategory = predicted["subcategory"]
    else:
        if category not in CATEGORIES:
            raise HTTPException(400, f"category must be one of {list(CATEGORIES)}")
        subcategory = None

    try:
        dominant_colors = extract_dominant_colors(img, n_colors=3, remove_bg=False)
    except Exception:
        dominant_colors = []

    item = store.add_wardrobe_item(
        current_user["username"],
        {
            "name": name,
            "category": category,
            "subcategory": subcategory,
            "image_path": filename,
            "image_url": f"/uploads/{filename}",
            "dominant_colors": dominant_colors,
            "embedding": predicted["embedding"],  # np.ndarray (512,) float32, L2-normed
        },
    )
    return _serialize_item(item)


@router.get("/items")
def list_items(current_user: dict = Depends(get_current_user)):
    return [_serialize_item(it) for it in store.list_wardrobe_items(current_user["username"])]


@router.get("/items/{item_id}")
def get_item(item_id: str, current_user: dict = Depends(get_current_user)):
    item = store.get_wardrobe_item(current_user["username"], item_id)
    if not item:
        raise HTTPException(404, "Item not found")
    return _serialize_item(item)


@router.get("/items/{item_id}/similar")
def similar_items(
    item_id: str,
    k: int = 8,
    current_user: dict = Depends(get_current_user),
):
    """
    Return up to `k` items from the user's wardrobe most similar to the
    given item, ranked by FashionCLIP cosine similarity. Excludes the
    source item from results.
    """
    src = store.get_wardrobe_item(current_user["username"], item_id)
    if not src:
        raise HTTPException(404, "Item not found")

    src_emb = src.get("embedding")
    if src_emb is None or not isinstance(src_emb, np.ndarray) or not src_emb.any():
        raise HTTPException(409, "Source item has no embedding (re-upload it).")

    others = [
        it for it in store.list_wardrobe_items(current_user["username"])
        if it["id"] != item_id
        and isinstance(it.get("embedding"), np.ndarray)
        and it["embedding"].any()
    ]
    if not others:
        return []

    matrix = np.stack([it["embedding"] for it in others])  # (M, 512)
    scores = matrix @ src_emb  # (M,)
    order = np.argsort(-scores)[:k]

    return [
        {**_serialize_item(others[int(i)]), "similarity": round(float(scores[int(i)]), 4)}
        for i in order
    ]


@router.delete("/items/{item_id}")
def delete_item(item_id: str, current_user: dict = Depends(get_current_user)):
    item = store.get_wardrobe_item(current_user["username"], item_id)
    if not item:
        raise HTTPException(404, "Item not found")

    file_path = Path(settings.UPLOAD_DIR) / item["image_path"]
    if file_path.exists():
        file_path.unlink()

    store.delete_wardrobe_item(current_user["username"], item_id)
    return {"detail": "deleted"}


def _ingest_image_bytes(data: bytes, original_name: str, username: str) -> dict | None:
    """Save bytes to disk, classify (category + embedding), and add to the
    wardrobe store. Returns the new item, or None if the bytes couldn't be
    parsed as an image."""
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except (UnidentifiedImageError, OSError):
        return None

    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    ext = Path(original_name).suffix.lower() if original_name else ""
    if ext not in _IMAGE_EXTS:
        ext = ".png"
    filename = f"{uuid.uuid4()}{ext}"
    (upload_dir / filename).write_bytes(data)

    predicted = categorize_item(img.convert("RGB"))
    try:
        dominant_colors = extract_dominant_colors(img.convert("RGBA"), n_colors=3, remove_bg=False)
    except Exception:
        dominant_colors = []

    return store.add_wardrobe_item(
        username,
        {
            "name": Path(original_name).stem if original_name else None,
            "category": predicted["category"],
            "subcategory": predicted["subcategory"],
            "image_path": filename,
            "image_url": f"/uploads/{filename}",
            "dominant_colors": dominant_colors,
            "embedding": predicted["embedding"],
        },
    )


@router.post("/items/bulk")
async def bulk_upload_items(
    archive: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """
    Upload a .zip of clothing images. Each entry is opened, classified by
    FashionCLIP, and saved as a wardrobe item with its embedding. Returns
    the list of items created (skipping anything that wasn't a readable
    image).
    """
    raw = await archive.read()
    try:
        zf = zipfile.ZipFile(io.BytesIO(raw))
    except zipfile.BadZipFile:
        raise HTTPException(400, "Not a valid zip archive")

    created: list[dict] = []
    skipped: list[str] = []
    for info in zf.infolist():
        if info.is_dir():
            continue
        # Skip macOS resource forks and dotfiles
        name = info.filename
        if name.startswith("__MACOSX/") or Path(name).name.startswith("."):
            continue
        if Path(name).suffix.lower() not in _IMAGE_EXTS:
            skipped.append(name)
            continue
        try:
            data = zf.read(info)
        except Exception:
            skipped.append(name)
            continue
        item = _ingest_image_bytes(data, Path(name).name, current_user["username"])
        if item is None:
            skipped.append(name)
        else:
            created.append(_serialize_item(item))

    return {"created": created, "skipped": skipped}


@router.post("/body-photo")
async def upload_body_photo(
    image: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    _, filename = _save_upload(image)
    store.set_body_photo(current_user["username"], filename)
    return {"body_photo_url": f"/uploads/{filename}"}


@router.get("/body-photo")
def get_body_photo(current_user: dict = Depends(get_current_user)):
    path = current_user.get("body_photo_path")
    if not path:
        raise HTTPException(404, "No body photo uploaded yet")
    return {"body_photo_url": f"/uploads/{path}"}
