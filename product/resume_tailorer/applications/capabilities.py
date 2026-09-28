"""Look up an ATS platform's capability declaration without needing a full
SubmissionEngine -- used by the Streamlit UI to disable "Confirm & Submit"
proactively (spec 003 Step 21), not just after a failed attempt.
"""

from resume_tailorer.applications.ats_parsers.ashby_parser import AshbyParser
from resume_tailorer.applications.ats_parsers.greenhouse_parser import GreenhouseParser
from resume_tailorer.applications.ats_parsers.lever_parser import LeverParser
from resume_tailorer.applications.ats_parsers.workday_parser import WorkdayParser
from resume_tailorer.applications.models import ATSCapability

_PARSER_MAP = {
    "greenhouse": GreenhouseParser,
    "lever": LeverParser,
    "ashby": AshbyParser,
    "workday": WorkdayParser,
}


def get_capability(ats_platform: str) -> ATSCapability:
    """Return the declared capability for a platform, or a manual-only
    fallback for an unrecognized/empty platform name (never assume more
    than Manual works for a platform this codebase has no parser for)."""
    parser_class = _PARSER_MAP.get((ats_platform or "").lower())
    if parser_class is None:
        return ATSCapability(platform=ats_platform or "unknown", notes="Unrecognized platform; Manual mode only.")
    return parser_class().get_capability()
