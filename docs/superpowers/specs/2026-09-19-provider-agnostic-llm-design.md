# Design: Provider-Agnostic LLM for Resume Tailoring

**Date:** 2026-09-19  
**Status:** Approved for planning (pending user review of this file)  
**Repo:** `yang95_msb341` / `product/`

## Problem

Resume tailoring is hardcoded to Anthropic (`anthropic.Anthropic()`, `ANTHROPIC_API_KEY`, Claude model id). Classmates and future users who have OpenAI, Gemini, Groq, Azure, OpenRouter, or a local/proxy endpoint cannot run the core product without code changes.

## Goals

- Users can bring **any** LLM provider via **model id + API key + optional base URL**.
- Configuration via **environment variables** (default) and **Streamlit sidebar override**.
- If neither env nor sidebar supplies model + key → **fail clearly** (no silent Anthropic default).
- Fabrication guardrails and prompt text stay in `ResumeTailorer`; only the network transport changes.
- Job Search and Applications continue to work without an LLM key.

## Non-goals

- Rewriting gap analysis, PDF, job search, or application submit logic.
- Persisting API keys to disk, SQLite, or git.
- Auto-detecting every vendor from key prefix alone.
- Requiring users to create an account with a specific aggregator brand.

## Architecture

```
Streamlit sidebar / env
        ↓
  LLMSettings (resolved config)
        ↓
  LLMClient.complete(system, user) → str
        ↓
  ResumeTailorer.tailor / _refine_resume
```

- **Single network boundary:** `LLMClient` (e.g. under `product/resume_tailorer/llm/`).
- Tailoring modules must not import Anthropic/OpenAI/Gemini SDKs directly.
- **Internal transport (implementation choice):** use a multi-provider client library (preferred: LiteLLM) so one `complete()` call covers Anthropic, OpenAI, Gemini, Groq, OpenRouter, Azure, Ollama-compatible endpoints, etc. Users never sign up for that library; they only see model / key / base URL.

## Configuration

**Resolution order:** sidebar values win when filled → else env → else hard fail.

| Setting | Env | Sidebar |
|---|---|---|
| Model id | `LLM_MODEL` | Text input + short common-models helper list |
| API key | `LLM_API_KEY` | Password field (session only) |
| Base URL (optional) | `LLM_API_BASE` | Optional advanced field |

**Examples (help text):**

- `openai/gpt-4o`
- `anthropic/claude-3-5-sonnet-20241022`
- `gemini/gemini-1.5-pro`
- Custom / Azure / Ollama / proxy: set **Base URL** and the model id that endpoint expects

**Security:**

- Never log the API key.
- Never write the key to git, `.env` from the UI, or application databases.
- Sidebar key lives in Streamlit session state only for the session.

**Scope of required config:**

- Only the **Tailor my resume** path requires resolved model + key.
- Job Search and Applications Preview do not.

## Error handling

| Condition | User-facing message (plain language) |
|---|---|
| Missing model or key | Set `LLM_MODEL` and `LLM_API_KEY` in the environment, or fill Model and API key in the sidebar. |
| HTTP 401 / auth failure | Provider rejected the API key. |
| Model not found / 404 | Model not found for this provider; check the model id (and Base URL if using a proxy). |
| Network / timeout | Could not reach the model provider. |

No network call is made when config is incomplete.

## Migration from Anthropic-only

- Stop treating `ANTHROPIC_API_KEY` as the sole supported path.
- Document `LLM_*` + sidebar in `product/README.md`.
- Anthropic users migrate by setting e.g. `LLM_MODEL=anthropic/claude-3-5-sonnet-20241022` and `LLM_API_KEY=<their Anthropic key>`.
- Optional UX: if only `ANTHROPIC_API_KEY` is present, show a **deprecation hint** to switch to `LLM_*` — still do not silently run on that key alone after this change ships (keeps the new contract honest).

## Testing

- Unit-test `LLMClient` with mocked network: asserts system + user prompts are forwarded; returns text.
- Tailor / optimizer tests mock `LLMClient` instead of `sys.modules['anthropic']`.
- Test: no config → clear error, zero network calls.
- Test: sidebar override beats env when both are set.
- Keep fabrication prompt content tests that do not depend on a live provider.

## Success criteria

1. A user with only an OpenAI (or Gemini, etc.) key can tailor a resume via sidebar without code edits.
2. A user with only env `LLM_*` can tailor without touching the sidebar.
3. With no config, the app explains what to set and does not call any provider.
4. Existing safety prompts remain the source of fabrication constraints.

## Implementation notes (for the plan)

- Add dependency only as needed for the chosen transport (document in README).
- Update Streamlit sidebar in `app.py` before the tailor button runs.
- Replace `anthropic.Anthropic()` / `messages.create` in `resume_tailorer.py` with `LLMClient.complete`.
- Update `requirements.txt`, architecture docs, and the requirements-pin test (no longer assert Anthropic-only Messages API pin as the sole LLM path).
