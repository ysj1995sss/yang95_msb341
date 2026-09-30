from __future__ import annotations

import re
import time
from typing import Callable

import litellm

from resume_tailorer.llm.settings import LLMSettings


_TRANSIENT_MARKERS = ("timeout", "timed out", "connection", "429", "rate limit", "500", "502", "503", "504", "overloaded")
_THINK_BLOCK = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)


class LLMClient:
    TIMEOUT_SECONDS = 180
    MAX_RETRIES = 2
    BACKOFF_SECONDS = 2.0
    # Reasoning models spend output tokens thinking before they answer. A reply
    # cut off at the limit is retried once with more room, then reported plainly.
    TRUNCATION_RETRY_FACTOR = 4
    MAX_TOKENS_CAP = 8000

    def __init__(self, settings: LLMSettings, sleep: Callable[[float], None] = time.sleep):
        self.settings = settings
        self._sleep = sleep

    def complete(self, system: str, user: str, *, max_tokens: int = 2000) -> str:
        text, truncated = self._complete_once(system, user, max_tokens)
        if truncated:
            larger = min(max_tokens * self.TRUNCATION_RETRY_FACTOR, self.MAX_TOKENS_CAP)
            if larger > max_tokens:
                text, truncated = self._complete_once(system, user, larger)
        if truncated:
            raise RuntimeError(
                "The model's reply was cut off before it finished. This usually means a reasoning "
                "model is spending its output on step-by-step thinking; choose a non-reasoning model."
            )
        return text

    def _complete_once(self, system: str, user: str, max_tokens: int):
        kwargs = {
            "model": self.settings.model,
            "api_key": self.settings.api_key,
            "max_tokens": max_tokens,
            "timeout": self.TIMEOUT_SECONDS,
            "num_retries": 0,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        if self.settings.api_base:
            kwargs["api_base"] = self.settings.api_base

        for attempt in range(self.MAX_RETRIES + 1):
            try:
                response = litellm.completion(**kwargs)
                break
            except Exception as exc:
                if attempt == self.MAX_RETRIES or not self._is_transient(exc):
                    raise self._map_error(exc) from exc
                self._sleep(self.BACKOFF_SECONDS * (attempt + 1))

        choice = response.choices[0]
        content = choice.message.content
        if content is None:
            raise RuntimeError("Model provider error: empty response")
        content = _THINK_BLOCK.sub("", content).strip()
        return content, getattr(choice, "finish_reason", None) == "length"

    @staticmethod
    def _is_transient(exc: Exception) -> bool:
        text = str(exc).lower()
        return any(marker in text for marker in _TRANSIENT_MARKERS)

    @staticmethod
    def _map_error(exc: Exception) -> RuntimeError:
        text = str(exc).lower()
        if "401" in text or "auth" in text or "invalid api key" in text or "unauthorized" in text:
            return RuntimeError("Provider rejected the API key.")
        if "404" in text or "model not found" in text or "does not exist" in text:
            return RuntimeError(
                "Model not found for this provider; check the model id (and Base URL if using a proxy)."
            )
        if "timeout" in text or "connection" in text or "network" in text:
            return RuntimeError("Could not reach the model provider.")
        # Never include raw exception if it might contain secrets; keep short.
        reason = str(exc)
        for secret_marker in ("sk-", "key=", "api_key"):
            if secret_marker in reason.lower():
                reason = "unexpected provider failure"
                break
        return RuntimeError(f"Model provider error: {reason[:200]}")
