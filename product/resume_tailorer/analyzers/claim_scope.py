"""A named tool elsewhere in a profile does not prove its use in this activity."""
from __future__ import annotations

import re

from resume_tailorer.analyzers.requirement_review import GENERIC_TERMS, _mentions_any
from resume_tailorer.models import CareerTruthProfile

# Reuse existing product/term spellings; generic capabilities are deliberately not products.
_TOOLS = {
    "SQL", "Excel", "Tableau", "Power BI", "Looker", "Google Analytics", "Python", "R",
    "Snowflake", "Salesforce", "HubSpot", "Marketo", "Jira", "Figma", "PowerPoint",
    "JavaScript", "TypeScript", "React", "AWS", "Kubernetes", "Docker", "Go",
    "Qualtrics", "SurveyMonkey", "SAP", "Oracle", "Workday", "QuickBooks", "Git",
    "PostgreSQL", "MySQL", "MongoDB", "Azure", "GCP", "SAS", "SPSS", "Stata",
}
_ACTION = re.compile(r"\b(?:built|used|using|implemented|developed|created|delivered|designed|automated)\b", re.I)


def introduced_unscoped_tools(original: str, proposed: str, profile: CareerTruthProfile, *,
                             section: str = "work_experience", review=None) -> list[str]:
    """Protect relationships, not profile-wide availability; unchanged source facts stay intact.

    No role is inferred by searching for the first equal string. An ambiguous/missing source
    therefore cannot authorize a new project/tool relationship. Skills can remain listed.
    """
    if not proposed:
        return []
    tools = set(_TOOLS)
    tools.update(t for t in profile.tools if t not in GENERIC_TERMS)
    tools.update(t for t in profile.skills if t not in GENERIC_TERMS
                 and (t in _TOOLS or re.search(r"[a-z][A-Z]", t)))
    if review:
        tools.update(t for row in review.rows for t in row.terms
                     if t in _TOOLS or re.search(r"[a-z][A-Z]", t))
    list_section = section in {"skills", "tools", "competencies"} and not _ACTION.search(proposed)
    summary_list = section == "summary" and not _ACTION.search(proposed) and bool(
        re.search(r"\b(?:skills?|skilled|proficien(?:t|cy)|familiar)\b", proposed, re.I))
    listed_facts = "\n".join([*profile.skills, *profile.tools])
    issues = []
    for tool in sorted(tools, key=str.casefold):
        if not _mentions_any(tool, proposed) or _mentions_any(tool, original or ""):
            continue
        if (list_section or summary_list) and _mentions_any(tool, listed_facts):
            continue
        issues.append(f"{tool} appears elsewhere or is newly added, but we can't verify that you used it "
                      "in this project. Keep the original or update this project's facts in Career Profile.")
    return issues
