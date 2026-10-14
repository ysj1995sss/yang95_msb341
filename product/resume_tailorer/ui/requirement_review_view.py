"""The requirement review and readability check, ready for a screen (spec 010). Used by the
Streamlit pages and served by the API to the web app, so both apps say the same thing."""

from __future__ import annotations

from typing import Iterable, Optional

from resume_tailorer.analyzers.requirement_review import (
    CHECK, DIRECT, LEFT_OUT_REASONS, MENTION, NONE, PARTIAL, STATUS_LABELS, TRANSFERABLE, UNCONFIRMED,
    RequirementReview, build_review, keyword_report, profile_text_for_report, with_resume,
)
from resume_tailorer.pdf.readability import NOTE as READABILITY_NOTE

TONES = {DIRECT: "verified", TRANSFERABLE: "primary", PARTIAL: "review", MENTION: "review", UNCONFIRMED: "review",
         CHECK: "review", NONE: "blocked"}
COMPUTED_NOW = ("This review was worked out now from your current Career Profile, because this tailoring run "
                "is from before reviews were saved.")
ADDED_TO_SKILLS = "Added to skills (adjacent)"


def adjacent_additions(changes: Iterable) -> set[str]:
    """Spec 022: the adjacent skills (level 3) a computed skills line puts in the finished resume,
    casefolded. They have no evidence, so the review shows them as added, never as evidence."""
    from resume_tailorer.analyzers.skill_additions import is_computed_skills_line

    return {term.casefold() for change in changes or () if is_computed_skills_line(change)
            for term, level, _reason in change.added_skills if level == 3}


def _all_added(row, adjacent: set[str]) -> bool:
    return row.status == NONE and bool(row.terms) and all(term.casefold() in adjacent for term in row.terms)


def work_authorization_state(row, authorization: Optional[dict]) -> Optional[tuple[str, str, str, bool]]:
    """(label, tone, reason, still a hard requirement) for a work authorization row, from the person's
    answer in Career Profile; None for any other row. A resume never shows it, so "no evidence" was
    wrong for everyone who simply hadn't answered (dogfood follow-up, 2026-10-13). Jobs and Tailor
    both use this."""
    from resume_tailorer.analyzers.requirement_review import is_work_authorization

    if not is_work_authorization(row):
        return None
    answer = authorization or {}
    if answer.get("authorized_to_work") is True and not (answer.get("sponsorship_required") is True
                                                         and "sponsor" in row.text.lower()):
        return ("You said yes in Career Profile", "verified",
                "You said you're authorized to work (Career Profile). A resume doesn't need to show it.", False)
    if answer.get("authorized_to_work") is False or answer.get("sponsorship_required") is True:
        return ("You said no in Career Profile", "blocked",
                "Your Career Profile answer doesn't meet this. Check it before applying.", True)
    return ("Not answered in Career Profile", "review",
            "Work authorization comes from your answer in Career Profile, not your resume. Answer it there.", False)


def review_view(review: RequirementReview, adjacent: set[str] = frozenset(),
                authorization: Optional[dict] = None) -> dict:
    def term_view(term: str, status: str) -> dict:
        if status == NONE and term.casefold() in adjacent:
            return {"term": term, "status": status, "label": ADDED_TO_SKILLS, "tone": "review"}
        return {"term": term, "status": status, "label": STATUS_LABELS[status], "tone": TONES[status]}

    groups = []
    for section, label in (("required", "Required"), ("preferred", "Preferred")):
        rows = [r for r in review.rows if r.section == section]
        if not rows:
            continue
        groups.append({"section": section, "label": label, "rows": [_row_view(r, adjacent, authorization, term_view)
                                                                    for r in rows]})
    return {"summary": review.summary, "computed_from": review.computed_from,
            "note": COMPUTED_NOW if review.computed_from == "now" else "", "groups": groups}


def _row_view(r, adjacent: set[str], authorization: Optional[dict], term_view) -> dict:
    view = {
        "id": r.id, "text": r.text, "status": r.status,
        "label": ADDED_TO_SKILLS if _all_added(r, adjacent) else r.label,
        "tone": "review" if _all_added(r, adjacent) else TONES[r.status],
        "reason": r.reason, "hard_gate": r.hard_gate, "shown_in_resume": r.shown_in_resume,
        "evidence": [{"text": e.text, "source": e.source, "confirmed": e.confirmed} for e in r.evidence],
        "terms": [term_view(t, st) for t, st in r.term_status],
    }
    work = work_authorization_state(r, authorization)
    if work is not None:
        view.update(label=work[0], tone=work[1], reason=work[2], hard_gate=work[3])
    return view


def review_for_state(state: dict, provenance: Optional[dict] = None) -> Optional[RequirementReview]:
    """The run's saved review, or (for a review saved before spec 010) one worked out now."""
    saved = state.get("requirement_review")
    if saved is not None:
        return saved
    job_analysis, profile = state.get("job_analysis"), state.get("profile")
    if job_analysis is None or profile is None:
        return None
    review = build_review(job_analysis, profile, provenance=provenance, computed_from="now")
    return with_resume(review, state.get("tailored_text") or "")


# Readability: the checks each path actually runs, so a screen never shows a pass for a check
# that didn't happen. The free-form path rewrites bullets and checks contact details and the
# changed text with its own content checks (CONTACT_MISSING and friends).
_CHECKS = (
    (("TEXT_NOT_EXTRACTABLE",), "Text can be read from the file", "all"),
    (("READABILITY_CONTACT_MISSING", "CONTACT_MISSING"), "Your name and contact details read back", "all"),
    (("READABILITY_BULLET_MISSING",), "Every bullet reads back", "all"),
    (("READABILITY_ORDER",), "Text reads back whole and in order", "all"),
    (("READABILITY_READERS_DISAGREE",), "Two different text readers agree", "all"),
    (("READABILITY_ROLE_ORDER",), "Roles read back in page order", "all"),
    (("READABILITY_UNMAPPED_SYMBOLS",), "No unknown symbols", "all"),
    (("READABILITY_HEADING_UNUSUAL",), "Standard section headings", "all"),
    (("DOCX_CONTACT_IN_HEADER",), "Word file: contact details in the body, not only the header", "docx"),
    (("DOCX_TEXT_IN_TABLES", "DOCX_TEXT_BOXES"), "Word file: no tables or text boxes for your content", "docx"),
)


def readability_view(findings: Iterable, source_kind: str, checks_run: Iterable[str] = ()) -> dict:
    findings = list(findings)
    ran = "readability" in set(checks_run)
    items = []
    for codes, label, scope in _CHECKS:
        if scope == "docx" and source_kind != "DOCX":
            continue
        hits = [f for f in findings if f.code in codes]
        checked = ran or codes[0] in ("TEXT_NOT_EXTRACTABLE",) or "CONTACT_MISSING" in codes
        items.append({
            "label": label,
            "state": ("fail" if any(h.severity.value == "FAIL" for h in hits) else "warn" if hits
                      else "ok" if checked else "not_checked"),
            "message": " ".join(h.message for h in hits),
        })
    return {"note": READABILITY_NOTE, "items": items}


def keyword_report_view(review: RequirementReview, state: dict) -> dict:
    """What this version added and what is still left out, with the change that added each
    term, and the model's reason for each target it didn't change (spec 011)."""
    from resume_tailorer.analyzers.term_match import short_requirement

    profile = state.get("profile")
    original = profile_text_for_report(profile) if profile is not None else ""
    report = keyword_report(review, original, state.get("tailored_text") or "")

    def change_for(term: str):
        for change in state.get("changes") or ():
            text = change.manual_text or change.proposed_text or ""
            if text and _names(term, text) and not _names(term, change.original_text or ""):
                return change.change_id
        return None

    notes = state.get("target_notes") or {}
    by_id = {r.id: r for r in review.rows}
    not_changed = [{"requirement": short_requirement(by_id[rid].text), "reason": reason}
                   for rid, reason in notes.items() if rid in by_id]

    def why_not(term: str):
        for r in review.rows:
            if r.id in notes and term in r.terms:
                return notes[r.id]
        return None

    return {
        "not_changed": not_changed,
        "why_not": {t: why_not(t) for t, k in report.left_out if k == "not_named" and why_not(t)},
        "added": [{"term": t, "change_id": change_for(t)} for t in report.added],
        "already": list(report.already),
        "left_out": [{"key": key, "label": LEFT_OUT_REASONS[key], "terms": [t for t, k in report.left_out if k == key]}
                     for key in LEFT_OUT_REASONS if any(k == key for _t, k in report.left_out)],
        "note": "Only terms the posting's requirements name are counted. Terms you haven't shown evidence for "
                "are never added.",
    }


def _names(term: str, text: str) -> bool:
    from resume_tailorer.analyzers.requirement_review import _mentions_any

    return _mentions_any(term, text)


def missing_list(review: Optional[RequirementReview], adjacent: set[str] = frozenset(),
                 authorization: Optional[dict] = None) -> list[dict]:
    """Tailor's "Missing, never added" list, from the requirement review (spec 011): requirements
    with no evidence, then each missing named term of a partly supported requirement. Adjacent
    skills the skills line now names (spec 022) aren't listed as never added."""
    from resume_tailorer.analyzers.term_match import short_requirement

    if review is None:
        return []
    def missing(r) -> bool:
        work = work_authorization_state(r, authorization)
        return work[3] if work is not None else r.status == NONE and not _all_added(r, adjacent)

    items = [{"label": short_requirement(r.text), "full": r.text} for r in review.rows if missing(r)]
    for r in review.rows:
        if r.status == PARTIAL:
            for term, state in r.term_status:
                if state == NONE and term.casefold() not in adjacent:
                    items.append({"label": f"{term} (part of “{short_requirement(r.text)}”)", "full": r.text})
    return items
