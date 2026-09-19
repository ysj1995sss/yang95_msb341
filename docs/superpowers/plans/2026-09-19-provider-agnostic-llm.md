# Provider-Agnostic LLM Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let any user tailor a resume with their own LLM provider via `LLM_MODEL` / `LLM_API_KEY` / optional `LLM_API_BASE` (env) or Streamlit sidebar override — with a clear failure when neither is set.

**Architecture:** Add `LLMSettings` + `LLMClient` as the single network boundary. `ResumeTailorer` calls `LLMClient.complete(system, user) -> str` only. LiteLLM is an internal transport; users never sign up for it. Sidebar values override env; incomplete config raises before any network call.

**Tech Stack:** Python 3.11+, Streamlit, LiteLLM, pytest, existing `ResumeTailorer` / optimizer prompts unchanged.

**Spec:** `docs/superpowers/specs/2026-09-19-provider-agnostic-llm-design.md`

## Global Constraints

- Resolution order: sidebar (when filled) → env → hard fail. No silent Anthropic default.
- Never log, persist, or commit API keys.
- Job Search / Applications must work without LLM config.
- Fabrication system prompts stay in `ResumeTailorer`; do not weaken them.
- Working directory for pytest: `product/` (run `python -m pytest ...` from there).
- Prefer TDD: failing test → implement → pass → commit per task.

## File map

| File | Responsibility |
|---|---|
| `product/resume_tailorer/llm/settings.py` | Resolve `LLMSettings` from env + optional overrides |
| `product/resume_tailorer/llm/client.py` | `LLMClient.complete` via LiteLLM; map errors to plain messages |
| `product/resume_tailorer/llm/__init__.py` | Export `LLMSettings`, `LLMClient`, `resolve_settings` |
| `product/resume_tailorer/tailorer/resume_tailorer.py` | Use `LLMClient` instead of `anthropic` |
| `product/resume_tailorer/app.py` | Sidebar model/key/base URL; pass overrides into tailorer |
| `product/requirements.txt` | Add `litellm`; drop hard `anthropic` pin as sole LLM path |
| `product/tests/test_llm_settings.py` | Settings resolution tests |
| `product/tests/test_llm_client.py` | Client + error mapping tests |
| `product/tests/test_resume_tailorer.py` | Mock `LLMClient` instead of anthropic |
| `product/tests/test_optimizer.py` | Same mock pattern |
| `product/tests/test_requirements_pin.py` | Assert LiteLLM present (replace Anthropic-only Messages pin) |
| `product/README.md`, `product/docs/architecture.md` | Document `LLM_*` + sidebar |

---

### Task 1: LLMSettings resolver

**Files:**
- Create: `product/resume_tailorer/llm/settings.py`
- Create: `product/resume_tailorer/llm/__init__.py`
- Test: `product/tests/test_llm_settings.py`

**Interfaces:**
- Consumes: `os.environ`
- Produces:
  - `@dataclass LLMSettings`: `model: str`, `api_key: str`, `api_base: str | None`
  - `resolve_settings(*, model: str | None = None, api_key: str | None = None, api_base: str | None = None, env: Mapping[str, str] | None = None) -> LLMSettings`
  - Raises `ValueError` with the exact message:  
    `Set LLM_MODEL and LLM_API_KEY in the environment, or fill Model and API key in the sidebar.`
  - Sidebar/override: non-empty `model` / `api_key` / `api_base` win over env `LLM_MODEL` / `LLM_API_KEY` / `LLM_API_BASE`
  - Empty string overrides count as “not filled” (fall through to env)
  - If only `ANTHROPIC_API_KEY` is in env (no `LLM_*`), still raise the same `ValueError` (no silent migrate)

- [ ] **Step 1: Write the failing tests**

```python
# product/tests/test_llm_settings.py
import pytest
from resume_tailorer.llm.settings import resolve_settings, LLMSettings


def test_resolve_from_env_only():
    settings = resolve_settings(
        env={
            "LLM_MODEL": "openai/gpt-4o",
            "LLM_API_KEY": "sk-test",
            "LLM_API_BASE": "https://example.com/v1",
        }
    )
    assert settings == LLMSettings(
        model="openai/gpt-4o",
        api_key="sk-test",
        api_base="https://example.com/v1",
    )


def test_sidebar_overrides_env():
    settings = resolve_settings(
        model="anthropic/claude-3-5-sonnet-20241022",
        api_key="sk-sidebar",
        api_base=None,
        env={"LLM_MODEL": "openai/gpt-4o", "LLM_API_KEY": "sk-env"},
    )
    assert settings.model == "anthropic/claude-3-5-sonnet-20241022"
    assert settings.api_key == "sk-sidebar"


def test_empty_sidebar_falls_back_to_env():
    settings = resolve_settings(
        model="",
        api_key="",
        env={"LLM_MODEL": "openai/gpt-4o", "LLM_API_KEY": "sk-env"},
    )
    assert settings.model == "openai/gpt-4o"
    assert settings.api_key == "sk-env"


def test_missing_config_raises_clear_error():
    with pytest.raises(ValueError, match="LLM_MODEL and LLM_API_KEY"):
        resolve_settings(env={})


def test_anthropic_env_alone_does_not_silently_work():
    with pytest.raises(ValueError, match="LLM_MODEL and LLM_API_KEY"):
        resolve_settings(env={"ANTHROPIC_API_KEY": "sk-ant-only"})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_llm_settings.py -v`  
Expected: FAIL (module not found / import error)

- [ ] **Step 3: Implement settings**

```python
# product/resume_tailorer/llm/settings.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Optional
import os

MISSING_CONFIG_MESSAGE = (
    "Set LLM_MODEL and LLM_API_KEY in the environment, or fill Model and API key in the sidebar."
)


@dataclass(frozen=True)
class LLMSettings:
    model: str
    api_key: str
    api_base: Optional[str] = None


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
```

```python
# product/resume_tailorer/llm/__init__.py
from resume_tailorer.llm.settings import LLMSettings, resolve_settings, MISSING_CONFIG_MESSAGE

__all__ = ["LLMSettings", "resolve_settings", "MISSING_CONFIG_MESSAGE", "LLMClient"]
```

(Export `LLMClient` from `__init__` only after Task 2; for Task 1 either omit it from `__all__` or add a placeholder import in Task 2.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_llm_settings.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add product/resume_tailorer/llm/settings.py product/resume_tailorer/llm/__init__.py product/tests/test_llm_settings.py
git commit -m "feat: add LLMSettings resolver for env and sidebar overrides"
```

---

### Task 2: LLMClient via LiteLLM

**Files:**
- Create: `product/resume_tailorer/llm/client.py`
- Modify: `product/resume_tailorer/llm/__init__.py`
- Modify: `product/requirements.txt`
- Test: `product/tests/test_llm_client.py`

**Interfaces:**
- Consumes: `LLMSettings`, `litellm.completion`
- Produces:
  - `class LLMClient:`
    - `__init__(self, settings: LLMSettings)`
    - `complete(self, system: str, user: str, *, max_tokens: int = 2000) -> str`
  - Error mapping (raise `RuntimeError` with these exact substrings users will see):
    - auth / 401 / `AuthenticationError` → `Provider rejected the API key.`
    - 404 / model not found → `Model not found for this provider; check the model id (and Base URL if using a proxy).`
    - timeout / connection → `Could not reach the model provider.`
    - other → `Model provider error: {short reason}` (no API key in the message)

- [ ] **Step 1: Write the failing tests**

```python
# product/tests/test_llm_client.py
from unittest.mock import MagicMock, patch
import pytest

from resume_tailorer.llm.settings import LLMSettings
from resume_tailorer.llm.client import LLMClient


def _settings():
    return LLMSettings(model="openai/gpt-4o", api_key="sk-test", api_base=None)


def test_complete_sends_system_and_user_and_returns_text():
    client = LLMClient(_settings())
    fake_response = MagicMock()
    fake_response.choices = [MagicMock()]
    fake_response.choices[0].message.content = "tailored resume"

    with patch("resume_tailorer.llm.client.litellm.completion", return_value=fake_response) as mock_completion:
        text = client.complete("system rules", "user payload", max_tokens=100)

    assert text == "tailored resume"
    kwargs = mock_completion.call_args.kwargs
    assert kwargs["model"] == "openai/gpt-4o"
    assert kwargs["api_key"] == "sk-test"
    assert kwargs["max_tokens"] == 100
    assert kwargs["messages"][0] == {"role": "system", "content": "system rules"}
    assert kwargs["messages"][1] == {"role": "user", "content": "user payload"}


def test_complete_passes_api_base_when_set():
    client = LLMClient(LLMSettings(model="openai/gpt-4o", api_key="sk", api_base="https://proxy.example/v1"))
    fake_response = MagicMock()
    fake_response.choices = [MagicMock()]
    fake_response.choices[0].message.content = "ok"

    with patch("resume_tailorer.llm.client.litellm.completion", return_value=fake_response) as mock_completion:
        client.complete("s", "u")

    assert mock_completion.call_args.kwargs["api_base"] == "https://proxy.example/v1"


def test_auth_error_maps_to_plain_message():
    client = LLMClient(_settings())
    with patch(
        "resume_tailorer.llm.client.litellm.completion",
        side_effect=Exception("AuthenticationError: invalid key 401"),
    ):
        with pytest.raises(RuntimeError, match="Provider rejected the API key"):
            client.complete("s", "u")


def test_model_not_found_maps_to_plain_message():
    client = LLMClient(_settings())
    with patch(
        "resume_tailorer.llm.client.litellm.completion",
        side_effect=Exception("404 model not found"),
    ):
        with pytest.raises(RuntimeError, match="Model not found for this provider"):
            client.complete("s", "u")


def test_timeout_maps_to_plain_message():
    client = LLMClient(_settings())
    with patch(
        "resume_tailorer.llm.client.litellm.completion",
        side_effect=Exception("Connection timeout"),
    ):
        with pytest.raises(RuntimeError, match="Could not reach the model provider"):
            client.complete("s", "u")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_llm_client.py -v`  
Expected: FAIL (import error)

- [ ] **Step 3: Add dependency and implement client**

Add to `product/requirements.txt` (keep or remove `anthropic` — prefer **remove** `anthropic==...` since LiteLLM pulls provider SDKs as needed; if removal breaks an unrelated import, leave a comment in the commit that anthropic is unused):

```
litellm==1.55.0
```

(Pin may be adjusted to a version that installs cleanly on the engineer’s Python; do not use an unpinned floating dependency in the committed file.)

```python
# product/resume_tailorer/llm/client.py
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
```

Update `__init__.py` to export `LLMClient`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pip install litellm==<pinned>` then `python -m pytest tests/test_llm_client.py tests/test_llm_settings.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add product/resume_tailorer/llm/client.py product/resume_tailorer/llm/__init__.py product/requirements.txt product/tests/test_llm_client.py
git commit -m "feat: add LLMClient transport via LiteLLM"
```

---

### Task 3: Wire ResumeTailorer to LLMClient

**Files:**
- Modify: `product/resume_tailorer/tailorer/resume_tailorer.py`
- Modify: `product/tests/test_resume_tailorer.py`
- Modify: `product/tests/test_optimizer.py`
- Modify: `product/tests/test_integration.py` (if it still mocks `anthropic`)

**Interfaces:**
- Consumes: `LLMClient`, `resolve_settings`, `LLMSettings`
- Produces:
  - `ResumeTailorer.__init__(self, llm: LLMClient | None = None, settings: LLMSettings | None = None)`
    - If `llm` given, use it.
    - Else if `settings` given, `llm = LLMClient(settings)`.
    - Else `llm = LLMClient(resolve_settings())` (env-only; may raise `ValueError`).
  - Remove `self.client` Anthropic object and `self.model` Claude hardcode.
  - Keep `self.llm` for tests.
  - `tailor(...)` and `_refine_resume(...)` call `self.llm.complete(system_prompt, user_prompt, max_tokens=2000)` and return the string.
  - Do not change prompt builder method bodies.

- [ ] **Step 1: Rewrite failing/updated tests first**

Replace anthropic mocking in `test_resume_tailorer.py` with:

```python
from unittest.mock import MagicMock
from resume_tailorer.tailorer import ResumeTailorer
from resume_tailorer.llm.settings import LLMSettings
from resume_tailorer.llm.client import LLMClient


def test_resume_tailorer_instantiation():
    llm = MagicMock(spec=LLMClient)
    tailorer = ResumeTailorer(llm=llm)
    assert tailorer is not None
    assert tailorer.llm is llm


def test_resume_tailorer_tailor_method_calls_llm(sample_profile, sample_job_analysis, sample_gap_report):
    llm = MagicMock(spec=LLMClient)
    llm.complete.return_value = "Here is the tailored resume content..."
    tailorer = ResumeTailorer(llm=llm)
    result = tailorer.tailor(sample_profile, sample_job_analysis, sample_gap_report)
    assert llm.complete.called
    args, kwargs = llm.complete.call_args
    assert "fabricat" in args[0].lower() or "never" in args[0].lower()
    assert isinstance(args[1], str)
    assert isinstance(result, str)
```

Keep `test_resume_tailorer_system_prompt_forbids_fabrication` but construct with `ResumeTailorer(llm=MagicMock())`.

In `test_optimizer.py` / `test_integration.py`: remove `sys.modules['anthropic']` bootstrap; inject `MagicMock` LLM via `ResumeTailorer(llm=...)` or patch `ResumeTailorer` construction sites. Optimizer creates `ResumeTailorer()` internally — update `ResumeTailoringOptimizer` only if needed:

If optimizer does `self.tailorer = ResumeTailorer()`, either:
- pass optional `llm` into `ResumeTailoringOptimizer.__init__(..., llm=None)` and forward to `ResumeTailorer(llm=llm)`, or
- patch at test time with `unittest.mock.patch.object`.

**Preferred:** add optional `llm` to optimizer:

```python
# in optimizer.py __init__
def __init__(self, max_iterations: int = 5, llm=None):
    self.max_iterations = max_iterations
    self.tailorer = ResumeTailorer(llm=llm) if llm is not None else ResumeTailorer()
```

Tests that previously asserted `optimizer.tailorer.model == "claude-..."` must assert `optimizer.tailorer.llm is not None` or that `complete` was called instead.

- [ ] **Step 2: Run tests — expect FAIL** until implementation matches

Run: `python -m pytest tests/test_resume_tailorer.py tests/test_optimizer.py -v`  
Expected: FAIL on Anthropic attributes / missing `llm` param

- [ ] **Step 3: Implement ResumeTailorer + optimizer wiring**

```python
# resume_tailorer.py — __init__ and call sites only
from resume_tailorer.llm.client import LLMClient
from resume_tailorer.llm.settings import LLMSettings, resolve_settings

class ResumeTailorer:
    def __init__(self, llm: LLMClient | None = None, settings: LLMSettings | None = None):
        if llm is not None:
            self.llm = llm
        elif settings is not None:
            self.llm = LLMClient(settings)
        else:
            self.llm = LLMClient(resolve_settings())

    def tailor(...):
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(...)
        return self.llm.complete(system_prompt, user_prompt, max_tokens=2000)

    def _refine_resume(...):
        system_prompt = self._build_refinement_system_prompt()
        user_prompt = self._build_refinement_user_prompt(...)
        return self.llm.complete(system_prompt, user_prompt, max_tokens=2000)
```

Update module docstring to say “LLM provider via LLMClient” not “Claude API” only. Keep fabrication wording inside prompts.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_resume_tailorer.py tests/test_optimizer.py tests/test_integration.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add product/resume_tailorer/tailorer/resume_tailorer.py product/resume_tailorer/tailorer/optimizer.py product/tests/test_resume_tailorer.py product/tests/test_optimizer.py product/tests/test_integration.py
git commit -m "feat: route resume tailoring through LLMClient"
```

---

### Task 4: Streamlit sidebar config + pass settings into pipeline

**Files:**
- Modify: `product/resume_tailorer/app.py`
- Test: `product/tests/test_app_llm_sidebar.py` (pure helpers — extract small functions so Streamlit is not required)

**Interfaces:**
- Produces (in `app.py` or tiny helper module `resume_tailorer/llm/ui.py`):
  - `COMMON_MODELS = ["openai/gpt-4o", "anthropic/claude-3-5-sonnet-20241022", "gemini/gemini-1.5-pro"]`
  - `def sidebar_overrides_from_widgets(model: str, api_key: str, api_base: str) -> dict` returning `{"model": ..., "api_key": ..., "api_base": ...}` with empties as `""`
  - App resolves settings **after** button click, **before** `ResumeTailorer` / optimizer:

```python
from resume_tailorer.llm.settings import resolve_settings, MISSING_CONFIG_MESSAGE
from resume_tailorer.llm.client import LLMClient

# in sidebar, after length controls, before run button:
st.header("4. Model provider")
st.caption("Optional: leave blank to use LLM_MODEL / LLM_API_KEY / LLM_API_BASE from the environment.")
model_choice = st.selectbox("Common models (helper)", options=["(custom / env)"] + COMMON_MODELS)
model_input = st.text_input("Model id", value="" if model_choice.startswith("(") else model_choice,
    help="Examples: openai/gpt-4o, anthropic/claude-3-5-sonnet-20241022, gemini/gemini-1.5-pro")
api_key_input = st.text_input("API key", type="password")
api_base_input = st.text_input("Base URL (optional)", help="Azure / Ollama / proxy / OpenRouter-compatible endpoints")

# after run_clicked validations, before parsing:
try:
    settings = resolve_settings(
        model=model_input,
        api_key=api_key_input,
        api_base=api_base_input,
    )
except ValueError as exc:
    st.error(str(exc))
    if os.environ.get("ANTHROPIC_API_KEY") and not os.environ.get("LLM_API_KEY"):
        st.info(
            "ANTHROPIC_API_KEY is set but no longer used alone. "
            "Set LLM_MODEL=anthropic/claude-3-5-sonnet-20241022 and LLM_API_KEY to your Anthropic key."
        )
    return

llm = LLMClient(settings)
# pass llm into ResumeTailoringOptimizer(llm=llm) / ResumeTailorer(llm=llm)
```

Find the current call sites that construct `ResumeTailorer()` / `ResumeTailoringOptimizer()` in `app.py` and pass `llm=llm`.

**Never** write `api_key_input` to disk, `st.write` it, or include it in exceptions shown to the user beyond the mapped RuntimeError messages.

- [ ] **Step 1: Write failing unit tests for override helper**

```python
# product/tests/test_app_llm_sidebar.py
from resume_tailorer.llm.ui import COMMON_MODELS, collect_sidebar_llm_fields


def test_common_models_include_major_providers():
    joined = " ".join(COMMON_MODELS).lower()
    assert "openai" in joined and "anthropic" in joined and "gemini" in joined


def test_collect_sidebar_fields_strips_whitespace():
    fields = collect_sidebar_llm_fields("  openai/gpt-4o  ", "  sk  ", "  https://x  ")
    assert fields == {"model": "openai/gpt-4o", "api_key": "sk", "api_base": "https://x"}
```

- [ ] **Step 2: Run — expect FAIL**

- [ ] **Step 3: Implement `llm/ui.py` and wire `app.py`**

```python
# product/resume_tailorer/llm/ui.py
COMMON_MODELS = [
    "openai/gpt-4o",
    "anthropic/claude-3-5-sonnet-20241022",
    "gemini/gemini-1.5-pro",
]

def collect_sidebar_llm_fields(model: str, api_key: str, api_base: str) -> dict:
    return {
        "model": (model or "").strip(),
        "api_key": (api_key or "").strip(),
        "api_base": (api_base or "").strip(),
    }
```

Wire as described above. On `RuntimeError` from tailor/optimize, `st.error(str(exc))`.

- [ ] **Step 4: Run unit tests**

Run: `python -m pytest tests/test_app_llm_sidebar.py tests/test_llm_settings.py -v`  
Expected: PASS

Manual smoke (engineer): start Streamlit without env → click Tailor → see missing-config message. Do not require live keys in CI.

- [ ] **Step 5: Commit**

```bash
git add product/resume_tailorer/llm/ui.py product/resume_tailorer/app.py product/tests/test_app_llm_sidebar.py
git commit -m "feat: add sidebar LLM provider settings for resume tailoring"
```

---

### Task 5: Docs + requirements pin test + full suite

**Files:**
- Modify: `product/README.md` (Configuration / Usage sections)
- Modify: `product/docs/architecture.md` (env var section)
- Modify: `product/tests/test_requirements_pin.py`
- Modify: `product/requirements.txt` (confirm final pins)

- [ ] **Step 1: Replace Anthropic-only pin test**

```python
# product/tests/test_requirements_pin.py
from pathlib import Path


def test_litellm_is_pinned_for_multi_provider_client():
    requirements = (Path(__file__).resolve().parent.parent / "requirements.txt").read_text()
    assert any(line.startswith("litellm==") for line in requirements.splitlines()), (
        "litellm must be pinned — LLMClient depends on it for multi-provider calls"
    )


def test_anthropic_is_not_the_sole_hardcoded_runtime_dep():
    """Anthropic may appear transitively; product code must not require anthropic== as the only LLM path."""
    requirements = (Path(__file__).resolve().parent.parent / "requirements.txt").read_text()
    # Soft check: litellm present is enough; if anthropic remains, that is ok only as unused legacy —
    # prefer absence after Task 2.
    assert "litellm==" in requirements
```

- [ ] **Step 2: Run pin test — FAIL if litellm missing, then ensure requirements already updated from Task 2**

- [ ] **Step 3: Update README Configuration section**

Replace Anthropic-only block with:

```markdown
### Required Environment Variables (or use the sidebar)

```bash
set LLM_MODEL=openai/gpt-4o
set LLM_API_KEY=sk-...
# optional
set LLM_API_BASE=https://your-proxy.example/v1
```

In the Streamlit sidebar, section **Model provider** overrides these when filled.
Job Search and Applications do not need an LLM key.
```

Update architecture.md env section similarly. Mention Anthropic migration one-liner.

- [ ] **Step 4: Full suite**

Run: `python -m pytest tests/ -q`  
Expected: all PASS (including prior 310+ tests; count may rise)

- [ ] **Step 5: Commit**

```bash
git add product/README.md product/docs/architecture.md product/tests/test_requirements_pin.py product/requirements.txt
git commit -m "docs: document provider-agnostic LLM_MODEL configuration"
```

---

## Spec coverage checklist

| Spec requirement | Task |
|---|---|
| Model + key + optional base URL | 1, 4 |
| Env default + sidebar override | 1, 4 |
| Hard fail if missing; no silent Anthropic default | 1, 4 |
| Single `LLMClient` boundary / LiteLLM internal | 2, 3 |
| Plain error messages | 2, 4 |
| Keys not persisted | 4 (session only) |
| Job Search / Applications without LLM | unchanged; verified by not requiring settings outside app tailor path |
| Tests: mock client, override beats env, no config error | 1, 2, 3 |
| README / architecture / pin test | 5 |
| Fabrication prompts unchanged | 3 (builders untouched) |

## Placeholder / consistency self-review

- No TBD steps; exact messages match the design spec.
- `LLMSettings` / `LLMClient.complete` names consistent across tasks.
- Optimizer optional `llm` param documented so tests do not need live env.
