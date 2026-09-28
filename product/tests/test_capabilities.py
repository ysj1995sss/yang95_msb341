from resume_tailorer.applications.capabilities import get_capability


def test_known_platform_returns_its_declared_capability():
    cap = get_capability("greenhouse")
    assert cap.platform == "greenhouse"
    assert cap.manual_supported is True
    assert cap.final_submission is False


def test_unrecognized_platform_falls_back_to_manual_only():
    cap = get_capability("some_unknown_ats")
    assert cap.manual_supported is True
    assert cap.assist_supported is False
    assert cap.final_submission is False


def test_empty_platform_falls_back_to_manual_only():
    cap = get_capability("")
    assert cap.manual_supported is True
    assert cap.final_submission is False


def test_platform_name_is_case_insensitive():
    assert get_capability("Greenhouse").platform == "greenhouse"
