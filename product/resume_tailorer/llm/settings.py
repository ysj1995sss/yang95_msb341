from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, MutableMapping, Optional
import os

MISSING_CONFIG_MESSAGE = (
    "Set LLM_MODEL and LLM_API_KEY in the environment, or fill Model and API key in the sidebar."
)


@dataclass(frozen=True)
class LLMSettings:
    model: str
    api_key: str
    api_base: Optional[str] = None
    # Tried in order when the main model is busy or returns nothing (decision 027).
    fallback_models: tuple[str, ...] = ()

# Same provider and key as the main model, so no extra secret is needed.
_DEFAULT_FALLBACKS = {"gemini/": ("gemini/gemini-flash-lite-latest", "gemini/gemini-2.5-flash")}


def apply_secret_settings(
    secrets: Mapping[str, object],
    env: Optional[MutableMapping[str, str]] = None,
) -> None:
    """Fill missing LLM environment values from a deployment secret store."""
    target = env if env is not None else os.environ
    for key in ("LLM_MODEL", "LLM_API_KEY", "LLM_API_BASE", "LLM_FALLBACK_MODELS"):
        value = secrets.get(key)
        if key not in target and value is not None and str(value).strip():
            target[key] = str(value).strip()


def _pick(override: Optional[str], env_value: Optional[str]) -> Optional[str]:
    if override is not None and str(override).strip():
        return str(override).strip()
    if env_value is not None and str(env_value).strip():
        return str(env_value).strip()
    return None


def resolve_settings(
    *,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    api_base: Optional[str] = None,
    env: Optional[Mapping[str, str]] = None,
) -> LLMSettings:
    source = env if env is not None else os.environ
    resolved_model = _pick(model, source.get("LLM_MODEL"))
    resolved_key = _pick(api_key, source.get("LLM_API_KEY"))
    resolved_base = _pick(api_base, source.get("LLM_API_BASE"))

    if resolved_model and _uses_codex_cli(resolved_model):
        resolved_key = resolved_key or ""  # the Codex CLI signs in with ChatGPT, not a key
    elif not resolved_model or not resolved_key:
        raise ValueError(MISSING_CONFIG_MESSAGE)

    return LLMSettings(
        model=resolved_model,
        api_key=resolved_key,
        api_base=resolved_base,
        fallback_models=_fallbacks(resolved_model, source.get("LLM_FALLBACK_MODELS")),
    )


def _uses_codex_cli(model: str) -> bool:
    return model == "codex-cli" or model.startswith("codex-cli/")


def uses_codex_cli(settings: LLMSettings) -> bool:
    """True when any model in these settings answers through the person's own ChatGPT plan."""
    return any(_uses_codex_cli(m) for m in (settings.model, *settings.fallback_models))


def _fallbacks(model: str, configured: Optional[str]) -> tuple[str, ...]:
    """LLM_FALLBACK_MODELS (comma-separated; "none" turns fallback off), else a built-in default."""
    if configured is not None and configured.strip():
        if configured.strip().lower() == "none":
            return ()
        names = [name.strip() for name in configured.split(",") if name.strip()]
    else:
        names = next((list(v) for prefix, v in _DEFAULT_FALLBACKS.items() if model.startswith(prefix)), [])
    return tuple(dict.fromkeys(name for name in names if name != model))
