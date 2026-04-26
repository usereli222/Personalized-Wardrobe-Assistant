import io
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from PIL import Image
from google import genai

from app.core.config import settings

router = APIRouter(prefix="/tryon", tags=["tryon"])


_PROMPT = (
    "You are a virtual try-on assistant. The first image is a full-body photo of a "
    "person. The second image is a top (shirt) and the third image is bottoms "
    "(pants/shorts/skirt). Generate a single new full-body photograph of the SAME "
    "person wearing both garments. "
    "Strict requirements: "
    "1) Preserve the person's face, skin tone, hair, body proportions, pose, and the "
    "original background exactly as in the first image. Do NOT change identity. "
    "2) Render the garments realistically with natural fabric folds, draping, and "
    "shadows that match the lighting of the original photo. "
    "3) Replace the clothing the person is currently wearing with the provided "
    "garments. Do not add extra clothing items. "
    "4) Match the silhouette, color, pattern, and material of each provided garment "
    "as faithfully as possible. "
    "5) Output a single photorealistic image at the same aspect ratio as the body "
    "photo. No text, watermarks, or borders."
)


def _open_image(upload: UploadFile, label: str) -> Image.Image:
    try:
        data = upload.file.read()
        img = Image.open(io.BytesIO(data))
        img.load()
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
