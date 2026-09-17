import pytest
from resume_tailorer.utils.scoring import calculate_keyword_alignment, calculate_qualification_alignment


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
        profile_text = "5+ years of software engineering experience. Strong proficiency in system design and leadership."
        required_quals = ["5+ years experience", "system design", "leadership"]
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
