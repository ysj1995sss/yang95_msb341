# Supervised run: added company career boards (spec 013, 2026-10-06)

**Why:** spec 013 requires a search against at least one real board that isn't curated, not only
stubbed tests.

**Setup:**

- **Server:** the local workspace API (`apps/api/scripts/run_local.py`) with a **scratch data
  folder**, not the builder's real data, and the real network.
- **The web app** (`npm run dev`) was started too. The browser pane was hidden, so the browser
  couldn't click. The steps were therefore driven through the same `/v2` API that the web
  page calls. The web interface itself is covered by the Playwright case "add a company career
  board, search it, and remove it" (stubbed platforms).
- **Observer:** Claude Code. The builder reviews this record.

## 1. Adding boards (real platform answers)

| Pasted link | Result | HTTP |
|---|---|---|
| `https://job-boards.greenhouse.io/elastic` | Added Elastic (Greenhouse): 414 open postings right now. | 200 |
| `https://jobs.ashbyhq.com/watershed` | Added Watershed (Ashby): 36 open postings right now. | 200 |
| `https://jobs.lever.co/whoop` | Added Whoop (Lever). It has no open postings right now; future searches will check it. | 200 |
| `https://boards.greenhouse.io/hubspot` | Greenhouse has no public board called 'hubspot'. Nothing saved. | 422 |
| `https://jobs.smartrecruiters.com/Visa` | SmartRecruiters gives the same answer for a company with no openings and one that doesn't exist, so it can't be confirmed. Nothing saved. | 422 |
| `https://boards.greenhouse.io/gitlab` | GitLab (Greenhouse) is already searched by default. | 409 |
| `https://careers.example.com/jobs` | "This page is on the company's own site…", plus the paste-a-description hint. | 400 |

Notes:

- HubSpot and Visa may well hire through other systems; the app makes no claim about that. It
  only says what the platform answered.
- An earlier direct check of `https://jobs.lever.co/plaid` was also "not found". Plaid is a
  curated **Ashby** board, which shows why the platform in the link matters.

## 2. A real search with the added boards

**Search:** "Software Engineer", all sources ticked, added boards on.

- **Time:** 10.2 s, cold.
- **Result line:** "Searched 78 boards." That is the 75 curated boards plus 3 added; none
  failed.
- **Roles found:** 1,923 matching roles. 111 came from Elastic and 3 from Watershed, each
  labeled "Greenhouse · board you added" or "Ashby · board you added".
- **Board statuses afterwards:**
  - Elastic: "111 matching roles at the last search (Oct 6)";
  - Watershed: "3 matching roles…";
  - Whoop: "0 matching roles…".

**Links checked** (fetched the stored URL and read the page title):

| Job | Link | Page |
|---|---|---|
| Watershed, "Senior software engineer, full-stack" | `https://jobs.ashbyhq.com/watershed/c24a97b1-…` | HTTP 200, "Senior software engineer, full-stack @ Watershed" |
| Watershed, "Software engineer, energy management" | `https://jobs.ashbyhq.com/watershed/275cb3f7-…` | HTTP 200, title matches |
| Elastic, "Senior Software Engineer - Streams - Observability" | `https://jobs.elastic.co/jobs?gh_jid=8255436&gh_jid=8255436` | HTTP 200, title matches. This is Elastic's own careers site, which is the link Greenhouse's API gives. |

## 3. Search help, with the same real data

- **"Senior Staff Software Engineer AI" in "Boise", needing sponsorship, only "watershed,
  Stripe":** 0 results.
  - The narrowing panel listed no filters. The title itself matched no stored role, so no single
    filter was hiding one, and it correctly says nothing.
  - Broader titles offered: "Staff Software Engineer AI", "Senior Software Engineer AI",
    "Senior Staff Engineer AI".
  - Company note: "'Stripe' isn't one of the boards searched, so it can't match. Add its career
    board?". "watershed" in lowercase matched the added board.
- **"Software Engineer", needing sponsorship, only "watershed":** 3 results, each marked
  "Sponsorship not stated — check the posting". Before spec 013 this filter returned 0 for
  every live board.
- **Removing Whoop:** the list became [Elastic, Watershed].

## Findings

1. **Works as designed.** Only boards the platform confirms are saved, and the reason is given
   for each that isn't. Added boards are searched, labeled and counted, and their links lead
   to the real posting.
2. **Elastic's posting links repeat `gh_jid`** (`?gh_jid=8255436&gh_jid=8255436`). This is older
   behavior from the decision 020 re-keying, not new; the link still opens the right posting.
   It's worth a small cleanup.
3. **Narrowing counts only roles this search stored.** When the title itself matches nothing,
   only the broader titles help. That's intended (spec 013 §6), but a person may expect a
   filter list there.
4. **Not verified by a person clicking through the web page** on real data. The web interface was
   verified with stubbed platforms in Playwright, and the real platforms through the API.
