"""The one career profile every workspace reads from the Streamlit session.

Fact Vault (verified, user-corrected facts) takes precedence: a profile parsed
from a resume uploaded in Tailoring Studio never overwrites it.
"""

from __future__ import annotations

from typing import Any, MutableMapping, Optional

from resume_tailorer.models.career_profile import CareerTruthProfile

CAREER_PROFILE_KEY = "career_profile"
PROFILE_SOURCE_KEY = "career_profile_source"
FACT_VAULT = "fact_vault"
RESUME_UPLOAD = "resume_upload"


def set_career_profile(
    session: MutableMapping[str, Any], profile: CareerTruthProfile | dict, source: str
) -> CareerTruthProfile:
    if isinstance(profile, dict):
        profile = CareerTruthProfile.from_dict(profile)
    if source == RESUME_UPLOAD and session.get(PROFILE_SOURCE_KEY) == FACT_VAULT:
        return session[CAREER_PROFILE_KEY]
    session[CAREER_PROFILE_KEY] = profile
    session[PROFILE_SOURCE_KEY] = source
    return profile


def get_career_profile(session: MutableMapping[str, Any]) -> Optional[CareerTruthProfile]:
    return session.get(CAREER_PROFILE_KEY)


def has_verified_profile(session: MutableMapping[str, Any]) -> bool:
    return session.get(PROFILE_SOURCE_KEY) == FACT_VAULT and session.get(CAREER_PROFILE_KEY) is not None
