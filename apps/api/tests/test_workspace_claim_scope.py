"""Public decisions/rebuild/download uses scoped facts, not a global skill permission."""
from tests.test_workspace_jobs import jobs_client  # noqa: F401
from tests.test_workspace_tailor import tailor_client, _ready, _run  # noqa: F401


def test_listed_tableau_cannot_be_added_to_sql_project(tailor_client, monkeypatch):
    from tests.e2e_server import fake_pdf
    monkeypatch.setattr('resume_tailorer.docx_export.pipeline.convert_docx_to_pdf', fake_pdf)
    _ready(tailor_client)
    tailor_client.post('/v2/profile/confirm')
    assert _run(tailor_client)['status'] == 'done'
    before = tailor_client.get('/v2/tailor/download/pdf').content
    review = tailor_client.get('/v2/tailor').json()['review']
    change = next(c for c in review['changes'] if 'SQL reporting' in c['proposed'])
    response = tailor_client.post('/v2/tailor/decisions', json={
        'change_id': change['id'], 'decision': 'MANUALLY_EDITED',
        'manual_text': 'Built SQL and Tableau reporting dashboards used by 40 managers across regional sales teams',
    })
    assert response.status_code == 200
    failed = tailor_client.post('/v2/tailor/rebuild')
    assert failed.status_code == 400 and 'only listed in your skills' in failed.json()['detail']
    assert tailor_client.get('/v2/tailor/download/pdf').content == before  # only previous safe version
    tailor_client.post('/v2/tailor/decisions', json={'change_id': change['id'], 'decision': 'REJECTED'})
    restored = tailor_client.post('/v2/tailor/rebuild')
    assert restored.status_code == 200 and not restored.json()['progress']['needs_rebuild']
    assert 'SQL and Tableau reporting dashboards' not in restored.json()['tailored_text']
