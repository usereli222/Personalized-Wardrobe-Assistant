from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    FIREBASE_SERVICE_ACCOUNT_PATH: str = "./firebase-service-account.json"
    OPENWEATHERMAP_API_KEY: str = ""
    UPLOAD_DIR: str = str(Path(__file__).resolve().parent.parent.parent.parent / "uploads")

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
