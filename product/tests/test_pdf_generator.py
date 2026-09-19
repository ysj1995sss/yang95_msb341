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


def test_generate_with_1_page_target_uses_default_preset(tmp_path):
    """target_length='1_page' (or omitted) matches today's existing font/margin values."""
    gen = PDFGenerator()
    preset = gen._get_length_preset("1_page")
    assert preset["font_size"] == 9
    assert preset["leading"] == 12
    assert preset["margin"] == 0.5

def test_generate_with_2_page_target_uses_larger_preset(tmp_path):
    """target_length='2_page' uses larger font/margins than 1_page."""
    gen = PDFGenerator()
    preset = gen._get_length_preset("2_page")
    assert preset["font_size"] == 10
    assert preset["leading"] == 14
    assert preset["margin"] == 0.75

def test_generate_with_preserve_target_uses_middle_preset(tmp_path):
    """target_length='preserve' uses a preset between 1_page and 2_page."""
    gen = PDFGenerator()
    preset = gen._get_length_preset("preserve")
    assert preset["font_size"] == 9.5
    assert preset["leading"] == 13
    assert preset["margin"] == 0.6

def test_generate_with_invalid_target_length_raises_value_error():
    """An unrecognized target_length string raises ValueError, not a silent fallback."""
    gen = PDFGenerator()
    with pytest.raises(ValueError, match="target_length"):
        gen._get_length_preset("3_page")

def test_build_styles_uses_larger_heading_for_bold_larger_hint():
    """style_hints={'heading_style': 'bold_larger'} produces a bigger section heading font than the default."""
    gen = PDFGenerator()
    preset = gen._get_length_preset("1_page")

    default_styles = gen._build_styles(preset, style_hints=None)
    plain_bold_styles = gen._build_styles(preset, style_hints={"heading_style": "bold"})
    larger_styles = gen._build_styles(preset, style_hints={"heading_style": "bold_larger"})

    assert larger_styles["section"].fontSize > default_styles["section"].fontSize
    assert larger_styles["section"].fontSize > plain_bold_styles["section"].fontSize
    assert plain_bold_styles["section"].fontSize == default_styles["section"].fontSize

def test_generate_default_target_length_matches_existing_output(tmp_path):
    """Calling generate() with no target_length produces identical output to explicit '1_page' (backward compatibility)."""
    gen = PDFGenerator()
    output_default = str(tmp_path / "default.pdf")
    output_explicit = str(tmp_path / "explicit.pdf")

    resume_text = "WORK EXPERIENCE\n- Built a system\nEDUCATION\nBS Computer Science"

    path1 = gen.generate(resume_text, "Jane Doe", output_path=output_default)
    path2 = gen.generate(resume_text, "Jane Doe", output_path=output_explicit, target_length="1_page")

    # Both files should be non-empty and roughly the same size (same layout params)
    size1 = os.path.getsize(path1)
    size2 = os.path.getsize(path2)
    assert size1 > 0
    assert size2 > 0
    assert abs(size1 - size2) < 50  # near-identical byte size; same layout params produce near-identical PDF bytes

def test_generate_2_page_target_produces_larger_fonts_in_output(tmp_path):
    """A resume generated with target_length='2_page' extracts with the larger font metadata (indirect check via file size difference from 1_page)."""
    gen = PDFGenerator()
    resume_text = "WORK EXPERIENCE\n- Built a system\nEDUCATION\nBS Computer Science"

    path_1page = gen.generate(resume_text, "Jane Doe", output_path=str(tmp_path / "one.pdf"), target_length="1_page")
    path_2page = gen.generate(resume_text, "Jane Doe", output_path=str(tmp_path / "two.pdf"), target_length="2_page")

    # Different presets must produce different PDF byte content (proves the preset actually affects generation)
    with open(path_1page, "rb") as f1, open(path_2page, "rb") as f2:
        assert f1.read() != f2.read()
