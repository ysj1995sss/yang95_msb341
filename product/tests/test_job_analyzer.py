import pytest
from resume_tailorer.analyzers.job_analyzer import JobAnalyzer, JobAnalysis

@pytest.fixture
def sample_job_description():
    return """
    Senior Software Engineer - Full Stack

    Requirements:
    - 5+ years of software engineering experience
    - Strong proficiency in Python and Go
    - Experience with Kubernetes and Docker
    - Familiarity with PostgreSQL or similar databases
    - Experience with microservices architecture

    Preferred:
    - Experience with AWS
    - Prior startup experience
    - Open source contributions

    Responsibilities:
    - Design and build scalable APIs
    - Mentor junior engineers
    - Participate in code reviews
    - Contribute to system architecture decisions

    We're looking for someone who can own projects end-to-end.
    """

def test_job_analyzer_extracts_requirements(sample_job_description):
    """Analyzer extracts required qualifications."""
    analyzer = JobAnalyzer()
    analysis = analyzer.analyze(sample_job_description)

    assert isinstance(analysis, JobAnalysis)
    assert "python" in [s.lower() for s in analysis.skills_required]
    assert "5+ years" in str(analysis.required_qualifications) or "5 years" in sample_job_description

def test_job_analyzer_extracts_preferred(sample_job_description):
    """Analyzer extracts preferred qualifications."""
    analyzer = JobAnalyzer()
    analysis = analyzer.analyze(sample_job_description)

    assert len(analysis.preferred_qualifications) > 0

def test_job_analyzer_identifies_weighted_keywords(sample_job_description):
    """Analyzer identifies keywords and weights them (high/medium/low)."""
    analyzer = JobAnalyzer()
    analysis = analyzer.analyze(sample_job_description)

    assert len(analysis.weighted_keywords) > 0
    # Keywords should include both hard skills and soft skills


def test_job_analyzer_skills_and_tools_do_not_overlap(sample_job_description):
    """
    skills_required and tools_required get concatenated downstream
    (ResumeBenchmarker, GapAnalyzer, ResumeTailoringOptimizer) to score
    keyword alignment. A keyword in both lists (previously "kubernetes",
    "docker", "terraform" were in both known_skills and known_tools) gets
    double-counted -- inflating "missing" lists with duplicates and
    skewing the alignment score's denominator.
    """
    analyzer = JobAnalyzer()
    analysis = analyzer.analyze(sample_job_description)

    skills_lower = {s.lower() for s in analysis.skills_required}
    tools_lower = {t.lower() for t in analysis.tools_required}
    assert not (skills_lower & tools_lower), (
        f"skills_required and tools_required overlap: {skills_lower & tools_lower}"
    )
    # Kubernetes and Docker are both in the sample JD -- confirm they still
    # get extracted somewhere, just not in both lists.
    assert "kubernetes" in tools_lower
    assert "docker" in tools_lower


class TestConversationalNonTechnicalPosting:
    """
    Regression tests for a real, non-technical job posting (2026-09-22)
    that broke every section-extraction assumption at once: headings were
    conversational ("What you'll need" instead of "Required"), apostrophes
    were Unicode curly quotes (U+2019) instead of ASCII, requirements were
    plain blank-line-separated sentences with no bullet markers, and
    several sentences contained ordinary hyphenated words. The analyzer
    produced a completely empty JobAnalysis, which cascaded into a 0%
    match score even though the candidate's resume was parsed correctly.
    """

    REAL_STYLE_POSTING = (
        "What you'll do:\n\n"
        "Broad strategic marketing exposure across a large, complex business.\n\n"
        "Hands-on ownership of work tied to real customer, brand, and growth priorities.\n\n"
        "What you'll bring:\n\n"
        "Strategic marketing leader who turns strategy into execution.\n\n"
        "Data-informed problem solver who uses insights to drive decisions.\n\n"
        "What you'll need:\n\n"
        "Earned Masters/MBA degree by June 2027, preferably in Marketing or Business.\n\n"
        "Two to seven years of relevant full-time work experience in marketing, business, "
        "consulting, and cross-functional execution.\n\n"
        "Experience leading cross-functional projects and translating strategy into execution.\n"
    ).replace("'", "’")  # Unicode right single quote, matching the real posting.

    def test_conversational_headings_are_recognized(self):
        analysis = JobAnalyzer().analyze(self.REAL_STYLE_POSTING)
        assert len(analysis.required_qualifications) > 0
        assert len(analysis.preferred_qualifications) > 0
        assert len(analysis.responsibilities) > 0

    def test_all_paragraphs_in_a_section_are_captured_not_just_the_first(self):
        """The old boundary stopped at the FIRST blank line, losing every
        paragraph after the first in a bullet-less, blank-line-separated
        section."""
        analysis = JobAnalyzer().analyze(self.REAL_STYLE_POSTING)
        required_text = " ".join(analysis.required_qualifications)
        assert "Masters/MBA" in required_text
        assert "cross-functional projects" in required_text

    def test_hyphenated_words_are_not_fragmented(self):
        """Splitting on every "-" anywhere in the text (the old approach)
        broke "full-time" and "cross-functional" into nonsense fragments."""
        analysis = JobAnalyzer().analyze(self.REAL_STYLE_POSTING)
        all_text = " ".join(analysis.required_qualifications + analysis.responsibilities)
        assert "full-time" in all_text
        assert "cross-functional" in all_text

    def test_fallback_keywords_populate_from_the_recovered_sections(self):
        """Once required/preferred/responsibilities are no longer empty,
        the non-technical fallback keyword extractor should have real
        content to draw from instead of producing an empty JobAnalysis."""
        analysis = JobAnalyzer().analyze(self.REAL_STYLE_POSTING)
        assert len(analysis.skills_required) > 0 or len(analysis.tools_required) > 0

    def test_fallback_keywords_do_not_invent_requirements_from_sentence_filler(self):
        """
        Regression test for a bug found live (2026-09-22): with full
        sentences as input (not short bullet fragments), the fallback
        extractor picked up ordinary grammatical words as if they were
        skills -- "Earned" and "degree" both became separate "required
        keywords," and "degree" was then flagged "truly missing" despite
        the candidate's resume showing a real degree. Filler words must
        not be treated as skills to be matched or found missing.
        """
        posting = (
            "What you'll need:\n\n"
            "Earned Masters/MBA degree by June 2027, preferably in Marketing or Business.\n\n"
            "Two to seven years of relevant full-time work experience in consulting.\n"
        ).replace("'", "’")
        analysis = JobAnalyzer().analyze(posting)
        lowered = [k.lower() for k in analysis.skills_required]
        for filler in ("earned", "degree", "preferably", "relevant", "full-time", "seven"):
            assert filler not in lowered, f"{filler!r} should not be extracted as a skill keyword"
