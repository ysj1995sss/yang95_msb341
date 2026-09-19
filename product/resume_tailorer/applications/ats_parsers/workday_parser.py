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
from resume_tailorer.applications.models import FormField


class WorkdayParser(BaseATSParser):
    """Reports Workday as unsupported; never extracts real fields."""

    def get_platform_name(self) -> str:
        return "workday"

    def is_supported(self) -> bool:
        return False

    def parse_form(self, form_html: str) -> List[FormField]:
        return []
