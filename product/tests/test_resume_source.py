from resume_tailorer.models.career_profile import CareerTruthProfile
from resume_tailorer.session_profile import FACT_VAULT, set_career_profile
from resume_tailorer.resume_source import resolve_fact_context, source_details, source_disclosure
from resume_tailorer.review_store import encode, decode
from resume_tailorer.freshness import profile_version


def _profile(summary):
    return CareerTruthProfile({}, [], [], ['SQL'], [], [], [], summary=summary)


def test_canonical_facts_and_unconfirmed_provenance_survive_different_upload():
    saved, uploaded = _profile('Saved summary'), _profile('Different uploaded facts')
    session = {'profile_record': {'provenance': {'skills[0]': 'resume'}}}
    set_career_profile(session, saved, FACT_VAULT)
    context = resolve_fact_context(session, uploaded)
    assert context.profile == saved and context.profile is not saved
    assert context.version == profile_version(saved)
    assert context.provenance == {'skills[0]': 'resume'}
    saved.summary = 'Later edit'
    assert context.profile.summary == 'Saved summary'


def test_independent_upload_has_no_saved_profile_hash():
    context = resolve_fact_context({}, _profile('Independent'))
    assert context.version is None and context.source == 'resume_upload'
    assert 'This uploaded resume' == source_details('only.pdf', True, context)['facts_label']


def test_saved_disclosure_roundtrip_is_not_current_selection():
    context = resolve_fact_context({}, career_profile=_profile('Canonical'))
    info = source_details('<synthetic>.docx', True, context)
    assert decode(encode(info)) == info
    assert 'not fully synced' in info['note'] and 'does not update' in info['note']
    assert source_details('other.pdf', True, context)['filename'] != info['filename']


def test_legacy_disclosure_is_unknown():
    assert 'unavailable' in source_disclosure(None)['file_label']
    assert 'Unknown' in source_disclosure(None)['facts_label']
