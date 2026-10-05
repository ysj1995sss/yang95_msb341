"""Tailoring reliability: empty replies, fallback models, length trimming (decision 027)."""

from unittest.mock import MagicMock, patch

import pytest

from resume_tailorer.llm.client import LLMClient
from resume_tailorer.llm.settings import LLMSettings, resolve_settings
from resume_tailorer.tailorer.docx_bullet_tailorer import BulletEdit, DocxBulletTailorer, compact_to_length


def _reply(content, finish="stop"):
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = content
    response.choices[0].finish_reason = finish
    return response


def _client(fallbacks=()):
    return LLMClient(LLMSettings(model="gemini/main", api_key="k", fallback_models=fallbacks), sleep=lambda s: None)


def test_one_empty_reply_is_retried_on_the_same_model():
    client = _client()
    with patch("resume_tailorer.llm.client.litellm.completion", side_effect=[_reply(""), _reply("ok")]) as call:
        assert client.complete("s", "u") == "ok"
    assert [c.kwargs["model"] for c in call.call_args_list] == ["gemini/main", "gemini/main"]


def test_repeated_empty_replies_fall_back_to_the_next_model():
    client = _client(("gemini/backup",))
    replies = [_reply(""), _reply(""), _reply("from backup")]
    with patch("resume_tailorer.llm.client.litellm.completion", side_effect=replies) as call:
        assert client.complete("s", "u") == "from backup"
    assert call.call_args_list[-1].kwargs["model"] == "gemini/backup"
    assert client.model_used == "gemini/backup"


def test_a_busy_provider_falls_back():
    client = _client(("gemini/backup",))
    busy = Exception("503 model overloaded")
    with patch("resume_tailorer.llm.client.litellm.completion",
               side_effect=[busy, busy, busy, busy, _reply("ok")]):
        assert client.complete("s", "u") == "ok"


def test_a_rejected_key_does_not_fall_back():
    client = _client(("gemini/backup",))
    with patch("resume_tailorer.llm.client.litellm.completion", side_effect=Exception("401 invalid api key")) as call:
        with pytest.raises(RuntimeError, match="rejected the API key"):
            client.complete("s", "u")
    assert all(c.kwargs["model"] == "gemini/main" for c in call.call_args_list)


def test_when_every_model_fails_the_last_reason_is_reported():
    client = _client(("gemini/backup",))
    with patch("resume_tailorer.llm.client.litellm.completion", return_value=_reply("")):
        with pytest.raises(RuntimeError, match="empty reply"):
            client.complete("s", "u")


def test_fallback_settings():
    env = {"LLM_MODEL": "gemini/gemini-flash-latest", "LLM_API_KEY": "k"}
    assert resolve_settings(env=env).fallback_models[0] == "gemini/gemini-flash-lite-latest"
    assert resolve_settings(env={**env, "LLM_FALLBACK_MODELS": "none"}).fallback_models == ()
    assert resolve_settings(env={**env, "LLM_FALLBACK_MODELS": "a/x, b/y"}).fallback_models == ("a/x", "b/y")
    assert resolve_settings(env={"LLM_MODEL": "openai/gpt-4o", "LLM_API_KEY": "k"}).fallback_models == ()


def test_compact_trims_filler_but_not_claims():
    text = "Successfully utilized SQL in order to build dashboards, as well as weekly reports"
    trimmed = compact_to_length(text, 60)
    assert trimmed == "Used SQL to build dashboards, and weekly reports"  # stops once it fits
    assert compact_to_length("Built forecasting models for 12 regional sales teams", 20) is None
    assert compact_to_length("Short", 10) == "Short"


def test_repair_prompt_shows_the_rejected_draft_and_its_length():
    from resume_tailorer.parsers.docx_structure import Bullet

    tailorer = DocxBulletTailorer(llm=MagicMock())
    bullet = Bullet(paragraph_index=4, text="Built dashboards", section="work_experience")
    draft = "Built interactive Tableau dashboards for leadership"
    edit = BulletEdit(4, bullet.text, bullet.text, False, rejected_reason="length cap exceeded", rejected_text=draft)
    prompt = tailorer._build_repair_prompt([edit], {4: bullet})
    assert draft in prompt and f'"your_rejected_attempt_length": {len(draft)}' in prompt


def test_litellm_service_unavailable_counts_as_busy_and_falls_back():
    client = _client(("gemini/backup",))
    down = Exception("litellm.ServiceUnavailableError: ServiceUnavailableError: OpenrouterException - ")
    with patch("resume_tailorer.llm.client.litellm.completion", side_effect=[down, down, down, down, _reply("ok")]):
        assert client.complete("s", "u") == "ok"


def test_a_provider_that_stays_down_gets_a_plain_message():
    client = _client()
    down = Exception("litellm.ServiceUnavailableError: ServiceUnavailableError: OpenrouterException - ")
    with patch("resume_tailorer.llm.client.litellm.completion", side_effect=down):
        with pytest.raises(RuntimeError, match="busy right now"):
            client.complete("s", "u")
