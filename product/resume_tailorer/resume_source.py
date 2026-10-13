"""File/layout selection is separate from the effective, frozen source of facts."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from resume_tailorer.models.career_profile import CareerTruthProfile

from resume_tailorer.freshness import profile_version
from resume_tailorer.session_profile import (
    FACT_VAULT, RESUME_UPLOAD, PROFILE_SOURCE_KEY, get_career_profile, set_career_profile,
)


@dataclass(frozen=True)
class FactContext:
    profile: CareerTruthProfile | None
    provenance: dict | None
    source: str
    version: str | None


def resolve_fact_context(session, parsed_profile=None, *, career_profile=None, provenance=None):
    saved = get_career_profile(session) if session.get(PROFILE_SOURCE_KEY) == FACT_VAULT else None
    profile = career_profile if career_profile is not None else saved
    if profile is not None:
        if provenance is None:
            provenance = (session.get('profile_record') or {}).get('provenance')
        return FactContext(deepcopy(profile), deepcopy(provenance), FACT_VAULT, profile_version(profile))
    if parsed_profile is None:
        return FactContext(None, None, RESUME_UPLOAD, None)
    profile = set_career_profile(session, parsed_profile, RESUME_UPLOAD)
    return FactContext(deepcopy(profile), deepcopy(provenance), RESUME_UPLOAD, None)


def source_details(filename: str, one_off: bool, facts: FactContext) -> dict:
    kind = 'DOCX' if Path(filename).suffix.lower() == '.docx' else 'PDF'
    info = dict(file_source='one_off' if one_off else 'career_profile', filename=filename,
                kind=kind, fact_source=facts.source, profile_version=facts.version)
    return {**info, **source_disclosure(info)}


def source_disclosure(info: dict | None) -> dict:
    if not info:
        return dict(file_label='Source details unavailable for this older review.',
                    facts_label='Unknown — this review predates source recording.', note='')
    file_label = f"{info['filename']} · {'one-off file' if info['file_source'] == 'one_off' else 'Career Profile resume'}"
    saved = info['fact_source'] == FACT_VAULT
    facts_label = 'Saved Career Profile (confirmation status preserved)' if saved else 'This uploaded resume'
    # Only a one-off file was uploaded on this page; saying "Uploading here..." for the Career Profile
    # resume described an upload that never happened (dogfood, 2026-10-13).
    note = ("This file is used for this job only. It does not update your Career Profile or replace its master resume. "
            if info['file_source'] == 'one_off' else '')
    if saved:
        note += 'Your saved Career Profile takes precedence as the source of facts. '
    else:
        note += 'No saved Career Profile is in use; facts come from this file. '
    if info['kind'] == 'DOCX':
        note += ('This Word file supplies layout and existing bullets; one-off files are not fully synced to the profile.'
                 if info['file_source'] == 'one_off' else 'Your Word file is synced to your Career Profile where it can be safely matched.')
    else:
        note += 'The PDF is rebuilt from the effective facts; its original layout may change.'
    return dict(file_label=file_label, facts_label=facts_label, note=note)
