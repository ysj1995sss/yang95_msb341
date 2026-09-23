from pathlib import Path
from typing import Optional
import re
from pypdf import PdfReader
from docx import Document

from resume_tailorer.models import CareerTruthProfile, WorkExperience, EducationEntry
from resume_tailorer.parsers.anchor_detection import find_anchor_blocks
from resume_tailorer.parsers.section_headings import SECTION_BOUNDARY_RE
from resume_tailorer.parsers.docx_structure import is_bullet_paragraph

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
        """
        Extract text from a DOCX file.

        A real Word bullet/numbered-list paragraph never has a literal
        "•"/"-" character in its own text -- Word draws the bullet glyph
        from the numbering definition, not the run text (confirmed by
        direct inspection of a real resume, 2026-09-22). The regex-based
        extraction below (_extract_work_experience et al.) only recognizes
        a line as a bullet when it's PREFIXED with "•"/"-", so a DOCX with
        real Word list formatting was silently losing every bullet before
        this fix -- either dropped entirely or merged as a "continuation
        line" onto whatever text preceded it. Prefixing here, once, keeps
        that regex-based extraction working unchanged for both PDF- and
        DOCX-sourced text.
        """
        doc = Document(file_path)
        lines = [
            f"- {para.text}" if is_bullet_paragraph(para) else para.text for para in doc.paragraphs
        ]
        return "\n".join(lines)

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

        # Extract the professional summary paragraph, if there is one --
        # found missing live (2026-09-22): a real resume's 3-sentence
        # summary under the name was silently dropped because
        # CareerTruthProfile had nowhere to put it at all.
        summary = self._extract_summary(text)

        return CareerTruthProfile(
            contact_info=contact_info,
            education=education,
            work_experience=work_experience,
            skills=skills,
            tools=tools,
            certifications=certifications,
            accomplishments=[],  # Will be extracted from work_experience
            summary=summary,
        )

    # Shared with the DOCX structural walker (parsers/section_headings.py) so
    # both formats agree on where a section ends.
    _SUMMARY_STOP_HEADINGS = SECTION_BOUNDARY_RE

    def _extract_summary(self, text: str) -> str:
        """
        Extract a professional-summary paragraph: the free text between the
        contact info block and the first recognized section heading.

        Skips the name line (short, near the top) and any line that looks
        like contact info (email, phone, URL) rather than prose.
        """
        lines = text.split("\n")
        start_idx = None
        end_idx = None

        for i, raw_line in enumerate(lines):
            line = raw_line.strip()
            if not line:
                continue
            if self._SUMMARY_STOP_HEADINGS.match(line):
                end_idx = i
                break
            looks_like_contact = (
                "@" in line
                or "http" in line.lower()
                or "linkedin" in line.lower()
                or re.search(r"\d{3}[-.\s]?\d{3}[-.\s]?\d{4}", line)
            )
            if looks_like_contact:
                continue
            if start_idx is None and i < NAME_SEARCH_LINES and len(line.split()) <= 6:
                # Short line near the top before any real prose -- almost
                # certainly the name, not the summary.
                continue
            if start_idx is None:
                start_idx = i

        if start_idx is not None and end_idx is not None and start_idx < end_idx:
            summary_lines = [lines[i].strip() for i in range(start_idx, end_idx) if lines[i].strip()]
            return " ".join(summary_lines)
        return ""

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
        """
        Extract education entries, anchored on each "Institution | Location
        Dates" line (contains a year, not a bullet) -- mirroring the fix
        applied to _extract_work_experience for the same reason: the
        previous per-entry splitter (looking for lines starting with a
        degree abbreviation) silently dropped a second degree entirely and
        discarded every bullet underneath each entry (scholarships, notable
        coursework) -- found live (2026-09-22) on a real two-degree resume
        where the MBA in progress vanished completely and a work-experience
        bullet ended up misfiled under Education.
        """
        education = []

        if "education" not in text.lower():
            return education

        edu_match = re.search(
            r"education[:]*\s*\n(.*?)(?:\n(?:TECHNICAL|SKILLS|WORK|EXPERIENCE|PROFESSIONAL|"
            r"CERTIFICATIONS|ADDITIONAL|[A-Z]{2,}[\s:]*$))",
            text,
            re.IGNORECASE | re.DOTALL | re.MULTILINE,
        )
        if not edu_match:
            return education

        lines = edu_match.group(1).split("\n")

        anchor_idxs = [
            i
            for i, line in enumerate(lines)
            if self._YEAR_PATTERN.search(line) and not line.strip().startswith(("•", "-"))
        ]

        for a, idx in enumerate(anchor_idxs):
            institution_line = lines[idx].strip()
            parts = re.split(r"\s*\|\s*", institution_line)
            institution = parts[0].strip() if parts and parts[0].strip() else "Unknown"

            years = [int(y) for y in re.findall(r"(?:19|20)\d{2}", institution_line)]
            year = years[-1] if years else None  # last year on the line = graduation/end year
            if not year:
                continue

            end_idx = anchor_idxs[a + 1] if a + 1 < len(anchor_idxs) else len(lines)

            # The degree is the next non-blank line after the institution
            # line, as long as it isn't a bullet.
            degree_text = ""
            after_degree_idx = idx + 1
            for j in range(idx + 1, end_idx):
                candidate = lines[j].strip()
                if not candidate:
                    continue
                if not candidate.startswith(("•", "-")):
                    degree_text = candidate
                    after_degree_idx = j + 1
                break

            # MBA/PhD tried before the shorter B.S./M.A.-style patterns, and
            # a negative lookahead blocks a mid-word false match (e.g.
            # "M.?A.?" was matching "Ma" inside "Master" before falling
            # through to the fallback below).
            degree_match = re.search(
                r"\b(MBA|Ph\.?D\.?|B\.?S\.?|M\.?S\.?|B\.?A\.?|M\.?A\.?)(?![a-zA-Z])\s*(.*)",
                degree_text,
                re.IGNORECASE,
            )
            if degree_match:
                degree = degree_match.group(1).strip()
                field = degree_match.group(2).strip()
            else:
                degree = degree_text
                field = ""

            notes = [
                lines[j].strip().lstrip("•-").strip()
                for j in range(after_degree_idx, end_idx)
                if lines[j].strip().startswith(("•", "-"))
            ]

            education.append(
                EducationEntry(
                    degree=degree,
                    field=field,
                    institution=institution,
                    year=year,
                    notes=notes,
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

        # "employment" alternative added alongside "EMPLOYMENT" heading
        # support (2026-09-23) -- a resume titling its whole section
        # "EMPLOYMENT" with no literal word "experience" anywhere would
        # otherwise never reach the regex below at all.
        if "experience" not in text.lower() and "employment" not in text.lower():
            return work_experience

        # "ADDITIONAL" added after a real resume (2026-09-22) put its
        # Technical Proficiency / Certificates / Core Competencies lines
        # under an "ADDITIONAL" heading with no year in it, right after the
        # last job -- since that heading wasn't a recognized boundary, those
        # lines had no anchor to stop at and got swallowed as trailing
        # bullets of the last job, duplicating the same content that
        # _extract_skills also (correctly) pulls out separately.
        exp_match = re.search(
            r"(?:(?:work|professional)\s+experience|experience|employment)[:]*\s*\n(.*?)"
            r"(?:\n(?:EDUCATION|TECHNICAL|SKILLS|CERTIFICATIONS|ADDITIONAL|$))",
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
        # and losing every bullet for that job. This anchor/title/body
        # detection is shared with the DOCX structural walker (see
        # anchor_detection.find_anchor_blocks) so the same algorithm never
        # drifts between the two formats.
        is_bullet_line = lambda line: line.strip().startswith(("•", "-"))
        blocks = find_anchor_blocks(lines, get_text=lambda line: line, is_bullet=is_bullet_line)

        for block in blocks:
            idx = block.anchor_index
            company_line = lines[idx].strip()

            title_line = lines[block.title_index].strip() if block.title_index is not None else ""
            if not title_line or len(title_line) < MIN_TITLE_LENGTH:
                continue
            title = title_line.replace("<b>", "").replace("</b>", "")

            parts = re.split(r"\s*(?:\||—|–)\s*", company_line)
            employer = parts[0] if parts else "Unknown"
            location = parts[1] if len(parts) > 1 else ""
            dates = parts[2] if len(parts) > 2 else ""

            bullet_lines = [lines[i] for i in block.body_indices]

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
            # The stop lookahead must tolerate an optional bullet marker
            # before the next label (e.g. "\n• Certificates: ...") --
            # without it, a bare "\n[A-Z]" check never matches a bulleted
            # next line, so one label's capture silently swallows every
            # subsequent labeled line all the way to end of document
            # (found live 2026-09-22: "Technical Proficiency: ...SQL"
            # swallowed the following "Certificates:" and "Core
            # Competencies:" lines whole, producing a malformed skill like
            # "Certificates: Prompt Engineering" instead of splitting it).
            match = re.search(
                r"(?:^|\n)\s*[•\-]?\s*" + re.escape(label) + r"\s*:\s*(.+?)(?:\n\s*\n|\n\s*[•\-]?\s*[A-Z][A-Za-z ]*:|\n[A-Z]{2,}\s*$|\Z)",
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

    # A font whose PDF /BaseFont name matches one of these (case/space/hyphen
    # -insensitive) is classified serif or sans-serif. Mapped to the closest
    # ATS-safe base-14 equivalent (Times-Roman / Helvetica) rather than
    # embedding the literal font file: embedding ties the output to whatever
    # happens to be installed on one developer's machine, which isn't
    # portable to a deployed server, and the entire point of restricting to
    # base-14 fonts is guaranteed ATS-parser compatibility -- an unusual
    # embedded font is exactly the kind of thing that can break parsing.
    # Serif vs. sans-serif is the single most visually significant
    # distinction between resume fonts, so this gets most of the visual
    # similarity a user asks for without that portability/safety risk.
    _SERIF_FONT_NAMES = {
        "timesnewroman", "times", "georgia", "cambria", "garamond",
        "bookantiqua", "palatino", "minionpro", "cardo", "cambriamath",
    }
    _SANS_SERIF_FONT_NAMES = {
        "arial", "calibri", "helvetica", "segoeui", "verdana", "tahoma",
        "trebuchetms", "centurygothic", "opensans", "lato", "roboto",
        "arialnarrow", "franklingothic",
    }

    _TF_OPERATOR = re.compile(r"(/F\d+)\s+[\d.]+\s+Tf")
    _TEXT_SHOW_OPERATOR = re.compile(r"\)\s*Tj|\]\s*TJ")

    def _dominant_font_name(self, page) -> str | None:
        """
        Find the /BaseFont name actually used for the most VISIBLE TEXT on
        a page, rather than just the first entry in /Resources/Font -- a
        PDF writer can register a font it never actually draws with
        (reportlab always pre-registers Helvetica this way, even when the
        visible text uses Times-Roman), so picking the first one found
        silently picks the wrong font.

        A font selected via "/F1 12 Tf" stays the active font for any text
        drawn afterward until the next Tf, even across separate BT/ET
        blocks (PDF text state persists in the graphics state) -- so simply
        counting how many times each font is named in "Tf" operators is
        misleading when a writer names two fonts once each in adjacent
        blocks but only draws text with the second. This instead walks the
        content stream in order and, for each text-showing operator (Tj or
        TJ), attributes it to whichever font was most recently selected.
        """
        resources = page.get("/Resources") or {}
        fonts = resources.get("/Font")
        if not fonts:
            return None

        font_names: dict[str, str] = {}
        for key, font_ref in fonts.items():
            try:
                font_obj = font_ref.get_object()
                font_names[key] = str(font_obj.get("/BaseFont", ""))
            except Exception:
                continue
        if not font_names:
            return None
        if len(font_names) == 1:
            return next(iter(font_names.values()))

        # page.get_contents() wraps the stream in a fresh pypdf ContentStream,
        # whose own get_data() reliably came back empty in testing (2026-09-22)
        # even on a freshly-opened reader. Reading the /Contents stream
        # object's get_data() directly -- the same call ContentStream itself
        # ends up making internally -- returns the real bytes every time, so
        # this bypasses ContentStream rather than retrying it.
        contents_ref = page.get("/Contents")
        if contents_ref is None:
            return next(iter(font_names.values()), None)
        resolved = contents_ref.get_object()
        try:
            if isinstance(resolved, list):
                raw = "\n".join(
                    s.get_object().get_data().decode("latin-1", errors="ignore")
                    for s in resolved
                )
            else:
                raw = resolved.get_data().decode("latin-1", errors="ignore")
        except Exception:
            raw = ""

        tf_positions = [(m.start(), m.group(1)) for m in self._TF_OPERATOR.finditer(raw)]
        usage_counts: dict[str, int] = {}
        current_font = None
        tf_idx = 0
        for show_match in self._TEXT_SHOW_OPERATOR.finditer(raw):
            show_pos = show_match.start()
            while tf_idx < len(tf_positions) and tf_positions[tf_idx][0] < show_pos:
                current_font = tf_positions[tf_idx][1]
                tf_idx += 1
            if current_font and current_font in font_names:
                usage_counts[current_font] = usage_counts.get(current_font, 0) + 1

        if not usage_counts:
            return next(iter(font_names.values()))
        dominant_key = max(usage_counts, key=usage_counts.get)
        return font_names[dominant_key]

    def _detect_pdf_style(self, file_path: str) -> dict:
        """
        Detect the original PDF's page count and font family, from the
        actual PDF file (not just its extracted text) -- used so a tailored
        resume can be generated in a similar style and length to what the
        user actually uploaded, instead of always defaulting to Helvetica
        and a fixed page-length preset regardless of the source.
        """
        try:
            reader = PdfReader(file_path)
        except Exception:
            return {}

        result: dict = {"page_count": len(reader.pages)}

        try:
            if reader.pages:
                base_font = self._dominant_font_name(reader.pages[0])
                if base_font:
                    name = base_font.split("+", 1)[-1].lower().replace(" ", "").replace("-", "")
                    if any(s in name for s in self._SERIF_FONT_NAMES):
                        result["font_family"] = "serif"
                    elif any(s in name for s in self._SANS_SERIF_FONT_NAMES):
                        result["font_family"] = "sans-serif"
        except Exception:
            pass

        return result

    def extract_style_hints(self, raw_text: str, file_path: str | None = None) -> dict:
        """
        Extract lightweight visual style hints from the original resume,
        used later to make the tailored PDF resemble the source resume's
        bullet style, heading emphasis, font family, and length.

        Args:
            raw_text: The original resume's extracted plain text.
            file_path: Optional path to the original PDF file. When given,
                also detects page count and font family directly from the
                PDF's own structure (not derivable from text alone).

        Returns:
            Dict with keys:
                "bullet_char": most common bullet marker found ("•", "-", "*"),
                    defaulting to "•" if none detected.
                "heading_style": "bold_larger" if a short (<30 char) ALL-CAPS
                    line is found (suggesting a large/bold heading font in
                    the original), else "bold".
                "page_count" (only if file_path given): the original PDF's
                    page count.
                "font_family" (only if file_path given and detected):
                    "serif" or "sans-serif".
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

        hints = {
            "bullet_char": dominant_bullet,
            "heading_style": heading_style,
        }
        if file_path:
            hints.update(self._detect_pdf_style(file_path))
        return hints

    # Same rationale as _INLINE_SKILL_LABELS: a resume can list certificates
    # under an inline "Certificates:"/"Certifications:" line (observed live
    # 2026-09-22, under an "ADDITIONAL" heading alongside Technical
    # Proficiency and Core Competencies lines) rather than a dedicated
    # section or a name matching the acronym allowlist below.
    _INLINE_CERT_LABELS = ("certificates", "certifications")

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

        for label in self._INLINE_CERT_LABELS:
            match = re.search(
                r"(?:^|\n)\s*[•\-]?\s*" + re.escape(label) + r"\s*:\s*(.+?)(?:\n\s*\n|\n\s*[•\-]?\s*[A-Z][A-Za-z ]*:|\n[A-Z]{2,}\s*$|\Z)",
                text,
                re.IGNORECASE | re.DOTALL,
            )
            if not match:
                continue
            for item in re.split(r"[|,\n]", match.group(1)):
                clean_item = item.strip().lstrip("•-").strip()
                if clean_item and len(clean_item) > 1:
                    certifications.append(clean_item)

        return list(set(certifications))  # Deduplicate
