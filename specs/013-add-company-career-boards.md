# Spec 013: Add a company career board, and search that explains itself

**Status:** Implemented and locally verified on 2026-10-06; see decision 035 and `discovery/experiments/2026-10-spec-013-custom-boards.md`. Not pushed yet.
**Builds on:** decisions 020 (real results only, goal filters) and 027 (sources, search speed,
SmartRecruiters).

## Problem and evidence

Jobs searches a fixed list of 75 public company boards in `job_search/job_attributes.py`:

| Platform | Boards |
|---|---|
| Greenhouse | 36 (`COMPANY_DIRECTORY`) |
| Lever | 8 (`LEVER_BOARDS`) |
| Ashby | 19 (`ASHBY_BOARDS`) |
| SmartRecruiters | 12 (`SMARTRECRUITERS_BOARDS`) |

A person whose target employer isn't on that list has no way to search it. They can only paste
the job description into Tailor.

What the code does today (checked on 2026-10-06 against `main` at `225499d`):

1. **The four source checkboxes pick platforms, not all companies on them.** "Greenhouse (36
   companies)" means those 36 curated boards. Greenhouse, Lever and Ashby have no public
   "all companies" listing, so a platform-wide search isn't possible.
2. **"Only these companies" is a filter, not a way to add a company.**
   `JobDatabase.search_jobs` runs `company IN (...)` over postings that the curated boards
   already returned.
   - The match is exact and case-sensitive: "acme retail" and "Acme" both miss "Acme Retail".
   - Typing a company that isn't curated always gives zero results, and nothing says why.
3. **The title must contain every meaningful word you typed** (`title_matches`; only filler
   words like "of" and "the" are ignored). For example:
   - "Senior Data Analyst" misses "Data Analyst".
   - "Data Analyst II" misses "Data Analyst".
   - "Product Marketing Manager" misses "Product Marketing Lead".
4. **"I need visa sponsorship" hides every live job.**
   - The SQL requires `sponsorship_available = 1`, but no live board states sponsorship, so
     every live job stores `NULL`.
   - Both apps turn the checkbox on by default from the profile's work-authorization answer
     (`ui/onboarding.py`; `search_setup` in `jobs_router.py`). A person who said they need
     sponsorship gets zero results in every search.
   - Confirmed with a temp database: the same job is returned without the filter and is gone
     with it.
5. **Location is a plain substring match** (`location LIKE %x%`). "New York" misses "NYC" and
   "Remote - US".
6. **The board count doesn't follow the selected sources.** "Searching 75 company boards" stays
   fixed whichever sources are ticked (`LIVE_BOARD_COUNT`). After a search, only an aggregate
   note such as "3 of 36 company boards did not respond" is kept, never which boards.

Board APIs, probed live on 2026-10-06:

| Platform | Unknown board | Real board with no postings |
|---|---|---|
| Greenhouse `boards-api.greenhouse.io/v1/boards/{token}` | 404 "Job board not found" | 200, and the board endpoint states the company name |
| Lever `api.lever.co/v0/postings/{token}` | 404 | 200 `[]` |
| Ashby `api.ashbyhq.com/posting-api/job-board/{name}` | 404 | 200 `{"jobs": []}` |
| SmartRecruiters `api.smartrecruiters.com/v1/companies/{id}/postings` | **200 `{"totalFound": 0}`** | **the same answer** |

On SmartRecruiters an empty answer could mean "real company, no openings" or "no such company".
Only a board with at least one posting can be verified there.

## What a user can do today, and what needs development

| A user can do this today | This needs development (this spec) |
|---|---|
| Untick platforms to search fewer curated boards | Search a company that isn't curated |
| Narrow results to curated companies with "Only these companies" (exact name) | Add a board, keep it, and see whether it answered |
| Shorten the title by hand to broaden it | Be told which filter or title word is hiding results |
| Paste a job description they found anywhere into Tailor | Use the sponsorship filter without losing every job |
| | See an accurate count of the boards searched |

## Goal and user workflow

On Jobs, a person opens **Company boards**. They see:

- the curated defaults, counted per platform;
- **Your added boards**, each with its platform, last result and a Remove button;
- an **Add a company career board** field.

They paste a public link, for example `https://job-boards.greenhouse.io/northwind` or
`https://jobs.lever.co/northwind/1a2b…`. The app then:

1. recognizes the platform and the board identifier, with no network request;
2. asks that platform's public API whether the board exists;
3. saves the board for this person only, if it's verified;
4. replies "Added Northwind (Greenhouse): 14 open postings right now", or explains plainly why
   it couldn't.

Every later search includes the added boards. The results say how many boards were searched,
and they name each added board that failed. When a search returns few or no results, a short
**What's narrowing your results** panel names each filter and how many more roles that filter
is hiding. It also offers broader titles the person can choose; the query is never changed for
them. The "paste a job description" path stays and is linked from empty states.

Success means:

- a person can reach any public Greenhouse, Lever, Ashby or SmartRecruiters board;
- every result from it is a real posting with the platform's own link;
- an unverified board is never saved or shown as live;
- a failing board is named, not hidden in a total.

## Design

### 1. Recognizing a link (`job_search/board_links.py`, new, pure)

`parse_board_link(text) -> BoardRef | LinkProblem`. It never fetches the pasted URL; it only
reads its host and path.

**Accepted forms** (http or https, with or without `www.`, with any query string or fragment;
trailing job paths are ignored):

| Platform | Accepted forms |
|---|---|
| Greenhouse | `boards.greenhouse.io/{t}`, `job-boards.greenhouse.io/{t}`, `…/{t}/jobs/{id}`, `boards.greenhouse.io/embed/job_board?for={t}`, `…/embed/job_app?for={t}`, `boards-api.greenhouse.io/v1/boards/{t}` |
| Lever | `jobs.lever.co/{t}`, `jobs.lever.co/{t}/{id}[/apply]` |
| Ashby | `jobs.ashbyhq.com/{t}`, `jobs.ashbyhq.com/{t}/{id}[/application]` |
| SmartRecruiters | `jobs.smartrecruiters.com/{t}[/...]`, `careers.smartrecruiters.com/{t}[/...]` |

**Identifier rule:** `^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$`. Case is kept, because SmartRecruiters
ids such as `BoschGroup` are case-sensitive. Duplicates are found by platform plus the lowercased
identifier.

**Recognized but not supported in this round, each with a plain message:**

- `job-boards.eu.greenhouse.io` and `jobs.eu.lever.co` (EU data centers with different API hosts);
- a company's own careers site, for example `careers.acme.com/?gh_jid=123`. The message: "This
  page is on the company's own site. Open a job there and look for a link on
  boards.greenhouse.io, jobs.lever.co, jobs.ashbyhq.com or jobs.smartrecruiters.com, then paste
  that."
- Workday, iCIMS, Taleo, LinkedIn, Indeed and Handshake: "not supported; paste the job
  description in Tailor instead".

**Safety:** only a fixed API host per platform, with a validated identifier, is ever called.
Nothing the user types becomes a URL that is fetched, so this can't be used to reach other
sites from the server (no SSRF).

### 2. Verifying a board (`board_links.verify_board(ref)`)

Uses the existing scrapers' `_make_get_request`, extended to also report the HTTP status, with
a 15-second timeout.

| Platform | Request | Verified when | Name taken from |
|---|---|---|---|
| Greenhouse | `/v1/boards/{t}` then `/v1/boards/{t}/jobs` | 200 with `jobs` list (empty allowed) | board `name` |
| Lever | `/v0/postings/{t}?mode=json` | 200 with a list (empty allowed) | identifier, title-cased |
| Ashby | `/posting-api/job-board/{t}` | 200 with `jobs` list (empty allowed) | identifier, title-cased |
| SmartRecruiters | `/v1/companies/{t}/postings?limit=1` | 200 and `totalFound ≥ 1` | `content[0].company.name` |

**Outcomes:**

| Outcome | Saved? | Message |
|---|---|---|
| `verified` | yes | "Added {name} ({platform}): {n} open postings right now." |
| `verified_empty` (not SmartRecruiters) | yes | "Added {name}. It has no open postings right now; future searches will check it." |
| `not_found` (404) | no | "{platform} has no public board called '{t}'. Check the link." |
| `unconfirmed` (SmartRecruiters, 0 found) | no | "SmartRecruiters gives the same answer for a company with no openings and one that doesn't exist, so this can't be confirmed. Try again when it has an opening." |
| `unreachable` (timeout, 5xx, bad JSON) | no | "{platform} didn't answer. Nothing was saved; try again." |

**Optional inputs:** a **company name**, prefilled from the board where the board states it.
Lever and Ashby don't state a name, so the person may correct it. An optional **industry**
picked from `INDUSTRY_OPTIONS`, defaulting to "Not specified". Both are labels the person
chooses; they never change which postings are returned or their links.

### 3. Saving per user (`job_search/custom_boards.py`, new)

Added boards are stored in the existing per-user profile record, under a new additive field
`custom_boards`. Both apps already read and write that record. "Your data" export and delete
already cover it (they include the whole user folder), and no SQLite schema change is needed.

```json
{"id": "greenhouse:northwind", "platform": "greenhouse", "token": "northwind",
 "name": "Northwind", "industry": "Not specified", "source_url": "https://job-boards.greenhouse.io/northwind",
 "added_at": "...", "verified_at": "...", "postings_at_check": 14,
 "last_search": {"at": "...", "status": "ok|failed|not_found", "matched": 3}}
```

**Duplicates:**

- the same platform and identifier added twice gives "Already added";
- a curated default gives "Already searched by default", and nothing is saved.

**Limits:**

- up to **25 added boards** per person, which keeps searches fast;
- up to **30 link checks per day**, a new `boards` kind in `apps/api/app/workspace/limits.py`
  set by `BOARD_CHECKS_PER_DAY` (0 turns it off).

**Records without the field** load as an empty list. Removing a board deletes only the board
entry. Stored jobs, triage and applications from it stay, the same rule decision 020 applies to
jobs that drop out of a search.

### 4. Searching added boards

- **Scrapers.** `BoardApiScraper` and `SmartRecruitersScraper` take extra boards on each call,
  `scrape(goals, extra_boards=None, include_curated=True)`, instead of mutating class-level
  `BOARDS`. Because the shared board cache is keyed by API URL, added boards are cached like
  curated ones; this is public data.
- **Per-board results.** Each scraper records `board_results[token] = answered | failed |
  not_found` plus the number matched. Curated boards keep the aggregate note, and added boards
  are reported by name.
- **The search service.** `JobService.search_and_store(goals, sources, custom_boards=())`
  groups added boards by platform. A platform runs when either its curated source is ticked or
  it has added boards and "Your added boards" is ticked.
- **Provenance.** `map_job` writes `raw_json["board"] = token`, an additive key. A posting's
  source, its platform-provided URL and its "real" status are unchanged. Rows and the detail
  view show "From a board you added" when the platform and token match one of this person's
  boards.
- **Industry.** `apply_goal_filters` accepts the person's `{company: industry}` labels for added
  boards. A board without a label stays "Not specified", which the industry filter keeps (the
  existing rule).
- **Status after each search.** Every added board's `last_search` is updated. A board that
  returned 404 shows "Not found at the last search (date). The company may have moved boards;
  remove it or paste the new link." It is never removed automatically.

### 5. Sources and counts

- **New labels:**
  - "Greenhouse: 36 curated companies";
  - "Lever: 8 curated companies";
  - "Ashby: 19 curated companies";
  - "SmartRecruiters: 12 curated companies";
  - "Your added boards: N" (shown only when N > 0).
- **Helper text:** "Each source searches the listed companies' own career boards, not every
  company on that platform. Add a company's board below."
- **Counting.** A shared helper, `ui/search_help.py::boards_in_scope(sources, custom_boards,
  include_custom)`, gives the count. Both the button ("Searching 41 company boards") and the
  results ("Searched 41 boards; 2 didn't answer: Northwind (Greenhouse), …") use it.

### 6. Filters that explain themselves (`ui/search_help.py`, shared by both apps)

1. **Sponsorship (a behavior fix).** "I need visa sponsorship" keeps jobs that don't state
   sponsorship and excludes only those that state "no". Such jobs are labeled **"Sponsorship
   not stated — check the posting"**. This follows decision 020's rule that anything not
   stated is kept, not hidden. The SQL becomes `(sponsorship_available = 1 OR
   sponsorship_available IS NULL)`.
2. **Company filters.**
   - "Only these companies" and "Skip these companies" become case-insensitive.
   - New help text: "Narrows results to companies already searched. It doesn't add a company;
     to search one that isn't listed, add its career board."
   - A name that matches no searched board gets an inline note: "'Stripe' isn't one of the
     boards searched. Add its career board?"
3. **What's narrowing your results.** Shown when a search gives fewer than 5 results.
   - For each active filter (location, work mode, sponsorship, level, industry, job type,
     minimum salary, only and skip companies), it shows how many more of this search's stored
     roles would appear without that filter.
   - The counts come from re-running `get_available_jobs` over the same run, with no new
     network fetch. Filters that hide nothing aren't listed.
   - Each line has a "Search without this filter" button. It runs only when the person clicks
     it, and the change is shown in the search summary. As built, the button searches at once
     rather than only changing the form.
4. **Broader titles.**
   - The rule is stated on the form: "Titles must contain every word you typed, in any order."
   - With fewer than 5 results, up to three broader titles are offered, each formed by dropping
     one word, seniority words first: senior, sr, junior, jr, lead, principal, staff, I, II,
     III.
   - These are buttons ("Search 'Data Analyst'") that search when clicked; nothing changes by
     itself. No counts are shown, since titles that didn't match aren't stored and guessing
     would be dishonest.
5. **The paste path.** The empty-results state and every "not supported" link message include
   "Found this role somewhere else? Paste its description in Tailor."

### 7. API (`apps/api/app/workspace/jobs_router.py`, `boards` routes)

| Route | Purpose |
|---|---|
| `GET /v2/boards` | curated counts per platform; added boards with `last_search` |
| `POST /v2/boards` `{url, name?, industry?}` | parse, check duplicates and the cap, verify, save; returns the outcome and message (400 for a link problem, 409 for a duplicate, 422 for not found or unconfirmed, 502 for unreachable, 429 when the limit is hit) |
| `DELETE /v2/boards/{id}` | remove |

Changes to existing routes:

- `GET /v2/jobs/setup` adds `custom_boards` and per-source `curated_count`, and keeps
  `board_count`.
- `POST /v2/jobs/search` adds `include_custom: bool = true`. It also stores
  `custom_board_results` and `boards_searched` in `last_search`.
- `GET /v2/jobs` returns `boards_searched`, `failed_boards`, `narrowing` and
  `broader_titles`.

Existing fields aren't renamed or removed.

### 8. Interfaces

- **Web** (`apps/web/src/app/jobs/`): a new `boards.tsx` with the **Company boards** panel
  inside the search form:
  - the add field with its result message;
  - the list of added boards with their status and Remove;
  - the source labels and live count.

  A `narrowing.tsx` panel sits above the results.
- **Streamlit** (`pages/2_Job_Search.py`): an equivalent "Company boards" expander, plus the
  same narrowing panel and title buttons. The wording comes from `ui/search_help.py`.

Both apps follow decision 033's rule: one shared source for the wording.

## Out of scope (rejected for this round, and why)

- **Finding a board from a company name by guessing identifiers** (for example probing
  `greenhouse/{slug}`). A slug can belong to a different company with the same name, which
  breaks provenance. Maybe later, as "suggestions to confirm".
- **Fetching the company's own careers page** to find its platform link. That means fetching
  user-supplied URLs (SSRF risk) and parsing arbitrary HTML.
- **Workday, iCIMS and Taleo.** They have no stable public JSON API and are a large separate
  job. This is the biggest remaining coverage gap.
- **LinkedIn, Indeed and Handshake scraping.** Excluded by decision 027.
- **Any automatic application submission.** Excluded by decision 016.
- **Sharing added boards between users, or adding them to the curated defaults.** Curated
  additions stay a code change with a live check.
- **Fuzzy location matching.** It's listed by the narrowing panel instead.

## Compatibility

- **Profile records** without `custom_boards` work unchanged.
- **Stored job postings and triage** are untouched; `raw_json["board"]` is additive.
- **`last_search` entries** saved before this change render without the new fields.
- **The sponsorship change** can only add results. It never hides a job that was shown before.
- **New dependencies:** none.

## Tests

- **Product:**
  - a parser table (every accepted form; EU, company-site, unsupported-platform and malformed
    inputs; identifier edge cases);
  - the verifier with mocked responses for each outcome, on each platform;
  - storage (add, duplicate, curated duplicate, cap, remove, legacy record);
  - scrapers with extra boards (curated on and off, per-board failure and 404, `raw_json`
    board key);
  - `JobService` grouping;
  - industry labels;
  - the sponsorship SQL;
  - case-insensitive company filters;
  - the narrowing counts, the broader titles and the board count.
- **API:** the three board routes with every status code, plus search with added boards and
  results with `failed_boards`. No network: the fetches are patched.
- **Web:** lint and types; a Playwright case where `e2e_server.py` stubs a non-curated
  Greenhouse board. It covers:
  - adding a board;
  - seeing the success message;
  - a search that includes the board's job, labeled "From a board you added";
  - the count;
  - a not-found link message;
  - Remove.
- **Supervised run:** add at least one real, non-curated board through the local web app and
  search it. Record it in `discovery/experiments/2026-10-spec-013-custom-boards.md`, with links
  checked by hand.

## Implementation plan (small verified commits; not pushed until the builder asks)

1. `board_links.py`: parsing and verification, with tests.
2. `custom_boards.py`: record storage, duplicates and the cap, with tests.
3. Scrapers and `JobService`: extra boards, per-board results, provenance key and industry
   labels, with tests.
4. Filters: the sponsorship fix, case-insensitive companies, and `ui/search_help.py`
   (narrowing, broader titles, counts), with tests.
5. API routes and the changed search and list responses, with tests.
6. The web Company boards panel, narrowing panel and counts, with Playwright.
7. The Streamlit equivalents.
8. Full suites, the supervised run and its record, decision 035, and updates to
   `AGENTS.md`, `HANDOFF-TO-CODEX.md` and `HANDOFF-TO-CLAUDE-CODE.md`.

**Files touched:**

- *Product:* `job_search/{board_links,custom_boards}.py` (new),
  `scrapers/{base,board,greenhouse,lever,ashby,smartrecruiters}_scraper.py`, `job_service.py`,
  `database.py`, `job_attributes.py`, `ui/search_help.py` (new), `ui/job_view.py`,
  `pages/2_Job_Search.py`.
- *API:* `apps/api/app/workspace/{jobs_router,limits}.py`, `app/config.py`.
- *Web:* `apps/web/src/app/jobs/{search-form,boards,narrowing,page}.tsx`, `lib/types.ts`,
  `e2e/journey.spec.ts`.
- *Tests:* `apps/api/tests/e2e_server.py` and the new test files.

## Builder's choices (2026-10-06)

| Question | Choice |
|---|---|
| Scope | Full spec 013, in both apps |
| Sponsorship | Keep and label "Sponsorship not stated"; no wording detection |
| Limits | 25 added boards per person and 30 link checks a day |
| Discovery | Link only, with guidance; no guessing from company names, no careers-page fetching |
