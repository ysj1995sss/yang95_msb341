"""Assist kit: copy-ready answers, never guessed (decision 027). Synthetic data only."""

from resume_tailorer.ui.application_kit import MISSING, OPTIONAL, READY, build_kit, kit_summary

RECORD = {
    "profile": {
        "contact_info": {"name": "Riley Ann Park", "email": "riley@example.com", "phone": "555-0100", "location": ""},
        "work_experience": [{"employer": "Acme", "title": "Analyst"}],
        "education": [{"institution": "State U", "degree": "BS", "field": "Economics"}],
    },
    "links": {"linkedin": "https://linkedin.example/riley", "portfolio": "", "github": ""},
    "authorization": {"authorized_to_work": True, "sponsorship_required": None},
}
HANDOFF = {"job_id": "j", "version": 2, "validation_status": "PASS"}


def _by_label(fields):
    return {f.label: f for f in fields}


def test_values_come_from_the_profile_resume_and_saved_answers():
    kit = _by_label(build_kit(RECORD, HANDOFF, [{"question": "Why Acme?", "answer": "Their analytics work."}]))
    assert (kit["First name"].value, kit["Last name"].value) == ("Riley", "Ann Park")
    assert kit["Email"].state == READY and kit["Resume"].value == "tailored_resume_v2.pdf"
    assert kit["Degree"].value == "BS Economics"
    assert kit["Legally authorized to work here?"].value == "Yes"
    assert kit["Why Acme?"].value == "Their analytics work." and kit["Why Acme?"].source == "Your saved answers"


def test_nothing_is_guessed():
    kit = _by_label(build_kit(RECORD, HANDOFF))
    assert kit["Location"].state == MISSING and kit["Location"].value == ""
    # A legal answer the user hasn't given stays missing, never defaulted to "No".
    assert kit["Will you need visa sponsorship?"].state == MISSING
    assert kit["Website or portfolio"].state == OPTIONAL
    assert "GitHub" not in kit


def test_a_failed_or_missing_resume_is_not_offered():
    assert _by_label(build_kit(RECORD, None))["Resume"].state == MISSING
    failed = dict(HANDOFF, validation_status="FAIL")
    assert _by_label(build_kit(RECORD, failed))["Resume"].fix == "Tailor"
    assert _by_label(build_kit(RECORD, failed))["Resume"].state == MISSING


def test_empty_record_is_all_missing_and_summarised():
    fields = build_kit({}, None)
    assert all(f.state != READY for f in fields)
    assert kit_summary(fields).startswith("0 answers ready to copy. Missing: First name")
