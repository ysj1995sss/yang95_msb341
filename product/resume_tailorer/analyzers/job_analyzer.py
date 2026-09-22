from dataclasses import dataclass, field
from typing import Optional
import re

@dataclass
class WeightedKeyword:
    """A keyword with its importance level."""
    keyword: str
    weight: str  # "high", "medium", "low"
    frequency: int = 1  # How many times mentioned

@dataclass
class JobAnalysis:
    """Analysis of a job description."""
    required_qualifications: list[str]
    preferred_qualifications: list[str]
    responsibilities: list[str]
    skills_required: list[str]
    tools_required: list[str]
    education_required: Optional[str]
    experience_required: Optional[str]
    weighted_keywords: list[WeightedKeyword]

class JobAnalyzer:
    """
    Analyzes job descriptions to extract requirements, skills, tools,
    and weighted keywords.

    For MVP, uses regex and heuristics; future versions will use Claude API
    for more nuanced analysis.
    """

    # Common stopwords excluded from the non-technical fallback keyword
    # extraction (see _extract_fallback_keywords). Not exhaustive -- just
    # enough to keep the fallback list meaningful rather than noise.
    _FALLBACK_STOPWORDS = {
        "about", "above", "after", "again", "against", "because", "before",
        "being", "below", "between", "candidate", "could", "during", "each",
        "experience", "further", "having", "other", "overall", "please",
        "responsibilities", "should", "strong", "their", "there", "these",
        "those", "through", "where", "which", "while", "would", "years",
        "you'll", "your", "ability", "looking", "working", "within",
        "across", "various", "ensure", "ensuring", "including", "include",
        "position", "opportunity", "team", "teams", "role", "roles",
        "company", "someone",
        # Added after a real posting (2026-09-22) phrased in full sentences
        # rather than short bullet fragments: the fallback was picking up
        # ordinary grammatical filler as if it were a skill -- "Earned" and
        # "degree" both ended up as separate "requirements," and "degree"
        # was then flagged "truly missing" despite the candidate obviously
        # having one. This isn't about recognizing more skills; it's about
        # not inventing fake ones out of sentence structure.
        "earned", "degree", "degrees", "preferably", "specializations",
        "specialization", "relevant", "full-time", "part-time", "demonstrated",
        "translating", "guide", "recommendations", "one", "two", "three",
        "four", "five", "six", "seven", "eight", "nine", "ten",
    }

    def analyze(self, job_description: str) -> JobAnalysis:
        """Parse a job description and return a JobAnalysis."""
        # Normalize Unicode "smart" punctuation to ASCII. Found live
        # (2026-09-22): a real job posting's "What you'll do:" used a
        # Unicode right single quote (U+2019) in "you'll", which silently
        # failed to match this module's ASCII-apostrophe regex below. With
        # required/preferred/responsibilities all consequently empty, there
        # was nothing left for even the fallback keyword extractor to work
        # from, producing a completely empty JobAnalysis and a 0% match
        # score despite the resume itself being parsed correctly.
        job_description = (
            job_description.replace("’", "'")
            .replace("‘", "'")
            .replace("“", '"')
            .replace("”", '"')
        )

        # Extract sections. Beyond formal "Required:"/"Preferred:" headings,
        # real postings (especially non-technical ones) often use
        # conversational phrasing instead -- "What you'll need", "What
        # you're bringing", "Qualifications" -- also found live (2026-09-22)
        # on a real marketing job posting that used none of the original
        # formal headings at all.
        #
        # SECTION_END stops at the next section heading (a capitalized
        # phrase ending in ":") rather than at every blank line. The
        # previous boundary (any "\n\n") truncated a section after its
        # FIRST paragraph on postings that separate every sentence with a
        # blank line instead of using bullet markers -- also found live on
        # the same real posting, which had five separate "What you'll
        # need" paragraphs and lost four of them to this exact bug.
        section_end = r"(?:\n\n(?=[A-Z][A-Za-z' ]*:)|\Z)"
        required_qual = self._extract_section(
            job_description,
            r"(?:must|required|requirements?|what you'll need|what we're looking for|qualifications)[:\n]+(.*?)"
            + section_end,
            re.IGNORECASE | re.DOTALL,
        )
        preferred_qual = self._extract_section(
            job_description,
            r"(?:preferred|nice.*?to.*?have|what you'll bring|what you bring)[:\n]+(.*?)" + section_end,
            re.IGNORECASE | re.DOTALL,
        )
        responsibilities = self._extract_responsibilities(job_description)

        # Extract skills and tools
        skills = self._extract_skills(job_description, required_qual)
        tools = self._extract_tools(job_description)

        # Non-technical job descriptions (marketing, sales, etc.) won't
        # match the software-only whitelist above. Rather than let both
        # lists come back empty -- which cascades into a degenerate 0%
        # keyword-alignment score downstream -- fall back to extracting
        # significant keywords directly from the requirements/responsibilities
        # text. The whitelist stays the primary/preferred path for technical
        # jobs; this only kicks in when it yields nothing.
        if not skills and not tools:
            skills = self._extract_fallback_keywords(
                required_qual, preferred_qual, responsibilities
            )

        # Extract education and experience requirements
        education = self._extract_education_requirement(job_description)
        experience = self._extract_experience_requirement(job_description)

        # Generate weighted keywords
        keywords = self._extract_weighted_keywords(job_description, required_qual, preferred_qual)

        return JobAnalysis(
            required_qualifications=required_qual,
            preferred_qualifications=preferred_qual,
            responsibilities=responsibilities,
            skills_required=skills,
            tools_required=tools,
            education_required=education,
            experience_required=experience,
            weighted_keywords=keywords,
        )

    def _extract_section(self, text: str, pattern: str, flags: int = 0) -> list[str]:
        """Extract a section from job description and return as list of items."""
        match = re.search(pattern, text, flags)
        if not match:
            return []
        return self._split_section_items(match.group(1))

    def _split_section_items(self, section_text: str) -> list[str]:
        """
        Split a captured section into individual items, one per line, only
        stripping a LEADING bullet marker from each line.

        Splitting on every "-" or ";" anywhere in the text (the previous
        approach) broke mid-sentence on ordinary hyphenated words
        ("full-time", "cross-functional") and semicolons -- found live
        (2026-09-22) on a real job posting whose "requirements" were plain
        blank-line-separated sentences with no bullet markers at all, where
        that splitting fragmented single sentences into nonsense pieces at
        every internal hyphen.
        """
        items = []
        for line in section_text.split("\n"):
            cleaned = line.strip()
            if not cleaned:
                continue
            cleaned = re.sub(r"^[•\-]\s+", "", cleaned)
            if cleaned:
                items.append(cleaned)
        return items

    def _extract_responsibilities(self, text: str) -> list[str]:
        """Extract job responsibilities."""
        # Look for "Responsibilities" section
        resp_match = re.search(
            r"(?:responsibilities?|what you'll do)[:\n]+(.*?)(?:\n\n(?=[A-Z][A-Za-z' ]*:)|\Z)",
            text,
            re.IGNORECASE | re.DOTALL,
        )
        if resp_match:
            return self._split_section_items(resp_match.group(1))
        return []

    def _extract_skills(self, text: str, required_section: list[str]) -> list[str]:
        """Extract technical skills mentioned in job description.

        "kubernetes", "docker", and "terraform" are deliberately excluded here
        even though they're common JD keywords: they're also in
        _extract_tools's known_tools set, and skills_required + tools_required
        get concatenated downstream (ResumeBenchmarker, GapAnalyzer,
        ResumeTailoringOptimizer) to score keyword alignment. Keeping them in
        both sets double-counted them -- inflating "missing" lists with
        duplicates and skewing the alignment score's denominator. Tools are
        the more natural home for infrastructure/platform keywords, so
        skills keeps languages, frameworks, and practices only.
        """
        known_skills = {
            "python", "javascript", "typescript", "go", "rust", "java", "c++", "c#",
            "react", "vue", "angular", "node.js", "django", "flask", "fastapi",
            "sql", "nosql", "graphql", "rest", "api", "microservices",
            "aws", "azure", "gcp",
            "agile", "scrum", "git", "ci/cd", "devops",
        }

        found_skills = []
        text_lower = text.lower()

        for skill in known_skills:
            if re.search(r"\b" + re.escape(skill) + r"\b", text_lower):
                found_skills.append(skill.title())

        return found_skills

    def _extract_tools(self, text: str) -> list[str]:
        """Extract tools/platforms (databases, CI/CD, etc.)."""
        known_tools = {
            "postgresql", "mysql", "mongodb", "redis", "elasticsearch",
            "jenkins", "gitlab", "github", "docker", "kubernetes",
            "aws s3", "datadog", "newrelic", "terraform",
        }

        found_tools = []
        text_lower = text.lower()

        for tool in known_tools:
            if re.search(r"\b" + re.escape(tool) + r"\b", text_lower):
                found_tools.append(tool.title())

        return found_tools

    def _extract_fallback_keywords(
        self,
        required_qual: list[str],
        preferred_qual: list[str],
        responsibilities: list[str],
        limit: int = 15,
    ) -> list[str]:
        """
        Fallback keyword extraction for job descriptions that don't use any
        of the hardcoded software-skill whitelist (e.g. marketing, sales,
        non-technical roles).

        Pulls significant words (longer than 4 characters, i.e. 5+ chars,
        minus common stopwords) directly out of the required/preferred
        qualifications and responsibilities sections, deduplicated and
        capped at `limit`, so downstream keyword-alignment scoring has a
        meaningful, non-empty target set instead of collapsing to 0%.
        """
        combined_text = " ".join(required_qual + preferred_qual + responsibilities)
        words = re.findall(r"\b[A-Za-z][A-Za-z\-]{4,}\b", combined_text)

        found = []
        seen_lower = set()
        for word in words:
            cleaned = word.strip("-")
            lower = cleaned.lower()
            if not cleaned or lower in self._FALLBACK_STOPWORDS or lower in seen_lower:
                continue
            seen_lower.add(lower)
            found.append(cleaned)
            if len(found) >= limit:
                break

        return found

    def _extract_education_requirement(self, text: str) -> Optional[str]:
        """Extract education requirement (e.g., 'BS in Computer Science')."""
        match = re.search(r"(b\.?s\.?|m\.?s\.?|b\.?a\.?|m\.?a\.?|phd?|diploma)\s+in\s+([^,\n]+)", text, re.IGNORECASE)
        if match:
            return match.group(0)
        return None

    def _extract_experience_requirement(self, text: str) -> Optional[str]:
        """Extract experience requirement (e.g., '5+ years')."""
        match = re.search(r"(\d+)\+?\s*years?\s+(?:of\s+)?([^,\n]*)", text, re.IGNORECASE)
        if match:
            return match.group(0)
        return None

    def _extract_weighted_keywords(self, text: str, required: list[str], preferred: list[str]) -> list[WeightedKeyword]:
        """Extract keywords and assign weights (high/medium/low)."""
        keywords = {}

        # High-weight: mentioned in required section
        for req in required:
            words = req.lower().split()
            for word in words:
                if len(word) > 3:  # Skip small words
                    if word not in keywords:
                        keywords[word] = WeightedKeyword(keyword=word, weight="high", frequency=1)
                    else:
                        keywords[word].frequency += 1

        # Medium-weight: mentioned in preferred section
        for pref in preferred:
            words = pref.lower().split()
            for word in words:
                if len(word) > 3 and word not in keywords:
                    keywords[word] = WeightedKeyword(keyword=word, weight="medium")

        # High-weight: if mentioned multiple times
        text_lower = text.lower()
        for keyword in list(keywords.keys()):
            count = len(re.findall(r"\b" + re.escape(keyword) + r"\b", text_lower))
            if count > 2:
                keywords[keyword].weight = "high"
                keywords[keyword].frequency = count

        return list(keywords.values())[:30]  # Return top 30 keywords
