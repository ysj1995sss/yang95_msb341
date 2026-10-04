from resume_tailorer.applications.models import ATSCapability, ApplicationStatus
from resume_tailorer.ui.apply_readiness import build_apply_view, mode_options, valid_employer_url

UNPROVEN = ATSCapability(platform="greenhouse", manual_supported=True, assist_supported=True,
                         final_submission=False, notes="Real submission is not verified.")
JOB = {"job_id": "greenhouse_1", "title": "Analyst", "company": "Northwind", "url": "https://boards.example.com/1"}
HANDOFF = {"pdf_path": "x.pdf", "version": 2, "validation_status": "PASS"}


def view(**kw):
    base = dict(job=JOB, handoff=HANDOFF, review_complete=True, facts_confirmed=True, has_profile=True,
                approved_answers=0, unanswered=(), status=None, capability=UNPROVEN)
    base.update(kw)
    return build_apply_view(**base)


def test_manual_is_the_recommended_mode_and_assist_auto_stay_unavailable():
    modes = {m.name: m for m in mode_options(UNPROVEN)}
    assert modes["Manual"].available and modes["Manual"].recommended
    assert not modes["Assist"].available and not modes["Auto"].available
    assert "Not available yet" in modes["Assist"].detail


def test_ready_job_can_be_opened_and_tracked_but_not_marked_applied_yet():
    v = view()
    assert v.stage == "ready" and v.can_open and v.can_track and not v.can_mark_applied


def test_without_a_tailored_resume_it_cannot_be_tracked():
    v = view(handoff=None)
    assert v.stage == "not_ready" and v.can_open and not v.can_track
    assert any(i.label == "Tailored resume" and i.state == "blocked" for i in v.checklist)


def test_a_bad_link_cannot_be_opened():
    assert not valid_employer_url("javascript:alert(1)")
    assert not valid_employer_url("")
    assert not view(job=dict(JOB, url="not a link")).can_open


def test_tracked_then_marked_applied():
    tracked = view(status=ApplicationStatus.READY_TO_APPLY)
    assert tracked.stage == "tracked" and tracked.can_mark_applied and not tracked.can_track
    applied = view(status=ApplicationStatus.APPLIED)
    assert applied.stage == "applied" and not applied.can_mark_applied


def test_opening_the_employer_page_is_never_called_submitting():
    for status in (None, ApplicationStatus.READY_TO_APPLY):
        v = view(status=status)
        assert "submitted" not in v.headline.lower()
        assert all("submitted" not in i.detail.lower() for i in v.checklist)


def test_warnings_and_unreviewed_changes_are_flagged():
    v = view(handoff=dict(HANDOFF, validation_status="WARNING"), review_complete=False, unanswered=("Why us?",))
    states = {i.label: i.state for i in v.checklist}
    assert states["Tailored resume"] == "review"
    assert states["Your review of the changes"] == "review"
    assert states["Application questions"] == "review"
