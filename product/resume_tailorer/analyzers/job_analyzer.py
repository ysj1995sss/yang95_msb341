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
    }

    def analyze(self, job_description: str) -> JobAnalysis:
        """Parse a job description and return a JobAnalysis."""
        # Extract sections
        required_qual = self._extract_section(job_description, r"(?:must|required|requirements?)[:\n]+(.*?)(?:\n\n|(?:[A-Za-z]+\s*:))", re.IGNORECASE | re.DOTALL)
        preferred_qual = self._extract_section(job_description, r"(?:preferred|nice.*?to.*?have)[:\n]+(.*?)(?:\n\n|(?:[A-Za-z]+\s*:))", re.IGNORECASE | re.DOTALL)
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

        section_text = match.group(1)
        # Split by bullets, newlines, semicolons
        items = re.split(r"[•\-\n;]", section_text)
        return [item.strip() for item in items if item.strip()]

    def _extract_responsibilities(self, text: str) -> list[str]:
        """Extract job responsibilities."""
        # Look for "Responsibilities" section
        resp_match = re.search(
            r"(?:responsibilities?|what you'll do)[:\n]+(.*?)(?:\n\n|(?:[A-Za-z]+\s*[:]))",
            text,
            re.IGNORECASE | re.DOTALL,
        )
        if resp_match:
            items = re.split(r"[•\-\n]", resp_match.group(1))
            return [item.strip() for item in items if item.strip()]
        return []

    def _extract_skills(self, text: str, required_section: list[str]) -> list[str]:
        """Extract technical skills mentioned in job description."""
        # Common programming languages and frameworks
        known_skills = {
            "python", "javascript", "typescript", "go", "rust", "java", "c++", "c#",
            "react", "vue", "angular", "node.js", "django", "flask", "fastapi",
            "sql", "nosql", "graphql", "rest", "api", "microservices",
            "aws", "azure", "gcp", "kubernetes", "docker", "terraform",
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
