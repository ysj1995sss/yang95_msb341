"""Who is calling the workspace API (spec 009, decision 029).

The browser never talks to this API directly. The Next.js server (apps/web) signs a
short-lived HS256 token for the signed-in Google user with WORKSPACE_TOKEN_SECRET and
forwards the request. The owner id is derived exactly as the Streamlit app derives it
(resume_tailorer.identity), so both frontends read and write the same user's data.

With no secret configured, outside production, every request is the local single-user
owner, like the Streamlit app without sign-in.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from fastapi import Header, HTTPException, status
from jose import JWTError, jwt

from app.config import get_settings
from resume_tailorer.identity import resolve_identity

ALGORITHM = "HS256"
AUDIENCE = "job-copilot-workspace"


@dataclass(frozen=True)
class Owner:
    owner_id: str
    name: str
    signed_in: bool
    email: str = ""


def owner_from_token(token: str, secret: str) -> Owner:
    try:
        claims = jwt.decode(token, secret, algorithms=[ALGORITHM], audience=AUDIENCE)
    except JWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sign in again.") from exc
    subject = claims.get("sub")
    if not subject:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sign in again.")
    identity = resolve_identity(True, {"is_logged_in": True, "sub": subject, "name": claims.get("name") or ""})
    return Owner(identity.owner_id, identity.display_name, True, str(claims.get("email") or ""))


def current_owner(authorization: Optional[str] = Header(default=None)) -> Owner:
    settings = get_settings()
    secret = settings.workspace_token_secret
    if authorization and authorization.lower().startswith("bearer "):
        if not secret:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sign-in isn't set up on this server.")
        return owner_from_token(authorization.split(" ", 1)[1].strip(), secret)
    if not secret and settings.app_env.lower() != "production":
        local = resolve_identity(False, {})
        return Owner(local.owner_id, local.display_name, False)
    raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sign in to continue.")
