from __future__ import annotations

import re
import time
from typing import Callable

import litellm

from resume_tailorer.llm.settings import LLMSettings


_TRANSIENT_MARKERS = ("timeout", "timed out", "connection", "429", "rate limit", "500", "502", "503", "504", "overloaded",
                      "unavailable")
# "unavailable" also catches litellm's "ServiceUnavailableError", which has no space.
_BUSY_MARKERS = ("overloaded", "503", "429", "rate limit", "unavailable", "temporarily")
_THINK_BLOCK = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)


class _FallbackWorthy(RuntimeError):
    """A failure another model might not have: busy provider, empty reply, unknown model id."""


class LLMClient:
    TIMEOUT_SECONDS = 180
    MAX_RETRIES = 3
    BACKOFF_SECONDS = 2.0
    BUSY_BACKOFF_SECONDS = 10.0  # a busy provider needs longer than a network blip
    # Reasoning models spend output tokens thinking before they answer. A reply
    # cut off at the limit is retried once with more room, then reported plainly.
    TRUNCATION_RETRY_FACTOR = 4
    MAX_TOKENS_CAP = 8000

    def __init__(self, settings: LLMSettings, sleep: Callable[[float], None] = time.sleep):
        self.settings = settings
        self._sleep = sleep
        self.model_used: str | None = None  # which model answered the last call

    def complete(self, system: str, user: str, *, max_tokens: int = 2000) -> str:
        models = (self.settings.model, *getattr(self.settings, "fallback_models", ()))
        for position, model in enumerate(models):
            try:
                text = self._complete_model(model, system, user, max_tokens)
                self.model_used = model
                return text
            except _FallbackWorthy as exc:
                if position == len(models) - 1:
                    raise RuntimeError(str(exc)) from exc
        raise AssertionError("unreachable")

    def _complete_model(self, model: str, system: str, user: str, max_tokens: int) -> str:
        text, truncated = self._complete_once(model, system, user, max_tokens)
        if truncated:
            larger = min(max_tokens * self.TRUNCATION_RETRY_FACTOR, self.MAX_TOKENS_CAP)
            if larger > max_tokens:
                text, truncated = self._complete_once(model, system, user, larger)
        if truncated:
            raise _FallbackWorthy(
                "The model's reply was cut off before it finished. This usually means a reasoning "
                "model is spending its output on step-by-step thinking; choose a non-reasoning model."
            )
        return text

    def _complete_once(self, model: str, system: str, user: str, max_tokens: int):
        kwargs = {
            "model": model,
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
        if model.startswith("openrouter/"):
            # Editing a bullet needs no step-by-step thinking. Reasoning models
            # otherwise spend the whole output budget (and minutes) on it.
            kwargs["extra_body"] = {"reasoning": {"enabled": False}}
        elif model.startswith("gemini/"):
            # Same for Gemini: current Flash models think by default, and the
            # thinking can use the whole budget, leaving an empty reply.
            kwargs["reasoning_effort"] = "disable"

        empty_retries = 1  # free models sometimes return nothing once, then answer
        for attempt in range(self.MAX_RETRIES + 1):
            try:
                response = litellm.completion(**kwargs)
                choice = response.choices[0]
                if not choice.message.content and getattr(choice, "finish_reason", None) != "length" and empty_retries:
                    empty_retries -= 1
                    self._sleep(self.BACKOFF_SECONDS)
                    continue
                break
            except Exception as exc:
                lowered = str(exc).lower()
                if "extra_body" in kwargs and "reasoning" in lowered:
                    # This model can't run without reasoning; use it as it is.
                    kwargs.pop("extra_body")
                    continue
                if "reasoning_effort" in kwargs and ("thinking" in lowered or "reasoning" in lowered or "budget" in lowered):
                    kwargs.pop("reasoning_effort")
                    continue
                if attempt == self.MAX_RETRIES or not self._is_transient(exc):
                    mapped = self._map_error(exc)
                    lowered_msg = str(mapped).lower()
                    if "busy" in lowered_msg or "model not found" in lowered_msg:
                        raise _FallbackWorthy(str(mapped)) from exc
                    raise mapped from exc
                busy = any(marker in str(exc).lower() for marker in _BUSY_MARKERS)
                self._sleep((self.BUSY_BACKOFF_SECONDS if busy else self.BACKOFF_SECONDS) * (attempt + 1))

        choice = response.choices[0]
        content = choice.message.content
        finish = getattr(choice, "finish_reason", None)
        if not content and finish == "length":
            return "", True  # all output went to thinking: retry with more room
        if not content:
            raise _FallbackWorthy(
                "The model returned an empty reply"
                + (f" (stopped: {finish})" if finish and finish != "stop" else "")
                + ". Try again, or choose a different model."
            )
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
        if any(marker in text for marker in _BUSY_MARKERS):
            return RuntimeError(
                "The model provider is busy right now (free models are often overloaded). "
                "Wait a minute and try again, or switch models in Model settings."
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
