from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user, security
from app.config import get_settings
from app.db import get_db
from app.devices.tokens import device_token_expires_at, generate_device_token, hash_device_token
from app.models import DeviceToken, User
from app.schemas.device import DeviceTokenOut

router = APIRouter(prefix="/devices", tags=["devices"])


@router.post("/token", response_model=DeviceTokenOut)
def create_device_token(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    plain = generate_device_token()
    expires_at = device_token_expires_at()
    row = DeviceToken(
        user_id=user.id,
        token_hash=hash_device_token(plain),
        expires_at=expires_at,
    )
    db.add(row)
    db.commit()
    return DeviceTokenOut(token=plain, expires_at=expires_at)


@router.delete("/token", status_code=status.HTTP_204_NO_CONTENT)
def revoke_device_token(
    creds: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    settings = get_settings()
    try:
        payload = jwt.decode(
            creds.credentials, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        user_id = payload.get("sub")
        if user_id:
            db.query(DeviceToken).filter(DeviceToken.user_id == user_id).delete()
            db.commit()
            return
    except JWTError:
        pass

    token_hash = hash_device_token(creds.credentials)
    row = db.query(DeviceToken).filter(DeviceToken.token_hash == token_hash).one_or_none()
    if not row:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    db.delete(row)
    db.commit()
