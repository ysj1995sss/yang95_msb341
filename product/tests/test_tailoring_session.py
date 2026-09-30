import os

from resume_tailorer.tailoring_session import (
    ACTIVE_JOB_KEY, HANDOFF_KEY, handoff_for_job, publish_artifact_handoff, sync_pending_job,
)

JD, STATE = "jd", "state"


def test_new_job_replaces_description_and_discards_previous_artifact():
    session = {}
    assert sync_pending_job(session, {"job_id": "A", "description": "Job A"}, JD, STATE)
    session[STATE] = {"pdf_bytes": b"A resume"}
    publish_artifact_handoff(session, pdf_bytes=b"A resume", validation_status="PASS",
                             tailored_alignment=0.8, version=1)

    assert sync_pending_job(session, {"job_id": "B", "description": "Job B"}, JD, STATE)
    assert session[JD] == "Job B"
    assert STATE not in session
    assert HANDOFF_KEY not in session


def test_same_job_again_keeps_user_edits():
    session = {}
    sync_pending_job(session, {"job_id": "A", "description": "Job A"}, JD, STATE)
    session[JD] = "Job A, edited by me"
    assert not sync_pending_job(session, {"job_id": "A", "description": "Job A"}, JD, STATE)
    assert session[JD] == "Job A, edited by me"


def test_handoff_carries_path_score_version_and_job():
    session = {ACTIVE_JOB_KEY: "greenhouse_1"}
    handoff = publish_artifact_handoff(session, pdf_bytes=b"%PDF ok", validation_status="WARNING",
                                       tailored_alignment=0.82, version=2)
    assert os.path.exists(handoff["pdf_path"])
    assert handoff["resume_match_score"] == 0.82
    assert handoff["version"] == 2
    assert handoff_for_job(session, "greenhouse_1") is handoff
    assert handoff_for_job(session, "greenhouse_2") is None


def test_failed_artifact_is_never_handed_off():
    session = {ACTIVE_JOB_KEY: "A"}
    publish_artifact_handoff(session, pdf_bytes=b"%PDF ok", validation_status="PASS",
                             tailored_alignment=0.8, version=1)
    assert publish_artifact_handoff(session, pdf_bytes=b"%PDF bad", validation_status="FAIL",
                                    tailored_alignment=0.9, version=2) is None
    assert HANDOFF_KEY not in session
