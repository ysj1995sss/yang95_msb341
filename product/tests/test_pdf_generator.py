"""
Tests for the PDF Generator.

Tests verify that the generator:
1. Produces a PDF file that exists and is non-empty
2. Produces a text-based (not image-based) PDF — text is extractable
3. Preserves resume structure (name header, sections) in the output text
4. Respects the requested/derived output path
"""

import os
import tempfile

import pytest
from pypdf import PdfReader

from resume_tailorer.pdf.generator import PDFGenerator


SAMPLE_RESUME_TEXT = """John Doe
john.doe@example.com | 555-123-4567 | San Francisco, CA

WORK EXPERIENCE

Software Engineer, TechCorp (2020-2022)
- Built microservices using Python and Go
- Managed Docker containers and Kubernetes deployments
- Improved system performance by 30%

Junior Developer, StartupXYZ (2018-2020)
- Developed frontend features with React
- Worked on PostgreSQL database schema design

EDUCATION

BS Computer Science, MIT, 2018

SKILLS

Python, Go, JavaScript, React, Docker, PostgreSQL, AWS
"""


@pytest.fixture
def tmp_output_path():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield os.path.join(tmpdir, "resume.pdf")


def test_generator_instantiation():
    generator = PDFGenerator()
    assert generator is not None


def test_generate_creates_file(tmp_output_path):
    generator = PDFGenerator()
    result_path = generator.generate(
        SAMPLE_RESUME_TEXT, "John Doe", output_path=tmp_output_path
    )

    assert result_path == tmp_output_path
    assert os.path.exists(result_path)
    assert os.path.getsize(result_path) > 0


def test_generate_returns_path_string():
    generator = PDFGenerator()
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = os.path.join(tmpdir, "out.pdf")
        result = generator.generate(SAMPLE_RESUME_TEXT, "John Doe", output_path=output_path)
        assert isinstance(result, str)


def test_generate_without_output_path_uses_default(tmp_path, monkeypatch):
    """When output_path is not given, generator should create one automatically."""
    monkeypatch.chdir(tmp_path)
    generator = PDFGenerator()
    result_path = generator.generate(SAMPLE_RESUME_TEXT, "Jane Smith")

    assert os.path.exists(result_path)
    assert result_path.endswith(".pdf")


def test_generated_pdf_is_text_based_not_image(tmp_output_path):
    """Critical constraint: PDF must be text-based (ATS-readable), never an image."""
    generator = PDFGenerator()
    generator.generate(SAMPLE_RESUME_TEXT, "John Doe", output_path=tmp_output_path)

    reader = PdfReader(tmp_output_path)
    assert len(reader.pages) >= 1

    extracted = reader.pages[0].extract_text() or ""
    assert len(extracted.strip()) > 0
    # Should contain real content, not be empty/garbage as an image-based PDF would be
    assert "John" in extracted or "Doe" in extracted


def test_generated_pdf_preserves_resume_structure(tmp_output_path):
    generator = PDFGenerator()
    generator.generate(SAMPLE_RESUME_TEXT, "John Doe", output_path=tmp_output_path)

    reader = PdfReader(tmp_output_path)
    full_text = "\n".join(page.extract_text() or "" for page in reader.pages)

    assert "John Doe" in full_text
    assert "WORK EXPERIENCE" in full_text.upper() or "EXPERIENCE" in full_text.upper()
    assert "EDUCATION" in full_text.upper()
    assert "SKILLS" in full_text.upper()


def test_generated_pdf_includes_contact_info(tmp_output_path):
    generator = PDFGenerator()
    generator.generate(SAMPLE_RESUME_TEXT, "John Doe", output_path=tmp_output_path)

    reader = PdfReader(tmp_output_path)
    full_text = "\n".join(page.extract_text() or "" for page in reader.pages)

    assert "john.doe@example.com" in full_text


def test_generate_handles_optional_job_title(tmp_output_path):
    generator = PDFGenerator()
    result_path = generator.generate(
        SAMPLE_RESUME_TEXT,
        "John Doe",
        output_path=tmp_output_path,
        job_title="Senior Software Engineer",
    )
    assert os.path.exists(result_path)


def test_generate_fits_target_page_count(tmp_output_path):
    """MVP target: fit on 1 page for a normal-length resume."""
    generator = PDFGenerator()
    generator.generate(SAMPLE_RESUME_TEXT, "John Doe", output_path=tmp_output_path)

    reader = PdfReader(tmp_output_path)
    # MVP allows some overflow, but a short sample resume should fit on 1 page
    assert len(reader.pages) == 1
