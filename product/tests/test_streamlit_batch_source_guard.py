"""An active one-off upload must never silently launch a master-resume batch."""
from types import SimpleNamespace
from resume_tailorer.ui import batch_panel


def test_active_one_off_upload_blocks_batch_launch(monkeypatch):
    errors, started = [], []
    monkeypatch.setattr(batch_panel, 'st', SimpleNamespace(
        session_state={'tailor_one_off': {'name': 'different.docx', 'bytes': b'synthetic'}}, error=errors.append))
    batch_panel._run(lambda: started.append('started'))
    assert started == []
    assert errors and 'Career Profile' in errors[0]


def test_removing_one_off_restores_batch_launch(monkeypatch):
    errors, started = [], []
    monkeypatch.setattr(batch_panel, 'st', SimpleNamespace(session_state={}, error=errors.append))
    batch_panel._run(lambda: started.append('started'))
    assert started == ['started'] and errors == []
