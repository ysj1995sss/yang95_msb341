"""Status from Gmail (spec 005 slice 2, decision 030).

The web app asks Google for read-only Gmail access in a separate consent step and hands the
refresh token to this API, which stores it encrypted in the user's folder. A scan asks Gmail
only for messages from job-application systems in the last 30 days and turns each into a
suggestion with the same email reader as pasting (applications/email_status.py). Nothing
changes until the user confirms a suggestion in Tracker. Disconnect revokes the access.

Gmail read access is a restricted Google scope: until Google's security review, only test users
listed in the Google project can connect, and Google shows them an "unverified app" warning.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Optional

import requests
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.config import get_settings
from app.workspace.context import Workspace, workspace

router = APIRouter(prefix="/v2", tags=["workspace"])

ATS_SENDERS = ("greenhouse.io", "greenhouse-mail.io", "lever.co", "hire.lever.co", "ashbyhq.com",
               "myworkdayjobs.com", "workday.com", "smartrecruiters.com")
QUERY = "from:(" + " OR ".join(ATS_SENDERS) + ") newer_than:30d"
GMAIL = "https://gmail.googleapis.com/gmail/v1/users/me"
TOKEN_URL = "https://oauth2.googleapis.com/token"
REVOKE_URL = "https://oauth2.googleapis.com/revoke"
TIMEOUT = 20


def _cipher():
    from cryptography.fernet import Fernet

    secret = get_settings().workspace_token_secret
    if not secret:
        raise HTTPException(400, "Gmail needs sign-in to be set up on this server.")
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(("gmail:" + secret).encode()).digest()))


def _path(owner_id: str):
    from resume_tailorer.identity import user_dir

    return user_dir(owner_id) / "gmail.json"


def _load(owner_id: str) -> Optional[dict]:
    try:
        return json.loads(_path(owner_id).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _save(owner_id: str, data: dict) -> None:
    path = _path(owner_id)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data), encoding="utf-8")
    os.replace(tmp, path)


def _client() -> tuple[str, str]:
    settings = get_settings()
    if not (settings.google_client_id and settings.google_client_secret):
        raise HTTPException(400, "Gmail isn't set up on this server (GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET).")
    return settings.google_client_id, settings.google_client_secret


def _access_token(owner_id: str) -> str:
    data = _load(owner_id)
    if not data:
        raise HTTPException(409, "Connect Gmail first.")
    client_id, client_secret = _client()
    refresh = _cipher().decrypt(data["refresh_token"].encode()).decode()
    response = requests.post(TOKEN_URL, data={"client_id": client_id, "client_secret": client_secret,
                                              "refresh_token": refresh, "grant_type": "refresh_token"}, timeout=TIMEOUT)
    if response.status_code != 200:
        raise HTTPException(409, "Gmail access has expired or was removed. Connect Gmail again.")
    return response.json()["access_token"]


@router.get("/gmail")
def gmail_status(ws: Workspace = Depends(workspace)):
    settings = get_settings()
    data = _load(ws.owner_id) or {}
    return {
        "available": bool(ws.owner.signed_in and settings.google_client_id and settings.google_client_secret),
        "connected": bool(data.get("refresh_token")),
        "connected_at": data.get("connected_at"),
        "last_scan": data.get("last_scan"),
    }


class Connect(BaseModel):
    refresh_token: str


@router.post("/gmail/connect")
def connect(body: Connect, ws: Workspace = Depends(workspace)):
    """Called by the web server after the Gmail consent step; the browser never sees the token."""
    if not ws.owner.signed_in:
        raise HTTPException(400, "Gmail needs sign-in.")
    _client()
    _save(ws.owner_id, {"refresh_token": _cipher().encrypt(body.refresh_token.encode()).decode(),
                        "connected_at": datetime.now(timezone.utc).isoformat(), "dismissed": []})
    return gmail_status(ws)


@router.delete("/gmail")
def disconnect(ws: Workspace = Depends(workspace)):
    data = _load(ws.owner_id)
    if data and data.get("refresh_token"):
        try:
            refresh = _cipher().decrypt(data["refresh_token"].encode()).decode()
            requests.post(REVOKE_URL, data={"token": refresh}, timeout=TIMEOUT)
        except Exception:  # removing our copy matters most; Google's side may already be gone
            pass
    try:
        _path(ws.owner_id).unlink()
    except OSError:
        pass
    return gmail_status(ws)


def _text(payload: dict) -> str:
    """The plain-text body of a Gmail message (or its HTML with tags stripped)."""
    from resume_tailorer.job_search.scrapers.board_scraper import strip_html

    def walk(part: dict) -> tuple[str, str]:
        plain, html = "", ""
        data = (part.get("body") or {}).get("data")
        if data:
            decoded = base64.urlsafe_b64decode(data + "=" * (-len(data) % 4)).decode("utf-8", "replace")
            if part.get("mimeType") == "text/plain":
                plain = decoded
            elif part.get("mimeType") == "text/html":
                html = decoded
        for child in part.get("parts") or []:
            p, h = walk(child)
            plain, html = plain or p, html or h
        return plain, html

    plain, html = walk(payload)
    return plain or strip_html(html)


@router.post("/gmail/scan")
def scan(ws: Workspace = Depends(workspace)):
    from resume_tailorer.applications.email_status import Candidate, read_email
    from resume_tailorer.ui.tracker_views import STATUS_WORDS

    from app.workspace.tracker_router import _rows

    token = _access_token(ws.owner_id)
    headers = {"Authorization": f"Bearer {token}"}
    listing = requests.get(f"{GMAIL}/messages", params={"q": QUERY, "maxResults": 25}, headers=headers, timeout=TIMEOUT)
    if listing.status_code != 200:
        raise HTTPException(502, "Gmail didn't answer. Try again in a minute.")
    data = _load(ws.owner_id) or {}
    dismissed = set(data.get("dismissed") or [])
    rows = [r for r, _ in _rows(ws)]
    candidates = [Candidate(r.application_id, r.company, r.role, r.status) for r in rows]
    by_id = {r.application_id: r for r in rows}
    suggestions = []
    for item in listing.json().get("messages") or []:
        if item["id"] in dismissed:
            continue
        message = requests.get(f"{GMAIL}/messages/{item['id']}", params={"format": "full"}, headers=headers, timeout=TIMEOUT)
        if message.status_code != 200:
            continue
        payload = message.json().get("payload") or {}
        head = {h["name"].lower(): h["value"] for h in payload.get("headers") or []}
        text = f"From: {head.get('from', '')}\nDate: {head.get('date', '')}\nSubject: {head.get('subject', '')}\n\n{_text(payload)}"
        reading = read_email(text, candidates)
        if reading.status is None or not reading.matches:
            continue
        chosen = reading.chosen
        current = by_id.get(chosen) if chosen else None
        if current is not None and current.status == reading.status:
            continue  # already up to date
        suggestions.append({
            "message_id": item["id"], "subject": reading.subject or head.get("subject", ""),
            "from": head.get("from", ""), "email_date": reading.email_date.isoformat() if reading.email_date else None,
            "status": reading.status.value, "status_label": STATUS_WORDS.get(reading.status, ""),
            "phrase": reading.phrase, "chosen": chosen,
            "options": [{"application_id": m.application_id,
                         "label": f"{by_id[m.application_id].role} at {by_id[m.application_id].company}",
                         "backwards": reading.moves_backwards(by_id[m.application_id].status)}
                        for m in reading.matches if m.application_id in by_id],
        })
    data["last_scan"] = datetime.now(timezone.utc).isoformat()
    _save(ws.owner_id, data)
    return {"suggestions": suggestions}


class Dismiss(BaseModel):
    message_id: str


@router.post("/gmail/dismiss")
def dismiss(body: Dismiss, ws: Workspace = Depends(workspace)):
    """Don't suggest this email again (also used after confirming it)."""
    data = _load(ws.owner_id)
    if not data:
        raise HTTPException(409, "Connect Gmail first.")
    data["dismissed"] = sorted(set(data.get("dismissed") or []) | {body.message_id})[-500:]
    _save(ws.owner_id, data)
    return {"dismissed": True}

