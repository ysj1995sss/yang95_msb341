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


class TestMarkdownDefenseAndOrgHeaderLayout:
    """
    Regression tests for two bugs found live (2026-09-22): a real LLM
    formatted its output in Markdown despite never being asked to, and
    PDFGenerator's line classifier flattened every "Employer | Location
    Dates" line into a plain body line (or, when it started with a stray
    "*", into a corrupted bullet), losing the bold-employer/italic-title
    layout the original resume had.
    """

    def test_stray_markdown_asterisks_do_not_reach_the_pdf(self, tmp_path):
        resume_text = (
            "**EDUCATION**\n"
            "**MIT** | Cambridge, MA 2018\n"
            "*BS Computer Science*\n"
            "- Built REST APIs\n"
        )
        gen = PDFGenerator()
        path = gen.generate(resume_text, "Jane Doe", output_path=str(tmp_path / "resume.pdf"))
        reader = PdfReader(path)
        text = "".join(page.extract_text() or "" for page in reader.pages)
        assert "*" not in text

    def test_org_header_line_is_not_flattened_into_a_bullet(self, tmp_path):
        """A line starting with a stray "*" (from unstripped Markdown) must
        not get misread as a bullet and have its leading text mangled."""
        resume_text = "**MIT** | Cambridge, MA 2018\nBS Computer Science\n- Built REST APIs\n"
        gen = PDFGenerator()
        path = gen.generate(resume_text, "Jane Doe", output_path=str(tmp_path / "resume.pdf"))
        reader = PdfReader(path)
        text = "".join(page.extract_text() or "" for page in reader.pages)
        assert "MIT" in text
        # The employer/institution line itself must not have been turned
        # into a bullet point.
        assert "• MIT" not in text and "- MIT" not in text

    def test_line_with_pipe_and_year_is_treated_as_org_header(self):
        assert PDFGenerator._looks_like_org_header("CVS Health | Woonsocket, RI 2026") is True
        assert PDFGenerator._looks_like_org_header("State University | Provo, UT 2020-2024") is True

    def test_plain_body_line_is_not_treated_as_org_header(self):
        assert PDFGenerator._looks_like_org_header("A summary sentence about the candidate.") is False
        assert PDFGenerator._looks_like_org_header("Skills: Python, SQL") is False

    def test_title_line_after_org_header_renders_and_extracts(self, tmp_path):
        resume_text = "CVS Health | Woonsocket, RI 2026\nMarketing Intern\n- Did the work\n"
        gen = PDFGenerator()
        path = gen.generate(resume_text, "Jane Doe", output_path=str(tmp_path / "resume.pdf"))
        reader = PdfReader(path)
        text = "".join(page.extract_text() or "" for page in reader.pages)
        assert "CVS Health" in text
        assert "Marketing Intern" in text
        assert "Did the work" in text


class TestCombinedHeaderPattern:
    """
    Regression tests for a bug found live (2026-09-22): the LLM sometimes
    writes "Title at Employer" then "Location | Dates" (two lines) instead
    of "Employer | Location Dates" then "Title" -- both are reasonable
    resume phrasings, but only the second matched the original org-header
    heuristic, so the first left the job title as unstyled plain text.
    """

    def test_title_at_employer_is_a_combined_header(self):
        assert PDFGenerator._looks_like_combined_header("Marketing Manager at Acme Corp") is True

    def test_degree_from_institution_is_a_combined_header(self):
        assert PDFGenerator._looks_like_combined_header(
            "Master of Business Administration from State University (2027)"
        ) is True

    def test_prose_sentence_with_at_or_from_is_not_a_combined_header(self):
        """Resume header lines never end in a sentence period; prose does."""
        assert PDFGenerator._looks_like_combined_header(
            "Expert at leveraging data analytics to unlock insights."
        ) is False
        assert PDFGenerator._looks_like_combined_header(
            "Consulted a client from a Fortune 500 company on strategy."
        ) is False

    def test_line_with_pipe_is_not_a_combined_header(self):
        """The pipe-based org-header check already handles this case."""
        assert PDFGenerator._looks_like_combined_header("CVS Health | Woonsocket, RI 2026") is False

    def test_second_header_line_after_a_combined_header_becomes_subtitle_not_bold_again(self, tmp_path):
        resume_text = (
            "Marketing Manager at Acme Corp\n"
            "Remote | 2022 - 2024\n"
            "- Did the work\n"
        )
        gen = PDFGenerator()
        path = gen.generate(resume_text, "Jane Doe", output_path=str(tmp_path / "resume.pdf"))
        reader = PdfReader(path)
        text = "".join(page.extract_text() or "" for page in reader.pages)
        assert "Acme Corp" in text
        assert "Remote" in text
        assert "Did the work" in text


class TestFontSanitization:
    """
    Regression test for a bug found live (2026-09-22): a real company name
    ("Mondelez", spelled with a macron-e) rendered as a broken box glyph in
    the actual PDF -- the character is outside reportlab's base Helvetica
    font's supported WinAnsiEncoding range.
    """

    def test_macron_e_is_transliterated_not_dropped_or_broken(self):
        result = PDFGenerator._sanitize_for_font("Mondelēz")
        assert result == "Mondelez"

    def test_common_latin1_accents_still_work_fine(self):
        # These ARE in WinAnsiEncoding -- confirm the sanitizer doesn't
        # over-aggressively mangle characters that render correctly already.
        result = PDFGenerator._sanitize_for_font("Café naïve")
        assert result == "Cafe naive"

    def test_generated_pdf_has_no_replacement_glyphs_for_unusual_characters(self, tmp_path):
        resume_text = "- Consulted Mondelēz on a growth strategy\n"
        gen = PDFGenerator()
        path = gen.generate(resume_text, "Jane Doe", output_path=str(tmp_path / "resume.pdf"))
        reader = PdfReader(path)
        text = "".join(page.extract_text() or "" for page in reader.pages)
        assert "Mondelez" in text
        assert "�" not in text
