"""
Curated mapping from abstract competencies to concrete evidence patterns
over verified profile text (e.g. "on-time delivery" + "risk mitigation"
demonstrate "project management").

Used by Candidate Fit (cf-v2) so transferable evidence is recognized
without loosening anti-fabrication standards.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from resume_tailorer.models import CareerTruthProfile

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
        ],
        "partial": [r"\bdata\b.{0,20}\b(insight|analysis|driven)"],
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
    "strategic thinking": {
        "strong": [r"go-to-market", r"market entry strateg", r"growth strateg"],
        "partial": [r"\bstrateg\w*"],
    },
    "product management": {
        "strong": [r"product lifecycle", r"concept to launch"],
        "partial": [r"\bproduct\b.{0,20}\b(launch|strategy|roadmap)"],
    },
}


def extract_profile_sentences(profile: CareerTruthProfile) -> list[str]:
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
    evidence_text: str


def _competency_keys_for(requirement_text: str) -> list[str]:
    req_words = set(re.findall(r"[a-z]{4,}", requirement_text.lower()))
    relevant = []
    for key in COMPETENCY_EVIDENCE_PATTERNS:
        key_words = set(re.findall(r"[a-z]{4,}", key))
        if req_words & key_words:
            relevant.append(key)
    return relevant


def find_transferable_evidence(
    requirement_text: str, profile_sentences: list[str]
) -> TransferableEvidence | None:
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
            else:
                level_match = "juris doctor" in degree_lower or degree_lower == "j.d."
            if not level_match:
                continue
        if req_years and str(edu.year) not in req_years:
            continue
        return f"{edu.degree}, {edu.institution} ({edu.year})"
    return None
