"""Search wording and help shared by the Streamlit Jobs page and the web app (spec 013).

Board counts that follow the chosen sources, each added board's last result, which filters
are hiding roles, and broader titles a person can choose. Nothing here changes a search by
itself: suggestions fill the form, and the person searches again.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Callable, Dict, Iterable, List, Optional, Sequence

from resume_tailorer.job_search.board_links import PASTE_HINT, PLATFORM_LABELS
from resume_tailorer.job_search.custom_boards import MAX_CUSTOM_BOARDS, curated_boards
from resume_tailorer.ui.job_view import SPONSORSHIP_NOT_STATED

PLATFORMS = ("greenhouse", "lever", "ashby", "smartrecruiters")
FEW_RESULTS = 5

SOURCES_HELP = ("Each source searches the listed companies' own career boards, not every company on "
                "that platform. To search a company that isn't listed, add its career board.")
ADD_BOARD_HELP = ("Paste a link to a company's public job board on Greenhouse, Lever, Ashby or "
                  "SmartRecruiters, or a link to one of its jobs there. It's checked with the platform "
                  "before it's saved, and only you see it.")
COMPANY_FILTER_HELP = ("Comma-separated. Narrows results to companies already searched; it doesn't add "
                       "a company. To search one that isn't listed, add its career board.")
TITLE_RULE = "Titles must contain every word you typed, in any order."
SPONSORSHIP_HELP = ("Hides only jobs that say they don't sponsor. Most boards don't say either way, so "
                    "those jobs are kept and marked “Sponsorship not stated”.")
PASTE_PATH = PASTE_HINT
ADDED_BOARDS_LIMIT_TEXT = f"You can add up to {MAX_CUSTOM_BOARDS} boards."
CUSTOM_SOURCE = "custom"


def curated_count(platform: str) -> int:
    return len(curated_boards(platform))


def source_label(platform: str) -> str:
    return f"{PLATFORM_LABELS[platform]}: {curated_count(platform)} curated companies"


def added_source_label(count: int) -> str:
    return f"Your added boards: {count}"


def boards_in_scope(sources: Iterable[str], custom_boards: Sequence[dict], include_custom: bool = True) -> int:
    """How many boards a search with these choices will ask: curated boards on the ticked
    platforms, plus the person's added boards that aren't already among them."""
    chosen = {getattr(s, "value", s) for s in sources}
    total = sum(curated_count(p) for p in PLATFORMS if p in chosen)
    if include_custom:
        for b in custom_boards:
            curated = {t.lower() for t in curated_boards(b["platform"])}
            if not (b["platform"] in chosen and b["token"].lower() in curated):
                total += 1
    return total


def searching_text(count: int) -> str:
    return f"Searching {count} company board{'s' if count != 1 else ''}"


def _short_date(value: Optional[str]) -> str:
    try:
        return f"{datetime.fromisoformat(value):%b} {datetime.fromisoformat(value).day}"
    except (TypeError, ValueError):
        return ""


def board_status(board: dict) -> tuple[str, str]:
    """(text, tone) for an added board's last result. Tones: verified | review | blocked | neutral."""
    last = board.get("last_search") or {}
    when = _short_date(last.get("at"))
    on = f" ({when})" if when else ""
    status = last.get("status")
    if status == "ok":
        n = int(last.get("matched") or 0)
        return f"{n} matching role{'s' if n != 1 else ''} at the last search{on}", "verified"
    if status == "not_found":
        return (f"Not found at the last search{on}. The company may have moved boards; remove it or "
                "paste its new link.", "blocked")
    if status == "failed":
        return f"Didn't answer at the last search{on}. It will be tried again next time.", "review"
    n = int(board.get("postings_at_check") or 0)
    return f"Verified with {n} open posting{'s' if n != 1 else ''}; not searched yet", "neutral"


def board_view(board: dict) -> dict:
    text, tone = board_status(board)
    return {
        "id": board.get("id") or f"{board['platform']}:{board['token'].lower()}",
        "name": board.get("name") or board["token"],
        "platform": PLATFORM_LABELS.get(board["platform"], board["platform"]),
        "industry": board.get("industry") or "Not specified",
        "source_url": board.get("source_url") or "",
        "status": text,
        "tone": tone,
    }


def search_result_line(boards_searched: int, boards_failed: int, failed_added: Sequence[str] = ()) -> str:
    """'Searched 41 boards; 2 didn't answer, including Northwind (Greenhouse).'"""
    if not boards_searched:
        return ""
    line = f"Searched {boards_searched} board{'s' if boards_searched != 1 else ''}"
    if boards_failed:
        line += f"; {boards_failed} didn't answer"
        if failed_added:
            line += (", including " if boards_failed > len(failed_added) else ": ") + ", ".join(failed_added)
    return line + "."


def failed_added_boards(custom_boards: Sequence[dict], results: Dict[str, dict]) -> List[str]:
    """Names of added boards that failed in the last search, as 'Name (Platform)'."""
    names = []
    for b in custom_boards:
        outcome = results.get(f"{b['platform']}:{b['token'].lower()}") or {}
        if outcome.get("status") in ("failed", "not_found"):
            names.append(f"{b.get('name') or b['token']} ({PLATFORM_LABELS[b['platform']]})")
    return names


def searched_company_names(sources: Iterable[str], custom_boards: Sequence[dict]) -> set:
    chosen = {getattr(s, "value", s) for s in sources}
    names = {name.lower() for p in PLATFORMS if p in chosen for name, _ in curated_boards(p).values()}
    return names | {(b.get("name") or "").lower() for b in custom_boards}


def unknown_company_notes(target_companies: str, sources: Iterable[str], custom_boards: Sequence[dict]) -> List[str]:
    """A note for each "Only these companies" name that no searched board belongs to."""
    known = searched_company_names(sources, custom_boards)
    notes = []
    for name in (part.strip() for part in (target_companies or "").split(",")):
        if name and name.lower() not in known:
            notes.append(f"“{name}” isn't one of the boards searched, so it can't match. Add its career board?")
    return notes


# --- broader titles -----------------------------------------------------------------------

_SENIORITY = ["senior", "sr", "sr.", "junior", "jr", "jr.", "lead", "principal", "staff", "head",
              "i", "ii", "iii", "iv", "entry", "level", "associate"]
_FILLER = {"a", "an", "and", "the", "of", "for", "in", "to", "at", "on", "with", "or", "&", "-", "/", ","}


def broader_titles(title: str, limit: int = 3) -> List[str]:
    """Titles with one word dropped, seniority words first, for the person to choose from."""
    words = re.findall(r"[^\s,]+", (title or "").strip())
    meaningful = [i for i, w in enumerate(words) if w.lower() not in _FILLER]
    if len(meaningful) < 2:
        return []
    # The last non-seniority word names the role ("Manager", "Analyst"), so it stays.
    head = next((i for i in reversed(meaningful) if words[i].lower() not in _SENIORITY), None)
    order = sorted((i for i in meaningful if i != head),
                   key=lambda i: (_SENIORITY.index(words[i].lower())
                                  if words[i].lower() in _SENIORITY else len(_SENIORITY), i))
    found: List[str] = []
    for drop in order:
        rest = [w for i, w in enumerate(words) if i != drop]
        while rest and rest[0].lower() in _FILLER:
            rest.pop(0)
        while rest and rest[-1].lower() in _FILLER:
            rest.pop()
        candidate = " ".join(rest)
        if candidate and candidate.lower() != title.strip().lower() and candidate not in found:
            found.append(candidate)
        if len(found) >= limit:
            break
    return found


# --- what's narrowing the results ----------------------------------------------------------

def _active_filters(form: dict) -> List[tuple[str, str, dict]]:
    """(key, label, the form's values with that filter removed)."""
    found = []

    def without(**changes):
        return {**form, **changes}

    location = (form.get("location") or "").strip()
    if location:
        found.append(("location", f"Location “{location}”", without(location="")))
    mode = form.get("remote_preference") or "any"
    if mode != "any":
        found.append(("remote_preference", f"Work mode: {mode.replace('onsite', 'on-site')}",
                      without(remote_preference="any")))
    if form.get("sponsorship_required"):
        found.append(("sponsorship_required", "Needs visa sponsorship", without(sponsorship_required=False)))
    for key, name in (("experience_level", "Level"), ("industries", "Industry"), ("employment_type", "Job type")):
        values = [v for v in form.get(key) or [] if v]
        if values:
            found.append((key, f"{name}: {', '.join(values)}", without(**{key: []})))
    if int(form.get("min_salary") or 0) > 0:
        found.append(("min_salary", f"Minimum salary ${int(form['min_salary']):,}", without(min_salary=0)))
    if (form.get("target_companies") or "").strip():
        found.append(("target_companies", f"Only these companies: {form['target_companies'].strip()}",
                      without(target_companies="")))
    if (form.get("exclude_companies") or "").strip():
        found.append(("exclude_companies", f"Skip these companies: {form['exclude_companies'].strip()}",
                      without(exclude_companies="")))
    return found


def narrowing(form: dict, current: int, count: Callable[[dict], int]) -> List[dict]:
    """Each active filter that hides roles this search found, with how many.

    `count(form)` counts the same search's stored roles under other filter values (no new fetch).
    Shown only when there are fewer than FEW_RESULTS results."""
    if current >= FEW_RESULTS:
        return []
    found = []
    for key, label, relaxed in _active_filters(form):
        extra = count(relaxed) - current
        if extra > 0:
            found.append({"key": key, "label": label, "extra": extra,
                          "text": f"{label} is hiding {extra} more role{'s' if extra != 1 else ''}."})
    return sorted(found, key=lambda item: -item["extra"])


def cleared(form: dict, key: str) -> dict:
    """The form with one filter removed, for "Remove this filter"."""
    for found_key, _, relaxed in _active_filters(form):
        if found_key == key:
            return relaxed
    return dict(form)
