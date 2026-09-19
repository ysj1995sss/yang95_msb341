"""
PDF Generator for tailored resumes.

Produces a TEXT-BASED, ATS-readable PDF from plain resume text using
reportlab's Platypus flowable layout. Text is drawn as real text objects
(never rendered to an image), which is required for ATS parsers and for
the round-trip validation hard gate in PDFValidator.

Layout approach:
- Candidate name as a large header, optionally followed by the job title.
- The rest of the resume text is split into lines. A line in ALL CAPS
  (e.g. "WORK EXPERIENCE", "EDUCATION", "SKILLS") is treated as a section
  heading and styled accordingly. Lines starting with "-" or "*" are
  treated as bullet points. Everything else is a normal paragraph line.
- Platypus's SimpleDocTemplate handles pagination automatically. For the
  MVP, resumes are expected to fit on a single page with the chosen
  margins/font sizes; if content is long enough to overflow, reportlab
  will simply continue onto additional pages rather than corrupt the
  layout. Enforcing a strict 1-page cutoff is out of scope for MVP.

Scope of `target_length` (important):
- target_length controls font size, line spacing, and margins only. It does
  NOT reprioritize, shorten, or cut resume content — if the tailored
  resume's content doesn't fit within the chosen target_length's page
  limit, PDFValidator will report a page-count overflow issue.
  Content-level length adaptation (choosing which bullets to include) is a
  future enhancement, not implemented here.
"""

import os
import re
import tempfile

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.enums import TA_CENTER


class PDFGenerator:
    """Generates a text-based, ATS-readable PDF from tailored resume text."""

    LENGTH_PRESETS = {
        "1_page": {"font_size": 9, "leading": 12, "margin": 0.5, "bullet_leading": 12},
        "2_page": {"font_size": 10, "leading": 14, "margin": 0.75, "bullet_leading": 14},
        "preserve": {"font_size": 9.5, "leading": 13, "margin": 0.6, "bullet_leading": 13},
    }

    def __init__(self):
        # Styles are built per-generate() call now (see _build_styles), since
        # they depend on target_length. __init__ keeps no fixed style state.
        pass

    def _get_length_preset(self, target_length: str) -> dict:
        """Look up font/margin/leading preset for a target length option.

        Args:
            target_length: One of "1_page", "2_page", "preserve".

        Returns:
            Dict with keys: font_size, leading, margin, bullet_leading.

        Raises:
            ValueError: If target_length is not a recognized preset name.
        """
        if target_length not in self.LENGTH_PRESETS:
            raise ValueError(
                f"Unknown target_length '{target_length}'. "
                f"Must be one of: {list(self.LENGTH_PRESETS.keys())}"
            )
        return self.LENGTH_PRESETS[target_length]

    def _build_styles(self, preset: dict, style_hints: dict = None):
        """Build Platypus ParagraphStyle objects from a length preset and optional style hints."""
        body_font = preset["font_size"]
        leading = preset["leading"]
        bullet_leading = preset["bullet_leading"]

        heading_style_hint = (style_hints or {}).get("heading_style", "bold")
        # "bold_larger" headings get an extra size bump beyond the standard +2;
        # plain "bold" headings keep the existing +2 sizing.
        heading_size_bump = 3 if heading_style_hint == "bold_larger" else 2

        name_style = ParagraphStyle(
            name="CandidateName",
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=19,
            alignment=TA_CENTER,
            spaceAfter=2,
        )
        title_style = ParagraphStyle(
            name="JobTitle",
            fontName="Helvetica",
            fontSize=10,
            leading=12,
            alignment=TA_CENTER,
            spaceAfter=8,
            textColor="#333333",
        )
        section_style = ParagraphStyle(
            name="SectionHeading",
            fontName="Helvetica-Bold",
            fontSize=body_font + heading_size_bump,
            leading=leading + heading_size_bump,
            spaceBefore=8,
            spaceAfter=4,
        )
        bullet_style = ParagraphStyle(
            name="Bullet",
            fontName="Helvetica",
            fontSize=body_font,
            leading=bullet_leading,
            leftIndent=14,
            spaceAfter=2,
        )
        body_style = ParagraphStyle(
            name="Body",
            fontName="Helvetica",
            fontSize=body_font,
            leading=leading,
            spaceAfter=2,
        )
        return {
            "name": name_style,
            "title": title_style,
            "section": section_style,
            "bullet": bullet_style,
            "body": body_style,
        }

    def generate(
        self,
        resume_text: str,
        candidate_name: str,
        output_path: str = None,
        job_title: str = None,
        target_length: str = "1_page",
        style_hints: dict = None,
    ) -> str:
        """
        Generate a text-based PDF from resume text.

        Args:
            resume_text: The full tailored resume body text (contact info,
                sections, bullets, etc). May or may not repeat the
                candidate's name at the top; the name is always rendered
                as the document header separately.
            candidate_name: Candidate's full name, used for the header.
            output_path: Where to write the PDF. If omitted, a path is
                generated in a temp directory.
            job_title: Optional job title to display under the name.
            target_length: One of "1_page" (default), "2_page", "preserve".
                Controls font size, line spacing, and margins. (Adjusts
                formatting only — does not shorten or omit resume content.
                See module docstring.)
            style_hints: Optional dict with keys "bullet_char" (str, e.g.
                "•", "-", "*") and "heading_style" (str, "bold" or
                "bold_larger") extracted from the original resume, used to
                make the tailored PDF visually resemble the source resume.

        Returns:
            The path to the generated PDF file.

        Raises:
            ValueError: If target_length is not a recognized preset.
        """
        preset = self._get_length_preset(target_length)
        styles = self._build_styles(preset, style_hints)

        if output_path is None:
            safe_name = re.sub(r"[^A-Za-z0-9_-]+", "_", candidate_name.strip()) or "resume"
            output_path = os.path.join(tempfile.gettempdir(), f"{safe_name}_resume.pdf")

        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        margin = preset["margin"]
        doc = SimpleDocTemplate(
            output_path,
            pagesize=LETTER,
            topMargin=margin * inch,
            bottomMargin=margin * inch,
            leftMargin=(margin + 0.1) * inch,
            rightMargin=(margin + 0.1) * inch,
        )

        story = []
        story.append(Paragraph(self._escape(candidate_name), styles["name"]))
        if job_title:
            story.append(Paragraph(self._escape(job_title), styles["title"]))
        else:
            story.append(Spacer(1, 6))

        story.extend(self._build_body_flowables(resume_text, candidate_name, styles, style_hints))

        doc.build(story)
        return output_path

    def _build_body_flowables(self, resume_text: str, candidate_name: str, styles: dict, style_hints: dict = None):
        """Convert plain resume text into a list of Platypus flowables."""
        flowables = []
        lines = resume_text.splitlines()
        bullet_char = (style_hints or {}).get("bullet_char", "•")

        for raw_line in lines:
            line = raw_line.strip()
            if not line:
                flowables.append(Spacer(1, 4))
                continue

            # Skip a leading line that just repeats the candidate's name;
            # it's already rendered as the header.
            if line.strip().lower() == candidate_name.strip().lower():
                continue

            if self._is_section_heading(line):
                flowables.append(Paragraph(self._escape(line), styles["section"]))
            elif line.startswith(("-", "*", "•")):
                bullet_text = line.lstrip("-*• ").strip()
                flowables.append(
                    Paragraph(f"{bullet_char} {self._escape(bullet_text)}", styles["bullet"])
                )
            else:
                flowables.append(Paragraph(self._escape(line), styles["body"]))

        return flowables

    @staticmethod
    def _is_section_heading(line: str) -> bool:
        """A line is treated as a section heading if it is short and all-caps."""
        letters = [c for c in line if c.isalpha()]
        if not letters:
            return False
        is_all_caps = all(c.isupper() for c in letters)
        return is_all_caps and len(line) <= 60

    @staticmethod
    def _escape(text: str) -> str:
        """Escape reportlab/XML-sensitive characters for Paragraph markup."""
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
