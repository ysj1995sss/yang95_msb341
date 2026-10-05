"""Your data (decision 030): download everything, delete everything, and sign out on every
device. These act only on the signed-in user's own folder."""

from __future__ import annotations

import io
import json
import shutil
import zipfile
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel

from app.workspace.context import Workspace, forget_owner, session_version, workspace
from app.workspace.identity import Owner, current_owner

router = APIRouter(prefix="/v2", tags=["workspace"])


@router.get("/account/session-version")
def get_session_version(owner: Owner = Depends(current_owner)):
    """Read at sign-in so the new session carries the current version."""
    return {"session_version": session_version(owner.owner_id)}


@router.get("/account/export")
def export_data(ws: Workspace = Depends(workspace)):
    """A zip of everything stored for this user: profile, resume versions, jobs and
    applications databases, tailored resumes and saved reviews."""
    from resume_tailorer.identity import user_dir

    root = user_dir(ws.owner_id)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(root.rglob("*")):
            if path.is_file() and path.suffix not in (".tmp",):
                archive.write(path, path.relative_to(root).as_posix())
        archive.writestr("README.txt", "Everything Job Copilot stored for you, exported "
                         f"{datetime.now():%Y-%m-%d %H:%M}.\ncareer_profile.json is your Career Profile; the .db files "
                         "are SQLite databases of your jobs and applications.\n")
    return Response(buffer.getvalue(), media_type="application/zip",
                    headers={"Content-Disposition": f'attachment; filename="job-copilot-data-{datetime.now():%Y%m%d}.zip"'})


class Confirm(BaseModel):
    confirm: str


@router.delete("/account")
def delete_account(body: Confirm, ws: Workspace = Depends(workspace)):
    from resume_tailorer.identity import user_dir

    if body.confirm != "DELETE":
        raise HTTPException(400, 'Type DELETE to confirm.')
    forget_owner(ws.owner_id)  # close this user's database connections first
    shutil.rmtree(user_dir(ws.owner_id), ignore_errors=False)
    return {"deleted": True}


@router.post("/account/sign-out-everywhere")
def sign_out_everywhere(ws: Workspace = Depends(workspace)):
    from resume_tailorer.identity import user_dir

    if not ws.owner.signed_in:
        raise HTTPException(400, "Sign-in isn't set up here, so there are no other sessions.")
    path = user_dir(ws.owner_id) / "account.json"
    path.write_text(json.dumps({"session_version": session_version(ws.owner_id) + 1}), encoding="utf-8")
    return {"signed_out": True}
