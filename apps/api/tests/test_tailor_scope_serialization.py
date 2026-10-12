from app.tailor.serialization import changes_to_json, changes_from_json
from resume_tailorer.artifacts.models import ResumeChange, ChangeCategory, ValidationStatus
import json


def test_scope_and_section_anchor_survive_legacy_api_roundtrip():
    change = ResumeChange('summary:0', 'summary', None, 'SQL skills', 'Used SQL at Example',
                          ChangeCategory.REPHRASED, 'Unverified relationship', '', 'profile', 'SQL skills',
                          ValidationStatus.FAIL, baseline_span=(10, 30), scope_issues=('Wrong project',))
    assert changes_from_json(json.loads(json.dumps(changes_to_json([change])))) == [change]
