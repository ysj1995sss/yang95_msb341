"""Which of a posting's key terms already appear on the resume, and which don't.

This is a presence check for the Jobs page, not a score: Candidate Fit stays
the only fit measure. Terms come from a curated vocabulary of phrases that
applicant-tracking systems commonly screen for, matched as whole words or
phrases (so "Go" never matches inside "go-to-market"). Missing terms are shown
to the user; they are never added to a resume unless the user's own verified
facts support them.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable

# Lowercase canonical term -> display label. Aliases map several spellings to one term.
VOCABULARY: dict[str, str] = {
    # Marketing and growth
    "product marketing": "Product marketing", "go-to-market": "Go-to-market", "gtm": "Go-to-market",
    "positioning": "Positioning", "messaging": "Messaging", "market research": "Market research",
    "competitive analysis": "Competitive analysis", "competitive intelligence": "Competitive intelligence",
    "customer segmentation": "Customer segmentation", "segmentation": "Segmentation",
    "demand generation": "Demand generation", "lead generation": "Lead generation",
    "lifecycle marketing": "Lifecycle marketing", "growth marketing": "Growth marketing",
    "brand strategy": "Brand strategy", "brand marketing": "Brand marketing", "content strategy": "Content strategy",
    "content marketing": "Content marketing", "email marketing": "Email marketing", "seo": "SEO", "sem": "SEM",
    "paid media": "Paid media", "paid search": "Paid search", "performance marketing": "Performance marketing",
    "social media": "Social media", "campaign management": "Campaign management", "product launch": "Product launch",
    "launches": "Product launch", "sales enablement": "Sales enablement", "customer journey": "Customer journey",
    "customer insights": "Customer insights", "pricing": "Pricing", "partner marketing": "Partner marketing",
    "field marketing": "Field marketing", "storytelling": "Storytelling", "copywriting": "Copywriting",
    "b2b": "B2B", "b2c": "B2C", "saas": "SaaS", "ecommerce": "E-commerce", "e-commerce": "E-commerce",
    # Product and strategy
    "product management": "Product management", "product strategy": "Product strategy", "roadmap": "Roadmap",
    "roadmapping": "Roadmap", "user research": "User research", "requirements gathering": "Requirements gathering",
    "agile": "Agile", "scrum": "Scrum", "okrs": "OKRs", "kpis": "KPIs", "a/b testing": "A/B testing",
    "experimentation": "Experimentation", "business strategy": "Business strategy", "strategic planning": "Strategic planning",
    "business development": "Business development", "partnerships": "Partnerships", "p&l": "P&L",
    "forecasting": "Forecasting", "financial modeling": "Financial modeling", "budgeting": "Budgeting",
    "market sizing": "Market sizing", "business case": "Business case", "consulting": "Consulting",
    # Working with people
    "stakeholder management": "Stakeholder management", "cross-functional": "Cross-functional collaboration",
    "project management": "Project management", "program management": "Program management",
    "change management": "Change management", "executive communication": "Executive communication",
    "presentation": "Presentations", "presentations": "Presentations", "negotiation": "Negotiation",
    "people management": "People management", "team leadership": "Team leadership", "mentoring": "Mentoring",
    "customer success": "Customer success", "account management": "Account management",
    # Analytics and operations
    "data analysis": "Data analysis", "analytics": "Analytics", "dashboards": "Dashboards", "reporting": "Reporting",
    "sql": "SQL", "excel": "Excel", "tableau": "Tableau", "power bi": "Power BI", "looker": "Looker",
    "google analytics": "Google Analytics", "python": "Python", "r": "R", "statistics": "Statistics",
    "machine learning": "Machine learning", "operations": "Operations", "supply chain": "Supply chain",
    "process improvement": "Process improvement", "logistics": "Logistics", "vendor management": "Vendor management",
    "salesforce": "Salesforce", "hubspot": "HubSpot", "marketo": "Marketo", "crm": "CRM", "jira": "Jira",
    "figma": "Figma", "powerpoint": "PowerPoint",
    # Engineering (kept short; the job analyzer covers more)
    "javascript": "JavaScript", "typescript": "TypeScript", "react": "React", "aws": "AWS", "api": "APIs",
    "apis": "APIs", "kubernetes": "Kubernetes", "docker": "Docker", "golang": "Go",
    # Credentials
    "mba": "MBA", "pmp": "PMP", "cpa": "CPA",
}

# Single letters and very short tokens need standalone context to count.
_AMBIGUOUS = {"r"}


@dataclass(frozen=True)
class KeywordCheck:
    present: tuple[str, ...]
    missing: tuple[str, ...]

    @property
    def summary(self) -> str:
        total = len(self.present) + len(self.missing)
        if total == 0:
            return "No common screening keywords were found in this posting."
        return f"{len(self.present)} of {total} key terms already on your resume."


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower().replace("–", "-").replace("—", "-"))


def _pattern(term: str) -> re.Pattern:
    # Whole word/phrase; a neighbouring letter, digit or hyphen means it's part of something else.
    escaped = re.escape(term).replace(r"\ ", r"\s+")
    return re.compile(rf"(?<![\w-]){escaped}(?![\w-]|-\w)")


_PATTERNS = {term: _pattern(term) for term in VOCABULARY}


def terms_in(text: str) -> list[str]:
    """Display labels of vocabulary terms found in text, most frequent first."""
    norm = _normalize(text)
    counts: dict[str, int] = {}
    for term, label in VOCABULARY.items():
        if term in _AMBIGUOUS:
            hits = len(re.findall(rf"(?:^|[\s,(/]){re.escape(term)}(?=[\s,)/.;]|$)", norm))
        else:
            hits = len(_PATTERNS[term].findall(norm))
        if hits:
            counts[label] = counts.get(label, 0) + hits
    return sorted(counts, key=lambda label: (-counts[label], label))


def profile_text(profile: Any) -> str:
    """Every string in a career profile, for a presence check."""
    data = profile.to_dict() if hasattr(profile, "to_dict") else (profile or {})
    parts: list[str] = []

    def walk(value: Any) -> None:
        if isinstance(value, str):
            parts.append(value)
        elif isinstance(value, dict):
            for item in value.values():
                walk(item)
        elif isinstance(value, (list, tuple)):
            for item in value:
                walk(item)

    walk(data)
    return "\n".join(parts)


def check_keywords(posting: str, resume_text: str, limit: int = 20) -> KeywordCheck:
    """Key terms in the posting, split into already-on-resume and missing."""
    wanted = terms_in(posting)[:limit]
    have = set(terms_in(resume_text))
    return KeywordCheck(
        present=tuple(t for t in wanted if t in have),
        missing=tuple(t for t in wanted if t not in have),
    )
