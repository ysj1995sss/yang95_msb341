from datetime import datetime, timedelta, timezone
from jose import jwt
from app.config import get_settings


def create_access_token(subject: str) -> str:
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    return jwt.encode(
        {"sub": subject, "exp": expire, "typ": "access"},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
