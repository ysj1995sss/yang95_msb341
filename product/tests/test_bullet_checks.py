from resume_tailorer.docx_export.bullet_checks import bullet_length_delta
from resume_tailorer.models import CareerTruthProfile, WorkExperience, EducationEntry
from resume_tailorer.diff_generator import DiffGenerator


class TestBulletLengthDelta:
    def test_no_warning_within_threshold(self):
        original = "Managed a team of five engineers"
        new = "Led a team of five engineers on schedule"
        assert bullet_length_delta(original, new) == []

    def test_warns_when_growth_exceeds_threshold(self):
        original = "Short bullet"
        new = "Short bullet " + "with a lot more words appended here to grow it substantially"
        warnings = bullet_length_delta(original, new)
        assert len(warnings) == 1
        assert "longer" in warnings[0]

    def test_no_warning_for_empty_original(self):
        assert bullet_length_delta("", "Some new text") == []

    def test_shrinking_a_bullet_never_warns(self):
        original = "A very long original bullet with lots of detail in it"
        new = "Shorter now"
        assert bullet_length_delta(original, new) == []


def _profile(**overrides):
    defaults = dict(
        contact_info={"name": "Jane Doe"},
        education=[],
        work_experience=[],
        skills=[],
        tools=[],
        certifications=[],
        accomplishments=[],
    )
    defaults.update(overrides)
    return CareerTruthProfile(**defaults)


class TestCheckBulletPairFabricationRisk:
    def test_metric_already_in_original_bullet_is_not_flagged(self):
        """'in Marketing' deliberately not used here anymore -- that's a
        genuinely new, ungrounded characterization the broader check below
        is now correctly supposed to catch; kept this fixture to only add
        already-present words so it stays a narrow test of the metric path."""
        profile = _profile()
        original = "Dean's List x5 Semesters | GPA: 3.92/4.0 | Top 1% of Class"
        new = "Top 1% of Class | Dean's List x5 Semesters | GPA: 3.92/4.0"
        issues = DiffGenerator().check_bullet_pair_fabrication_risk(original, new, profile)
        assert issues == []

    def test_new_metric_not_in_original_or_profile_is_flagged(self):
        profile = _profile()
        original = "Managed a project"
        new = "Managed a project, boosting revenue by 42%"
        issues = DiffGenerator().check_bullet_pair_fabrication_risk(original, new, profile)
        assert any("42%" in issue for issue in issues)

    def test_metric_present_in_education_notes_is_not_flagged(self):
        """The education-notes gap found live (2026-09-22): a metric only
        ever stored in EducationEntry.notes must still count as known-true."""
        profile = _profile(
            education=[
                EducationEntry(
                    degree="B.S.",
                    field="Hospitality",
                    institution="Some University",
                    year=2022,
                    notes=["Top 1% of Class"],
                )
            ]
        )
        original = "Some unrelated bullet"
        new = "Some unrelated bullet, recognized in the Top 1% of Class"
        issues = DiffGenerator().check_bullet_pair_fabrication_risk(original, new, profile)
        assert issues == []

    def test_tech_keyword_not_in_original_or_profile_is_flagged(self):
        profile = _profile()
        original = "Built internal tools"
        new = "Built internal tools using Kubernetes"
        issues = DiffGenerator().check_bullet_pair_fabrication_risk(original, new, profile)
        assert any("kubernetes" in issue.lower() for issue in issues)

    def test_tech_keyword_present_in_profile_skills_is_not_flagged(self):
        profile = _profile(skills=["Kubernetes"])
        original = "Built internal tools"
        new = "Built internal tools using Kubernetes"
        issues = DiffGenerator().check_bullet_pair_fabrication_risk(original, new, profile)
        assert issues == []

    def test_single_new_word_is_not_flagged_as_unverified(self):
        """One new word is normal stylistic rephrasing (a different verb,
        a connector) -- only flag when the pattern is stronger."""
        profile = _profile()
        original = "Built a customer acquisition and experience framework"
        new = "Developed a customer acquisition and experience framework"
        issues = DiffGenerator().check_bullet_pair_fabrication_risk(original, new, profile)
        assert issues == []

    def test_two_or_more_unverified_new_words_are_flagged(self):
        """Found live (2026-09-23): 'loyalty' was added to describe a
        program never characterized that way anywhere in the profile --
        a domain-agnostic case _TECH_KEYWORDS could never catch."""
        profile = _profile()
        original = "Built a customer acquisition and experience framework"
        new = "Built a customer acquisition and loyalty rewards framework"
        issues = DiffGenerator().check_bullet_pair_fabrication_risk(original, new, profile)
        assert any("loyalty" in issue.lower() and "rewards" in issue.lower() for issue in issues)

    def test_new_characterizing_noun_is_flagged_even_alone(self):
        """A single new NOUN characterizing the accomplishment (not a verb
        synonym) is still flagged, even alone -- the exact 'loyalty' case
        found live (2026-09-23) was the ONLY new word in that edit, so a
        2+-words threshold missed it; this must catch it with just one."""
        profile = _profile()
        original = "Top 1% of Class"
        new = "Top 1% of Class in Marketing"
        issues = DiffGenerator().check_bullet_pair_fabrication_risk(original, new, profile)
        assert any("marketing" in issue.lower() for issue in issues)

    def test_new_words_grounded_elsewhere_in_profile_are_not_flagged(self):
        profile = _profile(skills=["Loyalty Marketing", "Rewards Programs"])
        original = "Built a customer acquisition and experience framework"
        new = "Built a customer acquisition and loyalty rewards framework"
        issues = DiffGenerator().check_bullet_pair_fabrication_risk(original, new, profile)
        assert issues == []


class TestCheckSemanticDrift:
    def test_no_drift_when_all_original_words_preserved(self):
        original = "Developed a front-store growth strategy identifying incremental sales"
        new = "Developed a front-store growth strategy to identify incremental sales potential"
        assert DiffGenerator().check_semantic_drift(original, new) == []

    def test_dropping_a_core_word_is_flagged(self):
        """The exact bug found live (2026-09-23): 'growth' silently
        replaced with 'acquisition', narrowing the claim even though
        'acquisition' was itself a legitimate word elsewhere."""
        original = "Developed a front-store growth strategy"
        new = "Developed a front-store acquisition strategy"
        issues = DiffGenerator().check_semantic_drift(original, new)
        assert len(issues) == 1
        assert "growth" in issues[0]

    def test_pure_addition_never_flagged(self):
        original = "Built a customer acquisition and experience framework"
        new = "Built a customer acquisition and experience framework across all regions"
        assert DiffGenerator().check_semantic_drift(original, new) == []

    def test_short_words_and_stopwords_ignored(self):
        original = "Led a 10-person team to cut costs"
        new = "Led the 10-person team to cut costs"
        assert DiffGenerator().check_semantic_drift(original, new) == []

    def test_swapping_the_leading_verb_is_not_flagged(self):
        """A SECOND real bug found live (2026-09-23) from the same check:
        rewriting the bullet to start with a different verb ('Led' instead
        of 'Developed') wrongly counted as dropping 'developed' and
        blocked an otherwise legitimate rephrase. A verb-for-verb swap
        changes HOW something is described, not WHAT was accomplished."""
        original = "Developed a front-store growth strategy identifying incremental sales"
        new = "Led a front-store growth strategy identifying incremental sales"
        assert DiffGenerator().check_semantic_drift(original, new) == []
