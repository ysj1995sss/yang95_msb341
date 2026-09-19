"""Greenhouse ATS form parser."""

from typing import List

from resume_tailorer.applications.ats_parsers.base_parser import BaseATSParser
from resume_tailorer.applications.models import FormField


class GreenhouseParser(BaseATSParser):
    """Parses Greenhouse job application forms."""

    def get_platform_name(self) -> str:
        return "greenhouse"

    def is_supported(self) -> bool:
        return True

    def parse_form(self, form_html: str) -> List[FormField]:
        return self._extract_fields(form_html)
