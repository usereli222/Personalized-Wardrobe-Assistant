import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from google.cloud.firestore_v1.base_client import BaseClient
from PIL import Image

from app.core.config import settings
from app.core.database import get_db
from app.models.wardrobe import item_to_dict, doc_to_item
from app.schemas.wardrobe import WardrobeItemResponse
from app.services.color_extraction import extract_dominant_colors

router = APIRouter(prefix="/wardrobe", tags=["wardrobe"])


@router.post("/items", response_model=WardrobeItemResponse)
async def upload_item(
    user_id: str = Form(...),
    category: str = Form(...),
    name: str = Form(None),
    image: UploadFile = File(...),
    db: BaseClient = Depends(get_db),
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

    # Save to Firestore
    doc_data = item_to_dict(
        user_id=user_id,
        name=name,
        category=category,
        image_path=str(filename),
        dominant_colors=dominant_colors,
        secondary_colors=dominant_colors[1:] if len(dominant_colors) > 1 else [],
    )
    _, doc_ref = db.collection("wardrobe_items").add(doc_data)
    doc = doc_ref.get()
    return doc_to_item(doc)


@router.get("/items", response_model=list[WardrobeItemResponse])
def list_items(user_id: str, db: BaseClient = Depends(get_db)):
    """List all wardrobe items for a user."""
    docs = db.collection("wardrobe_items").where("user_id", "==", user_id).get()
    return [doc_to_item(doc) for doc in docs]


@router.get("/items/{item_id}", response_model=WardrobeItemResponse)
def get_item(item_id: str, db: BaseClient = Depends(get_db)):
    """Get a specific wardrobe item."""
    doc = db.collection("wardrobe_items").document(item_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Item not found")
    return doc_to_item(doc)


@router.delete("/items/{item_id}")
def delete_item(item_id: str, db: BaseClient = Depends(get_db)):
    """Delete a wardrobe item."""
    doc_ref = db.collection("wardrobe_items").document(item_id)
    doc = doc_ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Item not found")

    # Delete image file
    item_data = doc.to_dict()
    file_path = Path(settings.UPLOAD_DIR) / item_data["image_path"]
    if file_path.exists():
        file_path.unlink()

    doc_ref.delete()
    return {"detail": "Item deleted"}
