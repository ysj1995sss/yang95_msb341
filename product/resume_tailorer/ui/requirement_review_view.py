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


def review_view(review: RequirementReview) -> dict:
    groups = []
    for section, label in (("required", "Required"), ("preferred", "Preferred")):
        rows = [r for r in review.rows if r.section == section]
        if not rows:
            continue
        groups.append({"section": section, "label": label, "rows": [{
            "id": r.id, "text": r.text, "status": r.status, "label": r.label, "tone": TONES[r.status],
            "reason": r.reason, "hard_gate": r.hard_gate, "shown_in_resume": r.shown_in_resume,
            "evidence": [{"text": e.text, "source": e.source, "confirmed": e.confirmed} for e in r.evidence],
            "terms": [{"term": t, "status": st, "label": STATUS_LABELS[st], "tone": TONES[st]} for t, st in r.term_status],
        } for r in rows]})
    return {"summary": review.summary, "computed_from": review.computed_from,
            "note": COMPUTED_NOW if review.computed_from == "now" else "", "groups": groups}


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
    (("READABILITY_BULLET_MISSING",), "Every bullet reads back", "docx"),
    (("READABILITY_ORDER",), "Text reads back whole and in order", "docx"),
    (("READABILITY_ROLE_ORDER",), "Roles read back in page order", "all"),
    (("READABILITY_UNMAPPED_SYMBOLS",), "No unknown symbols", "all"),
    (("READABILITY_HEADING_UNUSUAL",), "Standard section headings", "all"),
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
    term (spec 011)."""
    profile = state.get("profile")
    original = profile_text_for_report(profile) if profile is not None else ""
    report = keyword_report(review, original, state.get("tailored_text") or "")

    def change_for(term: str):
        for change in state.get("changes") or ():
            text = change.manual_text or change.proposed_text or ""
            if text and _names(term, text) and not _names(term, change.original_text or ""):
                return change.change_id
        return None

    return {
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


def missing_list(review: Optional[RequirementReview]) -> list[dict]:
    """Tailor's "Missing, never added" list, from the requirement review (spec 011): requirements
    with no evidence, then each missing named term of a partly supported requirement."""
    from resume_tailorer.analyzers.term_match import short_requirement

    if review is None:
        return []
    items = [{"label": short_requirement(r.text), "full": r.text} for r in review.rows if r.status == NONE]
    for r in review.rows:
        if r.status == PARTIAL:
            for term, state in r.term_status:
                if state == NONE:
                    items.append({"label": f"{term} (part of “{short_requirement(r.text)}”)", "full": r.text})
    return items
