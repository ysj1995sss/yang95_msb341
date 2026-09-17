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

    def __init__(self):
        self.name_style = ParagraphStyle(
            name="CandidateName",
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=19,
            alignment=TA_CENTER,
            spaceAfter=2,
        )
        self.title_style = ParagraphStyle(
            name="JobTitle",
            fontName="Helvetica",
            fontSize=10,
            leading=12,
            alignment=TA_CENTER,
            spaceAfter=8,
            textColor="#333333",
        )
        self.section_style = ParagraphStyle(
            name="SectionHeading",
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            spaceBefore=8,
            spaceAfter=4,
        )
        self.bullet_style = ParagraphStyle(
            name="Bullet",
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            leftIndent=14,
            spaceAfter=2,
        )
        self.body_style = ParagraphStyle(
            name="Body",
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            spaceAfter=2,
        )

    def generate(
        self,
        resume_text: str,
        candidate_name: str,
        output_path: str = None,
        job_title: str = None,
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

        Returns:
            The path to the generated PDF file.
        """
        if output_path is None:
            safe_name = re.sub(r"[^A-Za-z0-9_-]+", "_", candidate_name.strip()) or "resume"
            output_path = os.path.join(tempfile.gettempdir(), f"{safe_name}_resume.pdf")

        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        doc = SimpleDocTemplate(
            output_path,
            pagesize=LETTER,
            topMargin=0.5 * inch,
            bottomMargin=0.5 * inch,
            leftMargin=0.6 * inch,
            rightMargin=0.6 * inch,
        )

        story = []
        story.append(Paragraph(self._escape(candidate_name), self.name_style))
        if job_title:
            story.append(Paragraph(self._escape(job_title), self.title_style))
        else:
            story.append(Spacer(1, 6))

        story.extend(self._build_body_flowables(resume_text, candidate_name))

        doc.build(story)
        return output_path

    def _build_body_flowables(self, resume_text: str, candidate_name: str):
        """Convert plain resume text into a list of Platypus flowables."""
        flowables = []
        lines = resume_text.splitlines()

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
                flowables.append(Paragraph(self._escape(line), self.section_style))
            elif line.startswith(("-", "*", "•")):
                bullet_text = line.lstrip("-*• ").strip()
                flowables.append(
                    Paragraph(f"• {self._escape(bullet_text)}", self.bullet_style)
                )
            else:
                flowables.append(Paragraph(self._escape(line), self.body_style))

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
