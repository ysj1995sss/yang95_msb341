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
PARTIAL = "partial"  # some of the requirement's named terms have direct evidence, others don't

STATUS_LABELS = {
    DIRECT: "Direct evidence",
    TRANSFERABLE: "Transferable evidence",
    MENTION: "Mentioned only",
    UNCONFIRMED: "Unconfirmed",
    CHECK: "Check yourself",
    NONE: "No evidence",
    PARTIAL: "Partly supported",
}
# Statuses whose evidence a tailored resume may make clearer. Everything else is never a target.
# A partly supported row is a target only for its terms that have evidence.
SUPPORTED = (DIRECT, TRANSFERABLE, PARTIAL)
# Strongest first, for picking a term's best status across requirements.
_RANK = {DIRECT: 0, TRANSFERABLE: 1, PARTIAL: 1, UNCONFIRMED: 2, MENTION: 3, CHECK: 4, NONE: 5}

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
    # Spec 011
    "pa": ("physician assistant", "personal assistant", "pennsylvania"),
    "ot": ("occupational therap", "overtime"),
    "pt": ("physical therap", "part-time", "part time"),
    "da": ("data analyst", "district attorney", "dental assistant"),
    "cs": ("computer science", "customer success", "customer service"),
    "sa": ("solutions architect", "sales associate"),
    "ae": ("account executive", "after effects"),
    "am": ("account manag", "asset manag"),
    "ds": ("data scien", "dental surg"),
    "ux": ("user experience",),
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
    # Spec 011: concept words from the wider vocabulary (things you show by doing, not tools)
    "Data pipelines", "Data modeling", "Data warehousing", "Deep learning", "Microservices", "Unit testing",
    "Test automation", "Financial reporting", "Financial analysis", "Variance analysis", "Month-end close",
    "Reconciliations", "Audit", "Tax", "Valuation", "Patient care", "Acute care", "Medication administration",
    "Triage", "Case management", "Clinical documentation", "Inventory management", "Procurement", "Sourcing",
    "Demand planning", "Warehouse management", "Quality assurance", "Quality control", "Quota attainment",
    "Pipeline management", "Lead qualification", "Prospecting", "Upselling", "Renewals",
    "Customer retention", "Recruiting", "Onboarding", "Employee relations", "Compensation",
    "Benefits administration", "Payroll", "Curriculum development", "Lesson planning", "Classroom management",
    "Instructional design", "UX design", "UI design", "Wireframing", "Prototyping", "Accessibility",
    "Contract negotiation", "Contracts", "Compliance", "Regulatory compliance", "Litigation", "Cybersecurity",
}

# Degree levels: a posting's wording and the abbreviations resumes use for the same level.
_DEGREE_LEVELS = (
    ("bachelor's", r"\bbachelor'?s?\b|\bundergraduate degree\b",
     r"\b(?:b\.?s\.?|b\.?a\.?|b\.?sc\.?|b\.?b\.?a\.?|bachelor'?s?)(?![a-z])"),
    # Bare "MA"/"MS" are also state abbreviations ("Boston, MA"): only "MA in ...", "M.A." etc.
    ("master's", r"\bmaster'?s?\b|\bgraduate degree\b",
     r"\b(?:m\.s\.|m\.a\.|m\.?sc\b|mba\b|master'?s?\b|(?:ms|ma)\s+(?:in|of)\b)"),
    ("MBA", r"\bmba\b", r"\bmba\b"),
    ("doctorate", r"\bph\.?d\b|\bdoctora", r"\bph\.?d\b|\bdoctora"),
)
_HIGHER = {"bachelor's": ("master's", "MBA", "doctorate"), "master's": ("doctorate",), "MBA": (), "doctorate": ()}


def _degree_evidence(requirement: str, education: list) -> Optional[tuple]:
    """(passage, level) when the education shows the degree level a requirement asks for, or a
    higher one. The field of study is left for the person to check."""
    for level, wanted, _ in _DEGREE_LEVELS:
        if not re.search(wanted, requirement, re.IGNORECASE):
            continue
        acceptable = (level, *_HIGHER[level])
        for passage in education:
            for other, _w, has in _DEGREE_LEVELS:
                if other in acceptable and re.search(has, passage.text, re.IGNORECASE):
                    return passage, other
    return None


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
    # Spec 011: each named (specific) term's own status, e.g. (("SQL", "direct"), ("Tableau", "none")).
    # Empty for rows from before spec 011 and for rows named only in general words.
    term_status: tuple[tuple[str, str], ...] = ()

    @property
    def label(self) -> str:
        return STATUS_LABELS[self.status]

    @property
    def shown_terms(self) -> tuple[str, ...]:
        """The named terms this row's evidence supports (all its terms when none are tracked)."""
        if self.term_status:
            return tuple(t for t, st in self.term_status if st == DIRECT)
        return self.terms if self.supported else ()

    @property
    def supported(self) -> bool:
        return self.status in SUPPORTED


@dataclass(frozen=True)
class RequirementReview:
    rows: tuple[RequirementRow, ...]
    computed_from: str = "run"  # "run" (at tailoring time) | "now" (rebuilt for an older review)
    listed: tuple[str, ...] = ()  # requirement terms the person lists (skills, tools, summary)

    def counts(self, section: str) -> tuple[int, int]:
        rows = [r for r in self.rows if r.section == section]
        return sum(1 for r in rows if r.supported), len(rows)

    def partly(self, section: str) -> int:
        return sum(1 for r in self.rows if r.section == section and r.status == PARTIAL)

    @property
    def summary(self) -> str:
        req, req_total = self.counts("required")
        pref, pref_total = self.counts("preferred")
        parts = []
        if req_total:
            partly = self.partly("required")
            parts.append(f"Required: {req} of {req_total} with evidence" + (f" ({partly} only partly)" if partly else ""))
        if pref_total:
            partly = self.partly("preferred")
            parts.append(f"Preferred: {pref} of {pref_total}" + (f" ({partly} only partly)" if partly else ""))
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
        parts = [" ".join(x for x in (edu.degree, edu.field) if x), edu.institution]
        if edu.year and str(edu.year) not in (edu.institution or ""):
            parts.append(str(edu.year))
        line = ", ".join(p for p in parts if p)
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
    # The posting's own skills and tools count only when they're real terms: a posting without
    # known tools falls back to frequent words ("active", "required"), which aren't skills.
    # Each is mapped to its vocabulary label ("launches" -> "Product launch"), so a spelling
    # never passes for a separate, specific term.
    labels = {v.lower(): v for v in VOCABULARY.values()}
    extra = []
    for t in ([*job_analysis.skills_required, *job_analysis.tools_required] if job_analysis is not None else []):
        key = t.strip().lower()
        if key in VOCABULARY:
            extra.append(VOCABULARY[key])
        elif key in labels:
            extra.append(labels[key])
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


def _term_state(term: str, all_passages: list[_Passage]) -> str:
    """One named term's own status: direct when a confirmed work, education or certification
    passage names it; unconfirmed when only unconfirmed ones do; mention when only listed."""
    context = [p for p in all_passages if p.kind in _CONTEXT_KINDS and _mentions_any(term, p.text)]
    if any(p.confirmed for p in context):
        return DIRECT
    if context:
        return UNCONFIRMED
    if any(_mentions_any(term, p.text) for p in all_passages if p.kind not in _CONTEXT_KINDS):
        return MENTION
    return NONE


def _row(rid: str, text: str, section: str, hard_gate: bool, job_analysis: Optional[JobAnalysis],
         profile: CareerTruthProfile, all_passages: list[_Passage], posting: str) -> RequirementRow:
    """The row with each named term's own status (spec 011): a requirement whose named terms are
    only partly backed is "partly supported", never shown as fully evidenced."""
    from dataclasses import replace

    row = _row_status(rid, text, section, hard_gate, job_analysis, profile, all_passages, posting)
    specific = [t for t in row.terms if t not in GENERIC_TERMS]
    if not specific:
        return row
    states = tuple((t, CHECK if row.status == CHECK and t.lower() in AMBIGUOUS_ACRONYMS else _term_state(t, all_passages))
                   for t in specific)
    row = replace(row, term_status=states)
    if row.status == DIRECT and any(st != DIRECT for _t, st in states) and any(st == DIRECT for _t, st in states):
        shown = ", ".join(t for t, st in states if st == DIRECT)
        missing = "; ".join(f"{t} ({STATUS_LABELS[st].lower()})" for t, st in states if st != DIRECT)
        years = _YEARS.search(text)
        reason = f"Shown: {shown}. Not shown: {missing}." + (
            f" It asks for {years.group(0)}: check your dates against it." if years else "")
        row = replace(row, status=PARTIAL, reason=reason)
    return row


def _row_status(rid: str, text: str, section: str, hard_gate: bool, job_analysis: Optional[JobAnalysis],
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
        degree = _degree_evidence(text, [p for p in context if p.kind == "education"])
        if degree:
            return make(DIRECT, [degree[0]], f"Your education shows a {degree[1]} degree. Check that the field "
                                             "matches what the posting asks for.")

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
                return make(MENTION, listed, "Only listed, with no passage that shows you using it, so it "
                                             "won't be built into new claims. If you used it in a job, add that "
                                             "to the role in Career Profile.")
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
    list_text = [p.text for p in all_passages if p.kind not in _CONTEXT_KINDS]
    listed = tuple(dict.fromkeys(t for r in rows for t in r.terms if any(_mentions_any(t, x) for x in list_text)))
    review = RequirementReview(tuple(sorted(rows, key=_order)), computed_from, listed)
    return with_resume(review, resume_text) if resume_text is not None else review


def _order(row: RequirementRow) -> tuple:
    # Required first; within it, missing hard gates first so they're never buried.
    return (row.section != "required", not (row.hard_gate and row.status == NONE), int(row.id[1:]))


def shown_in(row: RequirementRow, resume_text: str) -> bool:
    """Whether the resume names this requirement. A row with terms is shown only when one of its
    terms appears: evidence written in other words ("led on-time delivery") is there, but the
    requirement ("project management") isn't named yet, and naming it is the improvement."""
    if not resume_text:
        return False
    if row.terms:
        return any(_mentions_any(t, resume_text) for t in row.terms)
    if row.evidence and all(e.kind in ("education", "certification") for e in row.evidence):
        return True  # a degree or credential sits in its own section; bullet edits can't add it
    flat = _flat(resume_text)
    return any(_flat(e.text)[:60] in flat for e in row.evidence if e.kind in _CONTEXT_KINDS and len(e.text) > 20)


def _flat(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


def with_resume(review: RequirementReview, resume_text: str) -> RequirementReview:
    """The same review, with "shown in this resume" filled in for supported rows."""
    from dataclasses import replace

    rows = tuple(replace(r, shown_in_resume=shown_in(r, resume_text) if r.supported else None) for r in review.rows)
    return replace(review, rows=rows)


# --- Using the review while tailoring (spec 010 steps 3-4) ---------------------------------

def _specific_terms(row: RequirementRow) -> list[str]:
    return [t for t in row.terms if t not in GENERIC_TERMS]


def _evidenced(row: RequirementRow) -> list[str]:
    """The terms of a supported row that its evidence actually shows (not every term it names:
    "SQL and Python" shown only through SQL doesn't support Python)."""
    if not row.supported:
        return []
    if row.term_status:
        shown = [t for t, st in row.term_status if st == DIRECT]
        return shown + [t for t in row.terms if t in GENERIC_TERMS]
    shown = [t for t in row.terms if any(_mentions_any(t, e.text) for e in row.evidence)]
    return shown + [t for t in row.terms if t in GENERIC_TERMS and t not in shown]


def _supported_terms(review: RequirementReview) -> set[str]:
    return {t.lower() for r in review.rows for t in _evidenced(r)}


def blocked_terms(review: RequirementReview) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """(never_add, list_only): specific terms a rewrite may not introduce. `never_add` comes from
    requirements with no supported evidence; `list_only` from terms that are only listed (they may
    stay in a skills list, never become a new claim in a bullet). A term some other requirement
    genuinely supports is never blocked."""
    supported = _supported_terms(review)
    never: list[str] = []
    listed: list[str] = []
    for r in review.rows:
        if r.supported:
            # A named term the evidence doesn't show is not supported by this row; it is
            # list-only when the person lists it, never-add otherwise.
            for t in _specific_terms(r):
                if t.lower() not in supported:
                    (listed if _is_listed(t, review) else never).append(t)
            continue
        terms = _specific_terms(r)
        if r.status == CHECK:
            terms += [a.upper() for a in AMBIGUOUS_ACRONYMS if re.search(rf"\b{a}\b", r.text, re.IGNORECASE)]
        for t in terms:
            if t.lower() in supported:
                continue
            (listed if r.status == MENTION else never).append(t)
    never = list(dict.fromkeys(never))
    listed = [t for t in dict.fromkeys(listed) if t not in never]
    return tuple(never), tuple(listed)


def _is_listed(term: str, review: RequirementReview) -> bool:
    return term in review.listed or any(r.status == MENTION and term in r.terms for r in review.rows)


def _is_list_line(text: str) -> bool:
    """A skills/tools style line: mostly short comma- or pipe-separated items."""
    stripped = re.sub(r"^[^:]{1,30}:\s*", "", (text or "").strip())
    items = [i.strip() for i in re.split(r"[,|•·;]", stripped) if i.strip()]
    return len(items) >= 3 and sum(len(i.split()) <= 4 for i in items) >= len(items) - 1


def introduced_unsupported(original: str, new: str, review: Optional[RequirementReview]) -> list[str]:
    """Terms `new` adds that the review doesn't support. Empty when the rewrite is safe."""
    if review is None or not new:
        return []
    never, listed = blocked_terms(review)
    problems = []
    for term in never:
        if _mentions_any(term, new) and not _mentions_any(term, original or ""):
            problems.append(f"adds “{term}”, which you haven't shown evidence for")
    for term in listed:
        if _mentions_any(term, new) and not _mentions_any(term, original or "") and not _is_list_line(new):
            problems.append(f"turns “{term}” from a listed skill into a claim; it's only listed in your profile")
    return problems


def format_for_prompt(review: RequirementReview, resume_text: Optional[str] = None) -> str:
    """The requirement review for a tailoring prompt: what to make clearer (with the exact
    evidence) and what never to add. Missing requirements are named only as things to leave out."""
    current = with_resume(review, resume_text) if resume_text is not None else review
    lines = ["MAKE CLEARER (the candidate has confirmed evidence; improve terminology, context, "
             "responsibility or outcome ONLY where the quoted evidence supports it):"]
    targets = [r for r in current.targets]
    if not targets:
        lines.append("  (none)")
    for r in targets:
        state = " [already shown; keep it]" if r.shown_in_resume else ""
        lines.append(f"  - [{r.id}] {r.section.upper()}: {r.text}{state}")
        if r.status == PARTIAL:
            lines.append(f"    Only these named terms are supported: {', '.join(r.shown_terms)}. "
                         "Never add the others.")
        for e in r.evidence:
            lines.append(f"    Evidence ({e.source}): \"{e.text}\"")
    lines += ["", "DO NOT ADD (no supported evidence; never claim these, never insert their terms):"]
    never, listed = blocked_terms(review)
    for r in review.not_to_add:
        lines.append(f"  - {r.section.upper()}: {r.text} ({STATUS_LABELS[r.status]})")
    if listed:
        lines.append(f"  Only listed as skills, so they may stay in a skills list but must not be added to "
                     f"any bullet: {', '.join(listed)}")
    if never:
        lines.append(f"  Never add these terms anywhere new. Where one already appears in the resume, keep it exactly "
                     f"as it is; never delete a true fact: {', '.join(never)}")
    unshown = [r.id for r in targets if not r.shown_in_resume]
    if unshown:
        lines += ["", "ANSWER EVERY TARGET THAT ISN'T SHOWN YET (" + ", ".join(unshown) + "): either make it clearer "
                  "in a rewrite, or add one object to the same JSON array saying why no safe rewrite exists: "
                  '{"target": "<id>", "no_safe_rewrite": "<one short sentence>"}.']
    return "\n".join(lines)


def unshown_targets(review: RequirementReview, resume_text: str) -> list[RequirementRow]:
    """Supported requirements this resume doesn't show yet: the only things a refinement round
    may work on."""
    return [r for r in with_resume(review, resume_text).targets if not r.shown_in_resume]


# --- Keyword report (spec 011) ---------------------------------------------------------------

LEFT_OUT_REASONS = {
    "not_named": "You have evidence, not named yet",
    MENTION: "Only listed in your skills",
    UNCONFIRMED: "Not confirmed yet",
    CHECK: "Check yourself",
    NONE: "No evidence (never added)",
}


@dataclass(frozen=True)
class KeywordReport:
    added: tuple[str, ...]  # named by this version, not by the original
    already: tuple[str, ...]  # named by both
    left_out: tuple[tuple[str, str], ...]  # (term, reason key from LEFT_OUT_REASONS)


def term_states(review: RequirementReview) -> dict[str, str]:
    """Every requirement term with its best status across the review, in review order."""
    best: dict[str, str] = {}
    for r in review.rows:
        pairs = list(r.term_status) or [(t, r.status) for t in r.terms]
        if r.term_status:  # general words of a tracked row follow the row
            pairs += [(t, r.status) for t in r.terms if t in GENERIC_TERMS]
        for term, state in pairs:
            if term not in best or _RANK[state] < _RANK[best[term]]:
                best[term] = state
    return best


def keyword_report(review: RequirementReview, original_text: str, tailored_text: str) -> KeywordReport:
    """Which of the posting's terms this version added, which it already had, and which are left
    out and why. Only terms that the posting's requirements name are counted."""
    added, already, left = [], [], []
    for term, state in term_states(review).items():
        now = _mentions_any(term, tailored_text or "")
        before = _mentions_any(term, original_text or "")
        if now and not before:
            added.append(term)
        elif now:
            already.append(term)
        else:
            left.append((term, "not_named" if state in SUPPORTED else state))
    order = list(LEFT_OUT_REASONS)
    left.sort(key=lambda pair: order.index(pair[1]))
    return KeywordReport(tuple(added), tuple(already), tuple(left))


def profile_text_for_report(profile: CareerTruthProfile) -> str:
    """The original resume's facts as one text, for "what did this version add"."""
    return "\n".join(p.text for p in passages(profile))
