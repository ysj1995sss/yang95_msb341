"""Maps a CareerTruthProfile onto known ATS form fields.

Never fabricates: a field is only filled when its name confidently matches
a known alias for a profile attribute. Anything else — custom essay
questions, ambiguous field names — is left blank for the user to fill in
Manual/Assist mode. AI-drafted answers to free-text questions are
explicitly out of scope for this MVP (see plan Task 3 design notes).
"""

import copy
from dataclasses import replace
from typing import List

from resume_tailorer.applications.models import FormField
from resume_tailorer.models.career_profile import CareerTruthProfile

# Each entry: (list of substrings to match in the lowercased field name, resolver function)
# Order matters: more specific patterns (e.g. "first_name") are checked before
# more general ones (e.g. "name") to avoid a generic pattern winning first.
_FIELD_ALIASES = [
    (["first_name", "firstname", "fname"], lambda p: p.contact_info.get("name", "").split()[0] if p.contact_info.get("name") else ""),
    (["last_name", "lastname", "lname"], lambda p: p.contact_info.get("name", "").split()[-1] if p.contact_info.get("name") and len(p.contact_info["name"].split()) > 1 else ""),
    (["full_name", "fullname"], lambda p: p.contact_info.get("name", "")),
    (["email"], lambda p: p.contact_info.get("email", "")),
    (["phone"], lambda p: p.contact_info.get("phone", "")),
    (["location", "city"], lambda p: p.contact_info.get("location", "")),
    (["current_company", "employer", "current_employer"], lambda p: p.work_experience[0].employer if p.work_experience else ""),
    (["current_title", "job_title", "current_role"], lambda p: p.work_experience[0].title if p.work_experience else ""),
    (["name"], lambda p: p.contact_info.get("name", "")),  # generic fallback, checked last
]


class FormFiller:
    """Fills known ATS form fields from a CareerTruthProfile; never fabricates."""

    def fill_form(self, fields: List[FormField], profile: CareerTruthProfile) -> List[FormField]:
        """
        Return a new list of FormFields with confidently-mappable fields filled.

        Args:
            fields: Parsed form fields (from an ATS parser).
            profile: The candidate's verified career data.

        Returns:
            A new list of FormField objects (input list is not mutated).
            Fields with a confident mapping have value set and prefilled=True.
            Fields with no confident mapping are returned unchanged.
        """
        result = []
        for original_field in fields:
            value = self._resolve_value(original_field.field_name, profile)
            if value:
                result.append(replace(original_field, value=value, prefilled=True))
            else:
                result.append(copy.deepcopy(original_field))
        return result

    def _resolve_value(self, field_name: str, profile: CareerTruthProfile) -> str:
        """Try each known alias pattern in order; return the first confident match."""
        name_lower = field_name.lower()
        for patterns, resolver in _FIELD_ALIASES:
            if any(pattern in name_lower for pattern in patterns):
                try:
                    value = resolver(profile)
                except (IndexError, AttributeError):
                    value = ""
                if value:
                    return value
        return ""
