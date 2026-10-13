"""Spec 022: change levels 2 and 3 are computed by code from the requirement review, never by
the model, and only ever land on the skills line. Synthetic reviews only."""

from resume_tailorer.analyzers.requirement_review import (
    DIRECT, MENTION, NONE, TRANSFERABLE, UNCONFIRMED, EvidenceRef, RequirementReview, RequirementRow,
)
from resume_tailorer.analyzers.skill_additions import MAX_ADDITIONS, propose_skill_additions

_BULLET = EvidenceRef("Built Tableau dashboards used by 40 managers", "Data Analyst at Acme, bullet 1",
                      "work_experience[0]", "experience", True)


def _row(rid, terms, status, section="required", hard_gate=False, evidence=(_BULLET,)):
    return RequirementRow(id=rid, text=f"Experience with {', '.join(t for t, _ in terms)}", section=section,
                          hard_gate=hard_gate, status=status, terms=tuple(t for t, _ in terms),
                          evidence=evidence if status != NONE else (), reason="",
                          term_status=tuple(terms))


def _review(*rows, listed=("SQL",)):
    return RequirementReview(rows=rows, listed=listed)


def test_level_2_a_skill_shown_in_experience_but_missing_from_the_skills_line():
    review = _review(_row("r1", [("Tableau", DIRECT)], DIRECT))
    [added] = propose_skill_additions(review, "SQL, Excel")
    assert (added.term, added.level) == ("Tableau", 2)
    assert "Data Analyst at Acme" in added.reason


def test_level_3_only_from_the_reviewed_adjacency_list():
    review = _review(_row("r1", [("PostgreSQL", NONE)], NONE), _row("r2", [("Kubernetes", NONE)], NONE))
    added = propose_skill_additions(review, "SQL, Excel")
    assert [(a.term, a.level) for a in added] == [("PostgreSQL", 3)]
    assert "SQL" in added[0].reason


def test_nothing_already_on_the_skills_line_is_added_again():
    review = _review(_row("r1", [("Tableau", DIRECT)], DIRECT), _row("r2", [("MySQL", NONE)], NONE))
    assert propose_skill_additions(review, "SQL, Tableau, MySQL") == []


def test_weak_or_unconfirmed_evidence_is_never_a_level_2_addition():
    review = _review(_row("r1", [("Tableau", UNCONFIRMED)], UNCONFIRMED),
                     _row("r2", [("Looker", TRANSFERABLE)], TRANSFERABLE),
                     _row("r3", [("Excel", MENTION)], MENTION), listed=())
    assert propose_skill_additions(review, "") == []


def test_hard_gates_and_level_4_kinds_are_never_added():
    review = _review(_row("r1", [("PostgreSQL", NONE)], NONE, hard_gate=True),
                     _row("r2", [("CPA license", NONE)], NONE),
                     _row("r3", [("5 years of experience", NONE)], NONE))
    assert propose_skill_additions(review, "SQL") == []


def test_at_most_five_and_required_before_preferred():
    rows = [_row(f"p{i}", [(t, DIRECT)], DIRECT, section="preferred",
                 evidence=(EvidenceRef(f"Used {t} daily", f"Analyst at Beta, bullet {i}", "work_experience[1]",
                                       "experience", True),))
            for i, t in enumerate(["Python", "Excel", "Jira", "Asana", "Git"])]
    rows.append(_row("req", [("Tableau", DIRECT)], DIRECT, section="required"))
    added = propose_skill_additions(_review(*rows), "")
    assert len(added) == MAX_ADDITIONS == 5
    assert added[0].term == "Tableau"


def test_a_term_wanted_by_two_rows_is_added_once():
    review = _review(_row("r1", [("Tableau", DIRECT)], DIRECT), _row("r2", [("Tableau", DIRECT)], DIRECT, "preferred"))
    assert [a.term for a in propose_skill_additions(review, "SQL")] == ["Tableau"]


def test_level_2_needs_a_confirmed_passage_that_names_the_skill():
    unrelated = EvidenceRef("Presented metrics to directors", "Analyst at Beta, bullet 3", "work_experience[1]",
                            "experience", True)
    review = _review(_row("r1", [("Tableau", DIRECT)], DIRECT, evidence=(unrelated,)))
    assert propose_skill_additions(review, "SQL") == []


def test_a_term_inside_a_longer_added_term_is_not_added_twice():
    """Live run, 2026-10-13: "APIs" beside "REST APIs" and "CI" beside "CI/CD" filled the cap with
    repeats, so MySQL (adjacent to the listed SQL) was left out."""
    def shown(term, i):
        return EvidenceRef(f"Built {term} for 2 million daily requests", f"Engineer at Beta, bullet {i}",
                           "work_experience[0]", "experience", True)

    rows = [_row(f"r{i}", [(t, DIRECT)], DIRECT, evidence=(shown(t, i),))
            for i, t in enumerate(["APIs", "REST APIs", "CI/CD", "CI"])]
    rows.append(_row("db", [("MySQL", NONE)], NONE))
    assert [a.term for a in propose_skill_additions(_review(*rows), "Python")] == ["REST APIs", "CI/CD", "MySQL"]


def test_level_3_counts_an_adjacent_skill_on_the_skills_line_the_posting_never_names():
    """Live run, 2026-10-13: "You list PostgreSQL" didn't count when the posting itself never named
    PostgreSQL, so MySQL was never offered. Spec 022: "a listed adjacent skill"."""
    review = _review(_row("db", [("MySQL", NONE)], NONE), listed=())
    [added] = propose_skill_additions(review, "Python, PostgreSQL, Redis")
    assert (added.term, added.level) == ("MySQL", 3) and "PostgreSQL" in added.reason
    assert propose_skill_additions(review, "Python, Redis") == []
