"""Spec 011: the model answers every target it doesn't change with a reason, and the reasons
reach Tailor. Codex runs with medium reasoning effort by default."""

import json
import re

from resume_tailorer.ui.requirement_review_view import keyword_report_view
from tests.test_profile_sync import A1, A2, A3, _docx, _profile


class AnswersWithReasons:
    """Keeps every bullet and explains each target it was asked about."""

    def __init__(self):
        self.prompts = []

    def complete(self, system, user, max_tokens=2000):
        self.prompts.append(user)
        found = re.search(r'\[\s*\{\s*"paragraph_index"', user)
        if not found:
            return "[]"
        bullets, _ = json.JSONDecoder().raw_decode(user[found.start():])
        answers = [{"paragraph_index": b["paragraph_index"], "change": "keep", "new_text": ""} for b in bullets]
        ids = re.search(r"ANSWER EVERY TARGET THAT ISN'T SHOWN YET \(([^)]*)\)", user)
        for rid in (ids.group(1).split(", ") if ids else []):
            answers.append({"target": rid, "no_safe_rewrite": "No bullet describes leading a launch as a project."})
        return json.dumps(answers)


def test_reasons_for_unchanged_targets_reach_the_keyword_report(monkeypatch, tmp_path):
    from resume_tailorer.docx_export import converter
    from resume_tailorer.tailoring_service import run_tailoring

    monkeypatch.setattr(converter, "_word_platform", lambda: False)
    monkeypatch.setattr(converter, "_soffice", lambda: None)
    posting = "Analyst.\nRequirements:\n- Proven project management experience leading cross-team launches.\n"
    model = AnswersWithReasons()
    state = run_tailoring({"artifacts_dir": str(tmp_path)}, original_bytes=_docx(), filename="r.docx",
                          job_description=posting, pending={"job_id": "j", "title": "Analyst", "company": "N"},
                          llm=model, career_profile=_profile([A1, A2, A3]))
    assert "ANSWER EVERY TARGET" in model.prompts[0]
    assert list(state["target_notes"].values()) == ["No bullet describes leading a launch as a project."]
    view = keyword_report_view(state["requirement_review"], state)
    assert view["not_changed"][0]["reason"].startswith("No bullet describes")
    assert view["why_not"]  # the not-yet-named term carries the model's reason


def test_codex_reasoning_effort_is_medium_by_default_and_can_be_changed(monkeypatch):
    from resume_tailorer.llm.client import _reasoning_effort

    monkeypatch.delenv("LLM_REASONING_EFFORT", raising=False)
    assert _reasoning_effort() == "medium"
    monkeypatch.setenv("LLM_REASONING_EFFORT", "high")
    assert _reasoning_effort() == "high"
    monkeypatch.setenv("LLM_REASONING_EFFORT", "turbo")
    assert _reasoning_effort() == "medium"
