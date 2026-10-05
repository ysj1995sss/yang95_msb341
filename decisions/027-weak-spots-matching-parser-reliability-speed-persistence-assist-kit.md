# 027: Fixing the known weak spots (matching, parser, tailoring reliability, search speed, review persistence, deploys, Assist)

**Date:** 2026-10-04
**Status:** Accepted 2026-10-04. The builder asked for items 3–10 of the weak-spot list to be
fixed and delegated the choices.

## 1. Whole-term skill matching (`analyzers/term_match.py`)

`\bgo\b` matched "go-to-market", "rest" matched "the rest of the team", and `c++` could never
match. There were four copies of that regex (fit scorer, job analyzer, gap check, keyword
score), so they now share one matcher. Terms that are also English words (Go, REST, Spring,
Express, Lambda, Rust, Windows, Apache, Hive, Spark, Swift, testing) count only in their
technology spelling; for example, "Go" counts but "Go-to"/"Go to" does not. Other terms match
case-insensitively as whole tokens, and `+`/`#` count as part of the token.

Tailor's "Missing, never added" list now shows a short key phrase, for example "SQL and
Tableau" instead of the whole requirement sentence. The full sentence appears on hover.

**Rejected:** an LLM call to classify ambiguous terms. It would be slow and nondeterministic,
and fit scores must be reproducible.

## 2. Parser formats (`parsers/bullets.py`, `split_one_line_header`)

- **Typed bullets in Word files.** Glyphs typed into the paragraph text ("• ", "▪\t", "- ") are
  now bullets and splice targets. When a bullet is rewritten, the marker runs keep their own
  font (often Symbol), and only the text run changes.
- **PDF text.** Lines starting with ▪ ◦ * ➤ and similar markers are read as bullets.
- **One-line job headers.** "Title | Company | Location | Dates" (also with commas or "at") is
  parsed when no separate title line exists. Before, the whole job was dropped.

## 3. Tailoring reliability

- **Empty replies.** One empty reply is retried on the same model.
- **Model fallback.** A busy provider, repeated empty replies or an unknown model id fall back
  through `LLM_FALLBACK_MODELS`. Gemini defaults to `gemini-flash-lite-latest` and then
  `gemini-2.5-flash` with the same key, so no new secret is needed; `none` turns fallback off.
  A rejected key never falls back.
- **Length cap.** A draft over the cap is first trimmed of filler ("in order to" → "to",
  "utilized" → "used", "successfully", and so on). It is rejected only if it still doesn't fit,
  and the trimmed text still goes through the drift and fabrication checks.
- **Repair call.** The repair call now receives its own rejected draft and that draft's
  length.

**Rejected:** raising the 15% length cap. It exists because a long bullet pushed a real one-page
resume onto two pages.

## 4. Search speed

Measured before the change: 17.9 s for "Data Analyst". The 63 boards download in about 5 s in
parallel. The rest of the time went to cleaning the HTML description of all 7,506 Greenhouse
postings before the title filter kept 44 of them.

- Titles are checked on the raw posting before mapping.
- Saves happen in one transaction.
- The deduplicator is indexed by (company, title, location) instead of quadratic.
- The board cache is shared by the whole process, so concurrent fetches of the same board share
  one request.
- A background warm-up runs whenever a page loads, at most once per 15-minute cache window.
- **Result:** the same search takes 9.5 s cold and 0.1–0.6 s once the boards are cached. A cold
  search is now limited by bandwidth (about 30–40 MB of postings with descriptions).

**Rejected:** fetching Greenhouse without descriptions and then each matching posting
separately. A broad title (about 500 matches) makes that slower.

## 5. Review persistence (`review_store.py`)

The whole Tailor review (changes, decisions, manual edits and the built files) is saved per job
in the user's data folder whenever a decision changes. The next session reopens it, and "Discard
and tailor again" deletes it.

It uses pickle because the review holds the app's own dataclasses and file bytes. The file is
written only by this app, inside the user's folder, and a file that fails to load is ignored.

**Rejected:**
- Saving only the decisions: they are meaningless without the exact proposed changes.
- A JSON schema for every review object: a large serializer to maintain for one feature.

## 6. Streamlit internals

Streamlit stays pinned (1.64.0). `tests/test_streamlit_css_hooks.py` checks every `data-testid`
and `.st*` class the theme targets against the installed frontend bundle. It found one selector
that was already dead (`stVerticalBlockBorderWrapper`), which now targets `stVerticalBlock`.

## 7. Deploys without a reboot (`code_freshness.py`)

Streamlit Cloud pulls new files on push, but modules already imported stay in memory, so pages
ran new page code against old shared code until someone rebooted.

The package's files are fingerprinted (size and mtime) when it is imported. When the files on
disk differ, the session's in-memory objects are cleared (everything that matters is on disk),
the `resume_tailorer.*` modules are dropped, and the page reruns on the new code.

This was checked on a local server with file watching off:
- with the check on, an edited shared string appeared on reload;
- with it off (the control), the old text stayed.

**Caveat:** the deploy that introduces this still needs one reboot, because the running old code
doesn't contain the check yet.

## 8. Assist and Auto

- **Auto (submitting for the user) is not offered.** Decisions 012 and 016 and the product
  promise ("never submits for you") already rule it out.
- **Assist is built as a kit for now.** The full browser helper in spec 006 still waits on two
  questions only the builder can answer: ATS terms of service, and packaging as an extension or
  a local app. Meanwhile, Apply shows an application kit (`ui/application_kit.py`): every value
  a form usually asks for, in form order, each in a copy box. Values come only from the
  confirmed profile, the tailored resume and approved answers. A missing value, including an
  unanswered legal question, is shown as missing and never defaulted.

**Rejected:** a bookmarklet that fills the employer's form. It would store personal data inside
a bookmark URL and inject script into third-party sites, which is the same terms-of-service
question as spec 006 with weaker safeguards.

## What would change our mind

- **Term matching:** if users report missed matches for an ambiguous term written in lowercase
  ("go"), add a context rule rather than reverting to plain word boundaries.
- **Review persistence:** if reviews ever need to be shared or synced across devices, replace
  pickle with an explicit schema.
- **Browser helper:** once the builder settles the terms-of-service and packaging questions in
  spec 006, build it.
