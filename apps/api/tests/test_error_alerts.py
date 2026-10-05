"""Optional error alerts (decision 030): only a reference, a place and an error type are sent."""

from unittest.mock import patch

from fastapi.testclient import TestClient


def _app_with_failing_route():
    from app.main import app

    if not any(getattr(r, "path", "") == "/__boom" for r in app.routes):
        @app.get("/__boom")
        def boom():
            raise ValueError("riley@example.com secret details")
    return app


class _InlineThread:
    def __init__(self, target, daemon=None):
        self.target = target

    def start(self):
        self.target()


def test_no_alert_without_a_webhook(monkeypatch):
    monkeypatch.setenv("ERROR_WEBHOOK_URL", "")
    with patch("app.alerts.requests.post") as post, patch("app.alerts.threading.Thread", _InlineThread):
        response = TestClient(_app_with_failing_route(), raise_server_exceptions=False).get("/__boom")
    assert response.status_code == 500 and "reference" in response.json()["detail"]
    post.assert_not_called()


def test_alert_carries_no_personal_details(monkeypatch):
    monkeypatch.setenv("ERROR_WEBHOOK_URL", "https://hooks.example/abc")
    with patch("app.alerts.requests.post") as post, patch("app.alerts.threading.Thread", _InlineThread):
        response = TestClient(_app_with_failing_route(), raise_server_exceptions=False).get("/__boom")
    reference = response.json()["detail"].rstrip(".").split()[-1]
    url, = post.call_args.args
    text = post.call_args.kwargs["json"]["text"]
    assert url == "https://hooks.example/abc"
    assert text == f"Job Copilot error {reference}: ValueError in GET /__boom"
    assert "riley" not in text and "secret" not in text
    assert post.call_args.kwargs["json"]["content"] == text
