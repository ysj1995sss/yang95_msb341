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
    client = LLMClient(_settings(), sleep=lambda s: None)
    with patch(
        "resume_tailorer.llm.client.litellm.completion",
        side_effect=Exception("Connection timeout"),
    ):
        with pytest.raises(RuntimeError, match="Could not reach the model provider"):
            client.complete("s", "u")


def _ok(text="ok"):
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = text
    return response


def test_every_call_has_a_timeout_and_no_hidden_provider_retries():
    client = LLMClient(_settings())
    with patch("resume_tailorer.llm.client.litellm.completion", return_value=_ok()) as mock_completion:
        client.complete("s", "u")
    kwargs = mock_completion.call_args.kwargs
    assert kwargs["timeout"] == LLMClient.TIMEOUT_SECONDS
    assert kwargs["num_retries"] == 0


def test_transient_failures_are_retried_a_bounded_number_of_times():
    sleeps = []
    client = LLMClient(_settings(), sleep=sleeps.append)
    errors = [Exception("Request timed out"), Exception("429 rate limit exceeded")]
    with patch("resume_tailorer.llm.client.litellm.completion", side_effect=[*errors, _ok("done")]) as mock_completion:
        assert client.complete("s", "u") == "done"
    assert mock_completion.call_count == 3
    assert len(sleeps) == 2


def test_gives_up_after_the_retry_limit():
    client = LLMClient(_settings(), sleep=lambda s: None)
    with patch("resume_tailorer.llm.client.litellm.completion", side_effect=Exception("503 service unavailable")) as mock_completion:
        with pytest.raises(RuntimeError):
            client.complete("s", "u")
    assert mock_completion.call_count == 1 + LLMClient.MAX_RETRIES


def test_auth_errors_are_not_retried():
    client = LLMClient(_settings(), sleep=lambda s: None)
    with patch("resume_tailorer.llm.client.litellm.completion", side_effect=Exception("401 Unauthorized")) as mock_completion:
        with pytest.raises(RuntimeError, match="rejected the API key"):
            client.complete("s", "u")
    assert mock_completion.call_count == 1


def _reply(text, finish="stop"):
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = text
    response.choices[0].finish_reason = finish
    return response


def test_a_reply_cut_off_at_the_token_limit_is_retried_with_more_room():
    client = LLMClient(_settings(), sleep=lambda s: None)
    replies = [_reply("Let me think about this...", "length"), _reply('{"ok": true}')]
    with patch("resume_tailorer.llm.client.litellm.completion", side_effect=replies) as mock_completion:
        assert client.complete("s", "u", max_tokens=2000) == '{"ok": true}'
    assert [c.kwargs["max_tokens"] for c in mock_completion.call_args_list] == [2000, 8000]


def test_a_reply_still_cut_off_after_the_retry_is_reported_plainly():
    client = LLMClient(_settings(), sleep=lambda s: None)
    with patch("resume_tailorer.llm.client.litellm.completion", return_value=_reply("thinking...", "length")) as mock_completion:
        with pytest.raises(RuntimeError, match="cut off.*non-reasoning model"):
            client.complete("s", "u", max_tokens=2000)
    assert mock_completion.call_count == 2


def test_think_blocks_are_removed_from_replies():
    client = LLMClient(_settings())
    with patch("resume_tailorer.llm.client.litellm.completion", return_value=_reply("<think>hmm\nlong</think>\n[1, 2]")):
        assert client.complete("s", "u") == "[1, 2]"


def test_openrouter_calls_turn_reasoning_off():
    client = LLMClient(LLMSettings(model="openrouter/nvidia/nemotron-3-ultra-550b-a55b:free", api_key="k"))
    with patch("resume_tailorer.llm.client.litellm.completion", return_value=_reply("ok")) as mock_completion:
        client.complete("s", "u")
    assert mock_completion.call_args.kwargs["extra_body"] == {"reasoning": {"enabled": False}}


def test_other_providers_are_not_sent_reasoning_options():
    client = LLMClient(_settings())
    with patch("resume_tailorer.llm.client.litellm.completion", return_value=_reply("ok")) as mock_completion:
        client.complete("s", "u")
    assert "extra_body" not in mock_completion.call_args.kwargs


def test_a_model_that_requires_reasoning_is_called_again_without_the_switch():
    client = LLMClient(LLMSettings(model="openrouter/some/always-thinks", api_key="k"), sleep=lambda s: None)
    calls = []

    def fake(**kwargs):
        calls.append("extra_body" in kwargs)
        if "extra_body" in kwargs:
            raise Exception("Reasoning is mandatory for this endpoint and cannot be disabled")
        return _reply("done")

    with patch("resume_tailorer.llm.client.litellm.completion", side_effect=fake):
        assert client.complete("s", "u") == "done"
    assert calls == [True, False]


def test_a_busy_provider_is_waited_out_longer_and_reported_plainly():
    sleeps = []
    client = LLMClient(_settings(), sleep=sleeps.append)
    busy = Exception("OpenrouterException - Upstream error: Service temporarily overloaded")
    with patch("resume_tailorer.llm.client.litellm.completion", side_effect=busy) as mock_completion:
        with pytest.raises(RuntimeError, match="busy right now"):
            client.complete("s", "u")
    assert mock_completion.call_count == 1 + LLMClient.MAX_RETRIES
    assert sleeps == [10.0, 20.0, 30.0]


def test_gemini_calls_turn_thinking_off():
    client = LLMClient(LLMSettings(model="gemini/gemini-flash-latest", api_key="k"))
    with patch("resume_tailorer.llm.client.litellm.completion", return_value=_reply("ok")) as mock_completion:
        client.complete("s", "u")
    assert mock_completion.call_args.kwargs["reasoning_effort"] == "disable"
    assert "extra_body" not in mock_completion.call_args.kwargs


def test_a_gemini_model_that_must_think_is_called_again_without_the_switch():
    client = LLMClient(LLMSettings(model="gemini/gemini-pro-latest", api_key="k"), sleep=lambda s: None)
    calls = []

    def fake(**kwargs):
        calls.append("reasoning_effort" in kwargs)
        if "reasoning_effort" in kwargs:
            raise Exception("Budget 0 is invalid. This model only works in thinking mode.")
        return _reply("done")

    with patch("resume_tailorer.llm.client.litellm.completion", side_effect=fake):
        assert client.complete("s", "u") == "done"
    assert calls == [True, False]


def test_an_empty_reply_that_hit_the_limit_is_retried_with_more_room():
    client = LLMClient(_settings(), sleep=lambda s: None)
    replies = [_reply(None, "length"), _reply("[1]")]
    with patch("resume_tailorer.llm.client.litellm.completion", side_effect=replies) as mock_completion:
        assert client.complete("s", "u", max_tokens=2000) == "[1]"
    assert [c.kwargs["max_tokens"] for c in mock_completion.call_args_list] == [2000, 8000]


def test_an_empty_reply_for_another_reason_is_reported_plainly():
    client = LLMClient(_settings(), sleep=lambda s: None)
    with patch("resume_tailorer.llm.client.litellm.completion", return_value=_reply(None, "content_filter")):
        with pytest.raises(RuntimeError, match="empty reply \(stopped: content_filter\)"):
            client.complete("s", "u")
