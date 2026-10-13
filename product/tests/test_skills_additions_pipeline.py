"""Spec 022: levels 2-3 reach a Word resume's skills line as their own reviewable change.
Synthetic documents and reviews; no model, no Word."""

import io

import pytest
from docx import Document

from resume_tailorer.analyzers.gap_analyzer import GapReport
from resume_tailorer.analyzers.job_analyzer import JobAnalyzer
from resume_tailorer.analyzers.requirement_review import DIRECT, NONE, EvidenceRef, RequirementReview, RequirementRow
from resume_tailorer.artifacts.models import ChangeCategory
from resume_tailorer.docx_export import pipeline as pipeline_module
from resume_tailorer.docx_export.converter import DocxConversionUnavailable
from resume_tailorer.docx_export.pipeline import run_docx_tailoring_pipeline
from resume_tailorer.models import CareerTruthProfile, WorkExperience
from resume_tailorer.tailorer.docx_bullet_tailorer import BulletEdit, BulletTailoringResult

_BULLET = "Built Tableau dashboards used by 40 managers"


def _docx(skills_line="SQL, Excel"):
    doc = Document()
    for line in ("Sam Example", "sam@example.com | (555) 010-0100", "EXPERIENCE", "Data Analyst", "Acme | 2021 - 2024"):
        doc.add_paragraph(line)
    doc.add_paragraph(_BULLET, style="List Bullet")
    if skills_line is not None:
        doc.add_paragraph("SKILLS")
        doc.add_paragraph(skills_line)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def _review():
    evidence = EvidenceRef(_BULLET, "Data Analyst at Acme, bullet 1", "work_experience[0]", "experience", True)
    rows = (
        RequirementRow("r1", "Tableau dashboards", "required", False, DIRECT, ("Tableau",), (evidence,), "",
                       term_status=(("Tableau", DIRECT),)),
        RequirementRow("r2", "PostgreSQL", "preferred", False, NONE, ("PostgreSQL",), (), "",
                       term_status=(("PostgreSQL", NONE),)),
    )
    return RequirementReview(rows=rows, listed=("SQL", "Excel"))


class _KeepAll:
    seen: list = []

    def tailor_bullets(self, bullets, profile, job_analysis, gap_report, **kwargs):
        _KeepAll.seen = [b.section for b in bullets]
        return BulletTailoringResult(edits=[BulletEdit(b.paragraph_index, b.text, b.text, changed=False) for b in bullets],
                                     warnings=[])


@pytest.fixture
def no_word(monkeypatch):
    monkeypatch.setattr(pipeline_module, "convert_docx_to_pdf",
                        lambda src, dst: (_ for _ in ()).throw(DocxConversionUnavailable("no Word in tests")))


def _profile():
    return CareerTruthProfile(contact_info={"name": "Sam Example", "email": "sam@example.com"}, education=[],
                              work_experience=[WorkExperience(employer="Acme", title="Data Analyst", dates="2021 - 2024",
                                                              responsibilities=[_BULLET], accomplishments=[])],
                              skills=["SQL", "Excel"], tools=[], certifications=[], accomplishments=[])


def _run(docx_bytes, review):
    return run_docx_tailoring_pipeline(docx_bytes, _profile(), JobAnalyzer().analyze("Tableau and PostgreSQL."),
                                       GapReport(items=[], summary=""), bullet_tailorer=_KeepAll(),
                                       convert_to_pdf=True, review=review)


def test_levels_2_and_3_are_one_reviewable_skills_change(no_word):
    result = _run(_docx(), _review())
    [change] = [c for c in result.changes if c.category is ChangeCategory.SKILLS_ADDED]
    assert change.section == "skills" and change.original_text == "SQL, Excel"
    assert change.proposed_text == "SQL, Excel, Tableau, PostgreSQL"
    assert [(term, level) for term, level, _reason in change.added_skills] == [("Tableau", 2), ("PostgreSQL", 3)]
    assert "skills" not in _KeepAll.seen  # the model never edits the skills line
    texts = [p.text for p in Document(io.BytesIO(result.docx_bytes)).paragraphs]
    assert "SQL, Excel, Tableau, PostgreSQL" in texts


def test_no_skills_line_or_no_review_adds_nothing(no_word):
    assert not [c for c in _run(_docx(skills_line=None), _review()).changes if c.category is ChangeCategory.SKILLS_ADDED]
    assert not [c for c in _run(_docx(), None).changes if c.category is ChangeCategory.SKILLS_ADDED]


def test_additions_that_push_the_resume_onto_another_page_are_dropped(no_word, monkeypatch):
    real = pipeline_module.finalize_docx_edits

    def finalize(**kwargs):
        result = real(**kwargs)
        grew = any(e.new_text.endswith("PostgreSQL") for e in kwargs["edits"])
        result.page_count_preserved = not grew
        return result

    monkeypatch.setattr(pipeline_module, "finalize_docx_edits", finalize)
    result = _run(_docx(), _review())
    assert not [c for c in result.changes if c.category is ChangeCategory.SKILLS_ADDED]
    assert any("onto another page" in w for w in result.bullet_warnings)


def _review_state(result, dispositions, manual_texts=None):
    from resume_tailorer.artifacts.models import FidelityMode

    return {"source_kind": "DOCX", "original_bytes": _docx(), "changes": list(result.changes),
            "dispositions": dispositions, "manual_texts": manual_texts or {}, "profile": _profile(),
            "requirement_review": _review(), "gap_report": GapReport(items=[], summary=""),
            "job_analysis": JobAnalyzer().analyze("Tableau and PostgreSQL."), "original_alignment": 0.5,
            "candidate_fit": None, "company": "Acme", "role": "Data Analyst",
            "fidelity_mode": FidelityMode.PRESERVED, "version": 1}


def test_an_accepted_addition_rebuilds_and_a_persons_own_edit_is_still_checked(no_word):
    from resume_tailorer.tailoring_service import TailoringError, regenerate

    result = _run(_docx(), _review())
    [change] = [c for c in result.changes if c.category is ChangeCategory.SKILLS_ADDED]
    state = _review_state(result, {change.change_id: "ACCEPTED"})
    regenerate({}, state)
    texts = [p.text for p in Document(io.BytesIO(state["docx_bytes"])).paragraphs]
    assert "SQL, Excel, Tableau, PostgreSQL" in texts

    edited = _review_state(result, {change.change_id: "MANUALLY_EDITED"},
                           {change.change_id: "SQL, Excel, Kubernetes"})
    with pytest.raises(TailoringError):
        regenerate({}, edited)
