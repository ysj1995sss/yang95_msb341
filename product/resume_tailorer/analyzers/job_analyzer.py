from dataclasses import dataclass, field
from typing import Optional
import re

from resume_tailorer.analyzers.competency_map import normalize_concept
from resume_tailorer.analyzers.jd_sections import PREFERRED, REQUIRED, RESPONSIBILITIES, split_sections
from resume_tailorer.utils.stemming import stem
from resume_tailorer.analyzers.term_match import mentions

@dataclass
class WeightedKeyword:
    """A keyword with its importance level."""
    keyword: str
    weight: str  # "high", "medium", "low"
    frequency: int = 1  # How many times mentioned

@dataclass
class JobRequirement:
    """
    A single structured requirement extracted from a job description.

    Added alongside the original flat string lists (required_qualifications,
    preferred_qualifications, responsibilities) rather than replacing them --
    every existing caller (GapAnalyzer, ResumeBenchmarker, the tailoring
    prompts) keeps working unchanged against those, while new/updated
    callers can consult the richer structured_requirements list instead.
    """
    id: str
    text: str  # the requirement item's own text, as extracted
    normalized_concept: str  # shared concept name (competency_map.normalize_concept)
    category: str  # "qualification" | "responsibility"
    required_or_preferred: str  # "required" | "preferred"
    importance: str  # "high" | "medium" | "low"
    hard_gate: bool  # true if failing this alone should be an honest, un-rewritable gap
    source_section: str  # "required_qualifications" | "preferred_qualifications" | "responsibilities"
    source_text: str  # the raw source-section text this item came from

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
    structured_requirements: list[JobRequirement] = field(default_factory=list)

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

    # A requirement matching one of these, in the REQUIRED section, is a
    # hard eligibility gate: failing it is an honest gap the tailoring
    # pipeline must never rewrite around (Step 12/13's "truly missing
    # requirements remain missing" principle). Deliberately narrow --
    # false positives here would wrongly mark a soft preference as
    # unwaivable; false negatives just fall back to ordinary importance
    # ranking, which is the safer failure direction.
    _HARD_GATE_PATTERNS = [
        # Non-greedy .*? between "years" and "experience" so a real posting's
        # "5+ years of marketing analytics experience" (arbitrary domain
        # words in between) still matches, not just "5+ years of experience"
        # verbatim -- found live testing this against a realistic JD.
        re.compile(r"\d+\+?\s*years?\s+(?:of\s+)?.{0,40}?\b(?:experience|exp)\b", re.IGNORECASE),
        re.compile(r"\bmust\s+(?:have|hold|possess|be\s+able)\b", re.IGNORECASE),
        # "Active CPA license", "valid state nursing license": up to three words in between.
        re.compile(r"\b(?:active|valid|current)\s+(?:[\w-]+\s+){0,3}(?:license|licensure|certification)\b", re.IGNORECASE),
        re.compile(r"\bauthoriz(?:ed|ation)\s+to\s+work\b", re.IGNORECASE),
        re.compile(r"\brequires?\s+a\s+(?:bachelor|master|phd|doctorate|degree)", re.IGNORECASE),
        re.compile(r"\b(?:bachelor|master|phd|doctorate)'?s?\s+degree\s+(?:is\s+)?required\b", re.IGNORECASE),
    ]

    # Generic filler with no real signal about candidate qualification --
    # downweighted to "low" importance unless it recurs (see
    # _rank_importance), so a job posting's boilerplate ("passion for our
    # mission") doesn't crowd out substantive requirements at the same
    # "high" tier just because it happened to land in the Required section.
    _GENERIC_FILLER_TERMS = {
        "passion", "dynamic", "fast-paced", "self-starter", "self starter",
        "detail-oriented", "detail oriented", "team player", "positive attitude",
        "work ethic", "hardworking", "go-getter", "multitasker", "flexible",
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
        #
        # Postings whose own heading lines can be classified are split by
        # those headings (jd_sections); the patterns below remain the
        # fallback for text with no recognizable headings.
        sections = split_sections(job_description)
        if sections is not None:
            required_qual = sections[REQUIRED]
            preferred_qual = sections[PREFERRED]
            responsibilities = sections[RESPONSIBILITIES]
        else:
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

        # Spec 011: a posting written as plain paragraphs, with no requirement headings at all,
        # still has requirement sentences ("You must have an active RN license"). Found only
        # when no required or preferred items were found the usual way.
        if not required_qual and not preferred_qual:
            required_qual, preferred_qual = sentence_requirements(job_description)

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

        structured_requirements = self._build_structured_requirements(
            required_qual, preferred_qual, responsibilities
        )

        return JobAnalysis(
            required_qualifications=required_qual,
            preferred_qualifications=preferred_qual,
            responsibilities=responsibilities,
            skills_required=skills,
            tools_required=tools,
            education_required=education,
            experience_required=experience,
            weighted_keywords=keywords,
            structured_requirements=structured_requirements,
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
            if mentions(skill, text):
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
            if mentions(tool, text):
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

    def _build_structured_requirements(
        self,
        required_qual: list[str],
        preferred_qual: list[str],
        responsibilities: list[str],
    ) -> list[JobRequirement]:
        """
        Build the structured JobRequirement model alongside the flat lists.

        Importance starts from the source section (required=high,
        preferred=medium, responsibilities=medium), is downgraded if the
        item is generic filler with no repeated emphasis, and is bumped
        back up one tier if its normalized_concept recurs elsewhere in the
        posting -- a requirement repeated across sections is a real signal
        of what the job actually cares about, not noise.
        """
        raw_items: list[tuple[str, str, str]] = (
            [(text, "required", "qualification") for text in required_qual]
            + [(text, "preferred", "qualification") for text in preferred_qual]
            + [(text, "required", "responsibility") for text in responsibilities]
        )

        # Count normalized-concept recurrence across the WHOLE posting
        # first, so an item's own importance can be bumped for being a
        # repeated theme regardless of which section it's in.
        concept_counts: dict[str, int] = {}
        concepts = [normalize_concept(text) for text, _, _ in raw_items]
        for concept in concepts:
            concept_counts[concept] = concept_counts.get(concept, 0) + 1

        requirements: list[JobRequirement] = []
        for idx, ((text, req_or_pref, category), concept) in enumerate(zip(raw_items, concepts)):
            source_section = (
                "required_qualifications" if (req_or_pref == "required" and category == "qualification")
                else "preferred_qualifications" if req_or_pref == "preferred"
                else "responsibilities"
            )
            requirements.append(JobRequirement(
                id=f"req-{idx}",
                text=text,
                normalized_concept=concept,
                category=category,
                required_or_preferred=req_or_pref,
                importance=self._rank_importance(text, req_or_pref, category, concept_counts[concept]),
                hard_gate=self._is_hard_gate(text, req_or_pref),
                source_section=source_section,
                source_text=text,
            ))
        return requirements

    def _is_hard_gate(self, text: str, required_or_preferred: str) -> bool:
        """A hard eligibility gate only ever applies to the required
        section -- a preferred item is, by definition, waivable."""
        if required_or_preferred != "required":
            return False
        return any(pattern.search(text) for pattern in self._HARD_GATE_PATTERNS)

    def _rank_importance(
        self, text: str, required_or_preferred: str, category: str, concept_frequency: int
    ) -> str:
        """Rank a single requirement's importance. See
        _build_structured_requirements for the recurrence-bump rule."""
        text_lower = text.lower()
        is_filler = any(term in text_lower for term in self._GENERIC_FILLER_TERMS)

        if is_filler and concept_frequency < 2:
            base = "low"
        elif required_or_preferred == "required":
            base = "high"
        else:
            base = "medium"

        if concept_frequency >= 2:
            order = ["low", "medium", "high"]
            bumped = min(order.index(base) + 1, len(order) - 1)
            return order[bumped]
        return base


# --- Requirement sentences in postings without headings (spec 011) ----------------------------

_REQUIREMENT_CUES = re.compile(
    r"\b(?:must|required|requires|requirements?|need to have|you have|you'?ll have|you bring|"
    r"experience (?:with|in|using|managing|leading)|proficien(?:t|cy) (?:in|with)|knowledge of|"
    r"familiar(?:ity)? with|expertise in|ability to|skilled in|"
    r"\d+\s*\+?\s*(?:-\s*\d+\s*)?years?|degree|license[ds]?|licensure|certifi(?:ed|cation)|bachelor|master'?s|"
    r"preferred|a plus|nice to have|bonus|desired|ideally)\b",
    re.IGNORECASE,
)
_PREFERRED_CUES = re.compile(
    r"\b(?:preferred|is a plus|a plus|nice to have|bonus|ideally|desired|an advantage|helpful)\b", re.IGNORECASE)
_NOT_REQUIREMENTS = re.compile(
    r"equal (?:employment )?opportunit|benefits?\b|we offer|pay range|salary|compensation|401\(?k|"
    r"paid time off|pto\b|reasonable accommodation|e-verify|privacy",
    re.IGNORECASE,
)
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?;])\s+|\n+|\s+[•▪◦]\s+")


def sentence_requirements(text: str) -> tuple[list[str], list[str]]:
    """(required, preferred) requirement sentences from a posting without requirement headings.
    Each sentence is classified by its own wording ("a plus", "preferred" mean preferred)."""
    required: list[str] = []
    preferred: list[str] = []
    for raw in _SENTENCE_SPLIT.split(text or ""):
        sentence = re.sub(r"^\s*(?:[-*•▪◦]|\d+[.)])\s*", "", raw).strip()
        if len(sentence.split()) < 3 or len(sentence) > 300:
            continue
        if _NOT_REQUIREMENTS.search(sentence) or not _REQUIREMENT_CUES.search(sentence):
            continue
        if re.match(r"(?i)^(?:you will|you'll|in this role|responsibilities)\b", sentence):
            continue  # what the job does, not what it asks of the candidate
        (preferred if _PREFERRED_CUES.search(sentence) else required).append(sentence.rstrip("."))
    return required, preferred
