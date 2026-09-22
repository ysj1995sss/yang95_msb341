from datetime import datetime

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from app.config import get_settings
from app.db import get_db
from app.devices.tokens import hash_device_token
from app.models import DeviceToken, User

security = HTTPBearer()


def _user_from_access_jwt(credentials: str, db: Session) -> User | None:
    settings = get_settings()
    try:
        payload = jwt.decode(
            credentials, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        user_id = payload.get("sub")
        if not user_id:
            return None
    except JWTError:
        return None
    return db.get(User, user_id)


def _user_from_device_token(credentials: str, db: Session) -> User | None:
    token_hash = hash_device_token(credentials)
    row = db.query(DeviceToken).filter(DeviceToken.token_hash == token_hash).one_or_none()
    if not row or row.expires_at < datetime.utcnow():
        return None
    return db.get(User, row.user_id)


def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    user = _user_from_access_jwt(creds.credentials, db)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return user


def get_current_user_access_or_device(
    creds: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    user = _user_from_access_jwt(creds.credentials, db)
    if user:
        return user
    user = _user_from_device_token(creds.credentials, db)
    if user:
        return user
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
