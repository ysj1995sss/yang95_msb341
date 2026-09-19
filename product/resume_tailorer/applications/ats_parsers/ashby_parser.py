"""Ashby ATS form parser."""

from typing import List

from resume_tailorer.applications.ats_parsers.base_parser import BaseATSParser
from resume_tailorer.applications.models import FormField


class AshbyParser(BaseATSParser):
    """Parses Ashby job application forms."""

    def get_platform_name(self) -> str:
        return "ashby"

    def is_supported(self) -> bool:
        return True

    def parse_form(self, form_html: str) -> List[FormField]:
        return self._extract_fields(form_html)
