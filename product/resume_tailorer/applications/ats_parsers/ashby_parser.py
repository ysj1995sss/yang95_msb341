"""Ashby ATS form parser."""

from typing import List

from resume_tailorer.applications.ats_parsers.base_parser import BaseATSParser
from resume_tailorer.applications.models import ATSCapability, FormField


class AshbyParser(BaseATSParser):
    """Parses Ashby job application forms."""

    def get_platform_name(self) -> str:
        return "ashby"

    def is_supported(self) -> bool:
        return True

    def get_capability(self) -> ATSCapability:
        # Not independently live-verified (decision 012), but assumed
        # architecturally similar to Greenhouse -- a modern SPA-based ATS.
        return ATSCapability(
            platform="ashby",
            manual_supported=True,
            assist_supported=False,
            auto_supported=False,
            resume_upload=False,
            profile_prefill=True,
            custom_questions=False,
            final_submission=False,
            status_fetch=False,
            notes="Assumed JS-rendered like Greenhouse (decision 012); not independently verified.",
        )

    def parse_form(self, form_html: str) -> List[FormField]:
        return self._extract_fields(form_html)
