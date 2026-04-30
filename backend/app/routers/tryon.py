import io
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from PIL import Image
from google import genai

from app.core import store
from app.core.auth import get_current_user
from app.core.config import settings

router = APIRouter(prefix="/tryon", tags=["tryon"])


_PROMPT = (
    "Replace the clothing on the person in image 1 with the top shown in image 2 "
    "and the bottom shown in image 3. The output must clearly show the person "
    "wearing the new top and bottom — this is the primary goal.\n\n"
    "Image 1: a full-body photo of the person whose outfit you are changing.\n"
    "Image 2: an isolated top garment (shirt/blouse/sweater) on a white "
    "background.\n"
    "Image 3: an isolated bottom garment (pants/shorts/skirt) on a white "
    "background.\n\n"
    "Requirements:\n"
    "- The person in the output must be wearing the exact top from image 2 and "
    "the exact bottom from image 3. Match their silhouette, color, pattern, and "
    "material faithfully. Do not keep any of the person's original clothing.\n"
    "- Keep the person's face, skin tone, hair, body proportions, pose, and the "
    "original background from image 1. Do not change their identity.\n"
    "- Render the new garments with realistic fabric folds, draping, and shadows "
    "that match the lighting of image 1.\n"
    "- Output a single photorealistic image at the same aspect ratio as image 1. "
    "No text, watermarks, or borders."
)


def _open_image(upload: UploadFile, label: str) -> Image.Image:
    """Read an uploaded image and return RGB. RGBA inputs (e.g. SAM-cropped
    garments with transparent backgrounds) are composited onto white rather
    than flattened to black, since Gemini interprets isolated garments more
    reliably on a white field."""
    try:
        data = upload.file.read()
        img = Image.open(io.BytesIO(data))
        img.load()
        if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
            rgba = img.convert("RGBA")
            white = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
            return Image.alpha_composite(white, rgba).convert("RGB")
        return img.convert("RGB")
    except Exception as exc:
        raise HTTPException(400, f"Could not read {label} image: {exc}")


@router.post("/generate")
async def generate_tryon(
    body_photo: UploadFile = File(...),
    top: UploadFile = File(...),
    bottom: UploadFile = File(...),
    extra_instructions: str | None = Form(None),
):
    if not settings.GEMINI_API_KEY:
        raise HTTPException(
            500,
            "GEMINI_API_KEY is not configured on the server. "
            "Add it to backend/.env and restart.",
        )

    body_img = _open_image(body_photo, "body")
    top_img = _open_image(top, "top")
    bottom_img = _open_image(bottom, "bottom")

    prompt = _PROMPT
    if extra_instructions:
        prompt += f"\n\nAdditional styling notes: {extra_instructions.strip()}"

    client = genai.Client(api_key=settings.GEMINI_API_KEY)

    try:
        response = client.models.generate_content(
            model=settings.GEMINI_IMAGE_MODEL,
            contents=[prompt, body_img, top_img, bottom_img],
        )
    except Exception as exc:
        raise HTTPException(502, f"Gemini request failed: {exc}")

    if not response.candidates:
        raise HTTPException(502, "Gemini returned no candidates")

    for part in response.candidates[0].content.parts:
        inline = getattr(part, "inline_data", None)
        if inline and inline.data:
            mime = getattr(inline, "mime_type", None) or "image/png"
            return Response(content=inline.data, media_type=mime)

    text_parts = [
        getattr(p, "text", "") for p in response.candidates[0].content.parts
    ]
    blocked = " ".join(t for t in text_parts if t).strip()
    raise HTTPException(
        502,
        f"Gemini returned no image. {blocked or 'The model may have refused the request.'}",
    )


@router.post("/saved")
async def save_outfit(
    image: UploadFile = File(...),
    top_image_url: str | None = Form(None),
    bottom_image_url: str | None = Form(None),
    body_photo_url: str | None = Form(None),
    top_name: str | None = Form(None),
    bottom_name: str | None = Form(None),
    name: str | None = Form(None),
    current_user: dict = Depends(get_current_user),
):
    """
    Persist a try-on result the user just generated. The frontend re-uploads
    the rendered image bytes here along with references to the source
    garments / body photo so the saved-outfits view can display thumbnails.
    """
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    ext = Path(image.filename or "").suffix.lower() or ".png"
    if ext not in {".png", ".jpg", ".jpeg", ".webp"}:
        ext = ".png"
    filename = f"tryon_{uuid.uuid4()}{ext}"
    (upload_dir / filename).write_bytes(image.file.read())

    saved = store.add_saved_outfit(
        current_user["username"],
        {
            "name": name,
            "image_path": filename,
            "image_url": f"/uploads/{filename}",
            "top_image_url": top_image_url,
            "bottom_image_url": bottom_image_url,
            "body_photo_url": body_photo_url,
            "top_name": top_name,
            "bottom_name": bottom_name,
        },
    )
    return saved


@router.get("/saved")
def list_saved_outfits(current_user: dict = Depends(get_current_user)):
    return store.list_saved_outfits(current_user["username"])


@router.delete("/saved/{outfit_id}")
def delete_saved_outfit(outfit_id: str, current_user: dict = Depends(get_current_user)):
    saved = store.get_saved_outfit(current_user["username"], outfit_id)
    if not saved:
        raise HTTPException(404, "Saved outfit not found")

    file_path = Path(settings.UPLOAD_DIR) / saved["image_path"]
    if file_path.exists():
        file_path.unlink()

    store.delete_saved_outfit(current_user["username"], outfit_id)
    return {"detail": "deleted"}
