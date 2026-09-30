from types import SimpleNamespace

from resume_tailorer.artifacts import length_control
from resume_tailorer.artifacts.length_control import (
    build_freeform_artifact,
    condense_bullet,
    condense_grown_changes,
    correct_docx_length_once,
    needs_length_correction,
)
from resume_tailorer.artifacts.models import (
    ArtifactValidation,
    ChangeCategory,
    ChangeDisposition,
    FindingCategory,
    FindingSeverity,
    ResumeChange,
    ValidationFinding,
    ValidationStatus,
)
from resume_tailorer.models import CareerTruthProfile, WorkExperience

PROFILE = CareerTruthProfile(
    contact_info={"name": "Alex Kim"},
    education=[],
    work_experience=[
        WorkExperience(employer="Acme", title="Analyst", dates="2020-2023",
                       responsibilities=["Built weekly sales dashboards in SQL for leadership"], accomplishments=[])
    ],
    skills=["SQL"], tools=[], certifications=[], accomplishments=[],
)
ORIGINAL = "Built weekly sales dashboards in SQL for leadership"
GROWN = "Built and maintained weekly sales dashboards in SQL that leadership used for planning"


class _LLM:
    def __init__(self, reply):
        self.reply = reply

    def complete(self, system, user, max_tokens=0):
        return self.reply


def _finding(code, severity=FindingSeverity.FAIL):
    return ValidationFinding(code, severity, FindingCategory.VISUAL, code)


def _change(original=ORIGINAL, proposed=GROWN):
    return ResumeChange(
        change_id="c1", section="work_experience", source_index=5, original_text=original,
        proposed_text=proposed, category=ChangeCategory.REPHRASED, reason="Tailored.",
        job_requirement="", evidence_source="career_profile", evidence_text="",
        validation_status=ValidationStatus.PASS, disposition=ChangeDisposition.PENDING,
    )


def test_only_length_failures_are_correctable():
    assert needs_length_correction(ArtifactValidation.from_findings([_finding("PAGE_LIMIT_EXCEEDED")]))
    assert not needs_length_correction(ArtifactValidation.from_findings(
        [_finding("PAGE_LIMIT_EXCEEDED"), _finding("UNSUPPORTED_CLAIM_PRESENT")]))
    assert not needs_length_correction(ArtifactValidation.from_findings([]))


def test_condense_uses_a_grounded_shorter_model_version():
    shorter = "Built weekly SQL sales dashboards for leadership"
    assert condense_bullet(ORIGINAL, GROWN, PROFILE, _LLM(shorter)) == shorter


def test_condense_falls_back_to_the_original_when_the_model_adds_claims_or_is_absent():
    fabricated = "Built SQL dashboards, saving $2M"
    assert condense_bullet(ORIGINAL, GROWN, PROFILE, _LLM(fabricated)) == ORIGINAL
    assert condense_bullet(ORIGINAL, GROWN, PROFILE, _LLM(GROWN + " again")) == ORIGINAL
    assert condense_bullet(ORIGINAL, GROWN, PROFILE, None) == ORIGINAL


def test_bullets_that_did_not_grow_are_left_alone():
    same = _change(proposed="Built weekly SQL dashboards for leadership")
    assert condense_grown_changes([same], PROFILE) == [same]


def test_freeform_overflow_is_repaired_once(monkeypatch):
    calls = []

    def fake_validate(self, path, **kwargs):
        calls.append(kwargs["target_length"])
        findings = [_finding("PAGE_LIMIT_EXCEEDED")] if len(calls) == 1 else []
        return ArtifactValidation.from_findings(findings)

    monkeypatch.setattr("resume_tailorer.pdf.validator.PDFValidator.validate_artifact", fake_validate)
    text = f"Alex Kim\nAcme | Analyst | 2020-2023\n- {GROWN}\n"
    _pdf, validation, final_text, final_changes, attempts = build_freeform_artifact(
        tailored_text=text, changes=[_change()], profile=PROFILE,
        target_length="1_page", style_hints={},
    )
    assert attempts == 2
    assert calls == ["1_page", "1_page"]
    assert validation.status is ValidationStatus.PASS
    assert f"- {ORIGINAL}" in final_text and GROWN not in final_text
    assert final_changes[0].proposed_text == ORIGINAL


def test_freeform_non_length_failure_is_not_repaired(monkeypatch):
    monkeypatch.setattr(
        "resume_tailorer.pdf.validator.PDFValidator.validate_artifact",
        lambda self, path, **kw: ArtifactValidation.from_findings([_finding("CONTACT_MISSING")]),
    )
    *_rest, attempts = build_freeform_artifact(
        tailored_text=f"- {GROWN}\n", changes=[_change()], profile=PROFILE,
        target_length="1_page", style_hints={},
    )
    assert attempts == 1


def test_docx_page_growth_is_rebuilt_once_with_shortened_bullets(monkeypatch):
    seen = {}

    def fake_regenerate(**kwargs):
        seen.update(kwargs)
        return "rebuilt"

    monkeypatch.setattr("resume_tailorer.artifacts.regeneration.regenerate_docx_artifact", fake_regenerate)
    grown = SimpleNamespace(
        validation=ArtifactValidation.from_findings([_finding("PAGE_COUNT_CHANGED")]),
        changes=[_change()],
    )
    assert correct_docx_length_once(
        original_docx_bytes=b"docx", docx_result=grown, profile=PROFILE, gap_report=None
    ) == "rebuilt"
    assert seen["changes"][0].proposed_text == ORIGINAL

    fine = SimpleNamespace(validation=ArtifactValidation.from_findings([]), changes=[])
    assert correct_docx_length_once(
        original_docx_bytes=b"docx", docx_result=fine, profile=PROFILE, gap_report=None
    ) is fine
