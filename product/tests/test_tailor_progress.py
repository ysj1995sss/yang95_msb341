from resume_tailorer.artifacts.models import ChangeCategory, ResumeChange, ValidationStatus
from resume_tailorer.models import CareerTruthProfile
from resume_tailorer.ui.tailor_progress import (
    VERBS,
    next_undecided,
    review_progress,
    supporting_fact,
)


def change(cid, original="Built weekly reports", proposed="Built weekly SQL reports", requirement="SQL", evidence=""):
    return ResumeChange(
        change_id=cid, section="experience", source_index=0, original_text=original, proposed_text=proposed,
        category=ChangeCategory.REPHRASED, reason="Names the tool the posting asks for", job_requirement=requirement,
        evidence_source="profile", evidence_text=evidence or original, validation_status=ValidationStatus.PASS,
    )


PROFILE = CareerTruthProfile(contact_info={"name": "Sam"}, education=[], work_experience=[],
                             skills=["SQL"], tools=["Tableau"], certifications=[], accomplishments=[])


def test_one_vocabulary_for_decisions():
    assert list(VERBS.values()) == ["Accept change", "Edit manually", "Keep original"]


def test_progress_counts_reviewed_changes_and_blocks_continue_until_rebuilt():
    changes = [change("a"), change("b")]
    p = review_progress(changes, ["a"], dirty=False, status=ValidationStatus.PASS)
    assert p.label == "1 of 2 meaningful changes reviewed" and not p.can_continue and "remaining 1" in p.blocker
    p = review_progress(changes, ["a", "b"], dirty=True, status=ValidationStatus.PASS)
    assert not p.can_continue and "Rebuild" in p.blocker
    p = review_progress(changes, ["a", "b"], dirty=False, status=ValidationStatus.PASS)
    assert p.can_continue and p.blocker == ""


def test_a_failed_resume_can_never_continue():
    p = review_progress([change("a")], ["a"], dirty=False, status=ValidationStatus.FAIL)
    assert not p.can_continue and "failed validation" in p.blocker


def test_no_changes_means_nothing_to_review():
    p = review_progress([], [], dirty=False, status="PASS")
    assert p.label == "No changes need your review" and p.can_continue


def test_next_undecided_wraps_around():
    changes = [change("a"), change("b"), change("c")]
    assert next_undecided(changes, ["a"], after="b") == "c"
    assert next_undecided(changes, ["b", "c"], after="c") == "a"
    assert next_undecided(changes, ["a", "b", "c"]) is None


def test_supporting_fact_points_at_the_skills_list_not_the_bullet():
    assert supporting_fact(change("a"), PROFILE) == "Listed in your skills: SQL"


def test_supporting_fact_falls_back_to_recorded_evidence_then_the_original():
    c = change("a", proposed="Built weekly reports for leadership", requirement="executive communication",
               evidence="Presented findings to the leadership team")
    assert supporting_fact(c, PROFILE) == "Presented findings to the leadership team"
    c = change("b", proposed="Built weekly reports for leadership", requirement="executive communication")
    assert supporting_fact(c, PROFILE).startswith("Your original bullet:")


def test_empty_queue_never_claims_more_than_is_known():
    from dataclasses import replace

    from resume_tailorer.ui.tailor_progress import empty_queue_message, rejected_by_checks

    assert "didn't propose any changes" in empty_queue_message([])
    rejected = replace(change("a", proposed="Built weekly reports"), category=ChangeCategory.REJECTED,
                       reason="162 chars exceeds the 121-char limit")
    assert rejected_by_checks([rejected, change("b")]) == (rejected,)
    message = empty_queue_message([rejected])
    assert "proposed 1 change" in message and "original wording was kept" in message
    assert "already covers" not in message


def test_a_skill_supports_a_change_only_when_the_change_adds_it():
    c = change("a", original="Wrote positioning across the website", proposed="Wrote positioning across website",
               requirement="go-to-market strategy and SQL")
    assert supporting_fact(c, PROFILE).startswith("Your original bullet:")


def test_long_requirements_are_shortened():
    from resume_tailorer.ui.tailor_progress import readable_requirement

    text = readable_requirement(change("a", requirement="word " * 60))
    assert len(text) <= 160 and text.endswith("…")


def test_a_placeholder_evidence_string_is_not_shown_as_a_fact():
    c = change("a", original="Wrote positioning", proposed="Wrote positioning copy", requirement="x", evidence="None")
    assert supporting_fact(c, PROFILE).startswith("Your original bullet:")
