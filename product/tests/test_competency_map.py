from resume_tailorer.analyzers.competency_map import (
    find_education_status_evidence,
    find_transferable_evidence,
    supported_competencies,
)
from resume_tailorer.models import CareerTruthProfile, EducationEntry


def _profile_with_education(*entries: EducationEntry) -> CareerTruthProfile:
    return CareerTruthProfile(
        contact_info={},
        education=list(entries),
        work_experience=[],
        skills=[],
        tools=[],
        certifications=[],
        accomplishments=[],
    )


class TestFindTransferableEvidence:
    def test_a_project_management_from_delivery_and_risk_evidence(self):
        """Test A from the fix request: JD says 'project management', the
        exact phrase never appears, but the evidence strongly demonstrates
        it -- must not be treated as unsupported."""
        sentences = [
            "Led a 10-person team and achieved 100% on-time delivery across 200+ performances through risk mitigation."
        ]
        result = find_transferable_evidence("cross-functional project management", sentences)
        assert result is not None
        assert result.competency == "project management"
        assert result.level == "strong"

    def test_b_business_analysis_from_analyzing_data(self):
        """Test B: 'business analysis' evidenced by analyzing data to
        diagnose a challenge and develop recommendations."""
        sentences = [
            "Analyzed Nielsen/Circana data to diagnose a business challenge and develop brand growth recommendations."
        ]
        result = find_transferable_evidence("business analysis", sentences)
        assert result is not None
        assert result.competency == "business analysis"
        assert result.level == "strong"

    def test_c_executive_communication_from_presenting_to_leadership(self):
        """Test C: 'executive communication' evidenced by presenting to
        C-suite/VP leaders."""
        sentences = ["Presented executive-ready recommendations to C-suite and VP leaders."]
        result = find_transferable_evidence("executive communication", sentences)
        assert result is not None
        assert result.competency == "executive communication"
        assert result.level == "strong"

    def test_d_cpg_experience_from_mondelez_consulting(self):
        """Test D: CPG experience via a consulting project, not full-time
        employment -- must register as evidence (not zero), and the
        caller distinguishes 'strong' project-based signal from full CPG
        employment history separately (this function only reports
        evidence existence/strength, not employment-duration semantics)."""
        sentences = ["Consulted Mondelēz using Nielsen/Circana data."]
        result = find_transferable_evidence("CPG experience", sentences)
        assert result is not None
        assert result.competency == "cpg experience"

    def test_no_match_returns_none(self):
        sentences = ["Baked pastries for a local coffee shop."]
        result = find_transferable_evidence("cross-functional project management", sentences)
        assert result is None

    def test_unrelated_requirement_has_no_relevant_competency_keys(self):
        """A requirement with no word overlap with any competency name
        (e.g. a pure duration/eligibility requirement) correctly finds no
        evidence -- this function doesn't fabricate matches for concepts
        it has no mapping for."""
        sentences = ["Led a 10-person team and achieved 100% on-time delivery."]
        result = find_transferable_evidence("4+ years of prior professional experience", sentences)
        assert result is None

    def test_strong_evidence_preferred_over_partial(self):
        sentences = [
            "Managed timelines for a small initiative.",  # partial signal
            "Achieved 100% on-time delivery through risk mitigation.",  # strong signal
        ]
        result = find_transferable_evidence("project management", sentences)
        assert result is not None
        assert result.level == "strong"


class TestFindEducationStatusEvidence:
    def test_in_progress_mba_matches_requirement_naming_mba_and_year(self):
        """The live GMDP bug: 'Currently enrolled in an accredited MBA
        program with an intended graduation of Spring 2027' must match a
        profile whose education entry spells out the degree in full and
        never uses the filler words in the requirement."""
        profile = _profile_with_education(
            EducationEntry(
                degree="Master of Business Administration",
                field="",
                institution="Brigham Young University",
                year=2027,
            )
        )
        result = find_education_status_evidence(
            "Currently enrolled in an accredited MBA program with an intended graduation of Spring 2027.",
            profile,
        )
        assert result is not None
        assert "2027" in result

    def test_wrong_graduation_year_does_not_match(self):
        profile = _profile_with_education(
            EducationEntry(degree="Master of Business Administration", field="", institution="BYU", year=2025)
        )
        result = find_education_status_evidence(
            "Currently enrolled in an MBA program with an intended graduation of Spring 2027.",
            profile,
        )
        assert result is None

    def test_wrong_degree_type_does_not_match(self):
        """A bachelor's degree does not satisfy an MBA requirement, even
        with a matching year -- this must never paper over a real gap."""
        profile = _profile_with_education(
            EducationEntry(degree="B.S.", field="Marketing", institution="BYU", year=2027)
        )
        result = find_education_status_evidence(
            "Currently enrolled in an MBA program with an intended graduation of Spring 2027.",
            profile,
        )
        assert result is None

    def test_requirement_with_no_degree_or_program_language_returns_none(self):
        """Deliberately narrow: a requirement that merely mentions a year
        for an unrelated reason must not accidentally match education."""
        profile = _profile_with_education(
            EducationEntry(degree="Master of Business Administration", field="", institution="BYU", year=2027)
        )
        result = find_education_status_evidence(
            "Experience with 2027-style retail point-of-sale systems.", profile
        )
        assert result is None

    def test_bachelor_requirement_matches_bachelor_degree_without_year(self):
        profile = _profile_with_education(
            EducationEntry(degree="B.S.", field="Hospitality", institution="BYU-Hawaii", year=2022)
        )
        result = find_education_status_evidence(
            "Bachelor's degree required.", profile
        )
        assert result is not None


class TestSupportedCompetencies:
    def test_returns_multiple_competencies_from_real_resume_bullets(self):
        sentences = [
            "Aligned 30+ cross-functional stakeholders and distilled complex consumer research into executive-ready recommendations, presented to C-suite and VP leaders.",
            "Led a 10-person operations team, diagnosed process bottlenecks through workflow mapping.",
            "Achieved 100% on-time delivery across 200+ performances via real-time communication and risk mitigation.",
            "Analyzed Nielsen/Circana data to diagnose a business challenge and develop brand growth.",
        ]
        results = supported_competencies(sentences)
        assert "project management" in results
        assert "cross-functional leadership" in results
        assert "business analysis" in results
        assert "executive communication" in results

    def test_empty_profile_returns_no_competencies(self):
        assert supported_competencies([]) == {}
