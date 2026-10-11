"""Windows-spawn-safe race through the actual pipeline and shared on-disk review."""
import multiprocessing as mp
import time
from pathlib import Path
from unittest.mock import patch

from resume_tailorer import batch_runner as br
from resume_tailorer.review_store import load_review


def _worker(folder, mode, ready, release):
    from resume_tailorer.batch import stage_tailor_job, publish_staged_review
    from tests.test_batch import _job, _fake_pdf, RewritesTheSqlBullet
    from tests.test_profile_sync import A1, A2, A3, _docx, _profile

    class ControlledModel(RewritesTheSqlBullet):
        def complete(self, *args, **kwargs):
            if mode == 'old':
                ready.set()
                assert release.wait(25)
            return super().complete(*args, **kwargs)

    job = _job(1, 'Data Analyst')
    def compute(claim):
        return stage_tailor_job(job, artifacts_dir=str(Path(folder) / 'artifacts'),
                               execution=claim.execution, original_bytes=_docx(), filename='synthetic.docx',
                               llm=ControlledModel(), career_profile=_profile([A1, A2, A3]))
    hooks = br.Hooks(tailor_one=lambda i: None, tailor_claim=compute, publish_result=publish_staged_review)
    with patch('resume_tailorer.docx_export.pipeline.convert_docx_to_pdf', _fake_pdf), \
         patch('resume_tailorer.docx_export.converter._word_platform', lambda: False), \
         patch('resume_tailorer.docx_export.converter._soffice', lambda: None):
        if mode == 'old':
            br.start(Path(folder), [br.new_item('greenhouse_1', job.title, job.company, job.description)], {},
                     hooks, background=False)
        else:
            br.continue_batch(Path(folder), hooks, background=False)


def test_superseded_process_cannot_publish(tmp_path):
    context = mp.get_context('spawn')
    ready, release = context.Event(), context.Event()
    old = context.Process(target=_worker, args=(str(tmp_path), 'old', ready, release))
    current = context.Process(target=_worker, args=(str(tmp_path), 'current', ready, release))
    old.start()
    try:
        assert ready.wait(15)
        with br._file_lock(tmp_path):
            data = br._read_batch_file(tmp_path)
            old_execution = data['execution']
            data['heartbeat'] = time.time() - br.STALE_SECONDS - 1
            br.write_batch(tmp_path, data)
        current.start()
        current.join(20)
        assert current.exitcode == 0
        saved = load_review(str(tmp_path / 'artifacts'), 'greenhouse_1')
        assert saved and saved['pdf_bytes']
        execution = br.read_batch(tmp_path)['execution']
        assert execution != old_execution
        release.set()
        old.join(15)
        assert old.exitcode == 0
        actual = load_review(str(tmp_path / 'artifacts'), 'greenhouse_1')
        assert actual['pdf_bytes'] == saved['pdf_bytes']
        assert actual['source_info'] == saved['source_info'] and actual['version'] == saved['version']
        batch = br.read_batch(tmp_path)
        assert batch['execution'] == execution and batch['items'][0]['status'] == 'done'
    finally:
        release.set()
        for process in (old, current):
            if process.pid:
                process.join(10)
                if process.is_alive():
                    process.terminate()  # only processes this fixture spawned
                    process.join(5)
