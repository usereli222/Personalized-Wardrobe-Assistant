from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+psycopg2://wardrobe:wardrobe@localhost:5432/wardrobe"
    UPLOAD_DIR: str = str(Path(__file__).resolve().parent.parent.parent.parent / "uploads")
    FIREBASE_CREDENTIALS_PATH: str = ""
    GEMINI_API_KEY: str = ""
    GEMINI_IMAGE_MODEL: str = "gemini-2.5-flash-image"
    GEMINI_VISION_MODEL: str = "gemini-2.5-flash"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
