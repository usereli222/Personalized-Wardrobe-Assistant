import firebase_admin
from firebase_admin import credentials, firestore

from app.core.config import settings

cred = credentials.Certificate(settings.FIREBASE_SERVICE_ACCOUNT_PATH)
firebase_admin.initialize_app(cred)

db = firestore.client()


def get_db():
    """FastAPI dependency — returns the Firestore client."""
    return db
