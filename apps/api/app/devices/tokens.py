import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from app.config import get_settings


def hash_device_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def generate_device_token() -> str:
    return secrets.token_urlsafe(32)


def device_token_expires_at() -> datetime:
    settings = get_settings()
    return datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(
        minutes=settings.device_token_expire_minutes
    )
