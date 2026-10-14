"""Match: the share of a job's stated requirements that a person's facts show (decision 047).

Built on the requirement review (spec 010), so the number in Jobs, Tailor and Tracker agrees with
the requirement-by-requirement list beside it. A profile that shows one requirement in ten
matches about 10%. It is Job Copilot's reading of the posting, not an employer's ATS score: no
universal ATS score exists, and each employer's system is set up differently (decision 032).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from functools import lru_cache
from typing import Mapping, Optional

from resume_tailorer.analyzers.ats_keywords import VOCABULARY, profile_text
from resume_tailorer.analyzers.job_analyzer import JobAnalysis, JobAnalyzer
from resume_tailorer.analyzers.requirement_review import (
    _YEARS, CHECK, DIRECT, MENTION, NONE, PARTIAL, TRANSFERABLE, UNCONFIRMED, RequirementReview, broad_only,
    build_review, is_work_authorization,
)
from resume_tailorer.job_search.models import (
    DIRECT_VERIFIED, FitEvidence, FitResult, JobPosting, TRANSFERABLE_PARTIAL, UNSUPPORTED, WEAK_INFERRED,
)
from resume_tailorer.models.career_profile import CareerTruthProfile

SCORING_VERSION = "match-v1"

# Direct evidence counts fully. Related experience in other words, or a skill only listed, counts
# half: it is real, but the posting's requirement isn't shown in a role. Facts not yet confirmed
# count nothing (decision 032). "Check yourself" rows (years, ambiguous wording) aren't counted.
CREDIT = {DIRECT: 1.0, TRANSFERABLE: 0.5, MENTION: 0.5, UNCONFIRMED: 0.0, NONE: 0.0}
SECTION_WEIGHT = {"required": 2.0, "preferred": 1.0}

MATCH_NOTE = (
    "Match is the share of this posting's stated requirements that your confirmed facts show. Required "
    "ones count twice as much as preferred ones. Direct evidence counts fully; related experience, a "
    "skill you only list, or a requirement shown only by one broad word counts half. A requirement to "
    "check yourself counts by the skills it names; years of experience and work authorization aren't "
    "counted. It's Job Copilot's reading of the posting, not an employer's ATS score: each employer's "
    "system is set up differently."
)

_LEVELS = {DIRECT: DIRECT_VERIFIED, TRANSFERABLE: TRANSFERABLE_PARTIAL, PARTIAL: TRANSFERABLE_PARTIAL,
           MENTION: WEAK_INFERRED}


@dataclass(frozen=True)
class Match:
    percent: Optional[float]  # None when the posting states nothing that can be counted
    required: Optional[float]
    preferred: Optional[float]
    to_check: int  # rows left for the person to check, not counted
    unconfirmed: int  # rows whose only evidence is in facts not yet confirmed


def row_credit(row) -> Optional[float]:
    """0-1 credit for one requirement row, or None when it isn't counted."""
    if is_work_authorization(row):
        return None  # eligibility, answered in Career Profile and shown as a hard requirement
    if row.status == CHECK:
        return _named_terms_credit(row)
    if broad_only(row):
        return 0.5
    if row.status == PARTIAL:
        named = [status for _term, status in row.term_status]
        shown = sum(status == DIRECT for status in named)
        # Some named terms shown: that share. General capability shown but not the named example: half.
        return shown / len(named) if shown else 0.5
    return CREDIT.get(row.status, 0.0)


def _named_terms_credit(row) -> Optional[float]:
    """A "check yourself" row (alternative wording, an unknown platform) still names terms the
    person may show: "SQL ... or R or Python" with SQL and Python shown is not unknown. Rows that
    name nothing (years) or only ambiguous acronyms stay uncounted (dogfood, 2026-10-13: 7 of 10
    rows uncounted made a 75% Match from the other 3)."""
    states = [status for _term, status in row.term_status if status != CHECK]
    if not states or _YEARS.search(row.text):
        return None  # years are the person's to check, whatever tools the row also names
    shown = sum(status == DIRECT for status in states)
    if row.term_relation == "any":
        return 1.0 if shown else 0.5 if MENTION in states else 0.0
    share = (shown + 0.5 * sum(status == MENTION for status in states)) / len(states)
    return max(share, 0.5) if shown else share


def match_from_review(review: RequirementReview) -> Match:
    totals = {section: [0.0, 0.0] for section in SECTION_WEIGHT}
    for row in review.rows:
        credit = row_credit(row)
        if credit is None or row.section not in totals:
            continue
        totals[row.section][0] += credit
        totals[row.section][1] += 1

    def share(section: str) -> Optional[float]:
        got, count = totals[section]
        return got / count * 100 if count else None

    weighted = sum(SECTION_WEIGHT[s] * got for s, (got, _n) in totals.items())
    possible = sum(SECTION_WEIGHT[s] * count for s, (_g, count) in totals.items())
    return Match(
        percent=weighted / possible * 100 if possible else None,
        required=share("required"), preferred=share("preferred"),
        to_check=sum(1 for r in review.rows if r.status == CHECK),
        unconfirmed=sum(1 for r in review.rows if r.status == UNCONFIRMED),
    )


def fit_from_review(review: RequirementReview) -> FitResult:
    """The Match in the FitResult shape every screen and snapshot already reads."""
    match = match_from_review(review)

    def one(value: Optional[float]) -> Optional[float]:
        return None if value is None else round(value, 1)

    rows = review.rows
    return FitResult(
        overall_fit=one(match.percent),
        core_capabilities=one(match.required),
        preferred_qualifications=one(match.preferred),
        strong_matches=[r.text for r in rows if r.status == DIRECT],
        partial_matches=[r.text for r in rows if r.status in (TRANSFERABLE, PARTIAL, MENTION)],
        true_gaps=[r.text for r in rows if r.status == NONE],
        unknown=[r.text for r in rows if r.status in (CHECK, UNCONFIRMED)],
        evidence=[FitEvidence(r.text, _LEVELS.get(r.status, UNSUPPORTED), r.evidence[0].text if r.evidence else "")
                  for r in rows],
        scoring_version=SCORING_VERSION,
    )


@lru_cache(maxsize=1024)
def _analysis(description: str) -> JobAnalysis:
    """A posting's analysis depends only on its text, so it is worked out once per posting."""
    return JobAnalyzer().analyze(description)


class MatchScorer:
    """Drop-in for the old CandidateFitScorer: `score_fit_detailed` returns a FitResult."""

    SCORING_VERSION = SCORING_VERSION

    def score_fit(self, profile: CareerTruthProfile, job: JobPosting,
                  provenance: Optional[Mapping[str, str]] = None) -> Optional[float]:
        return self.score_fit_detailed(profile, job, provenance=provenance).overall_fit

    def score_fit_detailed(self, profile: CareerTruthProfile, job: JobPosting,
                           provenance: Optional[Mapping[str, str]] = None) -> FitResult:
        description = (job.description or "").strip()
        if not description:
            return FitResult(overall_fit=None, scoring_version=SCORING_VERSION)
        analysis = _analysis(description)
        review = build_review(analysis, profile, provenance=provenance, posting=description)
        if match_from_review(review).percent is None and (analysis.skills_required or analysis.tools_required):
            # Nothing countable in its requirement list (only years, say): count the skills and tools it names.
            named = replace(analysis, structured_requirements=[], required_qualifications=[], preferred_qualifications=[])
            review = build_review(named, profile, provenance=provenance, posting=description)
        return fit_from_review(review)


# --- A quick first pass, to choose which of a large search's jobs get the full Match ----------

_TOKEN = re.compile(r"\.net\b|[a-z0-9][a-z0-9+#&./-]*[a-z0-9+#]|[a-z0-9]")


def _tokens(text: str) -> list[str]:
    return _TOKEN.findall((text or "").lower().replace("–", "-").replace("—", "-"))


@lru_cache(maxsize=1)
def _vocabulary_grams() -> tuple[dict[tuple[str, ...], str], int]:
    grams = {tuple(_tokens(key)): label for key, label in VOCABULARY.items() if len(key) > 1}
    return grams, max(len(g) for g in grams)


def quick_terms(text: str) -> frozenset[str]:
    """Vocabulary labels a text names, by word lookup: about 20 times faster than `terms_in`,
    and close enough to rank a search's jobs before the full Match."""
    grams, longest = _vocabulary_grams()
    words = _tokens(text)
    found = set()
    for start in range(len(words)):
        for size in range(1, longest + 1):
            label = grams.get(tuple(words[start:start + size]))
            if label:
                found.add(label)
    return frozenset(found)


def quick_match_score(profile: CareerTruthProfile, job: JobPosting, profile_terms: Optional[frozenset] = None) -> float:
    """The share of the posting's named terms the person's facts also name (0-1)."""
    have = profile_terms if profile_terms is not None else quick_terms(profile_text(profile))
    wanted = quick_terms(job.description or "")
    return len(wanted & have) / len(wanted) if wanted else 0.0
