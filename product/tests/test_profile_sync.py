"""Spec 011: Career Profile edits reach a Word resume before tailoring, keeping its layout.
Anonymized, synthetic documents."""

import io

from docx import Document

from resume_tailorer.docx_export.profile_sync import sync_docx_to_profile
from resume_tailorer.models import CareerTruthProfile, EducationEntry, WorkExperience
from resume_tailorer.parsers.docx_structure import is_bullet_paragraph

A1 = "Built SQL dashboards used by 40 regional managers"
A2 = "Led on-time delivery of a 6-month store launch across 4 teams"
A3 = "Ran weekly campaign reviews with merchandising"
B1 = "Cleaned Salesforce campaign data before each quarterly review"


def _docx(typed=False) -> bytes:
    doc = Document()
    for line in ("Riley Park", "riley@example.com", "EXPERIENCE", "Marketing Analyst", "Acme Retail | Jan 2022 - Present"):
        doc.add_paragraph(line)
    for b in (A1, A2, A3):
        doc.add_paragraph(f"• {b}") if typed else doc.add_paragraph(b, style="List Bullet")
    for line in ("Marketing Coordinator", "Bluebird Goods | Jun 2019 - Dec 2021"):
        doc.add_paragraph(line)
    doc.add_paragraph(f"• {B1}") if typed else doc.add_paragraph(B1, style="List Bullet")
    for line in ("EDUCATION", "BS Economics, State University, 2019"):
        doc.add_paragraph(line)
    out = io.BytesIO()
    doc.save(out)
    return out.getvalue()


def _profile(acme_bullets, extra_role=False) -> CareerTruthProfile:
    jobs = [  # deliberately NOT in the file's order
        WorkExperience(employer="Bluebird Goods", title="Marketing Coordinator", dates="Jun 2019 - Dec 2021",
                       responsibilities=[B1], accomplishments=[]),
        WorkExperience(employer="Acme Retail", title="Marketing Analyst", dates="Jan 2022 - Present",
                       responsibilities=list(acme_bullets), accomplishments=[]),
    ]
    if extra_role:
        jobs.append(WorkExperience(employer="Northwind Outdoor", title="Strategy Intern", dates="2024",
                                   responsibilities=["Sized a new market"], accomplishments=[]))
    return CareerTruthProfile(contact_info={"name": "Riley Park"}, education=[EducationEntry("BS", "Economics", "State University", 2019)],
                              work_experience=jobs, skills=[], tools=[], certifications=[], accomplishments=[])


def _texts(docx_bytes):
    return [p.text for p in Document(io.BytesIO(docx_bytes)).paragraphs]


def test_an_unchanged_profile_leaves_the_file_byte_for_byte():
    original = _docx()
    result = sync_docx_to_profile(original, _profile([A1, A2, A3]))
    assert result.docx_bytes == original and result.summary == ""


def test_edits_additions_and_removals_reach_the_file_in_its_own_order():
    edited = A2.replace("store launch", "store launch and Tableau reporting")
    new = "Built Tableau dashboards for the loyalty program"
    result = sync_docx_to_profile(_docx(), _profile([new, edited, A1]))  # A3 removed, order differs
    texts = _texts(result.docx_bytes)
    acme = texts[texts.index("Acme Retail | Jan 2022 - Present") + 1: texts.index("Marketing Coordinator")]
    assert acme == [A1, edited, new]  # the file's order kept; the new bullet after the last one
    assert (result.changed, result.added, result.removed) == (1, 1, 1)
    assert B1 in texts  # the other role untouched
    assert "1 bullet(s) updated, 1 added, 1 removed" in result.summary


def test_an_added_bullet_keeps_the_roles_bullet_style_and_numbering():
    result = sync_docx_to_profile(_docx(), _profile([A1, A2, A3, "Built Tableau dashboards for the loyalty program"]))
    doc = Document(io.BytesIO(result.docx_bytes))
    added = next(p for p in doc.paragraphs if p.text.startswith("Built Tableau"))
    assert added.style.name == "List Bullet" and is_bullet_paragraph(added)


def test_typed_bullets_keep_their_marker():
    result = sync_docx_to_profile(_docx(typed=True), _profile([A1, A2 + " on budget", A3]))
    assert f"• {A2} on budget" in _texts(result.docx_bytes)


def test_roles_are_matched_by_employer_not_position_and_the_profile_is_aligned_to_the_file():
    result = sync_docx_to_profile(_docx(), _profile([A1, A2, A3]))
    assert [j.employer for j in result.aligned_profile.work_experience] == ["Acme Retail", "Bluebird Goods"]


def test_roles_only_in_the_profile_or_only_in_the_file_are_reported():
    result = sync_docx_to_profile(_docx(), _profile([A1, A2, A3], extra_role=True))
    assert result.unmatched_profile_roles == ["Strategy Intern at Northwind Outdoor"]
    assert "Not in your Word file" in result.summary
    one_role = _profile([A1, A2, A3])
    one_role.work_experience = one_role.work_experience[1:]  # Bluebird removed from the profile
    result = sync_docx_to_profile(_docx(), one_role)
    assert result.unmatched_file_roles and "Bluebird Goods" in result.unmatched_file_roles[0]
    assert B1 in _texts(result.docx_bytes)  # left as it is


def test_a_profile_edit_reaches_the_tailored_resume_and_closes_the_dead_end(monkeypatch, tmp_path):
    """Adding 'Built Tableau dashboards...' to a role in Career Profile makes Tableau direct
    evidence on the next run, and the bullet is in the tailored Word file (it used to be ignored)."""
    from resume_tailorer.docx_export import converter
    from resume_tailorer.tailoring_service import run_tailoring

    monkeypatch.setattr(converter, "_word_platform", lambda: False)
    monkeypatch.setattr(converter, "_soffice", lambda: None)

    class KeepEverything:
        def complete(self, system, user, max_tokens=2000):
            return "[]"

    posting = ("Data Analyst at Northwind.\nRequirements:\n- SQL and Tableau dashboards for business partners.\n")
    new_bullet = "Built Tableau dashboards for the loyalty program"
    profile = _profile([A1, A2, A3, new_bullet])
    session = {"artifacts_dir": str(tmp_path)}
    state = run_tailoring(session, original_bytes=_docx(), filename="riley.docx", job_description=posting,
                          pending={"job_id": "j1", "title": "Data Analyst", "company": "Northwind"},
                          llm=KeepEverything(), career_profile=profile)
    row = next(r for r in state["requirement_review"].rows if r.text.startswith("SQL and Tableau"))
    assert dict(row.term_status)["Tableau"] == "direct"
    assert new_bullet in _texts(state["docx_bytes"])
    assert "1 added" in state["sync_summary"]
    # The session keeps the real Career Profile (not the file-ordered working copy).
    from resume_tailorer.session_profile import get_career_profile

    assert [j.employer for j in get_career_profile(session).work_experience] == ["Bluebird Goods", "Acme Retail"]
