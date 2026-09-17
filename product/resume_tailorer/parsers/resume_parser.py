from pathlib import Path
from typing import Optional
import re
from pypdf import PdfReader
from docx import Document

from resume_tailorer.models import CareerTruthProfile, WorkExperience, EducationEntry

class ResumeParser:
    """
    Parses PDF/DOCX resumes and extracts a CareerTruthProfile.
    Uses simple pattern matching and Claude API for ambiguous sections.
    """

    def parse(self, file_path: str) -> CareerTruthProfile:
        """Parse a resume file (PDF or DOCX) and return a CareerTruthProfile."""
        path = Path(file_path)

        if path.suffix.lower() == ".pdf":
            text = self._extract_text_from_pdf(file_path)
        elif path.suffix.lower() in [".docx", ".doc"]:
            text = self._extract_text_from_docx(file_path)
        else:
            raise ValueError(f"Unsupported file format: {path.suffix}")

        # Parse the extracted text into a CareerTruthProfile
        return self._parse_text(text)

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
        for line in lines[:5]:  # Check first 5 lines
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
                r"education[:]*\s*\n(.*?)(?:\n(?:TECHNICAL|SKILLS|WORK|EXPERIENCE|CERTIFICATIONS|$))",
                text,
                re.IGNORECASE | re.DOTALL
            )

            if edu_match:
                edu_section = edu_match.group(1)

                # Split education entries by looking for degree patterns at start of line
                entries = re.split(r'\n(?=[A-Z])', edu_section)

                for entry in entries:
                    if not entry.strip():
                        continue

                    lines = entry.strip().split('\n')

                    # First line should contain degree and field
                    degree_line = lines[0]

                    # Look for degree patterns: BS, MS, BA, MA, PhD, MBA
                    degree_match = re.search(
                        r"(B\.?S\.?|M\.?S\.?|B\.?A\.?|M\.?A\.?|Ph\.?D\.?|MBA)\s*(?:in|of|Computer)?\s*([^,\n|–—]*?)(?:\n|$)",
                        degree_line,
                        re.IGNORECASE
                    )

                    if degree_match:
                        degree = degree_match.group(1).strip()
                        field = degree_match.group(2).strip()

                        # Get institution and year from second line if available
                        institution = "Unknown"
                        year = None

                        if len(lines) > 1:
                            detail_line = lines[1]

                            # Extract year (4 digits)
                            year_match = re.search(r'(\d{4})', detail_line)
                            if year_match:
                                year = int(year_match.group(1))

                            # Extract institution (everything before year/pipe)
                            inst_match = re.search(r'^([^|–—\d]+?)(?:\s*[|–—]|\s*\d{4}|$)', detail_line)
                            if inst_match:
                                institution = inst_match.group(1).strip()

                        if year:
                            education.append(
                                EducationEntry(
                                    degree=degree,
                                    field=field,
                                    institution=institution,
                                    year=year,
                                )
                            )

        # Fallback: Look for patterns in full text
        if not education:
            patterns = [
                r"(B\.?S\.?|M\.?S\.?|B\.?A\.?|M\.?A\.?|Ph\.?D\.?|MBA)\s*(?:in|of)?\s*([^,\n]+)\s*(?:from|at)?\s*([^,\n]+?)(?:\s*,?\s*(\d{4}))?",
            ]

            for pattern in patterns:
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    degree = match.group(1)
                    field = match.group(2).strip()
                    institution = match.group(3).strip() if match.group(3) else "Unknown"
                    year = int(match.group(4)) if match.group(4) else None

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
                    if len(title_line) < 3 or title_line.startswith('•') or title_line.startswith('-'):
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
                            if re.search(r'\d+[%K$M]', text_content):
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
            # Simple heuristic: find the Skills section and extract comma-separated items
            skills_section = re.search(
                r"(?:skills?|technical\s+skills?)[:]*\s*\n(.*?)(?:\n\n|(?=[A-Z]\w+\s*[:]))",
                text,
                re.IGNORECASE | re.DOTALL,
            )
            if skills_section:
                items = skills_section.group(1)
                # Split by comma, newline, or bullet
                skills = [
                    s.strip() for s in re.split(r"[,•\n]", items) if s.strip()
                ][:20]  # Cap at 20 for MVP

        return skills

    def _extract_tools(self, text: str) -> list[str]:
        """Extract tools/technologies (databases, frameworks, etc.)."""
        # For MVP, we'll extract from skills section or mention in work experience
        return []

    def _extract_certifications(self, text: str) -> list[str]:
        """Extract certifications."""
        certifications = []
        # Look for patterns like "AWS Solutions Architect", "CPA", etc.
        patterns = [
            r"((?:AWS|Azure|Google Cloud|Kubernetes|Docker|Certified)\s+[^,\n]+)",
            r"(C[A-Z]{1,2}|PMP|CISSP|CCNA)\b",
        ]
        for pattern in patterns:
            for match in re.finditer(pattern, text):
                certifications.append(match.group(0).strip())

        return list(set(certifications))  # Deduplicate
