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


# Alias used by the task brief interface description.
sidebar_overrides_from_widgets = collect_sidebar_llm_fields
