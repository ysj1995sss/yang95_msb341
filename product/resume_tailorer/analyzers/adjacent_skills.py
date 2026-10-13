"""Reviewed adjacent skills (spec 022, change level 3).

Each group is a set of skills where knowing one makes the others quick to pick up, so a person
who lists one may honestly put another on their skills line when a job asks for it. A skills
line claims familiarity, never use at a particular job; level 3 additions never go in bullets.

This list is deliberately short and meant to be read by the builder. Add a group only when the
skills are close substitutes (two SQL dialects, two BI tools), never for a skill that merely
appears near another in job postings. Names use the spelling in ats_keywords.VOCABULARY.
"""

from __future__ import annotations

ADJACENT_GROUPS: tuple[tuple[str, ...], ...] = (
    ("SQL", "PostgreSQL", "MySQL", "SQL Server", "Oracle"),  # SQL and its dialects
    ("Snowflake", "BigQuery", "Redshift"),  # cloud data warehouses
    ("Tableau", "Power BI", "Looker"),  # BI and dashboard tools
    ("Python", "pandas", "NumPy"),  # Python's core data libraries
    ("AWS", "Azure", "Google Cloud"),  # cloud platforms, at a basics level
    ("Salesforce", "HubSpot"),  # CRMs
    ("Jira", "Asana"),  # work tracking
    ("JavaScript", "TypeScript"),
)


def adjacent_to(term: str) -> tuple[str, ...]:
    """The reviewed skills adjacent to `term` (case-insensitive), not including it."""
    key = term.strip().lower()
    for group in ADJACENT_GROUPS:
        if any(member.lower() == key for member in group):
            return tuple(member for member in group if member.lower() != key)
    return ()
