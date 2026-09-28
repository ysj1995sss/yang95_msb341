"""Greenhouse ATS form parser."""

from typing import List

from resume_tailorer.applications.ats_parsers.base_parser import BaseATSParser
from resume_tailorer.applications.models import ATSCapability, FormField


class GreenhouseParser(BaseATSParser):
    """Parses Greenhouse job application forms."""

    def get_platform_name(self) -> str:
        return "greenhouse"

    def is_supported(self) -> bool:
        return True

    def get_capability(self) -> ATSCapability:
        # Verified live (decision 012): a real Greenhouse application form
        # has ~15+ visible fields but exactly 1 named HTML input -- the
        # rest are JS-rendered React components a static fetch can't see.
        # profile_prefill=True because THAT logic is real and correct for
        # whatever fields a page does expose; the gap is that pages expose
        # almost none, not that prefill itself is broken.
        return ATSCapability(
            platform="greenhouse",
            manual_supported=True,
            assist_supported=False,
            auto_supported=False,
            resume_upload=False,
            profile_prefill=True,
            custom_questions=False,
            final_submission=False,
            status_fetch=False,
            notes="Real forms are JS-rendered; static HTML exposes almost no named fields (decision 012).",
        )

    def parse_form(self, form_html: str) -> List[FormField]:
        return self._extract_fields(form_html)
