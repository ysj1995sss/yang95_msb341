from resume_tailorer.ui.design_system import (
    WORKSPACES,
    build_workflow_state,
    display_optional,
    semantic_status,
)


def test_workspaces_use_the_five_user_facing_destinations():
    assert [workspace.name for workspace in WORKSPACES] == [
        "Fact Vault",
        "Job Discovery",
        "Tailoring Studio",
        "Apply Launchpad",
        "Application Tracker",
    ]


def test_empty_session_starts_at_fact_vault():
    state = build_workflow_state({})
    assert [step.state for step in state] == [
        "current",
        "pending",
        "pending",
        "pending",
    ]


def test_completed_stages_follow_real_session_evidence():
    state = build_workflow_state(
        {
            "career_profile": object(),
            "job_description_text": "Build reliable systems",
            "artifact_run_state": {
                "reviewed": True,
                "validation": "PASS",
                "pdf_bytes": b"pdf",
            },
        }
    )
    assert [step.state for step in state] == [
        "complete",
        "complete",
        "complete",
        "complete",
    ]


def test_unreviewed_artifact_does_not_complete_review_or_ready_stages():
    state = build_workflow_state(
        {
            "career_profile": object(),
            "job_description_text": "Build reliable systems",
            "artifact_run_state": {"reviewed": False, "validation": "PASS", "pdf_bytes": b"pdf"},
        }
    )
    assert [step.state for step in state] == ["complete", "complete", "current", "pending"]


def test_failed_artifact_never_completes_application_ready_stage():
    state = build_workflow_state(
        {
            "career_profile": object(),
            "job_description_text": "Build reliable systems",
            "artifact_run_state": {"reviewed": True, "validation": "FAIL", "pdf_bytes": b"pdf"},
        }
    )
    assert [step.state for step in state][-1] == "current"


def test_warning_is_review_not_ready():
    status = semantic_status("WARNING")
    assert status.label == "Review required"
    assert status.application_ready is False


def test_unknown_value_is_not_zero():
    assert display_optional(None, "Not assessed") == "Not assessed"
    assert display_optional("", "Not stated") == "Not stated"
    assert display_optional(0, "Not assessed") == "0"
