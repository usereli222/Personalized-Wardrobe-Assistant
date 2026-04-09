import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from PIL import Image

from app.core.config import settings
from app.core.database import get_db
from app.models.wardrobe import WardrobeItem
from app.schemas.wardrobe import WardrobeItemResponse
from app.services.color_extraction import extract_dominant_colors

router = APIRouter(prefix="/wardrobe", tags=["wardrobe"])


@router.post("/items", response_model=WardrobeItemResponse)
async def upload_item(
    user_id: int = Form(...),
    category: str = Form(...),
    name: str = Form(None),
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Upload a clothing item image and extract its dominant colors."""
    valid_categories = {"top", "bottom", "shoes", "accessory", "outerwear"}
    if category not in valid_categories:
        raise HTTPException(status_code=400, detail=f"Category must be one of: {valid_categories}")

    # Save image
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    ext = Path(image.filename).suffix or ".png"
    filename = f"{uuid.uuid4()}{ext}"
    file_path = upload_dir / filename

    contents = await image.read()
    with open(file_path, "wb") as f:
        f.write(contents)

    # Extract colors
    img = Image.open(file_path)
    dominant_colors = extract_dominant_colors(img, n_colors=3)

    # Save to DB
    item = WardrobeItem(
        user_id=user_id,
        name=name,
        category=category,
        image_path=str(filename),
        dominant_colors=dominant_colors,
        secondary_colors=dominant_colors[1:] if len(dominant_colors) > 1 else [],
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("/items", response_model=list[WardrobeItemResponse])
def list_items(user_id: int, db: Session = Depends(get_db)):
    """List all wardrobe items for a user."""
    items = db.query(WardrobeItem).filter(WardrobeItem.user_id == user_id).all()
    return items


@router.get("/items/{item_id}", response_model=WardrobeItemResponse)
def get_item(item_id: int, db: Session = Depends(get_db)):
    """Get a specific wardrobe item."""
    item = db.query(WardrobeItem).filter(WardrobeItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@router.delete("/items/{item_id}")
def delete_item(item_id: int, db: Session = Depends(get_db)):
    """Delete a wardrobe item."""
    item = db.query(WardrobeItem).filter(WardrobeItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    # Delete image file
    file_path = Path(settings.UPLOAD_DIR) / item.image_path
    if file_path.exists():
        file_path.unlink()

    db.delete(item)
    db.commit()
    return {"detail": "Item deleted"}
