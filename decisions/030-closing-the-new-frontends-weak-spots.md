# Decision 030: Closing the new frontend's weak spots

**Date:** 2026-10-05
**Status:** Active. After spec 009 was built, the builder asked for a list of weak spots and
then said "do these", with the choices made for them. Each section lists what was rejected and
what is still open.

## 1. Browser tests run on every push (Playwright)

`apps/web/e2e/` drives the real web app against a real API (`apps/api/tests/e2e_server.py`).
Only the outside world is stubbed: the job boards, the language model and the PDF converter.

- **Journey:** upload a resume, confirm facts, set goals, search, tailor, review, apply, track,
  and confirm a recruiter email.
- **Keyboard:** on every page, the first Tab reaches the skip link, and every stop after it is
  visible with an outline of at least 2px.
- **Phone:** no sideways scrolling on a Pixel 7 screen.
- **Accessibility:** axe (WCAG 2.2 A and AA) on every page, in light and dark.
- **Browser helper:** `extension/fill.js` runs on `extension/test/fixture.html`.
- **Gmail:** the Tracker card, with Google's answers faked in the browser.

CI (`.github/workflows/tests.yml`) runs them in the `web-e2e` job.

**Not done:** a screen-reader pass (NVDA or VoiceOver). Automated checks can't hear what is read
aloud. A person has to do it.

## 2. Work survives an API restart

- **Run state:** a tailoring run's state lives in `users/<owner>/tailor/run.json`, not in memory.
- **Restart during a run:** a run still marked running from an earlier server start (`BOOT_ID`)
  is reported as failed ("The server restarted while tailoring. Start again.") instead of
  spinning forever.
- **One-off resumes:** they are saved on disk.

**Rejected: a job queue (Redis or Celery).** One API instance and one run per person don't need
one. Revisit with more than one instance.

## 3. Paste a job description; your own model for one run

- **Pasted job:** Tailor accepts a pasted job description of at least 40 words. It is stored as
  a job (`source_id` `pasted-<hash>`, labelled "Pasted by you"), so Apply and Tracker work the
  same as for a searched job.
- **Own model:** "Your own model (optional)" takes a model name and key for one run. The key is
  used for that run and never saved.
- **Custom API address:** refused for signed-in users. On a shared server it would let anyone
  make the API call any address. It is allowed in local single-user mode only.

## 4. Your data: download, delete, sign out everywhere

These are on the Career Profile page under **Your data**.

- **Download my data:** a zip of the person's whole folder, with a README.
- **Delete:** you type DELETE to confirm. It closes the databases, then removes the folder.
- **Sign out on every device:** raises a session version kept in `account.json`. Every session
  cookie carries its version (`sv`). An older one gets a 401, and the web server clears its
  cookie.

**Rejected: backups run by the app.** Render disk snapshots are the host's job. Download is
the person's own copy.

## 5. Limits and logging

- **Limits** (`app/workspace/limits.py`), counted per person in `limits.json`:
  - 15 tailoring runs a day;
  - 30 searches an hour;
  - 20 resume imports a day.

  Going over returns a plain 429 message. Each limit is a setting, and 0 turns it off.
- **Logging:** every request is logged with an id (`X-Request-Id`). A server error shows the
  person a reference to quote, and the full trace goes to the log.

**Rejected: an error-monitoring service (Sentry or similar).** It needs an account and sends
data to a third party. That is the builder's choice when deploying.

## 6. Search results in pages

Jobs returns 50 at a time with `total` and `offset`. **Show more** loads the next 50. The
ranking still runs over every stored result, so page 2 never ranks above page 1.

## 7. Dark theme

The dark theme follows the device setting (`prefers-color-scheme`). It is built from tokens in
`globals.css`: canvas, paper, ink, primary, `on-primary`, `inverse` and so on. Components use
only the tokens. axe checks both themes.

**Rejected: a theme switch in the app.** The device setting is what people already chose.

## 8. The browser helper attaches the tailored resume

The helper code from Apply now includes the tailored PDF (base64). `fill.js` puts it in the
form's resume field through a `DataTransfer`. If a site's upload control refuses it, the field
is outlined amber for the person to attach the file. It still never submits.

**Not done:** publishing to the Chrome Web Store, which needs the builder's developer account.

## 9. Gmail status sync (spec 005 slice 2)

- **Connecting:** Tracker → **Recruiter emails from Gmail**. **Connect Gmail** is a separate
  Google consent step for `gmail.readonly` with offline access, started and finished on the web
  server (`/api/gmail/connect` and `/api/gmail/callback`).
- **The token:** the refresh token goes server to server to `POST /v2/gmail/connect`. It is
  stored encrypted (Fernet, with a key derived from `WORKSPACE_TOKEN_SECRET`) in
  `users/<owner>/gmail.json`. The browser never sees it.
- **Scanning:** **Check Gmail now** searches only for messages from job-application systems in
  the last 30 days (at most 25). It reads each one with the same email reader as pasting. Only
  an email that clearly says a status and matches a tracked application becomes a suggestion.
- **Suggestions:** nothing changes until the person confirms one. Confirmed and dismissed
  messages aren't suggested again.
- **Disconnect:** revokes the token at Google and deletes it.

**Honest limits:**

- Gmail has no per-sender permission. Google's consent covers reading the whole mailbox. The
  sender limit is the search query, and the app's text says so.
- Gmail read access is a restricted scope. Until Google's security review, only test users
  listed in the Google project can connect, and they see an "unverified app" warning.
- Not yet run against a real Gmail account. The API tests and the browser test stub Google.
- The API needs `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`, the same client as the web app's
  `AUTH_GOOGLE_*`. The Google client also needs `<site>/api/gmail/callback` as a redirect.

**Rejected: scanning in the background on a schedule.** It would read mail when the person
isn't there, and it needs a worker. Scans happen only on a click.

## 10. Bugs found while testing

- **Handoff to Apply:** a reviewed resume never reached Apply in the new app. The API didn't set
  the active job after restoring it. Fixed in `context.py`, with a regression test.
- **Download links:** Next.js prefetched them. They are plain `<a download>` now.
- **Career Profile focus:** the page focused its editor on load, which skipped the skip link.
  Focus now moves only after a click.

## 11. Found on the builder's PC: another project's `.env`

litellm loads the first `.env` it finds above its install folder. On the builder's PC that is
`C:\Users\ysj19\.env`, which belongs to a different project. It sets `DATABASE_URL`, Google
client settings and an OpenAI key, which leak into any Job Copilot process that imports
litellm. The values were never read or printed. The test server sets its own values before
litellm is imported. The builder should move or rename that file.

## Still the builder's decisions

- **Two apps:** keep the Streamlit app as well as the new one, or retire it after the new one is
  deployed (decision 028 keeps `ui-streamlit-v1` either way).
- **Tailoring quality:** free models stay weak at tailoring. A paid or stronger model is a cost
  decision.
- **Deployment:** Render or Vercel accounts, domains and secrets.
- **Terms of service:** the judgment on the job boards' terms (decision 027) still stands.
