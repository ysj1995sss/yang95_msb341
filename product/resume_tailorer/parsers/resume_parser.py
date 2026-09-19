from pathlib import Path
from typing import Optional
import re
from pypdf import PdfReader
from docx import Document

from resume_tailorer.models import CareerTruthProfile, WorkExperience, EducationEntry

# Constants for extraction heuristics
NAME_SEARCH_LINES = 5  # Number of first lines to check for name
MAX_SKILLS = 20  # Maximum number of skills to extract
ACCOMPLISHMENT_PATTERN = r'\d+[%K$M]'  # Pattern to identify accomplishments (contains numbers with %, K, $, M)
MIN_TITLE_LENGTH = 3  # Minimum length for job title

class ResumeParser:
    """
    Parses PDF/DOCX resumes and extracts a CareerTruthProfile.
    Uses simple pattern matching and Claude API for ambiguous sections.
    """

    def parse(self, file_path: str) -> CareerTruthProfile:
        """Parse a resume file (PDF or DOCX) and return a CareerTruthProfile."""
        text = self.get_raw_text(file_path)

        # Parse the extracted text into a CareerTruthProfile
        return self._parse_text(text)

    def get_raw_text(self, file_path: str) -> str:
        """
        Extract raw text from a resume file, dispatching by file extension.

        This is the same extraction logic parse() uses internally, exposed
        as a public method so callers (like the UI's style-hint extraction)
        don't need to duplicate the file-type dispatch or reach into private
        methods.

        Args:
            file_path: Path to the resume file (.pdf, .docx, or .doc).

        Returns:
            Extracted raw text.

        Raises:
            ValueError: If the file extension is not supported.
        """
        path = Path(file_path)

        if path.suffix.lower() == ".pdf":
            return self._extract_text_from_pdf(file_path)
        elif path.suffix.lower() in [".docx", ".doc"]:
            return self._extract_text_from_docx(file_path)
        else:
            raise ValueError(f"Unsupported file format: {path.suffix}")

    def _extract_text_from_pdf(self, file_path: str) -> str:
        """Extract text from a PDF file."""
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text

    def _extract_text_from_docx(self, file_path: str) -> str:
        """Extract text from a DOCX file."""
        doc = Document(file_path)
        text = "\n".join([para.text for para in doc.paragraphs])
        return text

    def _parse_text(self, text: str) -> CareerTruthProfile:
        """
        Parse extracted text into a CareerTruthProfile.

        This is a simplified parser; more sophisticated parsing (using Claude)
        will be added in future iterations.
        """
        # Extract contact info (name, email, phone)
        contact_info = self._extract_contact_info(text)

        # Extract education
        education = self._extract_education(text)

        # Extract work experience
        work_experience = self._extract_work_experience(text)

        # Extract skills, tools, certifications
        skills = self._extract_skills(text)
        tools = self._extract_tools(text)
        certifications = self._extract_certifications(text)

        return CareerTruthProfile(
            contact_info=contact_info,
            education=education,
            work_experience=work_experience,
            skills=skills,
            tools=tools,
            certifications=certifications,
            accomplishments=[],  # Will be extracted from work_experience
        )

    def _extract_contact_info(self, text: str) -> dict:
        """Extract name, email, phone, location from resume text."""
        contact_info = {}

        # Email (simple regex)
        email_match = re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text)
        if email_match:
            contact_info["email"] = email_match.group(0)

        # Phone (US format)
        phone_match = re.search(r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", text)
        if phone_match:
            contact_info["phone"] = phone_match.group(0)

        # Name: typically first line or top section
        lines = text.split("\n")
        for line in lines[:NAME_SEARCH_LINES]:  # Check first N lines
            if line.strip() and len(line.split()) <= 4 and not re.search(r"@|\d", line):
                contact_info["name"] = line.strip()
                break

        contact_info.setdefault("name", "Unknown")
        return contact_info

    def _extract_education(self, text: str) -> list[EducationEntry]:
        """Extract education entries (simple regex-based)."""
        education = []

        # Look for EDUCATION section
        if "education" in text.lower():
            edu_match = re.search(
                r"education[:]*\s*\n(.*?)(?:\n(?:TECHNICAL|SKILLS|WORK|EXPERIENCE|CERTIFICATIONS|[A-Z]{2,}[\s:]*$))",
                text,
                re.IGNORECASE | re.DOTALL | re.MULTILINE
            )

            if edu_match:
                edu_section = edu_match.group(1).strip()

                # Split education entries by looking for patterns with degrees
                # Look for lines that start with degree abbreviations
                degree_lines = re.findall(
                    r"((?:B\.?S\.?|M\.?S\.?|B\.?A\.?|M\.?A\.?|Ph\.?D\.?|MBA)\s+.+?)(?:\n(?:[A-Z][a-zA-Z\s,\.0-9&-]*?\s*\|?\s*\d{4})?)",
                    edu_section,
                    re.IGNORECASE
                )

                # Process each potential education entry
                entries = edu_section.split('\n\n')  # Split by double newline first
                if len(entries) == 1:
                    # If no double newlines, try to extract based on degree pattern
                    lines = edu_section.split('\n')
                    entries = []
                    current_entry = []
                    for line in lines:
                        if re.match(r"^(B\.?S\.?|M\.?S\.?|B\.?A\.?|M\.?A\.?|Ph\.?D\.?|MBA)\b", line, re.IGNORECASE):
                            if current_entry:
                                entries.append('\n'.join(current_entry))
                            current_entry = [line]
                        else:
                            current_entry.append(line)
                    if current_entry:
                        entries.append('\n'.join(current_entry))

                for entry in entries:
                    if not entry.strip():
                        continue

                    lines = [l.strip() for l in entry.strip().split('\n') if l.strip()]
                    if not lines:
                        continue

                    degree_line = lines[0]

                    # Extract degree and field from first line
                    degree_match = re.search(
                        r"(B\.?S\.?|M\.?S\.?|B\.?A\.?|M\.?A\.?|Ph\.?D\.?|MBA)\s+(.+?)$",
                        degree_line,
                        re.IGNORECASE
                    )

                    if degree_match:
                        degree = degree_match.group(1).strip()
                        field = degree_match.group(2).strip()

                        # Get institution and year from remaining lines
                        institution = "Unknown"
                        year = None

                        for i in range(1, len(lines)):
                            detail_line = lines[i]

                            # Extract year (4 digits)
                            year_match = re.search(r'(\d{4})', detail_line)
                            if year_match:
                                year = int(year_match.group(1))

                            # Extract institution (everything before year or pipe)
                            inst_part = detail_line.split('|')[0].strip()
                            if inst_part and inst_part != str(year):
                                institution = inst_part

                        if year:
                            education.append(
                                EducationEntry(
                                    degree=degree,
                                    field=field,
                                    institution=institution,
                                    year=year,
                                )
                            )

        return education

    def _extract_work_experience(self, text: str) -> list[WorkExperience]:
        """
        Extract work experience (simplified).

        In MVP, this uses regex to find job sections; future iterations
        will use Claude to parse ambiguous sections.
        """
        work_experience = []

        # Look for job patterns like "Title | Company | Location | Dates"
        # Pattern: Title at Company (location) dates
        patterns = [
            # Pattern 1: "Title\nCompany | Location | Dates"
            r"([A-Z][^|\n]+)\s*\n([A-Za-z\s&\.]+?)\s*(?:\||—)?\s*([^|,\n]+?)\s*(?:\||—)?\s*((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}[^|,\n]*?)(?:\n|$)",
        ]

        # Simple heuristic: look for "WORK EXPERIENCE" or "EXPERIENCE" section
        if "work experience" in text.lower() or "experience" in text.lower():
            # Find the experience section
            exp_match = re.search(
                r"(?:work\s+)?experience[:]*\s*\n(.*?)(?:\n(?:EDUCATION|TECHNICAL|SKILLS|CERTIFICATIONS|$))",
                text,
                re.IGNORECASE | re.DOTALL
            )

            if exp_match:
                exp_section = exp_match.group(1)

                # Split by job entries (look for patterns like "Senior Software Engineer")
                # Jobs usually start with a title line followed by company/location/dates
                job_blocks = re.split(r'\n(?=[A-Z][a-z]+ )', exp_section)

                for block in job_blocks:
                    if not block.strip():
                        continue

                    lines = block.strip().split('\n')
                    if len(lines) < 2:
                        continue

                    title_line = lines[0].strip()

                    # Skip if line is too short or looks like a bullet point
                    if len(title_line) < MIN_TITLE_LENGTH or title_line.startswith('•') or title_line.startswith('-'):
                        continue

                    # Extract title (remove bold/italic markers if any)
                    title = title_line.replace('<b>', '').replace('</b>', '')

                    # Extract employer, location, dates from next line if available
                    company_line = lines[1].strip() if len(lines) > 1 else ""

                    # Split company line by pipe or dash
                    parts = re.split(r'\s*(?:\||—|–)\s*', company_line)
                    employer = parts[0] if len(parts) > 0 else "Unknown"
                    location = parts[1] if len(parts) > 1 else ""
                    dates = parts[2] if len(parts) > 2 else ""

                    # Extract bullet points (responsibilities and accomplishments)
                    responsibilities = []
                    accomplishments = []
                    for line in lines[2:]:
                        line = line.strip()
                        if line.startswith('•') or line.startswith('-'):
                            # Remove bullet point marker
                            text_content = line.lstrip('•-').strip()

                            # Heuristic: if it contains numbers/percentages, it's likely an accomplishment
                            if re.search(ACCOMPLISHMENT_PATTERN, text_content):
                                accomplishments.append(text_content)
                            else:
                                responsibilities.append(text_content)

                    # Create WorkExperience entry if we have at least a title and dates
                    if title and (dates or employer):
                        work_experience.append(
                            WorkExperience(
                                employer=employer.strip(),
                                title=title.strip(),
                                dates=dates.strip(),
                                responsibilities=responsibilities,
                                accomplishments=accomplishments,
                                location=location.strip() if location else None,
                            )
                        )

        return work_experience

    def _extract_skills(self, text: str) -> list[str]:
        """Extract technical skills from resume."""
        # Look for a "Skills" section
        skills = []
        if "skills" in text.lower():
            # Find the Skills section and extract items
            skills_section = re.search(
                r"(?:technical\s+)?skills?[:]*\s*\n(.*?)(?:\n(?:TOOLS?|CERTIFICATIONS?|LANGUAGES?|EDUCATION|EXPERIENCE|WORK|[A-Z]{2,}[\s:]*$)|\Z)",
                text,
                re.IGNORECASE | re.DOTALL | re.MULTILINE,
            )
            if skills_section:
                items = skills_section.group(1)
                # Split by comma, newline, pipe, or bullet
                # First split by newline to get lines
                lines = items.split('\n')
                for line in lines:
                    if line.strip():
                        # Split each line by comma or colon (for "Languages: Python, Java, etc.")
                        line_items = re.split(r'[:,]', line)
                        for item in line_items:
                            clean_item = item.strip().lstrip('•-').strip()
                            if clean_item and len(clean_item) > 1:  # Skip single characters
                                skills.append(clean_item)

        # Remove duplicates while preserving order
        seen = set()
        unique_skills = []
        for skill in skills:
            if skill not in seen:
                seen.add(skill)
                unique_skills.append(skill)

        return unique_skills[:MAX_SKILLS]  # Cap at max for MVP

    def _extract_tools(self, text: str) -> list[str]:
        """Extract tools/technologies (databases, frameworks, etc.)."""
        # For MVP, we'll extract from skills section or mention in work experience
        return []

    def extract_style_hints(self, raw_text: str) -> dict:
        """
        Extract lightweight visual style hints from the original resume text,
        used later to make the tailored PDF resemble the source resume's
        bullet style and heading emphasis.

        Args:
            raw_text: The original resume's extracted plain text.

        Returns:
            Dict with keys:
                "bullet_char": most common bullet marker found ("•", "-", "*"),
                    defaulting to "•" if none detected.
                "heading_style": "bold_larger" if a short (<30 char) ALL-CAPS
                    line is found (suggesting a large/bold heading font in
                    the original), else "bold".
        """
        lines = raw_text.splitlines()

        bullet_counts = {"•": 0, "-": 0, "*": 0}
        has_short_caps_heading = False

        for raw_line in lines:
            line = raw_line.strip()
            if not line:
                continue

            for marker in bullet_counts:
                if line.startswith(marker):
                    bullet_counts[marker] += 1
                    break

            letters = [c for c in line if c.isalpha()]
            if letters and all(c.isupper() for c in letters) and len(line) < 30:
                has_short_caps_heading = True

        dominant_bullet = max(bullet_counts, key=bullet_counts.get)
        if bullet_counts[dominant_bullet] == 0:
            dominant_bullet = "•"

        heading_style = "bold_larger" if has_short_caps_heading else "bold"

        return {
            "bullet_char": dominant_bullet,
            "heading_style": heading_style,
        }

    def _extract_certifications(self, text: str) -> list[str]:
        """Extract certifications."""
        certifications = []
        # Look for patterns like "AWS Solutions Architect", "CPA", etc.
        # Use explicit allowlist of known certification acronyms to avoid false positives
        patterns = [
            r"((?:AWS|Azure|Google Cloud|Kubernetes|Docker|Certified)\s+[^,\n]+)",
            # Known certification acronyms (CPA, PMP, CISSP, CCNA, etc.)
            r"\b(CPA|CFA|CFP|PMP|CISSP|CCNA|CCNP|CHES|CAPM|CSM|ACP|ITIL)\b",
        ]
        for pattern in patterns:
            for match in re.finditer(pattern, text):
                certifications.append(match.group(0).strip())

        return list(set(certifications))  # Deduplicate
