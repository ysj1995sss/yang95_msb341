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
        if path.suffix.lower() == ".docx":
            return self._extract_text_from_docx(file_path)
        if path.suffix.lower() == ".doc":
            raise ValueError(
                "Legacy .doc files are not supported. Save the resume as PDF or .docx."
            )
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

    # A "company | location, dates" line contains a 4-digit year and is
    # never itself a bullet.
    _YEAR_PATTERN = re.compile(r"(?:19|20)\d{2}")

    def _extract_work_experience(self, text: str) -> list[WorkExperience]:
        """
        Extract work experience (simplified).

        In MVP, this uses regex to find job sections; future iterations
        will use Claude to parse ambiguous sections.
        """
        work_experience = []

        if "experience" not in text.lower():
            return work_experience

        exp_match = re.search(
            r"(?:work\s+)?experience[:]*\s*\n(.*?)(?:\n(?:EDUCATION|TECHNICAL|SKILLS|CERTIFICATIONS|$))",
            text,
            re.IGNORECASE | re.DOTALL,
        )
        if not exp_match:
            return work_experience

        lines = exp_match.group(1).split("\n")

        # Anchor each job on its "company | location, dates" line (contains
        # a year, is not a bullet) rather than guessing job boundaries from
        # capitalization. The previous approach split on ANY line starting
        # with a capitalized word followed by lowercase letters, which
        # incorrectly split a title away from its OWN company line whenever
        # the company name starts with a normal capitalized word rather
        # than an all-caps abbreviation -- found live (2026-09-22): "Acme
        # Corp | ..." got split from its title "Marketing Manager" (while
        # an all-caps company like "CVS Health" happened not to trigger it,
        # since "CVS" isn't `[A-Z][a-z]+`), scrambling employer/title/dates
        # and losing every bullet for that job.
        anchor_idxs = [
            i
            for i, line in enumerate(lines)
            if self._YEAR_PATTERN.search(line) and not line.strip().startswith(("•", "-"))
        ]

        for a, idx in enumerate(anchor_idxs):
            company_line = lines[idx].strip()

            # The title is the nearest preceding non-blank line, as long as
            # it isn't itself a bullet (which would mean we've walked back
            # into the previous job's content with no title in between).
            title_line = ""
            for j in range(idx - 1, -1, -1):
                candidate = lines[j].strip()
                if not candidate:
                    continue
                if not candidate.startswith(("•", "-")):
                    title_line = candidate
                break

            if not title_line or len(title_line) < MIN_TITLE_LENGTH:
                continue
            title = title_line.replace("<b>", "").replace("</b>", "")

            parts = re.split(r"\s*(?:\||—|–)\s*", company_line)
            employer = parts[0] if parts else "Unknown"
            location = parts[1] if len(parts) > 1 else ""
            dates = parts[2] if len(parts) > 2 else ""

            # Bullets run from just after this anchor to just before the
            # next job's anchor (or end of section) -- but that range's
            # last non-blank, non-bullet line is the NEXT job's title, so
            # trim it off rather than swallowing it as a bullet.
            end_idx = anchor_idxs[a + 1] if a + 1 < len(anchor_idxs) else len(lines)
            bullet_lines = lines[idx + 1 : end_idx]
            if a + 1 < len(anchor_idxs):
                for k in range(len(bullet_lines) - 1, -1, -1):
                    candidate = bullet_lines[k].strip()
                    if not candidate:
                        continue
                    if not candidate.startswith(("•", "-")):
                        bullet_lines = bullet_lines[:k]
                    break

            # PDF text extraction wraps long bullets onto a second physical
            # line with no bullet marker (e.g. "...identifying up to $120M
            # in incremental sales\npotential targeted for implementation
            # by 2027" is ONE bullet, not two). Continuation lines are
            # appended to whichever bullet list last received an entry,
            # instead of being silently dropped -- found live (2026-09-22)
            # losing real content, which then caused the fabrication-risk
            # checker to flag a genuine, verbatim accomplishment as
            # fabricated (it was missing from the structured profile it
            # checks against, not actually absent from the resume).
            bullets: list[tuple[str, str]] = []  # (category, text), in order
            for line in bullet_lines:
                line = line.strip()
                if not line:
                    continue
                if line.startswith("•") or line.startswith("-"):
                    text_content = line.lstrip("•-").strip()
                    category = (
                        "accomplishments"
                        if re.search(ACCOMPLISHMENT_PATTERN, text_content)
                        else "responsibilities"
                    )
                    bullets.append((category, text_content))
                elif bullets:
                    prev_category, prev_text = bullets[-1]
                    merged_text = f"{prev_text} {line}"
                    # A continuation line can be where the metric actually
                    # lands (e.g. "...backstage transition time by 30%"
                    # wraps to "(60s -> 42s)"), so re-check the category
                    # against the FULL merged text, not just the first line.
                    category = (
                        "accomplishments"
                        if re.search(ACCOMPLISHMENT_PATTERN, merged_text)
                        else prev_category
                    )
                    bullets[-1] = (category, merged_text)

            responsibilities = [t for cat, t in bullets if cat == "responsibilities"]
            accomplishments = [t for cat, t in bullets if cat == "accomplishments"]

            work_experience.append(
                WorkExperience(
                    employer=employer.strip(),
                    title=title,
                    dates=dates.strip(),
                    responsibilities=responsibilities,
                    accomplishments=accomplishments,
                    location=location.strip() if location else None,
                )
            )

        return work_experience

    # Labels resumes use for a skills-equivalent line that never contains the
    # literal word "skill" -- observed live (2026-09-22): a real resume
    # labeled this "Technical Proficiency" and "Core Competencies" instead,
    # under a generic "ADDITIONAL" heading, and the original section-only
    # detection below (which requires the word "skill" somewhere) returned
    # an empty list for it entirely.
    _INLINE_SKILL_LABELS = (
        "technical proficiency",
        "technical proficiencies",
        "core competencies",
        "areas of expertise",
        "key skills",
        "technical skills",
        "relevant skills",
        "competencies",
    )

    def _extract_skills(self, text: str) -> list[str]:
        """Extract technical skills from resume."""
        skills = []

        # Path 1: a dedicated "Skills" section.
        if "skills" in text.lower():
            skills_section = re.search(
                r"(?:technical\s+)?skills?[:]*\s*\n(.*?)(?:\n(?:TOOLS?|CERTIFICATIONS?|LANGUAGES?|EDUCATION|EXPERIENCE|WORK|[A-Z]{2,}[\s:]*$)|\Z)",
                text,
                re.IGNORECASE | re.DOTALL | re.MULTILINE,
            )
            if skills_section:
                items = skills_section.group(1)
                lines = items.split('\n')
                for line in lines:
                    if line.strip():
                        # Split each line by comma or colon (for "Languages: Python, Java, etc.")
                        line_items = re.split(r'[:,]', line)
                        for item in line_items:
                            clean_item = item.strip().lstrip('•-').strip()
                            if clean_item and len(clean_item) > 1:  # Skip single characters
                                skills.append(clean_item)

        # Path 2: an inline labeled line anywhere in the resume, e.g.
        # "Technical Proficiency: Tableau | Power BI | SQL" or
        # "Core Competencies: Strategic Thinker | Competitive Analysis",
        # which can wrap onto a following line with no repeated label.
        for label in self._INLINE_SKILL_LABELS:
            match = re.search(
                r"(?:^|\n)\s*[•\-]?\s*" + re.escape(label) + r"\s*:\s*(.+?)(?:\n\s*\n|\n[A-Z][A-Za-z ]*:|\n[A-Z]{2,}\s*$|\Z)",
                text,
                re.IGNORECASE | re.DOTALL,
            )
            if not match:
                continue
            captured = match.group(1)
            # The label's value can wrap onto the next physical line without
            # its own bullet marker -- treat the whole captured block as one
            # run of items rather than stopping at the first newline.
            for item in re.split(r"[|,\n]", captured):
                clean_item = item.strip().lstrip('•-').strip()
                if clean_item and len(clean_item) > 1:
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
        """Extract known tools/platforms mentioned in the resume."""
        known_tools = {
            "docker": "Docker",
            "kubernetes": "Kubernetes",
            "postgresql": "PostgreSQL",
            "mysql": "MySQL",
            "mongodb": "MongoDB",
            "redis": "Redis",
            "aws": "AWS",
            "azure": "Azure",
            "gcp": "GCP",
            "terraform": "Terraform",
            "jenkins": "Jenkins",
            "git": "Git",
            "jira": "Jira",
            "salesforce": "Salesforce",
            "tableau": "Tableau",
            "excel": "Excel",
        }
        found = []
        lower = text.lower()
        for token, label in known_tools.items():
            if re.search(r"\b" + re.escape(token) + r"\b", lower):
                found.append(label)
        return found

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
