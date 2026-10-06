"""Section-specific review for rebuilt resumes, using synthetic facts."""

import pytest
from dataclasses import replace

from resume_tailorer.analyzers.gap_analyzer import GapReport
from resume_tailorer.artifacts.changes import build_freeform_changes
from resume_tailorer.artifacts.freeform_sections import SectionAmbiguity, find_sections
from resume_tailorer.artifacts.models import ChangeCategory, ChangeDisposition, ResumeChange, ValidationStatus
from resume_tailorer.artifacts.regeneration import apply_dispositions_to_text
from resume_tailorer.artifacts.regeneration import validate_manual_text
from resume_tailorer.models import CareerTruthProfile, WorkExperience
from resume_tailorer.pdf.content_validator import validate_pdf_content
from resume_tailorer.review_store import load_review, save_review


def _profile() -> CareerTruthProfile:
    return CareerTruthProfile(
        contact_info={"name": "Riley Park"}, education=[],
        work_experience=[WorkExperience("Acme Retail", "Analyst", "2022-Present", ["Built SQL reports"], [])],
        skills=["SQL", "Tableau"], tools=[], certifications=[], accomplishments=[], summary="Retail analyst",
    )


def test_summary_and_wrapped_skills_have_exact_spans():
    text = "Riley Park\nSUMMARY\nRetail analyst\nEXPERIENCE\n- Built SQL reports\nSKILLS\nSQL, Tableau,\nPower BI\nEDUCATION\nBS Economics\n"
    spans = find_sections(text)
    assert text[spans["summary"].start:spans["summary"].end] == "SUMMARY\nRetail analyst\n"
    assert "SQL, Tableau,\nPower BI" in spans["skills"].text
    assert "Built SQL reports" not in spans["skills"].text


def test_duplicate_skills_heading_is_ambiguous():
    text = "SUMMARY\nAnalyst\nSKILLS\nSQL\nEXPERIENCE\n- Built reports\nSKILLS\nPython\n"
    with pytest.raises(SectionAmbiguity, match="skills"):
        find_sections(text)


def test_skills_span_stops_before_a_separate_tools_section():
    text = "SUMMARY\nAnalyst\nSKILLS\nSQL, Tableau\nTOOLS & PLATFORMS\nGoogle Analytics\nEXPERIENCE\n- Built SQL reports\n"
    span = find_sections(text)["skills"]
    assert span.text == "SKILLS\nSQL, Tableau\n"


def test_separate_tools_section_does_not_make_unchanged_skills_a_review_change():
    candidate = _profile()
    candidate.tools = ["Google Analytics"]
    text = "SUMMARY\nRetail analyst\nEXPERIENCE\n- Built SQL reports\nSKILLS\nSQL, Tableau\nTOOLS & PLATFORMS\nGoogle Analytics\n"
    changes = build_freeform_changes(candidate, text, GapReport([], ""))
    assert not any(change.section == "skills" for change in changes)


def test_wrapping_and_heading_alias_alone_are_not_a_skills_edit():
    text = "Riley Park\nTECHNICAL SKILLS\nSQL,\nTableau\nEXPERIENCE\n- Built SQL reports\n"
    changes = build_freeform_changes(_profile(), text, GapReport([], ""))
    assert not any(change.section == "skills" for change in changes)


def test_summary_and_skills_are_independent_review_changes():
    text = "Riley Park\nSUMMARY\nRetail analyst focused on reporting\nEXPERIENCE\n- Built SQL reports\nSKILLS\nSQL, Tableau, Power BI\n"
    changes = build_freeform_changes(_profile(), text, GapReport([], ""))
    assert {c.change_id for c in changes if c.section in {"summary", "skills"}} == {
        "freeform:summary:0", "freeform:skills:0",
    }
    assert not any(c.original_text == "SQL" and not c.proposed_text for c in changes)


def test_rejecting_summary_changes_only_its_span_not_repeated_work_wording():
    baseline = "SUMMARY\nSQL analyst\nEXPERIENCE\n- Built SQL reports\n"
    proposed = "SUMMARY\nSQL analyst\n"
    change = ResumeChange(
        change_id="freeform:summary:0", section="summary", source_index=None,
        original_text="SUMMARY\nRetail analyst\n", proposed_text=proposed,
        category=ChangeCategory.REPHRASED, reason="", job_requirement="",
        evidence_source="career_profile", evidence_text="Retail analyst",
        validation_status=ValidationStatus.PASS, disposition=ChangeDisposition.REJECTED,
        baseline_span=(0, len(proposed)),
    )
    assert apply_dispositions_to_text(baseline, [change]) == (
        "SUMMARY\nRetail analyst\nEXPERIENCE\n- Built SQL reports\n"
    )


def test_section_span_mismatch_fails_instead_of_replacing_another_occurrence():
    baseline = "SUMMARY\nSQL analyst\nEXPERIENCE\n- Built SQL reports\n"
    change = ResumeChange(
        change_id="freeform:summary:0", section="summary", source_index=None,
        original_text="SUMMARY\nRetail analyst\n", proposed_text="SUMMARY\nSQL analyst\n",
        category=ChangeCategory.REPHRASED, reason="", job_requirement="",
        evidence_source="career_profile", evidence_text="Retail analyst",
        validation_status=ValidationStatus.PASS, disposition=ChangeDisposition.REJECTED,
        baseline_span=(8, 28),
    )
    with pytest.raises(ValueError, match="summary"):
        apply_dispositions_to_text(baseline, [change])


def test_manual_summary_cannot_introduce_unverified_credential():
    from resume_tailorer.analyzers.job_analyzer import JobAnalyzer
    from resume_tailorer.analyzers.requirement_review import build_review
    from tests.fixtures.ats import POSTING, PROVENANCE, profile

    candidate = profile()
    review = build_review(JobAnalyzer().analyze(POSTING), candidate,
                          provenance=PROVENANCE, posting=POSTING)
    issues = validate_manual_text("Retail analyst", "CPA retail analyst", candidate, review)
    assert any("CPA" in issue for issue in issues)


def test_accepting_unsupported_summary_still_blocks_download():
    change = ResumeChange(
        change_id="freeform:summary:0", section="summary", source_index=None,
        original_text="SUMMARY\nRetail analyst\n", proposed_text="SUMMARY\nCPA retail analyst\n",
        category=ChangeCategory.REPHRASED, reason="Unsupported CPA credential", job_requirement="",
        evidence_source="career_profile", evidence_text="Retail analyst",
        validation_status=ValidationStatus.FAIL, disposition=ChangeDisposition.ACCEPTED,
        baseline_span=(0, len("SUMMARY\nCPA retail analyst\n")),
    )
    findings = validate_pdf_content("SUMMARY\nCPA retail analyst\n", _profile(), [change])
    assert any(f.code == "UNSUPPORTED_CLAIM_PRESENT" for f in findings)


def test_section_decisions_survive_format_two_reload_and_rebuild(tmp_path):
    baseline = "SUMMARY\nRetail analyst focused on SQL reports\nEXPERIENCE\n- Built SQL reports\nSKILLS\nTableau, SQL\n"
    changes = build_freeform_changes(_profile(), baseline, GapReport([], ""))
    by_section = {change.section: change for change in changes if change.section in {"summary", "skills"}}
    assert set(by_section) == {"summary", "skills"}
    assert save_review(str(tmp_path), "job-1", {"changes": changes, "baseline_text": baseline})
    loaded = load_review(str(tmp_path), "job-1")
    assert {c.section: c.baseline_span for c in loaded["changes"] if c.section in by_section} == {
        name: change.baseline_span for name, change in by_section.items()
    }
    rejected_summary = replace(by_section["summary"], disposition=ChangeDisposition.REJECTED)
    manual_skills = replace(by_section["skills"], disposition=ChangeDisposition.MANUALLY_EDITED,
                            manual_text="SKILLS\nSQL, Tableau\n")
    result = apply_dispositions_to_text(baseline, [rejected_summary, manual_skills])
    assert "SUMMARY\nRetail analyst\n" in result
    assert "SKILLS\nSQL, Tableau\n" in result
    assert "- Built SQL reports" in result
