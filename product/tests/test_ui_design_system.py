from resume_tailorer.ui.design_system import (
    DESTINATIONS,
    THEME_CSS,
    TOKENS,
    display_optional,
    progress_steps,
    semantic_status,
)


def _luminance(hex_color: str) -> float:
    h = hex_color.lstrip("#")
    channels = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def _contrast(a: str, b: str) -> float:
    hi, lo = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def test_six_user_facing_destinations_in_order():
    assert [d.name for d in DESTINATIONS] == ["Home", "Career Profile", "Jobs", "Tailor", "Apply", "Tracker"]
    assert DESTINATIONS[0].path == "app.py"


def test_text_tokens_meet_aa_on_paper():
    for name in ("ink", "action", "verified", "review", "blocked", "muted"):
        assert _contrast(TOKENS[name], TOKENS["paper"]) >= 4.5, name


def test_text_tokens_meet_aa_on_canvas_with_the_darker_amber():
    for name in ("ink", "action", "verified", "blocked", "muted", "review_on_canvas"):
        assert _contrast(TOKENS[name], TOKENS["canvas"]) >= 4.5, name
    assert _contrast(TOKENS["review"], TOKENS["canvas"]) < 4.5  # the reason review_on_canvas exists


def test_css_respects_reduced_motion_and_has_no_global_ribbon():
    assert "prefers-reduced-motion" in THEME_CSS
    assert "jc-ribbon" not in THEME_CSS


def test_progress_marks_first_unfinished_step_current():
    steps = progress_steps(("a", "b", "c"), (True, False, False))
    assert [s.state for s in steps] == ["complete", "current", "pending"]
    assert [s.state for s in progress_steps(("a", "b"), (True, True))] == ["complete", "complete"]


def test_warning_is_review_not_ready():
    status = semantic_status("WARNING")
    assert status.label == "Review required"
    assert status.application_ready is False
    assert semantic_status("FAIL").application_ready is False


def test_unknown_value_is_not_zero():
    assert display_optional(None, "Not assessed") == "Not assessed"
    assert display_optional("", "Not stated") == "Not stated"
    assert display_optional(0, "Not assessed") == "0"


def test_primary_buttons_use_white_text_on_action_blue():
    assert _contrast("#FFFFFF", TOKENS["action"]) >= 4.5
    assert 'stBaseButton-primary"] * { color: #FFFFFF' in THEME_CSS.replace("\n", " ") or "color: #FFFFFF !important" in THEME_CSS
