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


class TestStructuredRequirements:
    """JobAnalysis.structured_requirements: added alongside the existing
    flat string lists (never replacing them), so every existing caller
    keeps working unchanged -- see job_analyzer.py's JobRequirement
    docstring."""

    @pytest.fixture
    def marketing_job_description(self):
        return """
        Senior Marketing Analyst

        Required Qualifications:
        - 5+ years of marketing analytics experience
        - Must hold an active Google Analytics certification
        - Strong stakeholder management skills
        - Passion for our mission

        Preferred:
        - Experience with SQL
        - Prior CPG experience

        Responsibilities:
        - Present executive-ready recommendations to senior leadership
        - Manage stakeholder relationships across teams
        - Analyze campaign performance data
        """

    def test_existing_flat_lists_still_populated_unchanged(self, sample_job_description):
        """Adding structured_requirements must not change any existing
        field's behavior -- backward compatibility for every downstream
        caller that only reads the flat lists."""
        analysis = JobAnalyzer().analyze(sample_job_description)
        assert len(analysis.required_qualifications) > 0
        assert len(analysis.preferred_qualifications) > 0
        assert len(analysis.responsibilities) > 0

    def test_every_requirement_and_responsibility_gets_a_structured_entry(self, marketing_job_description):
        analysis = JobAnalyzer().analyze(marketing_job_description)
        expected_count = (
            len(analysis.required_qualifications)
            + len(analysis.preferred_qualifications)
            + len(analysis.responsibilities)
        )
        assert len(analysis.structured_requirements) == expected_count

    def test_years_of_experience_in_required_section_is_a_hard_gate(self, marketing_job_description):
        analysis = JobAnalyzer().analyze(marketing_job_description)
        years_item = next(
            r for r in analysis.structured_requirements if "5+ years" in r.text
        )
        assert years_item.hard_gate is True
        assert years_item.required_or_preferred == "required"

    def test_active_certification_requirement_is_a_hard_gate(self, marketing_job_description):
        analysis = JobAnalyzer().analyze(marketing_job_description)
        cert_item = next(
            r for r in analysis.structured_requirements if "certification" in r.text.lower()
        )
        assert cert_item.hard_gate is True

    def test_preferred_qualification_is_never_a_hard_gate_even_with_gate_language(self):
        """A hard-gate PATTERN in the Preferred section must not become a
        hard gate -- by definition preferred items are waivable."""
        jd = """
        Required:
        - Bachelor's degree in Marketing

        Preferred:
        - 10+ years of experience in the industry
        """
        analysis = JobAnalyzer().analyze(jd)
        preferred_years = next(
            r for r in analysis.structured_requirements
            if r.required_or_preferred == "preferred" and "10+ years" in r.text
        )
        assert preferred_years.hard_gate is False

    def test_generic_filler_gets_low_importance(self, marketing_job_description):
        analysis = JobAnalyzer().analyze(marketing_job_description)
        filler_item = next(
            r for r in analysis.structured_requirements if "Passion for our mission" in r.text
        )
        assert filler_item.importance == "low"

    def test_semantically_similar_requirements_share_a_normalized_concept(self, marketing_job_description):
        """'Strong stakeholder management skills' (Required) and 'Manage
        stakeholder relationships across teams' (Responsibilities) describe
        the same underlying concept and should normalize to the same
        value, even though they're phrased differently and sit in
        different sections."""
        analysis = JobAnalyzer().analyze(marketing_job_description)
        concepts = {
            r.text: r.normalized_concept for r in analysis.structured_requirements
        }
        stakeholder_items = [
            concept for text, concept in concepts.items() if "stakeholder" in text.lower()
        ]
        assert len(stakeholder_items) == 2
        assert stakeholder_items[0] == stakeholder_items[1] == "stakeholder management"

    def test_repeated_concept_gets_importance_bumped_up(self, marketing_job_description):
        """'stakeholder management' appears twice (Required + a
        Responsibility) -- the responsibility instance starts at 'medium'
        by default but should bump to 'high' for being a repeated theme."""
        analysis = JobAnalyzer().analyze(marketing_job_description)
        resp_item = next(
            r for r in analysis.structured_requirements
            if r.category == "responsibility" and "Manage stakeholder" in r.text
        )
        assert resp_item.importance == "high"

    def test_required_or_preferred_matches_source_section(self, marketing_job_description):
        analysis = JobAnalyzer().analyze(marketing_job_description)
        for r in analysis.structured_requirements:
            if r.source_section == "required_qualifications":
                assert r.required_or_preferred == "required"
                assert r.category == "qualification"
            elif r.source_section == "preferred_qualifications":
                assert r.required_or_preferred == "preferred"
                assert r.category == "qualification"
            elif r.source_section == "responsibilities":
                assert r.category == "responsibility"

    def test_requirement_ids_are_unique(self, marketing_job_description):
        analysis = JobAnalyzer().analyze(marketing_job_description)
        ids = [r.id for r in analysis.structured_requirements]
        assert len(ids) == len(set(ids))


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
