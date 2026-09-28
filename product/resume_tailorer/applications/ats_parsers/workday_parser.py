"""Workday ATS form parser.

Workday application forms are rendered client-side by a JavaScript SPA —
the HTML returned by a plain HTTP GET contains no usable form fields, only
a script-loading shell. Parsing them would require a real browser
(Selenium/Playwright), which is explicitly out of scope for this plan.
This parser honestly reports itself as unsupported and always returns an
empty field list, rather than pretending to work.
"""

from typing import List

from resume_tailorer.applications.ats_parsers.base_parser import BaseATSParser
from resume_tailorer.applications.models import ATSCapability, FormField


class WorkdayParser(BaseATSParser):
    """Reports Workday as unsupported; never extracts real fields."""

    def get_platform_name(self) -> str:
        return "workday"

    def is_supported(self) -> bool:
        return False

    def get_capability(self) -> ATSCapability:
        return ATSCapability(
            platform="workday",
            manual_supported=True,
            assist_supported=False,
            auto_supported=False,
            resume_upload=False,
            profile_prefill=False,
            custom_questions=False,
            final_submission=False,
            status_fetch=False,
            notes="Client-side SPA; no fields ever parsed from a plain HTTP GET.",
        )

    def parse_form(self, form_html: str) -> List[FormField]:
        return []
