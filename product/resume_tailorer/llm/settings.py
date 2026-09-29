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


def apply_secret_settings(
    secrets: Mapping[str, object],
    env: Optional[MutableMapping[str, str]] = None,
) -> None:
    """Fill missing LLM environment values from a deployment secret store."""
    target = env if env is not None else os.environ
    for key in ("LLM_MODEL", "LLM_API_KEY", "LLM_API_BASE"):
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

    if not resolved_model or not resolved_key:
        raise ValueError(MISSING_CONFIG_MESSAGE)

    return LLMSettings(
        model=resolved_model,
        api_key=resolved_key,
        api_base=resolved_base,
    )
