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
