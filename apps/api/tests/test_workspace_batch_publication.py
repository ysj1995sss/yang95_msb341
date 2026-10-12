"""Actual API hook factory, private pipeline, atomic review and public download."""
import threading
import time

from tests.test_workspace_jobs import jobs_client  # noqa: F401
from tests.test_workspace_tailor import tailor_client, StubModel  # noqa: F401
from tests.test_workspace_batch import _setup, _wait


def test_api_late_worker_preserves_current_download_and_status(tailor_client, monkeypatch):
    from resume_tailorer import batch_runner as br
    from resume_tailorer.identity import user_dir
    from resume_tailorer.review_store import load_review
    from tests.e2e_server import fake_pdf

    entered, release = threading.Event(), threading.Event()
    calls = []
    class Model(StubModel):
        def __init__(self, settings=None):
            self.old = not calls
            calls.append(self)
        def complete(self, *args, **kwargs):
            if self.old:
                entered.set()
                assert release.wait(20)
            return super().complete(*args, **kwargs)
    monkeypatch.setattr('resume_tailorer.llm.client.LLMClient', Model)
    monkeypatch.setattr('resume_tailorer.docx_export.pipeline.convert_docx_to_pdf', fake_pdf)
    _setup(tailor_client)
    tailor_client.post('/v2/profile/confirm')
    started = tailor_client.post('/v2/batch/tailor', json={'job_ids': ['greenhouse_101']})
    assert started.status_code == 200
    first = br.read_batch(user_dir('local'))
    try:
        assert entered.wait(10)
        with br._file_lock(user_dir('local')):
            data = br._read_batch_file(user_dir('local'))
            data['heartbeat'] = time.time() - br.STALE_SECONDS - 1
            br.write_batch(user_dir('local'), data)
        response = tailor_client.post('/v2/batch/continue', json={})
        assert response.status_code == 200, response.text
        assert _wait(tailor_client)['items'][0]['status'] == 'done'
        folder = user_dir('local') / 'artifacts'
        saved = load_review(str(folder), 'greenhouse_101')
        assert saved and saved['pdf_bytes']
        release.set()
        for thread in threading.enumerate():
            if thread.name == f"batch-{first['id']}":
                thread.join(10)
                assert not thread.is_alive()
        assert load_review(str(folder), 'greenhouse_101')['pdf_bytes'] == saved['pdf_bytes']
        assert tailor_client.get('/v2/tailor/run').json()['status'] == 'done'
        assert tailor_client.post('/v2/batch/open', json={'job_id': 'greenhouse_101'}).status_code == 200
        downloaded = tailor_client.get('/v2/apply/resume')
        assert downloaded.status_code == 200 and downloaded.content == saved['pdf_bytes']
    finally:
        release.set()
        for thread in threading.enumerate():
            if thread.name == f"batch-{first['id']}":
                thread.join(10)


def test_delayed_callbacks_cannot_replace_current_execution_status(tailor_client):
    from app.workspace.batch_router import _hooks
    from app.workspace.identity import Owner
    from app.workspace.tailor_router import RunRequest, _write_run
    from resume_tailorer import batch_runner as br
    from resume_tailorer.identity import user_dir
    folder = user_dir('local')
    data = dict(id='batch', execution='c' * 32, boot=br.PROCESS_ID, heartbeat=time.time(), status='running',
                items=[dict(job_id='job-a', status='running')])
    br.write_batch(folder, data)
    _write_run('local', dict(status='running', step='Current step', batch=True, boot=br.PROCESS_ID))
    hooks = _hooks(Owner(owner_id='local', name='Synthetic', signed_in=False), None, RunRequest())
    obsolete = br.ExecutionClaim(folder, 'batch', 'a' * 32, 'job-a')
    hooks.on_claim_step(obsolete, 'Obsolete step')
    hooks.on_claim_finish(br.ExecutionClaim(folder, 'batch', 'a' * 32))
    assert tailor_client.get('/v2/tailor/run').json()['step'] == 'Current step'
    hooks.on_claim_step(br.ExecutionClaim(folder, 'batch', 'c' * 32, 'job-a'), 'New step')
    assert tailor_client.get('/v2/tailor/run').json()['step'] == 'New step'
    # After a new single run starts, even a matching old batch token cannot finish it.
    _write_run('local', dict(status='running', step='Single run', boot=br.PROCESS_ID))
    hooks.on_claim_finish(br.ExecutionClaim(folder, 'batch', 'c' * 32))
    assert tailor_client.get('/v2/tailor/run').json()['step'] == 'Single run'
