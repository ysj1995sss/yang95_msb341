"""
Thin HTTP client for the apps/api backend's auth/profile endpoints, used
by the Streamlit "Review Your Profile" page. Kept free of any Streamlit
import so it's unit-testable with a mocked `requests` session -- the page
module itself is UI-only wiring, per this app's existing convention (see
resume_tailorer/pages/2_Job_Search.py's docstring) of keeping business
logic out of files that require a browser to exercise.

This is a genuinely different integration style from the rest of this
Streamlit app, which calls the resume_tailorer engine in-process: profile
review needs the apps/api backend specifically, since that's where
per-user auth and persistence (Profile, ResumeFile, verification state)
actually live -- the in-process engine used elsewhere in this app has no
concept of a logged-in user or a stored profile at all.
"""

from dataclasses import dataclass

import requests


class ApiError(RuntimeError):
    def __init__(self, status_code: int, detail: str):
        super().__init__(f"{status_code}: {detail}")
        self.status_code = status_code
        self.detail = detail


@dataclass
class ApiSession:
    base_url: str
    token: str

    @property
    def headers(self) -> dict:
        return {"Authorization": f"Bearer {self.token}"}


def _raise_for_status(response: requests.Response) -> None:
    if response.status_code >= 400:
        try:
            detail = response.json().get("detail", response.text)
        except ValueError:
            detail = response.text
        raise ApiError(response.status_code, detail)


def login_or_register(base_url: str, email: str, password: str) -> ApiSession:
    """Try login first (the common case for a returning user). apps/api's
    /auth/login returns 401 for BOTH "no such account" and "wrong
    password" (standard practice, avoids leaking which one it was), so a
    401 alone can't distinguish "new user" from "existing user, typo'd
    password" -- fall back to register, and if THAT fails with 409
    (email already registered), the account really does exist, so
    re-raise the ORIGINAL login failure (a real bad-password error)
    rather than the confusing 409."""
    response = requests.post(f"{base_url}/auth/login", json={"email": email, "password": password})
    if response.status_code == 401:
        register_response = requests.post(
            f"{base_url}/auth/register", json={"email": email, "password": password}
        )
        if register_response.status_code == 409:
            _raise_for_status(response)
        _raise_for_status(register_response)
        return ApiSession(base_url=base_url, token=register_response.json()["access_token"])
    _raise_for_status(response)
    return ApiSession(base_url=base_url, token=response.json()["access_token"])


def get_profile(session: ApiSession) -> dict:
    response = requests.get(f"{session.base_url}/profile", headers=session.headers)
    _raise_for_status(response)
    return response.json()


def put_profile(session: ApiSession, profile: dict) -> dict:
    response = requests.put(f"{session.base_url}/profile", json=profile, headers=session.headers)
    _raise_for_status(response)
    return response.json()


def get_verification(session: ApiSession) -> dict:
    response = requests.get(f"{session.base_url}/profile/verification", headers=session.headers)
    _raise_for_status(response)
    return response.json()


def upload_resume(session: ApiSession, filename: str, content: bytes, content_type: str) -> dict:
    response = requests.post(
        f"{session.base_url}/profile/upload",
        files={"file": (filename, content, content_type)},
        headers=session.headers,
    )
    _raise_for_status(response)
    return response.json()


def get_resume_meta(session: ApiSession) -> dict | None:
    response = requests.get(f"{session.base_url}/profile/resume-meta", headers=session.headers)
    if response.status_code == 404:
        return None
    _raise_for_status(response)
    return response.json()


def get_resume_versions(session: ApiSession) -> list[dict]:
    response = requests.get(f"{session.base_url}/profile/resume-versions", headers=session.headers)
    _raise_for_status(response)
    return response.json()
