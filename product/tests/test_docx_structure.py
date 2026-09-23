from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

from resume_tailorer.parsers.docx_structure import (
    is_bullet_paragraph,
    extract_docx_structure,
)


def _add_bullet_paragraph(doc: Document, text: str):
    """Build a paragraph with a real <w:numPr> element, mirroring a genuine
    Word numbered-list bullet -- is_bullet_paragraph() only checks for the
    element's presence, so a synthetic numId/ilvl is sufficient; this is
    never rendered to PDF in these tests."""
    paragraph = doc.add_paragraph(text, style="List Paragraph")
    pPr = paragraph._p.get_or_add_pPr()
    numPr = OxmlElement("w:numPr")
    ilvl = OxmlElement("w:ilvl")
    ilvl.set(qn("w:val"), "0")
    numId = OxmlElement("w:numId")
    numId.set(qn("w:val"), "1")
    numPr.append(ilvl)
    numPr.append(numId)
    pPr.append(numPr)
    return paragraph


def _build_sample_resume() -> Document:
    doc = Document()
    doc.add_paragraph("Jane Doe")
    doc.add_paragraph("jane@example.com")
    doc.add_paragraph("A data-savvy professional with a track record of growth.")
    doc.add_paragraph("EDUCATION")
    doc.add_paragraph("Some University | 2020")
    doc.add_paragraph("B.S. Computer Science")
    doc.add_paragraph("PROFESSIONAL EXPERIENCE")
    doc.add_paragraph("Marketing Manager")
    doc.add_paragraph("Acme Corp | Remote\t2022-2024")
    _add_bullet_paragraph(doc, "Did a thing")
    _add_bullet_paragraph(doc, "Did another thing")
    doc.add_paragraph("")
    doc.add_paragraph("Operations Lead")
    doc.add_paragraph("Beta Inc | NYC\t2019-2021")
    _add_bullet_paragraph(doc, "Led a team")
    doc.add_paragraph("ADDITIONAL")
    _add_bullet_paragraph(doc, "Technical Proficiency: Excel, SQL")
    return doc


class TestIsBulletParagraph:
    def test_true_for_list_paragraph_with_numpr(self):
        doc = Document()
        p = _add_bullet_paragraph(doc, "A bullet")
        assert is_bullet_paragraph(p) is True

    def test_false_for_normal_paragraph(self):
        doc = Document()
        p = doc.add_paragraph("Just a heading")
        assert is_bullet_paragraph(p) is False

    def test_false_for_list_paragraph_style_without_numpr(self):
        """Style alone isn't enough -- must also have a real <w:numPr>."""
        doc = Document()
        p = doc.add_paragraph("Looks like a bullet but isn't", style="List Paragraph")
        assert is_bullet_paragraph(p) is False


class TestExtractDocxStructure:
    def test_finds_summary_paragraph(self):
        doc = _build_sample_resume()
        structure = extract_docx_structure(doc)
        assert structure.summary_paragraph_indices == [2]

    def test_finds_two_jobs_with_correct_bullets(self):
        doc = _build_sample_resume()
        structure = extract_docx_structure(doc)
        assert len(structure.jobs) == 2

        job1 = structure.jobs[0]
        assert doc.paragraphs[job1.title_index].text == "Marketing Manager"
        assert "Acme Corp" in doc.paragraphs[job1.anchor_index].text
        assert [doc.paragraphs[i].text for i in job1.bullet_paragraph_indices] == [
            "Did a thing",
            "Did another thing",
        ]

        job2 = structure.jobs[1]
        assert doc.paragraphs[job2.title_index].text == "Operations Lead"
        assert [doc.paragraphs[i].text for i in job2.bullet_paragraph_indices] == ["Led a team"]

    def test_stops_at_additional_heading_not_absorbing_its_bullets(self):
        doc = _build_sample_resume()
        structure = extract_docx_structure(doc)
        all_we_bullets = [
            i for job in structure.jobs for i in job.bullet_paragraph_indices
        ]
        additional_bullet_idx = next(
            i for i, p in enumerate(doc.paragraphs) if "Technical Proficiency" in p.text
        )
        assert additional_bullet_idx not in all_we_bullets

    def test_splice_targets_flattened_in_document_order(self):
        doc = _build_sample_resume()
        structure = extract_docx_structure(doc)
        targets = structure.splice_targets(doc.paragraphs)
        indices = [t.paragraph_index for t in targets]
        assert indices == sorted(indices)
        assert any(t.section == "summary" for t in targets)
        assert all(
            t.section == "work_experience" for t in targets if t.section != "summary"
        )

    def test_no_experience_section_returns_empty_jobs(self):
        doc = Document()
        doc.add_paragraph("Jane Doe")
        doc.add_paragraph("A summary paragraph here.")
        doc.add_paragraph("EDUCATION")
        doc.add_paragraph("Some University | 2020")
        structure = extract_docx_structure(doc)
        assert structure.jobs == []
