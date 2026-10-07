# Decision 035: People can add company career boards; search explains its filters

**Date:** 2026-10-06
**Status:** Active. This implements spec 013, which the builder approved with these choices: full
scope, sponsorship kept and labeled, 25 boards and 30 checks a day, links only.
**Builds on:** decisions 020 and 027.

## Context

Jobs searched only 75 curated boards. Typing a company in "Only these companies" filtered those
results, so a company that wasn't curated always gave zero results with no reason. "I need visa
sponsorship" required jobs that state sponsorship, but no live board states it. Both apps tick
that box from the profile, so anyone who needs sponsorship got zero results.

## Decisions

1. **Add a board by pasting its link** (`job_search/board_links.py`).
   - **What's accepted:** Greenhouse, Lever, Ashby and SmartRecruiters board or job links. The
     platform and identifier are read from the link's host and path only.
   - **What's called:** only the platform's fixed public API, with a checked identifier. The
     pasted URL is never fetched (no SSRF).
   - **Explained refusals:** company careers sites, EU-hosted boards, and Workday, iCIMS,
     Taleo, LinkedIn, Indeed and Handshake each get a plain message plus the paste-a-description
     path.
2. **Saved only when verified.**
   - **Greenhouse, Lever, Ashby:** a 404 means not found, and an empty board is real.
   - **SmartRecruiters:** it answers the same for an unknown company and an empty one, so it
     needs at least one posting.
   - **Never saved:** a board that didn't answer is never saved, and no demo or placeholder
     listing is ever shown.
3. **Stored per person** in the profile record (`custom_boards`, `job_search/custom_boards.py`).
   - **Why there:** both apps share it, and "Your data" export and delete already cover it.
     There's no schema change.
   - **Limits:** 25 boards per person, and 30 platform checks a day (`BOARD_CHECKS_PER_DAY`).
   - **Duplicates:** duplicates and curated boards are refused before any network call.
   - **Removing a board** keeps its jobs, triage and applications.
4. **Searched with the curated boards.**
   - **The scrapers** take `extra_boards` and `include_curated` per call. They report each
     board's result (ok, failed, not found) and the number of matches.
   - **Provenance:** a posting from an added board keeps its platform source and the platform's
     own link. It gains `raw_json["board"]` and shows "board you added".
   - **Searching added boards alone:** an added board is searched even when its platform's
     curated source is unticked. An API request without `sources` still means every curated
     source; an empty list means only the added boards.
5. **Counts and failures are accurate.** The board count follows the ticked sources and the
   added boards ("Searched 78 boards; 2 didn't answer, including Northwind (Greenhouse).").
   A board that isn't found is never removed automatically.
6. **Sponsorship keeps "not stated" jobs.** The filter now hides only jobs that state they don't
   sponsor. Unstated jobs are kept and labeled "Sponsorship not stated — check the posting", as
   decision 020 does for every other unknown.
7. **Company filters ignore case and surrounding spaces**, and they say they don't add a
   company. A name that matches no searched board is called out.
8. **Search help** (`ui/search_help.py`, shared by both apps).
   - **Fewer than 5 results:** each active filter is listed with how many of this search's
     stored roles it hides, and up to three broader titles are offered.
   - **How the titles are formed:** seniority words are dropped first, and the role's head noun
     is kept.
   - **Nothing changes by itself:** each suggestion is a button the person chooses ("Search
     without this filter", "Search 'Data Analyst'").

## Rejected

- **Guessing a board from a company name.** The same slug can belong to another company, which
  breaks provenance.
- **Fetching the company's careers page to find its board link.** It means fetching
  user-supplied URLs (SSRF) and parsing arbitrary HTML.
- **Workday, iCIMS and Taleo** in this round. They have no stable public JSON API. This is the
  largest remaining coverage gap.
- **Detecting "we don't sponsor" in posting text.** Wording rules miss phrasings and would hide
  real jobs. Maybe later, with labels instead of hiding.
- **Counts on the broader titles.** Titles that didn't match aren't stored, so any count would
  be a guess.

## Evidence

**Tests:**

| Suite | Passed |
|---|---|
| Product | 1,225 (1 skipped) |
| API | 132 |
| Web | lint and types clean |
| Playwright | 21, including the new board journey |

**Supervised run** (`discovery/experiments/2026-10-spec-013-custom-boards.md`): with real
Elastic (Greenhouse) and Watershed (Ashby) boards, a search went over 78 boards and found 111
and 3 labeled roles. Their links open the real postings.

## Still open

- **Real-data UI check:** the web interface wasn't clicked through by a person on real data.
- **EU-hosted boards** aren't supported: Greenhouse and Lever EU.
- **SmartRecruiters** boards with no openings can't be added.
- **Elastic's posting links repeat `gh_jid`.** This is older behavior and harmless.
- **No real user** has tried adding a board.
