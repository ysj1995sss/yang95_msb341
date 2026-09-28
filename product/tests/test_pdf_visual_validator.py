from reportlab.pdfgen import canvas

from resume_tailorer.pdf.visual_validator import compare_pdf_renders


def _pdf(path, text: str, x: int = 20, y: int = 160, pagesize=(200, 200)):
    drawing = canvas.Canvas(str(path), pagesize=pagesize)
    drawing.drawString(x, y, text)
    drawing.showPage()
    drawing.save()
    return str(path)


def test_visual_change_outside_edited_region_fails(tmp_path):
    original = _pdf(tmp_path / "original.pdf", "Candidate Header", y=170)
    shifted = _pdf(tmp_path / "shifted.pdf", "Candidate Header", y=110)
    findings = compare_pdf_renders(original, shifted, edited_regions=[])
    assert any(finding.code == "LAYOUT_DRIFT_OUTSIDE_EDIT" for finding in findings)


def test_text_change_inside_edited_region_passes(tmp_path):
    original = _pdf(tmp_path / "original.pdf", "Old wording", y=100)
    tailored = _pdf(tmp_path / "tailored.pdf", "New wording", y=100)
    findings = compare_pdf_renders(
        original, tailored, edited_regions=[(10, 85, 150, 115)]
    )
    assert not any(finding.code == "LAYOUT_DRIFT_OUTSIDE_EDIT" for finding in findings)


def test_page_dimension_change_fails(tmp_path):
    original = _pdf(tmp_path / "original.pdf", "Same", pagesize=(200, 200))
    tailored = _pdf(tmp_path / "tailored.pdf", "Same", pagesize=(220, 200))
    findings = compare_pdf_renders(original, tailored, edited_regions=[])
    assert any(finding.code == "PAGE_DIMENSIONS_CHANGED" for finding in findings)
