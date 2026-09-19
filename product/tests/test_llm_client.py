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
