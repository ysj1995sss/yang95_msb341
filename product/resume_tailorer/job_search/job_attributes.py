"""Derive filterable attributes (industry, experience level, job type) for a
posting, and apply the user's goal filters to a list of postings.

Nothing here guesses. An attribute is only set when it is stated: industry
comes from a curated company directory, level and job type only from explicit
words in the title. Anything not stated is NOT_SPECIFIED, and an unspecified
job is kept by a filter rather than hidden -- except where noted.
"""

import re
from typing import Dict, Iterable, List, Set

from resume_tailorer.job_search.models import JobPosting, SearchGoals

NOT_SPECIFIED = "Not specified"

# Greenhouse board token -> (display name, industry). Confirmed live on 2026-09-29.
COMPANY_DIRECTORY: Dict[str, tuple] = {
    "airbnb": ("Airbnb", "Travel & Hospitality"),
    "gitlab": ("GitLab", "Technology"),
    "datadog": ("Datadog", "Technology"),
    "cloudflare": ("Cloudflare", "Technology"),
    "figma": ("Figma", "Technology"),
    "mongodb": ("MongoDB", "Technology"),
    "okta": ("Okta", "Technology"),
    "twilio": ("Twilio", "Technology"),
    "asana": ("Asana", "Technology"),
    "dropbox": ("Dropbox", "Technology"),
    "databricks": ("Databricks", "Technology"),
    "anthropic": ("Anthropic", "Technology"),
    "scaleai": ("Scale AI", "Technology"),
    "vercel": ("Vercel", "Technology"),
    "coinbase": ("Coinbase", "Finance"),
    "robinhood": ("Robinhood", "Finance"),
    "affirm": ("Affirm", "Finance"),
    "brex": ("Brex", "Finance"),
    "chime": ("Chime", "Finance"),
    "sofi": ("SoFi", "Finance"),
    "block": ("Block", "Finance"),
    "oscar": ("Oscar Health", "Healthcare"),
    "zocdoc": ("Zocdoc", "Healthcare"),
    "flatironhealth": ("Flatiron Health", "Healthcare"),
    "duolingo": ("Duolingo", "Education"),
    "reddit": ("Reddit", "Media"),
    "pinterest": ("Pinterest", "Media"),
    "discord": ("Discord", "Media"),
    "instacart": ("Instacart", "Retail"),
    "faire": ("Faire", "Retail"),
    "glossier": ("Glossier", "Retail"),
    "sweetgreen": ("Sweetgreen", "Food & Beverage"),
    "hellofresh": ("HelloFresh", "Food & Beverage"),
    "lyft": ("Lyft", "Transportation"),
    "waymo": ("Waymo", "Transportation"),
    "peloton": ("Peloton", "Consumer Goods"),
}

# Lever board token -> (display name, industry). Confirmed live on 2026-09-30.
LEVER_BOARDS: Dict[str, tuple] = {
    "spotify": ("Spotify", "Media"),
    "palantir": ("Palantir", "Technology"),
    "wealthfront": ("Wealthfront", "Finance"),
    "zoox": ("Zoox", "Transportation"),
    "ro": ("Ro", "Healthcare"),
    "matchgroup": ("Match Group", "Media"),
    "tala": ("Tala", "Finance"),
    "jumpcloud": ("JumpCloud", "Technology"),
}

# Ashby job-board name -> (display name, industry). Confirmed live on 2026-09-30.
ASHBY_BOARDS: Dict[str, tuple] = {
    "openai": ("OpenAI", "Technology"),
    "notion": ("Notion", "Technology"),
    "ramp": ("Ramp", "Finance"),
    "linear": ("Linear", "Technology"),
    "vanta": ("Vanta", "Technology"),
    "zapier": ("Zapier", "Technology"),
    "multiverse": ("Multiverse", "Education"),
    "cursor": ("Cursor", "Technology"),
    "perplexity": ("Perplexity", "Technology"),
    "replit": ("Replit", "Technology"),
    "posthog": ("PostHog", "Technology"),
    "sentry": ("Sentry", "Technology"),
    "plaid": ("Plaid", "Finance"),
    "docker": ("Docker", "Technology"),
    "supabase": ("Supabase", "Technology"),
    "benchling": ("Benchling", "Technology"),
    "harvey": ("Harvey", "Technology"),
    "elevenlabs": ("ElevenLabs", "Technology"),
    "cohere": ("Cohere", "Technology"),
}

# SmartRecruiters company id -> (display name, industry). Confirmed live on 2026-10-04.
SMARTRECRUITERS_BOARDS: Dict[str, tuple] = {
    "AbbVie": ("AbbVie", "Healthcare"),
    "Equinox": ("Equinox", "Consumer Goods"),
    "ServiceNow": ("ServiceNow", "Technology"),
    "BoschGroup": ("Bosch Group", "Technology"),
    "NBCUniversal3": ("NBCUniversal", "Media"),
    "LinkedIn3": ("LinkedIn", "Technology"),
    "Continental": ("Continental", "Transportation"),
    "WesternDigital": ("Western Digital", "Technology"),
    "Wise": ("Wise", "Finance"),
    "Experian": ("Experian", "Finance"),
    "Canva": ("Canva", "Technology"),
    "Ubisoft2": ("Ubisoft", "Media"),
}

_ALL_COMPANIES = [*COMPANY_DIRECTORY.values(), *LEVER_BOARDS.values(), *ASHBY_BOARDS.values(),
                  *SMARTRECRUITERS_BOARDS.values()]
LIVE_BOARD_COUNT = len(_ALL_COMPANIES)
INDUSTRY_OPTIONS = sorted({industry for _, industry in _ALL_COMPANIES})
_INDUSTRY_BY_COMPANY = {name.lower(): industry for name, industry in _ALL_COMPANIES}

EXPERIENCE_LEVEL_OPTIONS = ["internship", "entry", "mid", "senior", "lead", "executive"]
EMPLOYMENT_TYPE_OPTIONS = ["full-time", "part-time", "contract", "internship"]

# Ordered: the first matching rule wins, most senior first.
_LEVEL_RULES = [
    ("internship", r"\bintern(ship)?\b|\bco-?op\b"),
    ("executive", r"\b(chief|vp|vice president|svp|evp|head of)\b|\bc[a-z]o\b"),
    ("lead", r"\b(director|principal|staff|lead)\b"),
    ("senior", r"\b(senior|sr\.?)\b"),
    ("entry", r"\b(junior|jr\.?|entry[- ]level|new grad(uate)?|associate)\b"),
]
_TYPE_RULES = [
    ("internship", r"\bintern(ship)?\b|\bco-?op\b"),
    ("contract", r"\b(contract|contractor|temporary|temp)\b"),
    ("part-time", r"\bpart[- ]time\b"),
]


def industry_for(job: JobPosting) -> str:
    return _INDUSTRY_BY_COMPANY.get((job.company or "").strip().lower(), NOT_SPECIFIED)


def experience_level_for(job: JobPosting) -> str:
    title = (job.title or "").lower()
    for level, pattern in _LEVEL_RULES:
        if re.search(pattern, title):
            return level
    return NOT_SPECIFIED


def employment_type_for(job: JobPosting) -> str:
    if job.employment_type:
        return job.employment_type
    title = (job.title or "").lower()
    for job_type, pattern in _TYPE_RULES:
        if re.search(pattern, title):
            return job_type
    return NOT_SPECIFIED


_TITLE_STOPWORDS = {"a", "an", "and", "the", "of", "for", "in", "to", "at", "on", "with", "or", "&", "-", "/"}


def title_keywords(goal_title: str) -> List[str]:
    return [
        word
        for word in re.findall(r"[\w+#.&/-]+", (goal_title or "").lower())
        if word not in _TITLE_STOPWORDS
    ]


def title_matches(goal_title: str, job_title: str) -> bool:
    """Every meaningful word of the goal title appears as a whole word in the job title, in any order."""
    lowered = (job_title or "").lower()
    return all(
        re.search(rf"(?<![\w]){re.escape(keyword)}(?![\w])", lowered)
        for keyword in title_keywords(goal_title)
    )


def selected_values(raw) -> Set[str]:
    """Normalize a multi-select value (list or comma-separated str); 'any'/blank means no filter."""
    if raw is None:
        return set()
    items: Iterable[str] = raw if isinstance(raw, (list, tuple, set)) else str(raw).split(",")
    values = {str(item).strip().lower() for item in items if str(item).strip()}
    values.discard("any")
    return values


def apply_goal_filters(jobs: List[JobPosting], goals: SearchGoals) -> List[JobPosting]:
    industries = selected_values(goals.industries)
    levels = selected_values(goals.experience_level)
    job_types = selected_values(goals.employment_type)

    kept = []
    for job in jobs:
        if goals.job_title and not title_matches(goals.job_title, job.title):
            continue
        if industries and not _passes_industry(industry_for(job), industries):
            continue
        if levels and not _passes_level(experience_level_for(job), levels):
            continue
        if job_types and not _passes_type(employment_type_for(job), job_types):
            continue
        kept.append(job)
    return kept


def _passes_industry(value: str, selected: Set[str]) -> bool:
    return value == NOT_SPECIFIED or value.lower() in selected


def _passes_level(value: str, selected: Set[str]) -> bool:
    if value == NOT_SPECIFIED:
        # Internships are always labeled in the title, so an unlabeled job is
        # not one; any other unstated level is kept rather than hidden.
        return selected != {"internship"}
    return value in selected


def _passes_type(value: str, selected: Set[str]) -> bool:
    if value == NOT_SPECIFIED:
        # An unlabeled posting is kept for full-time searches only; part-time,
        # contract and internship roles say so in the title.
        return "full-time" in selected
    return value in selected
