import pytest
from resume_tailorer.utils.scoring import (
    calculate_keyword_alignment,
    calculate_qualification_alignment,
    _semantic_match_qualification,
    qualification_match_ratio,
)


class TestKeywordAlignment:
    """Tests for keyword alignment scoring."""

    def test_perfect_match_returns_score_1_0(self):
        """Perfect match of all keywords returns score of 1.0."""
        resume_text = "I have experience with Python, JavaScript, Docker, and Kubernetes."
        required_keywords = ["python", "javascript", "docker", "kubernetes"]

        score, matched, missing = calculate_keyword_alignment(resume_text, required_keywords)

        assert score == 1.0
        assert len(matched) == 4
        assert len(missing) == 0
        assert set(matched) == {"python", "javascript", "docker", "kubernetes"}

    def test_partial_match_returns_score_between_0_and_1(self):
        """Partial match of keywords returns score between 0 and 1.0."""
        resume_text = "I have experience with Python and JavaScript."
        required_keywords = ["python", "javascript", "docker", "kubernetes", "golang"]

        score, matched, missing = calculate_keyword_alignment(resume_text, required_keywords)

        assert 0 < score < 1.0
        assert score == 2.0 / 5.0  # 2 matched out of 5
        assert len(matched) == 2
        assert len(missing) == 3
        assert set(matched) == {"python", "javascript"}
        assert set(missing) == {"docker", "kubernetes", "golang"}

    def test_case_insensitive_matching(self):
        """Keyword matching is case-insensitive."""
        resume_text = "I have experience with PYTHON, JavaScript, and DOCKER."
        required_keywords = ["python", "javascript", "docker"]

        score, matched, missing = calculate_keyword_alignment(resume_text, required_keywords)

        assert score == 1.0
        assert len(matched) == 3
        assert len(missing) == 0


class TestQualificationAlignment:
    """Tests for qualification alignment scoring."""

    def test_perfect_qualification_match_returns_score_1_0(self):
        """Perfect match of all qualifications returns score of 1.0."""
        profile_text = "5+ years of software engineering. Strong proficiency in system design and leadership."
        required_quals = ["software engineering", "system design", "leadership"]
        preferred_quals = []

        score, covered, missing = calculate_qualification_alignment(profile_text, required_quals, preferred_quals)

        assert score == 1.0
        assert len(covered) == 3
        assert len(missing) == 0

    def test_partial_qualification_match_returns_score_between_0_and_1(self):
        """Partial match of qualifications returns score between 0 and 1.0."""
        profile_text = "3 years of software engineering experience. Experience with system design."
        required_quals = ["5+ years experience", "system design", "leadership", "mentoring"]
        preferred_quals = []

        score, covered, missing = calculate_qualification_alignment(profile_text, required_quals, preferred_quals)

        assert 0 < score < 1.0
        assert len(covered) > 0
        assert len(missing) > 0
        # At least system design should be covered
        assert any("design" in q.lower() for q in covered)

    def test_qualification_match_case_insensitive(self):
        """Qualification matching is case-insensitive."""
        profile_text = "STRONG LEADERSHIP SKILLS. Experience with SYSTEM DESIGN and AGILE METHODOLOGIES."
        required_quals = ["leadership", "system design", "agile"]
        preferred_quals = []

        score, covered, missing = calculate_qualification_alignment(profile_text, required_quals, preferred_quals)

        assert score == 1.0
        assert len(covered) == 3
        assert len(missing) == 0


class TestSemanticMatchDoesNotFabricate:
    def test_generic_words_alone_do_not_match(self):
        profile = "Led a small team of interns on campus projects"
        qualification = "strong communication and stakeholder leadership"
        assert _semantic_match_qualification(profile, qualification) is False

    def test_distinctive_content_words_do_match(self):
        profile = "Built REST APIs in Python and deployed them with Docker"
        qualification = "experience building Python APIs"
        assert _semantic_match_qualification(profile, qualification) is True


class TestShortAcronymQualificationMatching:
    """
    Regression tests for a bug found live (2026-09-21): a qualification
    phrase whose only substantive word is a short tech acronym (AWS, SQL,
    API, ...) was filtered out entirely by the 4+-character word filter,
    leaving zero distinctive words and forcing ratio 0.0 -- so "Experience
    with AWS" was misclassified Category E ("truly missing") even when AWS
    was clearly present in the profile.
    """

    def test_short_acronym_present_now_matches(self):
        profile_text = "Deployed services on AWS using Docker containers"
        assert qualification_match_ratio(profile_text, "Experience with AWS") == 1.0

    def test_short_acronym_absent_still_scores_zero(self):
        """The fix must not make short acronyms match when they're genuinely absent."""
        profile_text = "Built REST APIs in Python and deployed them with Docker"
        assert qualification_match_ratio(profile_text, "Experience with AWS") == 0.0

    def test_multiple_short_acronyms_partial_match(self):
        profile_text = "Experience with SQL databases"
        # "AWS" present via SQL context is false; only "sql" is present here.
        ratio = qualification_match_ratio(profile_text, "Experience with SQL and AWS")
        assert 0.0 < ratio < 1.0

    def test_unrelated_short_word_is_not_treated_as_an_acronym(self):
        """Only the known tech-acronym allowlist gets the short-word carve-out;
        this must not silently start matching on any short word (e.g. "the")."""
        profile_text = "Managed a relational database migration project"
        # "with" and "the" are stopwords/too short and not in the acronym
        # allowlist, so "Experience with the database" reduces to
        # "database" only (a long word), which is present here.
        ratio = qualification_match_ratio(profile_text, "Experience with the database")
        assert ratio == 1.0
