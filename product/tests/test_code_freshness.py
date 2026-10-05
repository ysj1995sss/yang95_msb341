"""New deployments are picked up without a reboot (decision 027)."""

from resume_tailorer import code_freshness
from resume_tailorer.code_freshness import drop_stale_modules, fingerprint


def test_fingerprint_changes_when_a_file_changes(tmp_path):
    (tmp_path / "a.py").write_text("x = 1")
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "a.cpython.py").write_text("ignored")
    before = fingerprint(tmp_path)
    assert [item[0] for item in before] == ["a.py"]
    (tmp_path / "a.py").write_text("x = 22")
    assert fingerprint(tmp_path) != before


def test_fingerprint_is_stable_when_nothing_changes(tmp_path):
    (tmp_path / "a.py").write_text("x = 1")
    assert fingerprint(tmp_path) == fingerprint(tmp_path)


def test_only_package_modules_are_dropped():
    modules = {"resume_tailorer": 1, "resume_tailorer.ui.shell": 2, "resume_tailorer_extra": 3, "streamlit": 4}
    assert drop_stale_modules(modules) == 2
    assert set(modules) == {"resume_tailorer_extra", "streamlit"}


def test_the_running_code_matches_disk():
    assert not code_freshness.code_changed_on_disk()


def test_a_deploy_is_detected(monkeypatch):
    monkeypatch.setattr(code_freshness, "_LOADED", ())
    assert code_freshness.code_changed_on_disk()


def test_a_session_from_older_code_is_reset(tmp_path, monkeypatch):
    """Another session may have triggered the reload; this one still holds old-class objects."""
    from pathlib import Path

    from streamlit.testing.v1 import AppTest

    monkeypatch.setenv("JOB_COPILOT_DATA_DIR", str(tmp_path / "data"))
    app = str(Path(__file__).resolve().parent.parent / "resume_tailorer" / "app.py")
    at = AppTest.from_file(app, default_timeout=60)
    at.session_state[code_freshness.SESSION_KEY] = "older-code"
    at.session_state["object_from_old_code"] = object()
    at.run()
    assert not at.exception, at.exception
    assert "object_from_old_code" not in at.session_state
    assert at.session_state[code_freshness.SESSION_KEY] == code_freshness.CODE_VERSION
