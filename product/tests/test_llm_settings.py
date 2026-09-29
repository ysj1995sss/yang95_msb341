import pytest
from resume_tailorer.llm.settings import apply_secret_settings, resolve_settings, LLMSettings


def test_streamlit_secrets_fill_missing_environment_without_overriding_local_values():
    env = {"LLM_MODEL": "local/model"}

    apply_secret_settings(
        {
            "LLM_MODEL": "cloud/model",
            "LLM_API_KEY": "cloud-key",
            "LLM_API_BASE": "https://cloud.example.test",
            "UNRELATED": "ignored",
        },
        env,
    )

    assert env == {
        "LLM_MODEL": "local/model",
        "LLM_API_KEY": "cloud-key",
        "LLM_API_BASE": "https://cloud.example.test",
    }


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
