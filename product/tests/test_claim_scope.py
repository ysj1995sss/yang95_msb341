"""Spec 016: a tool elsewhere in the profile cannot establish its use on this project."""
import pytest
from resume_tailorer.analyzers.gap_analyzer import GapReport
from resume_tailorer.artifacts.changes import build_freeform_changes
from resume_tailorer.artifacts.models import ChangeCategory, ChangeDisposition, ResumeChange, ValidationStatus
from resume_tailorer.artifacts.regeneration import validate_manual_text
from resume_tailorer.models import WorkExperience
from resume_tailorer.pdf.content_validator import validate_pdf_content
from tests.fixtures.ats import profile
from tests.test_unsupported_claim_guards import _tailorer, _bullets, SQL
from resume_tailorer.analyzers.job_analyzer import JobAnalyzer


def other_project_profile():
    candidate = profile()
    candidate.skills.append("Tableau")
    candidate.work_experience.append(WorkExperience(
        "Example B", "Analyst", "2023-2025", ["Built Tableau dashboards for inventory planning."], [],
    ))
    return candidate


def test_tool_from_another_role_does_not_pass_manual_validation():
    candidate = other_project_profile()
    issues = validate_manual_text(SQL, SQL + " using Tableau", candidate)
    assert any("Tableau" in issue for issue in issues)


@pytest.mark.parametrize('proposed', [
    'Analyst at Acme Retail skilled in SQL; spearheaded Tableau reporting for regional teams.',
    'Analyst at Acme Retail skilled in SQL and Tableau who spearheaded reporting for regional teams.',
    'Analyst at Acme Retail skilled in SQL and Tableau, orchestrating reporting for regional teams.',
])
def test_summary_listing_cannot_gain_activity_with_an_unrecognized_verb(proposed):
    candidate = profile()
    candidate.skills.append('Tableau')
    candidate.summary = 'Analyst at Acme Retail skilled in SQL, Tableau, and reporting for regional teams.'
    assert validate_manual_text(candidate.summary, proposed, candidate, section='summary')
    changes = build_freeform_changes(candidate, 'SUMMARY\n' + proposed + '\nEXPERIENCE\n- ' + SQL + '\n', GapReport([], ''))
    summary = next(c for c in changes if c.section == 'summary')
    assert summary.validation_status == ValidationStatus.FAIL
    assert any(f.code == 'UNSUPPORTED_TOOL_ATTRIBUTION' for f in validate_pdf_content(summary.proposed_text, candidate, [summary]))


def test_summary_can_reorder_listed_tools_without_changing_other_context():
    candidate = profile()
    candidate.skills.append('Tableau')
    original = 'Analyst at Acme Retail skilled in SQL, Tableau, and reporting for regional teams.'
    proposed = 'Analyst at Acme Retail skilled in Tableau and SQL, reporting for regional teams.'
    assert validate_manual_text(original, proposed, candidate, section='summary') == []


def test_summary_existing_activity_with_unrecognized_verb_can_be_rephrased():
    candidate = profile()
    candidate.skills.append('Tableau')
    original = 'Analyst at Acme Retail who spearheaded Tableau reporting.'
    assert validate_manual_text(original, original[:-1] + ' for regional teams.', candidate, section='summary') == []


def test_summary_can_add_a_known_skill_listing_without_new_activity():
    from resume_tailorer.analyzers.claim_scope import introduced_unscoped_tools
    candidate = profile()
    candidate.skills.append('Tableau')
    assert introduced_unscoped_tools('Analyst', 'Analyst proficient in SQL and Tableau.', candidate, section='summary') == []


def test_bare_summary_list_cannot_become_tool_use():
    candidate = profile()
    candidate.skills.append('Tableau')
    candidate.summary = 'SQL, Tableau, analytics, reporting, regional sales teams, data analysis.'
    proposed = 'Built SQL and Tableau analytics reporting and data analysis for regional sales teams.'
    assert validate_manual_text(candidate.summary, proposed, candidate, section='summary')
    changes = build_freeform_changes(candidate, 'SUMMARY\n' + proposed + '\nEXPERIENCE\n', GapReport([], ''))
    summary = next(c for c in changes if c.section == 'summary')
    assert summary.validation_status == ValidationStatus.FAIL
    assert any(f.code == 'UNSUPPORTED_TOOL_ATTRIBUTION' for f in validate_pdf_content(summary.proposed_text, candidate, [summary]))


def test_listed_rust_without_posting_evidence_cannot_be_attached_to_sql_activity():
    candidate = profile()
    candidate.skills.append('Rust')
    assert validate_manual_text(SQL, SQL + ' using Rust', candidate)


def test_existing_rust_source_use_can_be_preserved():
    candidate = profile()
    candidate.skills.append('Rust')
    original = SQL + ' using Rust'
    assert validate_manual_text(original, original + ' weekly', candidate) == []


@pytest.mark.parametrize('tool', ['Alteryx', 'Java', 'Photoshop', 'Terraform', 'SQL Server'])
def test_curated_tool_elsewhere_cannot_be_assigned_to_sql_project(tool):
    from resume_tailorer.analyzers.requirement_review import build_review
    candidate = other_project_profile()
    candidate.work_experience[-1].responsibilities = [f'Used {tool} for inventory planning.']
    candidate.skills.append(tool)
    posting = f'Required Qualifications:\n- SQL and {tool} experience.'
    analysis = JobAnalyzer().analyze(posting)
    assert any("can't verify" in issue for issue in validate_manual_text(
        SQL, SQL + f' using {tool}', candidate, build_review(analysis, candidate, posting=posting)))


def test_summary_cannot_attach_listed_tools_to_an_employer_without_an_action_word():
    candidate = other_project_profile()
    original = 'Analyst skilled in Tableau and SQL reporting for regional teams.'
    proposed = original[:-1] + ' at Acme Retail.'
    assert any("can't verify" in issue for issue in validate_manual_text(original, proposed, candidate, section='summary'))


def test_research_and_development_is_not_the_r_language():
    from resume_tailorer.analyzers.claim_scope import introduced_unscoped_tools
    candidate = other_project_profile()
    assert introduced_unscoped_tools('Built SQL dashboards.', 'Built SQL dashboards for R&D.', candidate) == []


def test_listed_skill_does_not_become_project_tool_even_without_a_job_review():
    candidate = profile()
    candidate.skills.append("Tableau")
    assert validate_manual_text(SQL, SQL + " using Tableau", candidate)


def test_summary_skill_mention_cannot_be_promoted_to_project_use():
    candidate = other_project_profile()
    original = 'Analyst skilled in Tableau.'
    proposed = 'Analyst skilled in Tableau who built reporting dashboards using Tableau at Example A.'
    assert any("can't verify" in issue for issue in validate_manual_text(original, proposed, candidate, section='summary'))


def test_a_tool_in_another_project_under_the_same_employer_is_not_local_evidence():
    candidate = profile()
    candidate.work_experience[0].responsibilities.append("Built Tableau inventory forecasts.")
    assert validate_manual_text(SQL, SQL + " using Tableau", candidate)


def test_word_path_rejects_cross_project_tool_and_preserves_the_source():
    tailorer, _ = _tailorer([{"paragraph_index": 10, "change": "rewrite", "new_text": SQL + " using Tableau"}])
    result = tailorer.tailor_bullets(_bullets(), other_project_profile(),
                                   JobAnalyzer().analyze("Required Qualifications:\n- SQL experience."),
                                   GapReport([], ""), max_repair_attempts=0)
    edit = next(e for e in result.edits if e.paragraph_index == 10)
    assert not edit.changed
    assert edit.new_text == SQL
    assert edit.rejected_reason


def test_freeform_change_flags_a_cross_project_tool_relationship():
    candidate = other_project_profile()
    text = "EXPERIENCE\nMarketing Analyst, Acme Retail\n- " + SQL + " using Tableau\n"
    changes = build_freeform_changes(candidate, text, GapReport([], ""))
    change = next(c for c in changes if c.original_text == SQL)
    assert change.validation_status == ValidationStatus.FAIL
    assert "Tableau" in change.reason


def test_accept_cannot_downgrade_project_tool_failure_to_a_warning():
    candidate = other_project_profile()
    change = ResumeChange(
        change_id="paragraph:10", section="work_experience", source_index=10,
        original_text=SQL, proposed_text=SQL + " using Tableau", category=ChangeCategory.REPHRASED,
        reason="Wrong project", job_requirement="", evidence_source="original_resume", evidence_text=SQL,
        validation_status=ValidationStatus.FAIL, disposition=ChangeDisposition.ACCEPTED,
    )
    findings = validate_pdf_content(change.proposed_text, candidate, [change])
    assert any(f.code == "UNSUPPORTED_TOOL_ATTRIBUTION" and f.severity.value == "FAIL" for f in findings)


def test_existing_truthful_tool_use_may_be_rephrased():
    candidate = other_project_profile()
    original = SQL + " using Tableau"
    assert validate_manual_text(original, original + " weekly", candidate) == []


def test_comma_heavy_experience_is_not_a_skills_list():
    candidate = other_project_profile()
    assert validate_manual_text(SQL, SQL + ", Tableau, Python, Excel", candidate)


def test_same_source_wording_under_two_roles_does_not_borrow_a_tool():
    candidate = other_project_profile()
    candidate.work_experience[1].responsibilities = [SQL]
    assert validate_manual_text(SQL, SQL + " using Tableau", candidate)


def test_accept_is_blocked_before_regeneration_even_when_a_legacy_flag_says_pass():
    from resume_tailorer.tailoring_service import regenerate, TailoringError
    change = ResumeChange(
        change_id="legacy", section="work_experience", source_index=10,
        original_text=SQL, proposed_text=SQL + " using Tableau", category=ChangeCategory.REPHRASED,
        reason="", job_requirement="", evidence_source="original_resume", evidence_text=SQL,
        validation_status=ValidationStatus.PASS,
    )
    state = {"changes": [change], "dispositions": {"legacy": "ACCEPTED"},
             "manual_texts": {}, "profile": other_project_profile()}
    with pytest.raises(TailoringError, match="project"):
        regenerate({}, state)


def test_refinement_cannot_move_an_existing_tool_to_a_different_project():
    from resume_tailorer.tailorer.optimizer import ResumeTailoringOptimizer
    from resume_tailorer.analyzers.requirement_review import build_review
    candidate = other_project_profile()
    sql = candidate.work_experience[0].responsibilities[0]
    tableau = candidate.work_experience[-1].responsibilities[0]
    launch = candidate.work_experience[0].responsibilities[1]
    initial = f"EXPERIENCE\nAcme Retail\n- {sql}\nExample B\n- {tableau}\n"
    refined = initial.replace(sql, sql + " using Tableau") + f"- {launch} (project management)\n"

    class Model:
        def complete(self, *args, **kwargs):
            return refined

    posting = "Required Qualifications:\n- Project management experience.\n- Tableau experience.\n- SQL experience."
    analysis = JobAnalyzer().analyze(posting)
    result = ResumeTailoringOptimizer(llm=Model()).optimize(
        candidate, analysis, initial, GapReport([], ""), review=build_review(analysis, candidate),
    )
    assert result.tailored_resume == initial
    assert "project/tool" in result.stop_reason
