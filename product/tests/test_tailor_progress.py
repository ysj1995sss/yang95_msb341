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


def test_queue_titles_distinguish_edits_with_the_same_requirement():
    from resume_tailorer.ui import tailor_progress

    title = getattr(tailor_progress, "change_title", None)
    assert callable(title), "change_title must make each review row identifiable"
    first = change("a", original="Built sales reports", proposed="Built SQL reports", requirement="SQL")
    second = change("b", original="Led customer surveys", proposed="Led survey analysis", requirement="SQL")
    assert title(first, 1) != title(second, 2)
    assert "Built sales reports" in title(first, 1)
    assert "Built SQL reports" in title(first, 1)


def test_duplicate_identity_never_merges_different_source_occurrences():
    from dataclasses import replace

    from resume_tailorer.ui import tailor_progress

    key = getattr(tailor_progress, "duplicate_key", None)
    assert callable(key), "duplicate_key must use a real source anchor"
    first = replace(change("a"), source_index=1)
    second = replace(change("b"), source_index=2)
    assert key(first) != key(second)
    assert key(first) is not None


def test_freeform_diff_ordinal_is_not_treated_as_a_source_anchor():
    from dataclasses import replace

    from resume_tailorer.ui import tailor_progress

    key = getattr(tailor_progress, "duplicate_key", None)
    assert callable(key)
    assert key(replace(change("freeform:0"), source_index=0)) is None


def test_check_reasons_read_as_plain_words():
    """Dogfood round 5: a change's "Resume change" box showed the raw check output, Python list and all."""
    from resume_tailorer.ui.tailor_progress import readable_reason

    raw = ("⚠️ POSSIBLY UNVERIFIED: new term(s) ['communicate', 'recurring'] in 'Led a team of 3 analysts "
           "building weekly sales dashboards in Tableau to communicate sales trends' not grounded in the original "
           "bullet or profile -- review before using")
    assert readable_reason(raw) == "Adds words your facts don't show: communicate, recurring."
    assert readable_reason("⚠️ FABRICATION RISK: 'kubernetes' mentioned in 'Ran Kubernetes clusters' but not in "
                           "the original bullet or profile") == "Names Kubernetes, which your facts don't show."
    assert readable_reason("⚠️ FABRICATION RISK: metric '40%' mentioned in 'Cut costs 40%' but not in the original "
                           "bullet or profile") == "Adds a number your facts don't show: 40%."
    assert readable_reason("SEMANTIC DRIFT: dropped metric(s) ['120'] from the original bullet 'Built SQL for 120 "
                           "stores' -- a number/scale disappearing changes the claim") == (
        "Drops a number from your original: 120.")
    assert readable_reason("SEMANTIC DRIFT: dropped word(s) ['pricing'] from the original bullet's core claim "
                           "'Built SQL pipelines feeding pricing reviews' -- rewrite changes what was claimed, not "
                           "just how it's phrased") == "Drops part of what you did: pricing."
    # Several issues, and messages that are already plain words, stay readable.
    both = readable_reason(raw + " adds “dbt”, which you haven't shown evidence for")
    assert both == "Adds words your facts don't show: communicate, recurring. Adds “dbt”, which you haven't shown evidence for."
    assert readable_reason("Names the tool the posting asks for") == "Names the tool the posting asks for"


def test_word_resume_turn_down_labels_read_as_plain_words():
    """Round 6 bug hunt: "Turned down by our checks" on a Word resume read "— semantic drift"."""
    from resume_tailorer.ui.tailor_progress import readable_reason

    assert readable_reason("semantic drift") == "It dropped part of what your original says."
    assert readable_reason("length cap exceeded") == "It made the line too long."
    assert readable_reason("unverified content") == "It added words your facts don't show."
    assert readable_reason("unsupported requirement term") == "It named a skill you haven't shown evidence for."
