from unittest.mock import patch, MagicMock

import pytest

from resume_tailorer.profile_review.api_client import (
    ApiError,
    ApiSession,
    login_or_register,
    get_profile,
    put_profile,
    get_verification,
    upload_resume,
    get_resume_meta,
)


def _response(status_code, json_body=None, text=""):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_body if json_body is not None else {}
    resp.text = text
    return resp


class TestLoginOrRegister:
    def test_successful_login_returns_session(self):
        with patch("resume_tailorer.profile_review.api_client.requests.post") as post:
            post.return_value = _response(200, {"access_token": "tok123"})
            session = login_or_register("http://api", "a@example.com", "pw")
        assert session.token == "tok123"

    def test_new_user_falls_back_to_register(self):
        with patch("resume_tailorer.profile_review.api_client.requests.post") as post:
            post.side_effect = [
                _response(401, {"detail": "Invalid credentials"}),
                _response(201, {"access_token": "new-tok"}),
            ]
            session = login_or_register("http://api", "new@example.com", "pw")
        assert session.token == "new-tok"

    def test_wrong_password_surfaces_original_login_error_not_register_conflict(self):
        with patch("resume_tailorer.profile_review.api_client.requests.post") as post:
            post.side_effect = [
                _response(401, {"detail": "Invalid credentials"}),
                _response(409, {"detail": "Email already registered"}),
            ]
            with pytest.raises(ApiError) as exc_info:
                login_or_register("http://api", "existing@example.com", "wrong-pw")
        assert exc_info.value.status_code == 401
        assert "Invalid credentials" in exc_info.value.detail


class TestProfileCalls:
    def test_get_profile(self):
        session = ApiSession(base_url="http://api", token="t")
        with patch("resume_tailorer.profile_review.api_client.requests.get") as get:
            get.return_value = _response(200, {"skills": ["Python"]})
            result = get_profile(session)
        assert result == {"skills": ["Python"]}
        get.assert_called_once_with("http://api/profile", headers={"Authorization": "Bearer t"})

    def test_put_profile(self):
        session = ApiSession(base_url="http://api", token="t")
        with patch("resume_tailorer.profile_review.api_client.requests.put") as put:
            put.return_value = _response(200, {"skills": ["Python", "SQL"]})
            result = put_profile(session, {"skills": ["Python", "SQL"]})
        assert result["skills"] == ["Python", "SQL"]

    def test_get_verification(self):
        session = ApiSession(base_url="http://api", token="t")
        with patch("resume_tailorer.profile_review.api_client.requests.get") as get:
            get.return_value = _response(200, {"skills[1]": "user_verified"})
            result = get_verification(session)
        assert result == {"skills[1]": "user_verified"}

    def test_get_resume_meta_returns_none_on_404(self):
        session = ApiSession(base_url="http://api", token="t")
        with patch("resume_tailorer.profile_review.api_client.requests.get") as get:
            get.return_value = _response(404, {"detail": "No original resume file stored for this user"})
            result = get_resume_meta(session)
        assert result is None

    def test_upload_resume(self):
        session = ApiSession(base_url="http://api", token="t")
        with patch("resume_tailorer.profile_review.api_client.requests.post") as post:
            post.return_value = _response(200, {"skills": []})
            upload_resume(session, "resume.pdf", b"bytes", "application/pdf")
        _, kwargs = post.call_args
        assert kwargs["files"]["file"][0] == "resume.pdf"

    def test_api_error_raised_on_failure_status(self):
        session = ApiSession(base_url="http://api", token="t")
        with patch("resume_tailorer.profile_review.api_client.requests.get") as get:
            get.return_value = _response(500, {"detail": "boom"})
            with pytest.raises(ApiError):
                get_profile(session)
