"""Synthetic upload context; real profile store, parser and tailoring service."""
from tests.test_workspace_tailor import tailor_client, _ready, _run  # noqa: F401
from tests.test_workspace_jobs import jobs_client  # noqa: F401
from tests.workspace_helpers import resume_docx
import io
from docx import Document


def test_one_off_keeps_effective_profile_freshness(tailor_client):
    _ready(tailor_client)
    tailor_client.post('/v2/profile/confirm')
    before = tailor_client.get('/v2/profile').json()['profile']
    doc = Document(io.BytesIO(resume_docx()))
    doc.add_paragraph('A different synthetic summary and skills: SurveyMonkey')
    buffer = io.BytesIO()
    doc.save(buffer)
    tailor_client.post('/v2/tailor/one-off', files={
        'file': ('different.docx', buffer.getvalue(), 'application/octet-stream'),
    })
    assert _run(tailor_client)['status'] == 'done'
    assert tailor_client.get('/v2/profile').json()['profile'] == before
    tailor_client.put('/v2/profile/summary', json={'summary': 'Corrected synthetic summary.'})
    page = tailor_client.get('/v2/tailor').json()
    assert page['stale_message']
    assert page['review']['source_info']['filename'] == 'different.docx'
    assert page['review']['source_info']['fact_source'] == 'fact_vault'


def test_selected_file_does_not_relabel_existing_review(tailor_client):
    _ready(tailor_client)
    assert _run(tailor_client)['status'] == 'done'
    tailor_client.post('/v2/tailor/one-off', files={
        'file': ('next.docx', resume_docx(), 'application/octet-stream'),
    })
    page = tailor_client.get('/v2/tailor').json()
    assert page['resume']['source_info']['filename'] == 'next.docx'
    assert page['review']['source_info']['filename'] == 'r.docx'
    assert 'does not update' in page['resume']['source_info']['note']
    tailor_client.delete('/v2/tailor/one-off')
    assert tailor_client.get('/v2/tailor').json()['resume']['source_info']['file_source'] == 'career_profile'


def test_one_off_does_not_confirm_an_optional_saved_fact(tailor_client):
    from resume_tailorer.profile_import import store_for
    from resume_tailorer.profile_store import FROM_RESUME
    _ready(tailor_client)
    store = store_for('local')
    record = store.load()
    index = len(record['profile']['skills'])
    record['profile']['skills'].append('Python')
    record['provenance'][f'skills[{index}]'] = FROM_RESUME
    store.save(record)
    tailor_client.post('/v2/tailor/one-off', files={
        'file': ('optional.docx', resume_docx(), 'application/octet-stream'),
    })
    assert _run(tailor_client)['status'] == 'done'
    rows = [row for group in tailor_client.get('/v2/tailor').json()['review']['requirement_review']['groups']
            for row in group['rows']]
    python = [row for row in rows if 'Python' in row['text']]
    assert python and all(not row['evidence'] or not any(e['confirmed'] for e in row['evidence']) for row in python)
    assert all(row['label'] not in ('Direct evidence', 'Transferable evidence') for row in python)


def test_independent_one_off_does_not_create_master_facts(tailor_client):
    from tests.test_workspace_tailor import JD
    tailor_client.post('/v2/tailor/pasted', json={'title': 'Synthetic Analyst', 'description': JD})
    tailor_client.post('/v2/tailor/one-off', files={
        'file': ('independent.docx', resume_docx(), 'application/octet-stream'),
    })
    assert _run(tailor_client)['status'] == 'done'
    info = tailor_client.get('/v2/tailor').json()['review']['source_info']
    assert info['fact_source'] == 'resume_upload' and info['profile_version'] is None
    from resume_tailorer.profile_import import store_for
    assert not store_for('local').load().get('profile')
