"""Use Streamlit's real background hook without accessing Streamlit state in the worker."""
from unittest.mock import patch

from resume_tailorer import batch_runner as br
from resume_tailorer.identity import artifacts_dir, job_db_path, applications_db_path, user_dir
from resume_tailorer.job_search.job_service import JobService
from resume_tailorer.profile_import import store_for
from resume_tailorer.review_store import load_review
from tests.test_batch import _job, _fake_pdf, RewritesTheSqlBullet
from tests.test_profile_sync import A1, A2, A3, _docx, _profile


def test_real_streamlit_hook_stages_then_runner_publishes(tmp_path, monkeypatch):
    from resume_tailorer.ui import batch_panel
    monkeypatch.setenv('JOB_COPILOT_DATA_DIR', str(tmp_path))
    monkeypatch.setenv('LLM_MODEL', 'stub/model')
    monkeypatch.setenv('LLM_API_KEY', 'stub-key')
    monkeypatch.setattr(batch_panel, '_owner', lambda: 'local')
    store = store_for('local')
    record = store.load()
    record['profile'] = _profile([A1, A2, A3]).to_dict()
    store.save_resume_file(record, 'synthetic.docx', _docx())
    store.save(record)
    service = JobService(db_path=job_db_path('local'), applications_db_path=applications_db_path('local'))
    job = _job(1, 'Data Analyst')
    service.db.save_job_posting(job)
    service.close()
    with patch('resume_tailorer.llm.client.LLMClient', lambda settings: RewritesTheSqlBullet()), \
         patch('resume_tailorer.docx_export.pipeline.convert_docx_to_pdf', _fake_pdf), \
         patch('resume_tailorer.docx_export.converter._word_platform', lambda: False), \
         patch('resume_tailorer.docx_export.converter._soffice', lambda: None):
        hooks = batch_panel._hooks({})
        assert hooks.tailor_claim is not None
        claimed = br.ExecutionClaim(user_dir('local'), 'test', 'a' * 32, 'greenhouse_1')
        staged = hooks.tailor_claim(claimed)
        assert load_review(artifacts_dir('local'), 'greenhouse_1') is None
        assert not list(staged.artifacts_dir.glob('*.pdf'))
        br.start(user_dir('local'), [br.new_item('greenhouse_1', job.title, job.company, job.description)], {},
                 hooks, background=False)
    saved = load_review(artifacts_dir('local'), 'greenhouse_1')
    assert saved and saved['pdf_bytes'] and saved['source_info']['filename'] == 'synthetic.docx'
    assert br.read_batch(user_dir('local'))['items'][0]['status'] == 'done'
