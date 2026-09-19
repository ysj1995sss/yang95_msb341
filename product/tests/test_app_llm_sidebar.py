from resume_tailorer.llm.ui import COMMON_MODELS, collect_sidebar_llm_fields


def test_common_models_include_major_providers():
    joined = " ".join(COMMON_MODELS).lower()
    assert "openai" in joined and "anthropic" in joined and "gemini" in joined


def test_collect_sidebar_fields_strips_whitespace():
    fields = collect_sidebar_llm_fields("  openai/gpt-4o  ", "  sk  ", "  https://x  ")
    assert fields == {"model": "openai/gpt-4o", "api_key": "sk", "api_base": "https://x"}
