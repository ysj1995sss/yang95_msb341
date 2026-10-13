"""Conservative automatic Tailor decisions; synthetic claims only."""

from dataclasses import replace
from types import SimpleNamespace

from resume_tailorer.artifacts.models import ChangeCategory, ResumeChange, ValidationStatus


def _assisted_module():
    import importlib.util

    assert importlib.util.find_spec("resume_tailorer.ui.assisted_review") is not None, "assisted policy is missing"
    from resume_tailorer.ui import assisted_review

    return assisted_review


def _change(cid="paragraph:1", source_index=1, status=ValidationStatus.PASS,
            category=ChangeCategory.REPHRASED):
    return ResumeChange(
        change_id=cid, section="work_experience", source_index=source_index,
        original_text="Built weekly SQL reports", proposed_text="Built weekly SQL dashboards and reports",
        category=category, reason="Clarify an existing SQL result", job_requirement="SQL reporting",
        evidence_source="original_resume", evidence_text="Built weekly SQL reports",
        validation_status=status,
    )


def _state(changes, mode="assisted"):
    return {"changes": changes, "report": SimpleNamespace(true_gaps=()), "dispositions": {},
            "decided": set(), "manual_texts": {}, "dirty": False, "review_revision": 0,
            "review_mode": mode}


def test_assisted_policy_accepts_only_anchored_passing_rephrases():
    policy = _assisted_module()
    safe = _change()
    failed = _change("paragraph:2", 2, ValidationStatus.FAIL)
    condensed = _change("paragraph:3", 3, category=ChangeCategory.CONDENSED)
    unanchored = _change("freeform:0", 0)
    warning = _change("paragraph:4", 4, ValidationStatus.WARNING)
    entries, reasons = policy.recommend_decisions([safe, failed, condensed, unanchored, warning], set())
    assert entries == [(safe.change_id, "ACCEPTED"), (failed.change_id, "REJECTED")]
    assert all(reasons[change_id] for change_id, _ in entries)


def test_named_platform_gap_and_source_scope_failure_are_never_auto_accepted():
    policy = _assisted_module()
    claimed_qualtrics = _change("paragraph:2", 2)
    wrong_project = replace(_change("paragraph:3", 3, ValidationStatus.FAIL),
                            proposed_text="Used Tableau on the SQL reporting project")
    entries, _reasons = policy.recommend_decisions([claimed_qualtrics, wrong_project],
                                                    {claimed_qualtrics.change_id})
    assert entries == [(wrong_project.change_id, "REJECTED")]


def test_same_wording_at_two_source_positions_remains_two_decisions():
    policy = _assisted_module()
    first = _change("paragraph:1", 1)
    second = _change("paragraph:8", 8)
    entries, _reasons = policy.recommend_decisions([first, second], set())
    assert entries == [("paragraph:1", "ACCEPTED"), ("paragraph:8", "ACCEPTED")]


def test_exact_same_occurrence_is_left_for_person_instead_of_applied_twice():
    policy = _assisted_module()
    first = _change("paragraph:1", 1)
    duplicate = _change("paragraph:duplicate", 1)
    entries, _reasons = policy.recommend_decisions([first, duplicate], set())
    assert entries == []


def test_assisted_mode_records_origin_once_and_never_overwrites_person():
    policy = _assisted_module()
    from resume_tailorer.review_decisions import apply_decisions

    initial = _state([_change()])
    automated = policy.apply_assisted_review(initial)
    assert automated["dispositions"] == {"paragraph:1": "ACCEPTED"}
    assert automated["decision_origins"]["paragraph:1"]["by"] == "AI-assisted"
    person = apply_decisions(automated, [("paragraph:1", "REJECTED")], origin="person", expected_revision=1)
    again = policy.apply_assisted_review(person)
    assert again["dispositions"]["paragraph:1"] == "REJECTED"
    assert again["decision_origins"]["paragraph:1"]["by"] == "person"
    assert again["review_revision"] == person["review_revision"]


def test_manual_mode_does_not_automatically_decide_anything():
    policy = _assisted_module()
    initial = _state([_change()], mode="manual")
    assert policy.apply_assisted_review(initial)["decided"] == set()


def test_rephrase_that_drops_a_substantive_original_detail_stays_for_person():
    policy = _assisted_module()
    omitted = replace(_change(),
                      original_text="Built weekly SQL reports for 40 regional managers",
                      proposed_text="Built SQL reports for managers")
    entries, _reasons = policy.recommend_decisions([omitted], set())
    assert entries == []


def test_assisted_review_accepts_computed_skills_additions_and_says_so():
    # Spec 022, builder's answer 4: AI-assisted review accepts change levels 2-3 automatically and
    # lists them; a manual review leaves them for the person.
    policy = _assisted_module()
    skills = replace(_change("paragraph:9", 9, category=ChangeCategory.SKILLS_ADDED), section="skills",
                     original_text="SQL, Excel", proposed_text="SQL, Excel, Tableau, PostgreSQL",
                     added_skills=(("Tableau", 2, "shown at Acme"), ("PostgreSQL", 3, "you have SQL")))
    entries, reasons = policy.recommend_decisions([skills], blocked_ids=set())
    assert entries == [("paragraph:9", "ACCEPTED")]
    assert "Tableau" in reasons["paragraph:9"] and "adjacent" in reasons["paragraph:9"].lower()
    assert policy.apply_assisted_review(_state([skills], mode="manual"))["decided"] == set()
