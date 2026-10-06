from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Callable

# litellm otherwise loads the first .env above its own install folder (for a user install, the
# home folder), which may belong to a different project (decision 030). Our settings come from
# the environment and the app's own .env loading only. This flag changes nothing else in litellm.
os.environ.setdefault("LITELLM_MODE", "PRODUCTION")

import litellm  # noqa: E402

from resume_tailorer.llm.settings import LLMSettings


_TRANSIENT_MARKERS = ("timeout", "timed out", "connection", "429", "rate limit", "500", "502", "503", "504", "overloaded",
                      "unavailable")
# "unavailable" also catches litellm's "ServiceUnavailableError", which has no space.
_BUSY_MARKERS = ("overloaded", "503", "429", "rate limit", "unavailable", "temporarily")
_THINK_BLOCK = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)

# "codex-cli" or "codex-cli/<model>": answers come from the Codex CLI signed in with the person's
# own ChatGPT plan, for running Job Copilot on their own computer (decision 031).
CODEX_CLI_PREFIX = "codex-cli"
def _reasoning_effort() -> str:
    """Codex reasoning effort: "medium" by default (spec 011: "low" proposed almost nothing),
    overridable with LLM_REASONING_EFFORT."""
    value = (os.environ.get("LLM_REASONING_EFFORT") or "medium").strip().lower()
    return value if value in ("minimal", "low", "medium", "high") else "medium"


_CODEX_INSTRUCTIONS = (
    "You are being used as a plain text-completion service by an application. Do not run commands, "
    "read or write files, or use any tools. Follow the instructions below exactly and reply with only "
    "the requested output, with no preamble and no closing remarks."
)


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
        if model == CODEX_CLI_PREFIX or model.startswith(CODEX_CLI_PREFIX + "/"):
            return self._complete_with_codex(model, system, user), False
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

    def _complete_with_codex(self, model: str, system: str, user: str) -> str:
        """One answer from `codex exec`: a throwaway session in an empty folder, read-only
        sandbox, no saved history. Uses the ChatGPT plan's Codex allowance, not an API key."""
        codex = shutil.which("codex")
        if codex is None:
            raise RuntimeError("The Codex CLI isn't installed on this computer. Install it with "
                               "`npm install -g @openai/codex`, then run `codex login`.")
        prompt = f"{_CODEX_INSTRUCTIONS}\n\n<instructions>\n{system}\n</instructions>\n\n<task>\n{user}\n</task>\n"
        with tempfile.TemporaryDirectory(prefix="jc-codex-") as work:
            answer_file = Path(work, "answer.txt")
            command = [codex, "exec", "--ephemeral", "--skip-git-repo-check", "--ignore-rules",
                       "--sandbox", "read-only", "--color", "never", "-C", work,
                       "-c", f'model_reasoning_effort="{_reasoning_effort()}"', "-o", str(answer_file)]
            if "/" in model:
                command += ["-m", model.split("/", 1)[1]]
            command.append("-")  # the prompt comes on stdin
            try:
                done = subprocess.run(command, input=prompt, capture_output=True, text=True, encoding="utf-8",
                                      errors="replace", timeout=self.TIMEOUT_SECONDS * 2)
            except subprocess.TimeoutExpired as exc:
                raise RuntimeError("Codex didn't answer in time. Try again.") from exc
            answer = answer_file.read_text(encoding="utf-8").strip() if answer_file.exists() else ""
        if done.returncode != 0 or not answer:
            details = f"{done.stderr}\n{done.stdout}".lower()
            if "usage limit" in details or "rate limit" in details or "429" in details:
                raise RuntimeError("Your ChatGPT plan's Codex usage limit is used up for now. Try again "
                                   "when it resets, or choose a different model for this run.")
            if "is not recognized" in details or "command not found" in details or "no such file" in details:
                raise RuntimeError("The Codex CLI couldn't start on this computer (Node.js, which it runs on, "
                                   "wasn't found). Reinstall Node.js or add it to PATH, then try again.")
            if "login" in details or "not logged in" in details or "unauthorized" in details or "401" in details:
                raise RuntimeError("Codex isn't signed in. Run `codex login` in a terminal, then try again.")
            raise _FallbackWorthy("Codex returned no answer. Try again, or choose a different model.")
        return _THINK_BLOCK.sub("", answer).strip()

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
