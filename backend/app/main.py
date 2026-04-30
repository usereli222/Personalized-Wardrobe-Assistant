from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.core.config import settings
from app.routers import auth, outfits, tryon, wardrobe
from app.services import ml_pipeline

app = FastAPI(
    title="Wardrobe AI",
    description="Outfit recommendations based on scraped style trends matched to your wardrobe",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

upload_path = Path(settings.UPLOAD_DIR)
upload_path.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(upload_path)), name="uploads")

# Outfit-library reference images live next to the cache, served read-only.
# Built by scripts/build_library.py — directory may not exist yet, hence the mkdir.
_library_images = Path(__file__).resolve().parents[2] / "data" / "library_cache" / "images"
_library_images.mkdir(parents=True, exist_ok=True)
app.mount("/library", StaticFiles(directory=str(_library_images)), name="library")

app.include_router(auth.router, prefix="/api")
app.include_router(wardrobe.router, prefix="/api")
app.include_router(outfits.router, prefix="/api")
app.include_router(tryon.router, prefix="/api")


@app.get("/")
def root():
    return {"message": "Wardrobe AI API", "docs": "/docs"}


@app.post("/api/health/warm")
def warm_models():
    """
    Trigger the cold-start of FashionCLIP and the FAISS outfit-library
    index. Call this once at frontend boot so the first user upload
    isn't the request that pays the ~10-30s model-load cost.

    Returns a status dict; safe to call repeatedly (no-op after first
    successful load).
    """
    return ml_pipeline.warm()
