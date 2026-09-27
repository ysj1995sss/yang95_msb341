"""Maps a CareerTruthProfile onto known ATS form fields.

Never fabricates: a field is only filled when its name confidently matches
a known alias for a profile attribute. Anything else — custom essay
questions, ambiguous field names — is left blank for the user to fill in
Manual/Assist mode. AI-drafted answers to free-text questions are
explicitly out of scope for this MVP (see plan Task 3 design notes).
"""

import copy
import re
from dataclasses import replace
from typing import List

from resume_tailorer.applications.models import FormField
from resume_tailorer.models.career_profile import CareerTruthProfile

# Each entry: (list of substrings to match in the lowercased field name, resolver function)
# Order matters: "full_name" is checked before "first_name"/"last_name" because
# the no-underscore spelling "fullname" contains "lname" as a substring
# (fu-LL-N-AME), which would otherwise let the last_name group match first and
# incorrectly resolve "fullname" to just the last name instead of the full name.
#
# NOTE: there is no bare ["name"] catch-all. A substring check against "name"
# would also match "last_name" and "company_name" (both literally contain
# "name"), so once _resolve_value stops scanning after the first matching
# group (see below), a bare "name" fallback would either shadow those more
# specific groups or, if placed last, would still incorrectly catch them
# after their own specific resolver legitimately returned "". Every pattern
# below is specific enough that a match is genuinely about that exact piece
# of data.
_FIELD_ALIASES = [
    (["full_name", "fullname", "your_name", "candidate_name", "applicant_name"], lambda p: p.contact_info.get("name", "")),
    (["first_name", "firstname", "fname"], lambda p: p.contact_info.get("name", "").split()[0] if p.contact_info.get("name") else ""),
    (["last_name", "lastname", "lname"], lambda p: p.contact_info.get("name", "").split()[-1] if p.contact_info.get("name") and len(p.contact_info["name"].split()) > 1 else ""),
    (["email"], lambda p: p.contact_info.get("email", "")),
    (["phone"], lambda p: p.contact_info.get("phone", "")),
    (["location", "city"], lambda p: p.contact_info.get("location", "")),
    (["current_company", "employer", "current_employer", "company_name"], lambda p: p.work_experience[0].employer if p.work_experience else ""),
    (["current_title", "job_title", "current_role"], lambda p: p.work_experience[0].title if p.work_experience else ""),
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
        """Try each known alias pattern in order; return the first matching group's result.

        Once a pattern group's substrings match the field name, that group's
        resolver result is returned immediately (even if empty) — later,
        more generic groups are never consulted for a field name that already
        matched something more specific. This prevents a field like
        "last_name" or "company_name" (which both contain the substring
        "name") from falling through to a generic name-fallback pattern
        when its own specific resolver has nothing to offer.
        """
        name_lower = field_name.lower().replace("-", "_")
        if "phone" in name_lower.split("_") and "screen" in name_lower.split("_"):
            return ""
        if "reloc" in name_lower:
            return ""
        for patterns, resolver in _FIELD_ALIASES:
            if any(FormFiller._alias_matches(name_lower, pattern) for pattern in patterns):
                try:
                    return resolver(profile)
                except (IndexError, AttributeError):
                    return ""
        return ""

    @staticmethod
    def _alias_matches(name_lower: str, pattern: str) -> bool:
        """Match an alias as a field token, not a random substring."""
        collapsed_name = name_lower.replace("_", "")
        collapsed_pat = pattern.replace("_", "")
        if name_lower == pattern or collapsed_name == collapsed_pat:
            return True
        return bool(re.search(r"(?:^|_)" + re.escape(pattern) + r"(?:_|$)", name_lower))
