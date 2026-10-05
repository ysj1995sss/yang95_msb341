"""The "codex-cli" model: answers come from the Codex CLI signed in with the person's own ChatGPT
plan, for running Job Copilot locally (decision 031). The CLI itself is faked here."""

import subprocess
from pathlib import Path

import pytest

from resume_tailorer.llm import client as client_module
from resume_tailorer.llm.client import LLMClient
from resume_tailorer.llm.settings import LLMSettings, resolve_settings


class FakeCodex:
    def __init__(self, answer="Tailored text", returncode=0, stderr=""):
        self.answer, self.returncode, self.stderr = answer, returncode, stderr
        self.calls = []

    def __call__(self, command, **kwargs):
        self.calls.append((command, kwargs))
        out = Path(command[command.index("-o") + 1])
        if self.returncode == 0:
            out.write_text(self.answer, encoding="utf-8")
        return subprocess.CompletedProcess(command, self.returncode, stdout="", stderr=self.stderr)


@pytest.fixture()
def codex(monkeypatch):
    fake = FakeCodex()
    monkeypatch.setattr(client_module.shutil, "which", lambda name: "C:/bin/codex.cmd" if name == "codex" else None)
    monkeypatch.setattr(client_module.subprocess, "run", fake)
    return fake


def test_no_api_key_needed_for_codex_cli():
    settings = resolve_settings(model="codex-cli", env={})
    assert settings.model == "codex-cli" and settings.api_key == ""
    with pytest.raises(ValueError):
        resolve_settings(model="gemini/gemini-2.5-flash", env={})  # other models still need a key


def test_answer_comes_from_codex_in_a_read_only_throwaway_session(codex):
    llm = LLMClient(LLMSettings(model="codex-cli", api_key=""), sleep=lambda s: None)
    assert llm.complete("SYSTEM RULES", "USER TASK") == "Tailored text"
    command, kwargs = codex.calls[0]
    assert command[0] == "C:/bin/codex.cmd" and command[1] == "exec"
    for flag in ("--ephemeral", "--skip-git-repo-check", "--ignore-rules"):
        assert flag in command
    assert command[command.index("--sandbox") + 1] == "read-only"
    assert "-m" not in command  # the person's Codex default model
    assert "SYSTEM RULES" in kwargs["input"] and "USER TASK" in kwargs["input"]
    assert "Do not run commands" in kwargs["input"]
    assert llm.model_used == "codex-cli"


def test_a_specific_model_can_be_chosen(codex):
    LLMClient(LLMSettings(model="codex-cli/gpt-5.5", api_key=""), sleep=lambda s: None).complete("s", "u")
    command, _ = codex.calls[0]
    assert command[command.index("-m") + 1] == "gpt-5.5"


def test_missing_cli_and_used_up_plan_are_explained(monkeypatch):
    monkeypatch.setattr(client_module.shutil, "which", lambda name: None)
    llm = LLMClient(LLMSettings(model="codex-cli", api_key=""), sleep=lambda s: None)
    with pytest.raises(RuntimeError, match="Codex CLI isn't installed"):
        llm.complete("s", "u")

    monkeypatch.setattr(client_module.shutil, "which", lambda name: "codex")
    monkeypatch.setattr(client_module.subprocess, "run",
                        FakeCodex(returncode=1, stderr="ERROR: You've hit your usage limit. Try again in 3 days."))
    with pytest.raises(RuntimeError, match="ChatGPT plan's Codex usage limit"):
        llm.complete("s", "u")

    monkeypatch.setattr(client_module.subprocess, "run", FakeCodex(returncode=1, stderr="Not logged in. Run codex login"))
    with pytest.raises(RuntimeError, match="codex login"):
        llm.complete("s", "u")
