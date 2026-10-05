"""Optional error alerts (decision 030).

With ERROR_WEBHOOK_URL set (a Slack or Discord incoming webhook the builder creates), each
server error posts one short line: the reference the person was shown, where it happened and
the error's type. Never the error message, request body or anything about the person, which
may contain their data. Without the setting nothing is sent. Sending happens on a background
thread and never affects the request.
"""

from __future__ import annotations

import logging
import threading

import requests

from app.config import get_settings

logger = logging.getLogger("job_copilot.api.alerts")


def notify(reference: str, where: str, error_type: str) -> None:
    url = get_settings().error_webhook_url
    if not url:
        return
    text = f"Job Copilot error {reference}: {error_type} in {where}"
    payload = {"text": text, "content": text}  # Slack reads "text", Discord reads "content"

    def send() -> None:
        try:
            requests.post(url, json=payload, timeout=5)
        except Exception:  # an alert that can't be sent must not cause another error
            logger.warning("Couldn't send the error alert for %s", reference)

    threading.Thread(target=send, daemon=True).start()
