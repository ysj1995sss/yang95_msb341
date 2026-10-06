"""The requirement review (spec 010): for each required and preferred qualification in a
posting, what evidence the candidate has, where exactly it is, and whether a resume shows it.

This is the guide for tailoring instead of a score. It never predicts an employer's ATS, and
it never treats a word in a skills list as proof. Statuses, from strongest to weakest:

- direct: the requirement's key term appears in a work, education or certification passage;
- transferable: a passage genuinely shows the capability in other words (competency map);
- mention: the term appears only in the skills or tools list or the summary;
- unconfirmed: the only evidence is in facts the person hasn't confirmed in Career Profile;
- check: a person must judge it (an ambiguous acronym, a years-of-experience threshold);
- none: nothing found. A missing requirement stays a visible gap, never a rewrite target.

Every status above "none" cites the exact passage it rests on. Pure functions, no I/O.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Mapping, Optional

from resume_tailorer.analyzers.ats_keywords import VOCABULARY, terms_in
from resume_tailorer.analyzers.competency_map import find_education_status_evidence, find_transferable_evidence
from resume_tailorer.analyzers.job_analyzer import JobAnalysis
from resume_tailorer.analyzers.term_match import mentions
from resume_tailorer.models import CareerTruthProfile
from resume_tailorer.utils.scoring import qualification_match_ratio

DIRECT = "direct"
TRANSFERABLE = "transferable"
MENTION = "mention"
UNCONFIRMED = "unconfirmed"
CHECK = "check"
NONE = "none"

STATUS_LABELS = {
    DIRECT: "Direct evidence",
    TRANSFERABLE: "Transferable evidence",
    MENTION: "Mentioned only",
    UNCONFIRMED: "Unconfirmed",
    CHECK: "Check yourself",
    NONE: "No evidence",
}
# Statuses whose evidence a tailored resume may make clearer. Everything else is never a target.
SUPPORTED = (DIRECT, TRANSFERABLE)

# Short acronyms with several common meanings in job postings. A match that rests only on one of
# these is never counted as evidence on its own: "PM" can be product or project management.
AMBIGUOUS_ACRONYMS: dict[str, tuple[str, ...]] = {
    "pm": ("product manag", "project manag", "program manag", "property manag"),
    "bi": ("business intelligence", "bisexual"),
    "crm": ("customer relationship", "client relationship"),
    "ml": ("machine learning", "milliliter"),
    "ar": ("accounts receivable", "augmented reality"),
    "sem": ("search engine marketing", "scanning electron"),
    "pr": ("public relations", "pull request"),
    "qa": ("quality assurance", "question"),
    "ops": ("operations", "devops"),
    "ea": ("executive assistant", "enterprise architect"),
}

# Broad concept words from the vocabulary. They help find a passage, but when a requirement names
# a specific tool or skill ("Tableau dashboards"), a generic word ("dashboards") never stands in
# for it.
GENERIC_TERMS = {
    "Analytics", "Dashboards", "Reporting", "Data analysis", "Presentations", "Operations",
    "Cross-functional collaboration", "Product launch", "Strategic planning", "Business strategy",
    "Partnerships", "Pricing", "Messaging", "Positioning", "Social media", "Storytelling", "KPIs",
    "Roadmap", "Customer insights", "Consulting", "Mentoring", "Negotiation", "Statistics",
    "Process improvement", "Business case", "Experimentation", "Customer journey", "Forecasting",
    "Budgeting", "Segmentation", "Project management", "Program management", "Change management",
    "Stakeholder management", "Team leadership", "People management", "Executive communication",
}

_YEARS = re.compile(r"\b(\d{1,2})\s*\+?\s*(?:-\s*\d{1,2}\s*)?years?\b", re.IGNORECASE)
_CREDENTIAL = re.compile(r"\b(licen[cs]e|licensed|certified|certification|clearance|registered)\b", re.IGNORECASE)


@dataclass(frozen=True)
class EvidenceRef:
    text: str  # the exact passage, never paraphrased
    source: str  # e.g. "Data Analyst at Acme, bullet 2" or "Skills list"
    path: str  # provenance path, e.g. "work_experience[0]"
    kind: str  # "experience" | "education" | "certification" | "skills" | "summary"
    confirmed: bool


@dataclass(frozen=True)
class RequirementRow:
    id: str
    text: str  # the posting's own sentence
    section: str  # "required" | "preferred"
    hard_gate: bool
    status: str
    terms: tuple[str, ...]
    evidence: tuple[EvidenceRef, ...]
    reason: str
    shown_in_resume: Optional[bool] = None  # None until a resume is checked

    @property
    def label(self) -> str:
        return STATUS_LABELS[self.status]

    @property
    def supported(self) -> bool:
        return self.status in SUPPORTED


@dataclass(frozen=True)
class RequirementReview:
    rows: tuple[RequirementRow, ...]
    computed_from: str = "run"  # "run" (at tailoring time) | "now" (rebuilt for an older review)

    def counts(self, section: str) -> tuple[int, int]:
        rows = [r for r in self.rows if r.section == section]
        return sum(1 for r in rows if r.supported), len(rows)

    @property
    def summary(self) -> str:
        req, req_total = self.counts("required")
        pref, pref_total = self.counts("preferred")
        parts = []
        if req_total:
            parts.append(f"Required: {req} of {req_total} with evidence")
        if pref_total:
            parts.append(f"Preferred: {pref} of {pref_total}")
        missing_gates = sum(1 for r in self.rows if r.hard_gate and r.section == "required" and r.status == NONE)
        if missing_gates:
            parts.append(f"{missing_gates} required credential or threshold not found")
        return " · ".join(parts) if parts else "No requirement list was found in this posting."

    @property
    def targets(self) -> tuple[RequirementRow, ...]:
        """Rows a tailored resume may make clearer: supported by confirmed evidence."""
        return tuple(r for r in self.rows if r.supported and r.evidence and all(e.confirmed for e in r.evidence))

    @property
    def not_to_add(self) -> tuple[RequirementRow, ...]:
        return tuple(r for r in self.rows if not r.supported)


@dataclass
class _Passage:
    text: str
    source: str
    path: str
    kind: str
    confirmed: bool = True

    def ref(self) -> EvidenceRef:
        return EvidenceRef(self.text, self.source, self.path, self.kind, self.confirmed)


def _confirmed(provenance: Optional[Mapping[str, str]], path: str) -> bool:
    """Untracked facts (no provenance given, or a path never tracked) count as the person's own."""
    if provenance is None or path not in provenance:
        return True
    return provenance[path] in ("confirmed", "edited")


def passages(profile: CareerTruthProfile, provenance: Optional[Mapping[str, str]] = None) -> list[_Passage]:
    out: list[_Passage] = []
    for i, job in enumerate(profile.work_experience):
        role = " at ".join(p for p in (job.title, job.employer) if p) or f"Role {i + 1}"
        for n, text in enumerate([*job.responsibilities, *job.accomplishments], start=1):
            if text and text.strip():
                out.append(_Passage(text.strip(), f"{role}, bullet {n}", f"work_experience[{i}]", "experience",
                                    _confirmed(provenance, f"work_experience[{i}]")))
    for i, edu in enumerate(profile.education):
        line = ", ".join(str(p) for p in (" ".join(x for x in (edu.degree, edu.field) if x), edu.institution, edu.year) if p)
        ok = _confirmed(provenance, f"education[{i}]")
        if line:
            out.append(_Passage(line, f"Education: {edu.institution or 'entry ' + str(i + 1)}", f"education[{i}]", "education", ok))
        for note in edu.notes or []:
            if note and note.strip():
                out.append(_Passage(note.strip(), f"Education: {edu.institution or 'entry ' + str(i + 1)}, note",
                                    f"education[{i}]", "education", ok))
    for cert in profile.certifications:
        if cert and cert.strip():
            out.append(_Passage(cert.strip(), "Certifications", "certifications", "certification",
                                _confirmed(provenance, "certifications")))
    for text in profile.accomplishments:
        if text and text.strip():
            out.append(_Passage(text.strip(), "Career accomplishments", "accomplishments", "experience", True))
    for key, items in (("skills", profile.skills), ("tools", profile.tools)):
        for item in items:
            if item and item.strip():
                out.append(_Passage(item.strip(), "Skills list" if key == "skills" else "Tools list", key, "skills",
                                    _confirmed(provenance, key)))
    if (profile.summary or "").strip():
        out.append(_Passage(profile.summary.strip(), "Summary", "summary", "summary", _confirmed(provenance, "summary")))
    return out


_CONTEXT_KINDS = ("experience", "education", "certification")


def requirement_terms(requirement: str, job_analysis: Optional[JobAnalysis] = None,
                      profile: Optional[CareerTruthProfile] = None) -> tuple[str, ...]:
    """The searchable terms a requirement names: curated vocabulary, the posting's own skills and
    tools, and the person's listed skills and tools found in this sentence."""
    found = list(terms_in(requirement))
    extra = [*job_analysis.skills_required, *job_analysis.tools_required] if job_analysis is not None else []
    if profile is not None:
        extra += [*profile.skills, *profile.tools]
    if extra:
        for term in extra:
            label = term.strip()
            if label and mentions(label, requirement) and label.lower() not in {f.lower() for f in found}:
                found.append(label)
    return tuple(dict.fromkeys(found))


def _search_forms(term: str) -> tuple[str, ...]:
    """A display label and every vocabulary spelling that maps to it ("Go-to-market" -> gtm too)."""
    forms = {term}
    for key, label in VOCABULARY.items():
        if label.lower() == term.lower():
            forms.add(key)
    return tuple(forms)


def _mentions_any(term: str, text: str) -> bool:
    return any(mentions(form, text) for form in _search_forms(term))


def _meaning(acronym: str, text: str) -> Optional[str]:
    lowered = text.lower()
    for expansion in AMBIGUOUS_ACRONYMS[acronym]:
        if expansion in lowered:
            return expansion
    return None


def _row(rid: str, text: str, section: str, hard_gate: bool, job_analysis: Optional[JobAnalysis],
         profile: CareerTruthProfile, all_passages: list[_Passage], posting: str) -> RequirementRow:
    terms = requirement_terms(text, job_analysis, profile)
    specific = tuple(t for t in terms if t not in GENERIC_TERMS)
    # The terms that decide direct evidence: the specific ones when there are any.
    deciding = specific or terms

    def make(status: str, evidence: Iterable[_Passage], reason: str) -> RequirementRow:
        refs = tuple(dict.fromkeys(p.ref() for p in evidence))[:3]
        return RequirementRow(rid, text, section, hard_gate, status, terms, refs, reason)

    def evaluate(pool: list[_Passage]) -> Optional[RequirementRow]:
        context = [p for p in pool if p.kind in _CONTEXT_KINDS]
        lists = [p for p in pool if p.kind not in _CONTEXT_KINDS]

        # Degrees and enrolment are checked against education itself.
        edu = find_education_status_evidence(text, profile)
        if edu:
            matching = [p for p in context if p.kind == "education"] or context
            return make(DIRECT, matching[:1], f"Matches your education: {edu}")

        # Ambiguous acronyms: never evidence unless both sides clearly mean the same thing.
        for acronym in [a for a in AMBIGUOUS_ACRONYMS if re.search(rf"\b{a}\b", text, re.IGNORECASE)]:
            term = acronym
            hits = [p for p in context + lists if re.search(rf"\b{acronym}\b", p.text, re.IGNORECASE)]
            if not hits:
                continue
            wanted = _meaning(acronym, text) or _meaning(acronym, posting)
            same = [p for p in hits if wanted and _meaning(acronym, p.text) == wanted]
            if not same:
                return make(CHECK, hits, f"“{term.upper()}” can mean different things; check that your experience "
                                         "means what this posting means before relying on it.")

        if deciding:
            direct = [p for p in context if any(_mentions_any(t, p.text) for t in deciding)]
            if direct:
                direct.sort(key=lambda p: -sum(_mentions_any(t, p.text) for t in deciding))
                shown = [t for t in deciding if any(_mentions_any(t, p.text) for p in direct)]
                missing = [t for t in deciding if t not in shown]
                reason = f"{', '.join(shown)} named in a passage that shows you using it."
                if missing:
                    reason += f" Not found: {', '.join(missing)}."
                return make(DIRECT, direct, reason)
        else:
            scored = sorted(((qualification_match_ratio(p.text, text), p) for p in context), key=lambda x: -x[0])
            if scored and scored[0][0] >= 0.6:
                return make(DIRECT, [scored[0][1]], "Most of this requirement's words appear in one passage.")

        # A named tool or skill can't be shown "in other words": no transferable credit for it.
        transferable = None if specific else find_transferable_evidence(text, [p.text for p in context])
        if transferable:
            hit = [p for p in context if p.text == transferable.evidence_text]
            strength = "Strongly shows" if transferable.level == "strong" else "Partly shows"
            return make(TRANSFERABLE, hit, f"{strength} “{transferable.competency}” in other words.")

        if deciding:
            listed = [p for p in lists if any(_mentions_any(t, p.text) for t in deciding)]
            if listed:
                return make(MENTION, listed, "Only listed, with no passage that shows you using it. "
                                             "It won't be built into new claims.")
        return None

    confirmed_pool = [p for p in all_passages if p.confirmed]
    found = evaluate(confirmed_pool)
    if found is None or found.status == MENTION:
        anywhere = evaluate(all_passages)
        if anywhere is not None and anywhere.status in SUPPORTED and any(not e.confirmed for e in anywhere.evidence):
            return RequirementRow(rid, text, section, hard_gate, UNCONFIRMED, terms, anywhere.evidence,
                                  "The only evidence is in facts you haven't confirmed. Confirm them in "
                                  "Career Profile first.")
    years = _YEARS.search(text)
    if found is not None and found.status in SUPPORTED and years:
        # The skill is shown; the number of years is the person's to check, not ours to assume.
        return RequirementRow(rid, text, section, hard_gate, found.status, terms, found.evidence,
                              f"{found.reason} It asks for {years.group(0)}: check your dates against it.")
    if found is not None:
        return found
    if years:
        return RequirementRow(rid, text, section, hard_gate, CHECK, terms, (),
                              f"Asks for {years.group(0)}. Job Copilot doesn't add up years for you; check your "
                              "dates against it.")
    reason = ("A required credential, license or degree that isn't in your Career Profile. It won't be added."
              if hard_gate or _CREDENTIAL.search(text) else
              "Not found in your Career Profile. It won't be added.")
    return RequirementRow(rid, text, section, hard_gate, NONE, terms, (), reason)


def build_review(job_analysis: JobAnalysis, profile: CareerTruthProfile, *,
                 provenance: Optional[Mapping[str, str]] = None, posting: str = "",
                 resume_text: Optional[str] = None, computed_from: str = "run") -> RequirementReview:
    """One row per required and preferred qualification (or, for a posting without those
    sections, per listed skill and tool), with linked evidence."""
    all_passages = passages(profile, provenance)
    items: list[tuple[str, str, bool]] = []
    structured = [r for r in job_analysis.structured_requirements if r.category == "qualification"]
    if structured:
        items = [(r.text, r.required_or_preferred, r.hard_gate) for r in structured]
    else:
        items = [(q, "required", False) for q in job_analysis.required_qualifications]
        items += [(q, "preferred", False) for q in job_analysis.preferred_qualifications]
    if not items:
        items = [(t, "required", False) for t in [*job_analysis.skills_required, *job_analysis.tools_required]]
    seen: set[str] = set()
    rows = []
    for n, (text, section, gate) in enumerate(items, start=1):
        key = re.sub(r"\s+", " ", text.strip().lower())
        if not key or key in seen:
            continue
        seen.add(key)
        rows.append(_row(f"r{n}", text.strip(), section, gate, job_analysis, profile, all_passages, posting))
    review = RequirementReview(tuple(sorted(rows, key=_order)), computed_from)
    return with_resume(review, resume_text) if resume_text is not None else review


def _order(row: RequirementRow) -> tuple:
    # Required first; within it, missing hard gates first so they're never buried.
    return (row.section != "required", not (row.hard_gate and row.status == NONE), int(row.id[1:]))


def shown_in(row: RequirementRow, resume_text: str) -> bool:
    if not resume_text:
        return False
    if row.terms and any(_mentions_any(t, resume_text) for t in row.terms):
        return True
    flat = _flat(resume_text)
    return any(_flat(e.text)[:60] in flat for e in row.evidence if e.kind in _CONTEXT_KINDS and len(e.text) > 20)


def _flat(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


def with_resume(review: RequirementReview, resume_text: str) -> RequirementReview:
    """The same review, with "shown in this resume" filled in for supported rows."""
    from dataclasses import replace

    rows = tuple(replace(r, shown_in_resume=shown_in(r, resume_text) if r.supported else None) for r in review.rows)
    return replace(review, rows=rows)
