import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from PIL import Image

from app.core.auth import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.models.wardrobe import WardrobeItem
from app.schemas.wardrobe import WardrobeItemResponse
from app.services.color_extraction import extract_dominant_colors

router = APIRouter(prefix="/wardrobe", tags=["wardrobe"])

VALID_CATEGORIES = {"top", "bottom", "shoes", "accessory", "outerwear"}


@router.post("/items", response_model=WardrobeItemResponse)
async def upload_item(
    category: str = Form(...),
    name: str | None = Form(None),
    subcategory: str | None = Form(None),
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload a single clothing item image and extract its dominant colors."""
    if category not in VALID_CATEGORIES:
        raise HTTPException(status_code=400, detail=f"Category must be one of: {sorted(VALID_CATEGORIES)}")

    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    ext = Path(image.filename).suffix or ".png"
    filename = f"{uuid.uuid4()}{ext}"
    file_path = upload_dir / filename

    contents = await image.read()
    with open(file_path, "wb") as f:
        f.write(contents)

    img = Image.open(file_path)
    dominant_colors = extract_dominant_colors(img, n_colors=3)

    item = WardrobeItem(
        user_id=current_user.id,
        name=name,
        category=category,
        subcategory=subcategory,
        image_path=str(filename),
        dominant_colors=dominant_colors,
        secondary_colors=dominant_colors[1:] if len(dominant_colors) > 1 else [],
        source="uploaded",
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("/items", response_model=list[WardrobeItemResponse])
def list_items(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(WardrobeItem).filter(WardrobeItem.user_id == current_user.id).all()


@router.get("/items/{item_id}", response_model=WardrobeItemResponse)
def get_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = db.query(WardrobeItem).filter(
        WardrobeItem.id == item_id,
        WardrobeItem.user_id == current_user.id,
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@router.delete("/items/{item_id}")
def delete_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = db.query(WardrobeItem).filter(
        WardrobeItem.id == item_id,
        WardrobeItem.user_id == current_user.id,
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    file_path = Path(settings.UPLOAD_DIR) / item.image_path
    if file_path.exists():
        file_path.unlink()

    db.delete(item)
    db.commit()
    return {"detail": "Item deleted"}
