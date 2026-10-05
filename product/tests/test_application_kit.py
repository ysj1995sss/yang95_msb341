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


def test_helper_code_carries_only_ready_values():
    import json

    from resume_tailorer.ui.application_kit import helper_payload

    code = json.loads(helper_payload(build_kit(RECORD, HANDOFF, [{"question": "Why Acme?", "answer": "Analytics."}])))
    assert code["jobCopilotKit"] == 1
    assert code["fields"]["first_name"] == "Riley" and code["fields"]["full_name"] == "Riley Ann Park"
    assert code["fields"]["authorized_to_work"] == "Yes"
    assert "needs_sponsorship" not in code["fields"]  # never answered, so never sent
    assert "location" not in code["fields"] and "portfolio" not in code["fields"]
    assert code["answers"] == [{"question": "Why Acme?", "answer": "Analytics."}]


def test_the_browser_helper_cannot_submit():
    """The helper fills; it must never submit or press a button (spec 006)."""
    import re
    from pathlib import Path

    extension = Path(__file__).resolve().parents[2] / "extension"
    text = (extension / "fill.js").read_text(encoding="utf-8")
    source = "\n".join(line.split("//")[0] for line in text.splitlines())  # code only, not comments
    assert not re.search(r"\.submit\(|requestSubmit|dispatchEvent\(new (?:Submit)?Event\(\"submit", source)
    # Every .click() is on a chosen radio or dropdown option.
    for line in source.splitlines():
        if ".click()" in line:
            assert re.search(r"\bpick\.click\(\)", line), line
    manifest = (extension / "manifest.json").read_text(encoding="utf-8")
    assert '"host_permissions"' not in manifest and '"content_scripts"' not in manifest  # runs only on request
