"""Real runner/storage/pipeline races; only synthetic model and converter boundaries replaced."""
import threading
import time
from pathlib import Path

import pytest

from resume_tailorer import batch, batch_runner as br
from resume_tailorer.review_store import load_review
from resume_tailorer.review_store import save_review
from resume_tailorer.batch_artifacts import StagedReview, new_stage, mark_stage, cleanup_staging, publish_staged_review
from types import SimpleNamespace
import json
import os
import socket
from tests.test_batch import setup, RewritesTheSqlBullet  # noqa: F401
from tests.test_profile_sync import A1, A2, A3, _docx, _profile


def test_late_worker_cannot_replace_current_review(setup, tmp_path):
    service, jobs, folder = setup
    entered, release, old_returned = threading.Event(), threading.Event(), threading.Event()
    job = jobs[0]
    job_id = 'greenhouse_1'

    class LateModel(RewritesTheSqlBullet):
        def complete(self, *args, **kwargs):
            entered.set()
            assert release.wait(15)
            return super().complete(*args, **kwargs)

    def compute(model, claim=None):
        kwargs = dict(artifacts_dir=folder, original_bytes=_docx(), filename='synthetic.docx',
                      llm=model, career_profile=_profile([A1, A2, A3]))
        if hasattr(batch, 'stage_tailor_job'):
            return batch.stage_tailor_job(job, execution=claim.execution, **kwargs)
        return batch.tailor_job(job, **kwargs)

    def hooks(model):
        if hasattr(batch, 'stage_tailor_job'):
            return br.Hooks(tailor_one=lambda i: None, tailor_claim=lambda claim: compute(model, claim),
                            publish_result=batch.publish_staged_review)
        return br.Hooks(tailor_one=lambda i: compute(model))

    original = hooks(LateModel())
    original_compute = original.tailor_claim if hasattr(batch, 'stage_tailor_job') else original.tailor_one
    def finish_compute(arg):
        try:
            return original_compute(arg)
        finally:
            old_returned.set()
    if hasattr(batch, 'stage_tailor_job'):
        original.tailor_claim = finish_compute
    else:
        original.tailor_one = finish_compute
    first = br.start(tmp_path, [br.new_item(job_id, job.title, job.company, job.description)], {}, original)
    try:
        assert entered.wait(10)
        data = br.read_batch(tmp_path)
        data['heartbeat'] = time.time() - br.STALE_SECONDS - 1
        br.write_batch(tmp_path, data)
        br.continue_batch(tmp_path, hooks(RewritesTheSqlBullet()), background=False)
        current = load_review(folder, job_id)
        assert current is not None
        resumed_execution = br.read_batch(tmp_path)['execution']
        assert resumed_execution != first['execution']
        release.set()
        assert old_returned.wait(10)
        # Join the old runner, including its publication/finalizer, not only the model.
        for thread in threading.enumerate():
            if thread.name == f"batch-{first['id']}":
                thread.join(10)
                assert not thread.is_alive()
        assert load_review(folder, job_id)['tailored_at'] == current['tailored_at']
        assert load_review(folder, job_id)['pdf_bytes'] == current['pdf_bytes']
        assert br.read_batch(tmp_path)['execution'] == resumed_execution
    finally:
        release.set()
        for thread in threading.enumerate():
            if thread.name == f"batch-{first['id']}":
                thread.join(10)


def _result(folder, payload=b'synthetic artifact'):
    stage = new_stage(folder, 'a' * 32, 'job-a')
    mark_stage(stage, active=False)
    state = {'changes': [], 'version': 2, 'pdf_bytes': payload}
    # Publisher reads only validation status; production race above covers a full real report.
    from resume_tailorer.artifacts.models import ValidationStatus
    state['report'] = SimpleNamespace(validation=SimpleNamespace(status=ValidationStatus.PASS))
    return StagedReview(state, stage, Path(folder))


def test_failed_publication_keeps_previous_review(tmp_path, monkeypatch):
    folder = tmp_path / 'artifacts'
    assert save_review(str(folder), 'job-a', {'changes': [], 'marker': 'previous'})
    result = _result(folder)
    monkeypatch.setattr('resume_tailorer.batch_artifacts.save_review', lambda *a: False)
    with pytest.raises(RuntimeError, match='previous review is unchanged'):
        publish_staged_review('job-a', result)
    assert load_review(str(folder), 'job-a')['marker'] == 'previous'


def test_publication_failure_is_resumable_and_never_done(tmp_path):
    def fail(*args):
        raise RuntimeError('disk refused review')
    br.start(tmp_path, [br.new_item('job-a', 'Analyst', 'Synthetic', 'SQL')], {},
             br.Hooks(tailor_one=lambda i: None, publish_result=fail), background=False)
    item = br.read_batch(tmp_path)['items'][0]
    assert item['status'] == 'failed' and item['resumable']


def test_cleanup_retains_live_and_current_stages_and_rejects_escape(tmp_path):
    folder = tmp_path / 'artifacts'
    old = new_stage(folder, 'a' * 32, 'old')
    active = new_stage(folder, 'b' * 32, 'live')
    current = new_stage(folder, 'c' * 32, 'current')
    for stage, is_active in [(old, False), (active, True), (current, False)]:
        (stage / 'worker.json').write_text(json.dumps(dict(pid=os.getpid(), host=socket.gethostname(),
                                                        active=is_active, updated=1)), encoding='utf-8')
    br.write_batch(tmp_path, {'execution': 'c' * 32, 'status': 'done', 'items': []})
    cleanup_staging(folder, now=time.time(), retention_seconds=1)
    assert not old.exists() and active.exists() and current.exists()
    result = _result(folder)
    result.staging_dir = tmp_path / 'outside'
    with pytest.raises(ValueError, match='workspace'):
        publish_staged_review('job-a', result)


def test_stop_can_publish_the_owned_draining_job(tmp_path):
    def compute(i):
        br.cancel(tmp_path)
        return 'owned'
    published = []
    br.start(tmp_path, [br.new_item('a', 'Analyst', 'Synthetic', 'SQL')], {},
             br.Hooks(tailor_one=compute, publish_result=lambda i, result: published.append(result)), background=False)
    assert published == ['owned'] and br.read_batch(tmp_path)['items'][0]['status'] == 'done'


def test_interruption_after_bytes_keeps_old_review_and_immutable_pdf(tmp_path, monkeypatch):
    import hashlib
    folder = tmp_path / 'artifacts'
    result = _result(folder)
    previous = b'previous synthetic artifact'
    previous_file = folder / (hashlib.sha256(previous).hexdigest()[:16] + '.pdf')
    previous_file.write_bytes(previous)
    assert save_review(str(folder), 'job-a', {'changes': [], 'pdf_bytes': previous})
    def interrupted(*args):
        raise OSError('interrupted review replacement')
    monkeypatch.setattr('resume_tailorer.batch_artifacts.save_review', interrupted)
    with pytest.raises(OSError):
        publish_staged_review('job-a', result)
    assert load_review(str(folder), 'job-a')['pdf_bytes'] == previous
    assert previous_file.read_bytes() == previous


def test_old_lock_cannot_be_stolen_from_a_live_publisher(tmp_path):
    lock = br._path(tmp_path).with_suffix('.lock')
    outcomes = []
    def compete():
        try:
            with br._file_lock(tmp_path, wait=0.05):
                outcomes.append('stolen')
        except br.BatchBusy:
            outcomes.append('busy')
    with br._file_lock(tmp_path):
        os.utime(lock, (1, 1))
        thread = threading.Thread(target=compete)
        thread.start()
        thread.join(3)
        assert not thread.is_alive() and outcomes == ['busy']


def test_linked_staging_root_never_writes_or_cleans_external_data(tmp_path):
    import subprocess
    folder, outside = tmp_path / 'artifacts', tmp_path / 'external'
    folder.mkdir()
    outside.mkdir()
    marker = outside / 'preserve.txt'
    marker.write_text('synthetic external data', encoding='utf-8')
    link = folder / '.batch-staging'
    if os.name == 'nt':
        subprocess.run(['cmd.exe', '/c', 'mklink', '/J', str(link), str(outside)],
                       capture_output=True, check=True)
        assert link.is_junction()
    else:
        link.symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match='links'):
        new_stage(folder, 'a' * 32, 'job-a')
    cleanup_staging(folder, now=time.time(), retention_seconds=0)
    assert marker.read_text(encoding='utf-8') == 'synthetic external data'
