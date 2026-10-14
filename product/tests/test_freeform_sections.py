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


@pytest.mark.parametrize("section,heading,next_heading", [
    ("summary", "SUMMARY", "EXPERIENCE"),
    ("skills", "SKILLS", "EDUCATION"),
])
def test_trimmed_manual_section_keeps_the_next_heading_on_its_own_line(section, heading, next_heading):
    proposed = f"{heading}\nSQL, Tableau\n\n"
    baseline = proposed + f"{next_heading}\nExisting facts\n"
    change = ResumeChange(
        change_id=f"freeform:{section}:0", section=section, source_index=None,
        original_text=proposed, proposed_text=proposed,
        category=ChangeCategory.REPHRASED, reason="", job_requirement="",
        evidence_source="career_profile", evidence_text="SQL, Tableau",
        validation_status=ValidationStatus.PASS, disposition=ChangeDisposition.MANUALLY_EDITED,
        manual_text=f"{heading}\nTableau, SQL",  # regenerate() trims the textarea input
        baseline_span=(0, len(proposed)),
    )
    result = apply_dispositions_to_text(baseline, [change])
    assert f"Tableau, SQL\n{next_heading}\nExisting facts\n" in result


def test_trimmed_manual_insertion_keeps_the_following_heading_separate():
    baseline = "EXPERIENCE\n- Built SQL reports\n"
    change = ResumeChange(
        change_id="freeform:summary:0", section="summary", source_index=None,
        original_text="SUMMARY\nRetail analyst\n", proposed_text="",
        category=ChangeCategory.REPHRASED, reason="", job_requirement="",
        evidence_source="career_profile", evidence_text="Retail analyst",
        validation_status=ValidationStatus.PASS, disposition=ChangeDisposition.MANUALLY_EDITED,
        manual_text="SUMMARY\nRetail analyst", baseline_span=(0, 0),
    )
    assert apply_dispositions_to_text(baseline, [change]) == "SUMMARY\nRetail analyst\n" + baseline


@pytest.mark.parametrize("disposition", [ChangeDisposition.REJECTED, ChangeDisposition.MANUALLY_EDITED])
def test_restoring_a_missing_skills_section_at_eof_separates_the_previous_bullet(disposition):
    baseline = "SUMMARY\nRetail analyst\nEXPERIENCE\n- Built SQL reports"  # no final newline
    changes = build_freeform_changes(_profile(), baseline, GapReport([], ""))
    skills = next(change for change in changes if change.section == "skills")
    restored = replace(skills, disposition=disposition, manual_text="SKILLS\nTableau, SQL")
    result = apply_dispositions_to_text(baseline, [restored])
    assert result.startswith(baseline + "\nSKILLS\n")


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


def _certified_person():
    return CareerTruthProfile(
        contact_info={"name": "Sam Example"}, education=[], skills=["SQL"], tools=[], accomplishments=[],
        certifications=["AWS Solutions Architect - Associate (2021)", "PMP"],
        work_experience=[WorkExperience("Acme", "Analyst", "2021 - 2024", ["Built SQL reports"], [])])


def test_a_certification_the_model_left_out_is_put_back_not_proposed_for_removal():
    """Dogfood, 2026-10-13: the model dropped the CERTIFICATIONS section "for space" (an AWS
    certification, for a job asking for AWS), so removing it was proposed, and the first PDF had none."""
    from resume_tailorer.artifacts.freeform_sections import with_certifications

    person = _certified_person()
    model_text = "SUMMARY\nAnalyst.\n\nWORK EXPERIENCE\nAcme | 2021 - 2024\nAnalyst\n- Built SQL reports\n\nSKILLS\nSQL\n"
    kept = with_certifications(model_text, person)
    assert "AWS Solutions Architect - Associate (2021)" in kept and "PMP" in kept
    changes = build_freeform_changes(person, kept, GapReport(items=[], summary=""))
    assert not [c for c in changes if c.original_text in person.certifications and not c.proposed_text]
    # Already there: nothing changes.
    assert with_certifications(kept, person) == kept


def test_a_pdf_resume_gets_the_same_computed_skills_additions_as_a_word_resume():
    # Spec 022 levels 2-3 reached only Word resumes; a PDF resume's skills line never gained a skill
    # its experience shows (open item, 2026-10-13).
    from resume_tailorer.analyzers.gap_analyzer import GapReport
    from resume_tailorer.analyzers.job_analyzer import JobAnalyzer
    from resume_tailorer.analyzers.requirement_review import build_review
    from resume_tailorer.artifacts.changes import build_freeform_changes
    from resume_tailorer.artifacts.freeform_sections import with_skill_additions
    from resume_tailorer.artifacts.models import ChangeCategory, ValidationStatus
    from resume_tailorer.models import CareerTruthProfile, WorkExperience

    person = CareerTruthProfile(
        contact_info={"name": "Sam Example"}, education=[], tools=[], certifications=[], accomplishments=[],
        skills=["SQL", "Excel"],
        work_experience=[WorkExperience(employer="Example Co", title="Analyst", dates="2021 - Present", accomplishments=[],
                                        responsibilities=["Built weekly sales dashboards in Tableau for regional managers"])])
    posting = "Requirements:\n- Experience with Tableau\n- Experience with PostgreSQL\n"
    review = build_review(JobAnalyzer().analyze(posting), person, posting=posting)
    tailored = ("Sam Example\nEXPERIENCE\nExample Co | Analyst | 2021 - Present\n"
                "- Built weekly sales dashboards in Tableau for regional managers\nSKILLS\nSQL, Excel\n")
    text, additions = with_skill_additions(tailored, review)
    assert "SKILLS\nSQL, Excel, Tableau, PostgreSQL\n" in text
    assert [(a.term, a.level) for a in additions] == [("Tableau", 2), ("PostgreSQL", 3)]
    changes = build_freeform_changes(person, text, GapReport(items=[], summary=""), review=review,
                                     skill_additions=additions)
    skills = next(c for c in changes if c.section == "skills")
    assert skills.category is ChangeCategory.SKILLS_ADDED and skills.validation_status is ValidationStatus.PASS
    assert [term for term, _level, _reason in skills.added_skills] == ["Tableau", "PostgreSQL"]


def test_a_computed_skills_line_passes_the_pdf_content_check():
    # The PDF check called the adjacent skill on a computed skills line an unverified tool, which
    # failed the whole resume; the Word path never had that problem.
    from resume_tailorer.artifacts.models import ChangeCategory, ResumeChange, ValidationStatus
    from resume_tailorer.models import CareerTruthProfile
    from resume_tailorer.pdf.content_validator import validate_pdf_content

    person = CareerTruthProfile(contact_info={"name": "Sam Example"}, education=[], work_experience=[],
                                skills=["SQL", "Excel"], tools=[], certifications=[], accomplishments=[])
    line = ResumeChange(change_id="freeform:skills:0", section="skills", source_index=None,
                        original_text="SKILLS\nSQL, Excel\n", proposed_text="SKILLS\nSQL, Excel, PostgreSQL\n",
                        category=ChangeCategory.SKILLS_ADDED, reason="", job_requirement="PostgreSQL",
                        evidence_source="career_profile", evidence_text="SQL, Excel",
                        validation_status=ValidationStatus.PASS,
                        added_skills=(("PostgreSQL", 3, "You have SQL; the job asks for PostgreSQL."),))
    findings = validate_pdf_content("Sam Example\nSKILLS\nSQL, Excel, PostgreSQL\n", person, [line])
    assert "UNSUPPORTED_TOOL_ATTRIBUTION" not in {f.code for f in findings}
