"""
Tests for the PDF Validator.

Tests verify the round-trip validation hard gate:
1. A properly generated (text-based) PDF passes validation
2. Page count is reported and flagged when outside the MVP 1-2 page range
3. A broken/empty PDF (no extractable text) is flagged as failing
4. A PDF with zero pages is flagged as failing
5. ValidationResult exposes passed, page_count, extracted_text, issues
"""

import os
import tempfile

import pytest
from pypdf import PdfWriter
from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas

from resume_tailorer.pdf.generator import PDFGenerator
from resume_tailorer.pdf.validator import PDFValidator, ValidationResult
from resume_tailorer.artifacts.models import ValidationStatus
from resume_tailorer.models import CareerTruthProfile


SAMPLE_RESUME_TEXT = """Jane Smith
jane.smith@example.com | 555-987-6543 | New York, NY

WORK EXPERIENCE

Product Manager, BigCo (2019-2023)
- Led cross-functional team of 12 engineers
- Shipped 4 major product launches

EDUCATION

MBA, Columbia University, 2019

SKILLS

Product Strategy, Agile, SQL, Roadmapping
"""


@pytest.fixture
def generated_pdf_path():
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = os.path.join(tmpdir, "resume.pdf")
        PDFGenerator().generate(SAMPLE_RESUME_TEXT, "Jane Smith", output_path=output_path)
        yield output_path


@pytest.fixture
def empty_pdf_path():
    """A PDF with a page but no text drawn on it (simulates broken/image-based output)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = os.path.join(tmpdir, "empty.pdf")
        c = canvas.Canvas(output_path, pagesize=LETTER)
        c.showPage()
        c.save()
        yield output_path


@pytest.fixture
def zero_page_pdf_path():
    """A structurally valid but pageless PDF."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = os.path.join(tmpdir, "zero_page.pdf")
        writer = PdfWriter()
        with open(output_path, "wb") as f:
            writer.write(f)
        yield output_path


def test_validator_instantiation():
    validator = PDFValidator()
    assert validator is not None


def test_validate_returns_validation_result(generated_pdf_path):
    validator = PDFValidator()
    result = validator.validate(generated_pdf_path)
    assert isinstance(result, ValidationResult)


def test_validation_result_has_required_fields():
    result = ValidationResult(
        passed=True, page_count=1, extracted_text="some text", issues=[]
    )
    assert result.passed is True
    assert result.page_count == 1
    assert result.extracted_text == "some text"
    assert result.issues == []


def test_validate_passes_for_well_formed_pdf(generated_pdf_path):
    validator = PDFValidator()
    result = validator.validate(generated_pdf_path)

    assert result.passed is True
    assert result.page_count >= 1
    assert len(result.extracted_text.strip()) > 0
    assert "Jane Smith" in result.extracted_text
    assert result.issues == []


def test_validate_flags_page_count_over_mvp_limit(generated_pdf_path, monkeypatch):
    """Page counts beyond the MVP 1-2 page target should be flagged, not silently passed."""
    validator = PDFValidator(max_pages=2)

    # Simulate a 3-page document by monkeypatching PdfReader via the validator's module
    import resume_tailorer.pdf.validator as validator_module

    class FakePage:
        def extract_text(self):
            return "Some resume content that is reasonably long and readable text."

    class FakeReader:
        def __init__(self, path):
            self.pages = [FakePage(), FakePage(), FakePage()]

    monkeypatch.setattr(validator_module, "PdfReader", FakeReader)

    result = validator.validate(generated_pdf_path)
    assert result.page_count == 3
    assert result.passed is False
    assert any("page" in issue.lower() for issue in result.issues)


def test_validate_flags_empty_text_pdf(empty_pdf_path):
    """A PDF with no extractable text (e.g. image-based) must fail validation - hard gate."""
    validator = PDFValidator()
    result = validator.validate(empty_pdf_path)

    assert result.passed is False
    assert result.extracted_text.strip() == ""
    assert len(result.issues) > 0
    assert any("text" in issue.lower() or "empty" in issue.lower() for issue in result.issues)


def test_validate_flags_zero_page_pdf(zero_page_pdf_path):
    validator = PDFValidator()
    result = validator.validate(zero_page_pdf_path)

    assert result.passed is False
    assert result.page_count == 0
    assert len(result.issues) > 0


def test_validate_flags_missing_file():
    validator = PDFValidator()
    result = validator.validate("/nonexistent/path/does_not_exist.pdf")

    assert result.passed is False
    assert len(result.issues) > 0


def test_validate_flags_garbage_dominated_text(generated_pdf_path, monkeypatch):
    """If extracted text is dominated by non-alphanumeric garbage, flag corruption."""
    validator = PDFValidator()

    import resume_tailorer.pdf.validator as validator_module

    class FakePage:
        def extract_text(self):
            return "\x00\x01\x02\x03###???///***@@@$$$%%%^^^&&&"

    class FakeReader:
        def __init__(self, path):
            self.pages = [FakePage()]

    monkeypatch.setattr(validator_module, "PdfReader", FakeReader)

    result = validator.validate(generated_pdf_path)
    assert result.passed is False
    assert any(
        "garbage" in issue.lower() or "corrupt" in issue.lower() or "readable" in issue.lower()
        for issue in result.issues
    )


def test_round_trip_generate_then_validate():
    """Full round-trip: generate a PDF, then validate it. Must pass."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = os.path.join(tmpdir, "roundtrip.pdf")
        PDFGenerator().generate(SAMPLE_RESUME_TEXT, "Jane Smith", output_path=output_path)

        result = PDFValidator().validate(output_path)

        assert result.passed is True
        assert "Jane Smith" in result.extracted_text
        assert "jane.smith@example.com" in result.extracted_text


def test_validate_with_1_page_target_uses_strict_limit(tmp_path):
    """target_length='1_page' rejects a 2-page PDF (stricter than the old default max_pages=2)."""
    from unittest.mock import patch, MagicMock

    validator = PDFValidator()
    fake_pdf_path = str(tmp_path / "fake.pdf")
    with open(fake_pdf_path, "wb") as f:
        f.write(b"%PDF-1.4 fake content for page count mock test")

    mock_reader = MagicMock()
    mock_page1 = MagicMock()
    mock_page1.extract_text.return_value = "Some resume text here that is long enough to pass the length check for sure."
    mock_page2 = MagicMock()
    mock_page2.extract_text.return_value = "More resume text on a second page that also passes length check easily."
    mock_reader.pages = [mock_page1, mock_page2]

    with patch("resume_tailorer.pdf.validator.PdfReader", return_value=mock_reader):
        result = validator.validate(fake_pdf_path, target_length="1_page")

    assert result.passed is False
    assert any("1 page" in issue for issue in result.issues)


def test_validate_with_2_page_target_allows_2_pages(tmp_path):
    """target_length='2_page' allows exactly 2 pages without flagging an issue."""
    from unittest.mock import patch, MagicMock

    validator = PDFValidator()
    fake_pdf_path = str(tmp_path / "fake.pdf")
    with open(fake_pdf_path, "wb") as f:
        f.write(b"%PDF-1.4 fake content")

    mock_reader = MagicMock()
    mock_page1 = MagicMock()
    mock_page1.extract_text.return_value = "Some resume text here that is long enough to pass the length check for sure."
    mock_page2 = MagicMock()
    mock_page2.extract_text.return_value = "More resume text on a second page that also passes length check easily."
    mock_reader.pages = [mock_page1, mock_page2]

    with patch("resume_tailorer.pdf.validator.PdfReader", return_value=mock_reader):
        result = validator.validate(fake_pdf_path, target_length="2_page")

    assert result.passed is True
    assert result.page_count == 2


def test_validate_with_preserve_target_allows_many_pages(tmp_path):
    """target_length='preserve' does not flag a 5-page PDF as too long."""
    from unittest.mock import patch, MagicMock

    validator = PDFValidator()
    fake_pdf_path = str(tmp_path / "fake.pdf")
    with open(fake_pdf_path, "wb") as f:
        f.write(b"%PDF-1.4 fake content")

    mock_reader = MagicMock()
    pages = []
    for _ in range(5):
        page = MagicMock()
        page.extract_text.return_value = "Resume text that is long enough to pass the minimum length check comfortably."
        pages.append(page)
    mock_reader.pages = pages

    with patch("resume_tailorer.pdf.validator.PdfReader", return_value=mock_reader):
        result = validator.validate(fake_pdf_path, target_length="preserve")

    assert result.passed is True
    assert result.page_count == 5


def test_validate_default_target_length_matches_1_page_behavior(tmp_path):
    """Calling validate() with no target_length defaults to '1_page' strict checking."""
    from unittest.mock import patch, MagicMock

    validator = PDFValidator()
    fake_pdf_path = str(tmp_path / "fake.pdf")
    with open(fake_pdf_path, "wb") as f:
        f.write(b"%PDF-1.4 fake content")

    mock_reader = MagicMock()
    mock_page1 = MagicMock()
    mock_page1.extract_text.return_value = "Resume text that is long enough to pass the minimum length check comfortably."
    mock_reader.pages = [mock_page1]

    with patch("resume_tailorer.pdf.validator.PdfReader", return_value=mock_reader):
        result_default = validator.validate(fake_pdf_path)
        result_explicit = validator.validate(fake_pdf_path, target_length="1_page")

    assert result_default.passed == result_explicit.passed
    assert result_default.page_count == result_explicit.page_count


def test_validate_with_invalid_target_length_raises_value_error(generated_pdf_path):
    """An unrecognized target_length raises ValueError (matching PDFGenerator), not a silent fallback."""
    validator = PDFValidator()
    with pytest.raises(ValueError, match="target_length"):
        validator.validate(generated_pdf_path, target_length="3_page")


def test_validate_artifact_returns_structured_failure_for_missing_contact(generated_pdf_path):
    profile = CareerTruthProfile(
        contact_info={"name": "Missing Person", "email": "missing@example.test"},
        education=[], work_experience=[], skills=[], tools=[], certifications=[], accomplishments=[]
    )
    result = PDFValidator().validate_artifact(
        generated_pdf_path, profile=profile, expected_page_count=1, accepted_changes=[]
    )
    assert result.status is ValidationStatus.FAIL
    assert result.has_code("CONTACT_MISSING")


def test_validate_artifact_marks_skipped_visual_check_as_warning(generated_pdf_path):
    profile = CareerTruthProfile(
        contact_info={}, education=[], work_experience=[], skills=[], tools=[],
        certifications=[], accomplishments=[]
    )
    result = PDFValidator().validate_artifact(
        generated_pdf_path, profile=profile, expected_page_count=1, accepted_changes=[]
    )
    assert result.has_code("VISUAL_CHECK_SKIPPED")
