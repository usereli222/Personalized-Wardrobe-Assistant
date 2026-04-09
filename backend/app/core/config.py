from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./wardrobe.db"
    OPENWEATHERMAP_API_KEY: str = ""
    UPLOAD_DIR: str = str(Path(__file__).resolve().parent.parent.parent.parent / "uploads")

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
