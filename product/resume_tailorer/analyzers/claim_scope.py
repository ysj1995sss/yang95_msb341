"""A named tool elsewhere in a profile does not prove its use in this activity."""
from __future__ import annotations

import re

from resume_tailorer.analyzers.requirement_review import GENERIC_TERMS, _mentions_any, _search_forms, explicit_platform_terms
from resume_tailorer.models import CareerTruthProfile
from resume_tailorer.analyzers.ats_keywords import NAMED_TOOLS

# Reuse existing product/term spellings; generic capabilities are deliberately not products.
_TOOLS = NAMED_TOOLS
_ACTION = re.compile(r"\b(?:built|used|using|implemented|developed|created|delivered|designed|automated|led|managed|owned|improved|reduced|analyzed|analysed|performed)\b", re.I)


def _listing_context(text: str, labels: set[str]) -> tuple[str, ...]:
    """A list may reorder known terms, not introduce a new surrounding claim.

    Compare the non-list wording rather than pretending a finite verb list recognizes
    every activity. Section headings, separators and equivalent list lead-ins aren't facts.
    """
    text = re.sub(r'^\s*(?:summary|professional summary|skills|technical skills|tools|competencies)\s*\n', '', text, flags=re.I)
    for label in sorted(labels, key=len, reverse=True):
        for form in _search_forms(label):
            text = re.sub(rf'(?<![\w+#]){re.escape(form)}(?![\w+#])', ' ', text, flags=re.I)
    text = re.sub(r'\b(?:skills?|skilled|proficient|proficiency|familiar)\s*(?:in|with|of)?\b', ' ', text, flags=re.I)
    return tuple(word for word in re.findall(r'[\w+#]+', text.lower()) if word not in {'and', 'or'})


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
        tools.update(t for row in review.rows for t in explicit_platform_terms(row.text))
    added_context = any(role.employer.strip() and _mentions_any(role.employer, proposed)
                        and not _mentions_any(role.employer, original or '') for role in profile.work_experience)
    added_context = added_context or bool(re.search(r'\b(?:at|for|on|during)\b[^.;\n]*\b(?:project|client|employer)\b', proposed, re.I)
                                          and not re.search(r'\b(?:project|client|employer)\b', original or '', re.I))
    listing_sections = {'summary', 'skills', 'tools', 'competencies'}
    context_changed = section in listing_sections and _listing_context(original or '', tools | set(profile.skills)) != _listing_context(proposed, tools | set(profile.skills))
    list_section = section in {"skills", "tools", "competencies"} and not _ACTION.search(proposed) and not added_context and not context_changed
    summary_list = section == "summary" and not _ACTION.search(proposed) and bool(
        re.search(r"\b(?:skills?|skilled|proficien(?:t|cy)|familiar)\b", proposed, re.I)) and not added_context and not context_changed
    listed_facts = "\n".join([*profile.skills, *profile.tools])
    if list_section:
        # A skills line claims familiarity, not use in one job: a tool any role shows may be listed
        # (typing a bullet-proven "Tableau" into the skills line was refused, 2026-10-13).
        listed_facts += "\n" + "\n".join(text for job in profile.work_experience
                                         for text in [*job.responsibilities, *job.accomplishments])
    bare_summary_list = section == 'summary' and (original or '').count(',') >= 2 and not re.search(r'\b(?:who|which|that|where)\b', original or '', re.I)
    original_listing = (section in {'skills', 'tools', 'competencies'} or bare_summary_list or
                        (section == 'summary' and bool(re.search(r'\b(?:skills?|skilled|proficien(?:t|cy)|familiar)\b', original or '', re.I)))) and not _ACTION.search(original or '')
    promoted_use = ((original_listing and (bool(_ACTION.search(proposed)) or context_changed))
                    or (section in {'summary', 'skills', 'tools', 'competencies'} and added_context))
    issues = []
    for tool in sorted(tools, key=str.casefold):
        if not _mentions_any(tool, proposed) or (_mentions_any(tool, original or "") and not promoted_use):
            continue
        if (list_section or summary_list) and _mentions_any(tool, listed_facts):
            continue
        issues.append(f"{tool} appears elsewhere or is newly added, but we can't verify that you used it "
                      "in this project. Keep the original or update this project's facts in Career Profile.")
    return issues
