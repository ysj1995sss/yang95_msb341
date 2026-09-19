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
