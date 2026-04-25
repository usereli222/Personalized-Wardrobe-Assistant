from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.core.config import settings
import app.core.database  # noqa: F401 — triggers Firebase initialization
from app.routers import users, wardrobe, recommendations

app = FastAPI(
    title="Wardrobe AI",
    description="Personalized wardrobe suggestions based on skin tone, weather, and color theory",
    version="0.1.0",
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve uploaded images
upload_path = Path(settings.UPLOAD_DIR)
upload_path.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(upload_path)), name="uploads")

# Routers
app.include_router(users.router, prefix="/api")
app.include_router(wardrobe.router, prefix="/api")
app.include_router(recommendations.router, prefix="/api")


@app.get("/")
def root():
    return {"message": "Wardrobe AI API", "docs": "/docs"}
