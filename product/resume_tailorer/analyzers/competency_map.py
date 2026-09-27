"""
Curated, hand-authored mapping from ABSTRACT COMPETENCIES to the concrete
evidence PATTERNS (regexes over verified profile text) that demonstrate
them -- e.g. "led a 10-person team", "100% on-time delivery", and "risk
mitigation" together demonstrate "project management" even though the
resume never uses that literal phrase.

This is the fix for a real, live-tested failure mode: the previous
matching logic was purely lexical (does the requirement's own literal
words appear in the resume?), so a job requirement phrased as "project
management" scored zero evidence against a resume that only ever
describes doing project-management WORK, never names it that way. That
produced badly-too-low fit scores and a tailoring pipeline that treated
clearly-transferable evidence as "unsupported."

Deliberately a CURATED table, not open-ended LLM synonym expansion --
Problem 2 of the fix request is explicit that arbitrary LLM-proposed
mappings must not be trusted without validation, so this file is the
validated, reviewable source of truth. If it's ever extended with
LLM-suggested candidates, those candidates get added here as a normal
code change (reviewed like any other), not consulted live and unvalidated.

Each competency's patterns are split into "strong" (specific, high-
confidence signals -- a name, a metric-shaped result, a named tool) and
"partial" (weaker, more generic signals) so callers can distinguish
LEVEL 3 "strongly supported" from LEVEL 2 "transferable/partial" evidence,
per the fix request's evidence-level model.

Also used by Candidate Fit (cf-v2, apps/api) so transferable evidence is
recognized there without loosening anti-fabrication standards.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from resume_tailorer.models import CareerTruthProfile
from resume_tailorer.utils.scoring import _QUALIFICATION_STOPWORDS
from resume_tailorer.utils.stemming import stem

# key: lowercase, human-readable competency name.
# "strong": patterns whose match alone is confident evidence.
# "partial": patterns that are suggestive but weaker alone, or that
#            usually co-occur with strong evidence.
COMPETENCY_EVIDENCE_PATTERNS: dict[str, dict[str, list[str]]] = {
    "project management": {
        "strong": [
            r"on-?time delivery",
            r"risk mitigation",
            r"workflow mapping",
            r"end-to-end",
            r"process bottleneck",
            r"project lifecycle",
            r"product lifecycle",
        ],
        "partial": [
            r"\bled\b.{0,15}\bteam\b",
            r"\bmanaged\b.{0,20}\b(deadline|timeline|workstream)",
            r"\bcoordinat\w*",
            r"\bmulti(ple)?\s*(project|initiative|workstream)",
        ],
    },
    "cross-functional leadership": {
        "strong": [r"cross-functional", r"cross-cultural"],
        "partial": [
            r"\baligned?\b.{0,20}\bstakeholders?\b",
            r"\bstakeholders?\b.{0,20}\bacross\b",
        ],
    },
    "stakeholder management": {
        "strong": [r"stakeholders?"],
        "partial": [
            r"\bsenior\b.{0,20}\bleaders?\b",
            r"\bexecutive\b.{0,20}\brecommendation",
        ],
    },
    "business analysis": {
        "strong": [
            r"\banaly(sis|zed|zing|tics)\b",
            r"data-driven",
            r"market (trend|research|entry)",
            r"diagnos\w*",
            r"\bnielsen\b",
            r"\bcircana\b",
        ],
        "partial": [r"\bidentif\w*\b.{0,25}\b(opportunit|challenge|insight|trend)"],
    },
    "data analytics": {
        "strong": [
            r"\btableau\b",
            r"power\s*bi",
            r"\bsql\b",
            r"\bexcel\b",
            r"data analytics",
            r"\bnielsen\b",
            r"\bcircana\b",
        ],
        "partial": [r"\bdata\b.{0,20}\b(insight|analysis|driven)"],
    },
    "translating insights into decisions": {
        "strong": [r"executive-ready recommendation", r"translat\w*.{0,20}insight"],
        "partial": [r"\bdistill\w*\b.{0,25}\brecommendation", r"data.{0,20}\bdecision"],
    },
    "executive communication": {
        "strong": [
            r"c-suite",
            r"\bvp\b.{0,15}leader",
            r"executive-ready",
            r"presented?\b.{0,25}\b(leadership|executive|senior)",
        ],
        "partial": [r"\bpresent\w*\b"],
    },
    "cpg experience": {
        "strong": [
            r"consumer packaged goods",
            r"\bcpg\b",
            r"\bnielsen\b",
            r"\bcircana\b",
            r"mondel[eē]z",
        ],
        "partial": [r"\bconsumer\b.{0,20}\b(good|product|brand)", r"\bretail\b"],
    },
    "financial acumen": {
        "strong": [r"\bp&l\b", r"profitabilit\w*", r"\bpricing\b.{0,20}strateg"],
        "partial": [r"\bbudget\w*", r"\brevenue\b", r"\bfinancial\b"],
    },
    "adaptability": {
        "strong": [r"fast-paced", r"dynamic environment"],
        "partial": [r"\bagil\w*", r"\bresilien\w*", r"\badapt\w*"],
    },
    "strategic thinking": {
        "strong": [r"go-to-market", r"market entry strateg", r"growth strateg"],
        "partial": [r"\bstrateg\w*"],
    },
    "product management": {
        "strong": [r"product lifecycle", r"concept to launch"],
        "partial": [r"\bproduct\b.{0,20}\b(launch|strategy|roadmap)"],
    },
    "customer insights": {
        "strong": [r"consumer research", r"customer journey", r"customer insight"],
        "partial": [r"\bcustomer\b.{0,20}\b(data|feedback|analytics)"],
    },
}


def extract_profile_sentences(profile: CareerTruthProfile) -> list[str]:
    """Individual bullets/sentences (not one flattened blob) for
    competency-map matching, so a match can quote a real, specific
    sentence as evidence. Shared by gap_analyzer, resume_benchmarker,
    docx_bullet_tailorer, and candidate_fit (cf-v2) so "what counts as
    searchable profile evidence" is defined once."""
    sentences: list[str] = []
    for job in profile.work_experience:
        sentences.extend(job.responsibilities)
        sentences.extend(job.accomplishments)
    for edu in profile.education:
        sentences.extend(getattr(edu, "notes", None) or [])
    if getattr(profile, "summary", None):
        sentences.append(profile.summary)
    sentences.extend(profile.accomplishments or [])
    return [s for s in sentences if s]


@dataclass
class TransferableEvidence:
    competency: str
    level: str  # "strong" | "partial"
    matched_pattern: str
    evidence_text: str  # the profile sentence/bullet the pattern matched in


# A competency-map word-matching token can come from a short acronym too,
# not just a 4+-letter word -- otherwise "cpg experience" has no usable
# identifying word at all once "experience" is excluded as a stopword ("cpg"
# itself is only 3 letters, below the regex used for ordinary words), making
# it permanently unmatchable. Mirrors scoring.py's _SHORT_TECH_ACRONYMS.
_SHORT_COMPETENCY_ACRONYMS = frozenset({"cpg"})


def _match_words(text: str) -> set[str]:
    """Stemmed content words (4+ letters, or a known short acronym) used
    for competency-map word-overlap matching, with generic connector words
    excluded so they can't trigger a match on their own."""
    lower = text.lower()
    long_words = re.findall(r"[a-z]{4,}", lower)
    short_acronyms = [w for w in re.findall(r"\b[a-z]{2,3}\b", lower) if w in _SHORT_COMPETENCY_ACRONYMS]
    return {stem(w) for w in long_words + short_acronyms if w not in _QUALIFICATION_STOPWORDS}


def _competency_keys_for(requirement_text: str) -> list[str]:
    """Which competency-map entries are even relevant to this requirement,
    by stemmed word overlap between the requirement and the competency's
    own name (e.g. requirement "cross-functional project management"
    overlaps both "project management" and "cross-functional leadership").
    Stemmed (not exact) so a plural/tense difference doesn't miss an
    otherwise-real match. Excludes generic connector words
    (_QUALIFICATION_STOPWORDS -- "experience", "years", "strong", etc.)
    from counting as a match on their own -- found live while adding
    normalize_concept() (2026-09-27): a pure years-of-experience gate like
    "4+ years of prior professional experience" was matching "cpg
    experience" purely because both happen to contain the word
    "experience", which would have let ANY candidate profile mentioning
    "retail" or "consumer" anywhere get credited as transferable evidence
    for a completely unrelated hard-eligibility requirement. Still won't
    bridge a derivational difference like "communicate" vs "communication"
    -- that needs a real lemmatizer, not this stemmer (see
    utils/stemming.py's own docstring)."""
    req_words = _match_words(requirement_text)
    scored: list[tuple[int, str]] = []
    for key in COMPETENCY_EVIDENCE_PATTERNS:
        key_words = _match_words(key)
        overlap = len(req_words & key_words)
        if overlap:
            scored.append((overlap, key))
    # Sort by overlap count descending (most specific match first) --
    # found live testing normalize_concept() (2026-09-27): "Strong
    # stakeholder management skills" shares the word "management" with
    # BOTH "project management" and "stakeholder management", and a caller
    # like normalize_concept() that just takes the first match picked
    # "project management" purely because it happens to be declared
    # earlier in COMPETENCY_EVIDENCE_PATTERNS, not because it's the better
    # fit -- "stakeholder management" shares 2 words (stakeholder,
    # management), "project management" only 1 (management). Stable sort
    # keeps dict declaration order as the tie-break for equal overlap
    # counts, same behavior as before for genuinely ambiguous cases.
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [key for _, key in scored]


def normalize_concept(requirement_text: str) -> str:
    """
    Map a JD requirement's phrasing onto a shared concept name using the
    SAME curated competency vocabulary the evidence-matching side already
    uses (ONE EVIDENCE MODEL, not a second synonym table) -- e.g.
    "communicate to senior leadership" and "present to executives" both
    normalize to "executive communication". Falls back to the requirement's
    own lowercased text when no competency-map entry is relevant, so every
    requirement still gets a normalized_concept, just not a shared one.
    """
    keys = _competency_keys_for(requirement_text)
    if keys:
        return keys[0]
    return requirement_text.strip().lower()


def find_transferable_evidence(
    requirement_text: str, profile_sentences: list[str]
) -> TransferableEvidence | None:
    """
    Search `profile_sentences` (individual bullets/responsibilities/
    accomplishments/notes -- NOT one giant blob, so the returned evidence
    is a real, quotable sentence) for evidence that transfers to
    `requirement_text`, using the curated competency map. Returns the
    single BEST match (strong preferred over partial), or None.
    """
    keys = _competency_keys_for(requirement_text)
    if not keys:
        return None

    best: TransferableEvidence | None = None
    for key in keys:
        patterns = COMPETENCY_EVIDENCE_PATTERNS[key]
        for level in ("strong", "partial"):
            if best is not None and best.level == "strong":
                break
            for pattern in patterns[level]:
                compiled = re.compile(pattern, re.IGNORECASE)
                for sentence in profile_sentences:
                    if compiled.search(sentence):
                        candidate = TransferableEvidence(
                            competency=key,
                            level=level,
                            matched_pattern=pattern,
                            evidence_text=sentence,
                        )
                        if best is None or (best.level == "partial" and level == "strong"):
                            best = candidate
                        break
    return best


_DEGREE_TYPE_RE = re.compile(
    r"\b(mba|m\.b\.a\.|master'?s?|bachelor'?s?|ph\.?d\.?|doctorate|juris doctor|j\.?d\.?)\b",
    re.IGNORECASE,
)


def find_education_status_evidence(
    requirement_text: str, profile: CareerTruthProfile
) -> str | None:
    """
    Recognize enrollment/degree-status requirements (e.g. "Currently enrolled
    in an accredited MBA program with an intended graduation of Spring 2027")
    directly against `profile.education`, instead of generic word-overlap.

    Found live (2026-09-23): a candidate with an actual in-progress MBA
    graduating 2027 still scored this requirement as a total gap, because
    "MBA" is only 3 letters (dropped by the 4+-letter word-overlap filter
    entirely) and the rest of the sentence is filler ("currently", "enrolled",
    "accredited", "intended", "graduation", "spring") that never appears
    verbatim in any resume, no matter how real the underlying fact is.

    Deliberately narrow: only fires when the requirement text plausibly
    names a degree/program at all (contains "degree", "program", "enrolled",
    "pursuing", or "graduat*"), so it never fires on an unrelated requirement
    that merely happens to mention a year.
    """
    req_lower = requirement_text.lower()
    if not re.search(r"\b(degree|program|enrolled|pursuing|graduat\w*)\b", req_lower):
        return None

    req_years = set(re.findall(r"\b(?:19|20)\d{2}\b", requirement_text))
    degree_match = _DEGREE_TYPE_RE.search(req_lower)

    for edu in profile.education:
        degree_lower = (edu.degree or "").lower()
        if degree_match:
            named = degree_match.group(1).replace(".", "").lower()
            if named == "mba":
                level_match = "mba" in degree_lower or "business administration" in degree_lower
            elif named.startswith("master"):
                level_match = "master" in degree_lower
            elif named.startswith("bachelor"):
                level_match = (
                    "bachelor" in degree_lower
                    or degree_lower.startswith("b.s")
                    or degree_lower.startswith("b.a")
                    or degree_lower == "bs"
                    or degree_lower == "ba"
                )
            elif named in ("phd", "doctorate"):
                level_match = "phd" in degree_lower or "doctor" in degree_lower
            else:  # juris doctor / jd
                level_match = "juris doctor" in degree_lower or degree_lower == "j.d."
            if not level_match:
                continue
        if req_years and str(edu.year) not in req_years:
            continue
        return f"{edu.degree}, {edu.institution} ({edu.year})"
    return None


def supported_competencies(profile_sentences: list[str]) -> dict[str, str]:
    """Every competency in the map with at least one match anywhere in the
    profile, mapped to its strongest evidence level ("strong"/"partial") --
    used to decide which Core Competencies items are safe to surface/swap
    in (Problem 6/10: 'competency abstraction', never inventing a new
    accomplishment, only naming one already demonstrated)."""
    results: dict[str, str] = {}
    for key, patterns in COMPETENCY_EVIDENCE_PATTERNS.items():
        for level in ("strong", "partial"):
            if key in results and results[key] == "strong":
                break
            for pattern in patterns[level]:
                compiled = re.compile(pattern, re.IGNORECASE)
                if any(compiled.search(s) for s in profile_sentences):
                    if key not in results or (results[key] == "partial" and level == "strong"):
                        results[key] = level
                    break
    return results
