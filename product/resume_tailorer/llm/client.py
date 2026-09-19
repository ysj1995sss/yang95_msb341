from __future__ import annotations

import litellm

from resume_tailorer.llm.settings import LLMSettings


class LLMClient:
    def __init__(self, settings: LLMSettings):
        self.settings = settings

    def complete(self, system: str, user: str, *, max_tokens: int = 2000) -> str:
        kwargs = {
            "model": self.settings.model,
            "api_key": self.settings.api_key,
            "max_tokens": max_tokens,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        if self.settings.api_base:
            kwargs["api_base"] = self.settings.api_base

        try:
            response = litellm.completion(**kwargs)
        except Exception as exc:
            raise self._map_error(exc) from exc

        content = response.choices[0].message.content
        if content is None:
            raise RuntimeError("Model provider error: empty response")
        return content

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
        safe = str(exc).replace(getattr(exc, "args", [""])[0] if False else "", "")
        reason = str(exc)
        for secret_marker in ("sk-", "key=", "api_key"):
            if secret_marker in reason.lower():
                reason = "unexpected provider failure"
                break
        return RuntimeError(f"Model provider error: {reason[:200]}")
