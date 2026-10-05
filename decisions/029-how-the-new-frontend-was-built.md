# Decision 029: How the new frontend was built (spec 009)

**Date:** 2026-10-05
**Status:** Active. The builder asked for all four phases to be built without questions, with
the choices made for them. Each choice below lists what was rejected.

## 1. Storage: the same per-user folders as Streamlit, not Postgres (for now)

The workspace API (`/v2`, `apps/api/app/workspace/`) reads and writes
`JOB_COPILOT_DATA_DIR/users/<owner>/` exactly as the Streamlit app does: the Career Profile
JSON, the job and application SQLite files, the tailored artifacts and the saved reviews.

**Why:** every shared module (`profile_store`, `job_service`, `review_store`, `tailoring_service`,
the `ui/*` view models) works unchanged. Both frontends see the same data for the same person,
which is what makes going back to `ui-streamlit-v1` painless (decision 028). A Render disk makes
it permanent.

**Rejected: moving to Postgres now.** Decision 023 already rejected it, because every raw-SQL query
would gain an owner filter and a leak risk. Spec 009 said Postgres, but nothing the app does
needs it yet. Revisit if more than one API instance must share data.

## 2. Sign-in: written directly, not with next-auth

Google OpenID Connect uses the authorization-code flow, about 100 lines in `apps/web/src/app/api/auth/`:

- **State:** a state cookie guards against forgery.
- **Token check:** the ID token is verified against Google's keys, issuer and audience, and the
  email must be verified.
- **Session:** a 7-day HS256 cookie that the browser can't read.
- **Return address:** `/api/auth/callback/google`, as spec 009 appendix A says.

**Why:** next-auth v5's support for Next.js 16 was uncertain, and the flow is small and testable.

## 3. The browser never talks to the API

`/api/backend/[...path]` on the web server forwards each request to the API, adding a 5-minute
token for the signed-in user, signed with `WORKSPACE_TOKEN_SECRET`. The API derives the owner id
exactly as `resume_tailorer.identity` does (a hash of the Google subject).

- **Without Google settings:** both sides run in local single-user mode, like Streamlit
  without `[auth]`.
- **Production:** the API refuses to start without the secret.

**Rejected: the browser calling the API with its own token.** It needs CORS, and a token
exposed to page scripts.

## 4. The screens make no decisions

The API returns the existing pure view models as JSON: `home_state`, `profile_readiness`,
`jobs_state` and `job_view`, `tailor_progress` and `tailoring_view`, `apply_readiness` and
`application_kit`, `tracker_views`, `email_status`. The pages only draw them. A rule changed in
Python changes both apps.

## 5. Tailoring moved out of the Streamlit page

`resume_tailorer/tailoring_service.py` holds `run_tailoring` and `regenerate`, moved unchanged
from `pages/5_Tailor.py`, which now calls them.

- **Runs:** the API runs them on a background thread, and the page checks progress every 1.5 s.
- **First step:** the same as the Streamlit review room. Changes that claim a missing
  requirement start rejected.

**Rejected: a job queue (Redis, Celery).** One API instance with one run per user doesn't need
one.

## 6. The last search lives in the profile record

Streamlit keeps it in the browser session. The API is stateless, so it's stored in the record
(`last_search`). It survives reloads and devices.

## 7. Components: hand-written, not shadcn/ui

About 15 small components in `apps/web/src/components/ui.tsx`. Every field has a visible
label, errors sit next to the field, focus is always visible, and touch targets are at least
44px. Fewer dependencies, and every pattern was checked with axe.

## 8. Deployment

- **API:** `apps/api/Dockerfile` (with LibreOffice) and `render.yaml` (a Docker service with a
  1 GB disk at `/data`).
- **Web:** Vercel, root directory `apps/web`.
- **`LEGACY_ROUTES=false`:** drops the older password-login routes and their database, so the
  new app needs only its disk and the shared secret.
- **CI:** builds the image and checks that it starts, refuses unsigned requests and finds
  LibreOffice.

## What was verified

- **Tests:** 93 API tests (the 79 from before plus 14 workspace tests across the four phases);
  the product suite is unchanged in behavior.
- **In the browser:** every page, at 1440px and 390px with no sideways scroll, and axe found no
  WCAG 2.2 AA violations. Specifically:
  - a real search across all four sources;
  - deciding and rebuilding a review to version 2;
  - tracking an application and updating it from an email.
- **Signed-in mode,** end to end except Google's own consent screen:
  - signed-out pages redirect and the API refuses;
  - forged sessions are refused;
  - two users can't see each other's data.

## Not verified

- **A real Google sign-in.** It needs the builder's OAuth client.
- **A successful real model run in the new app.** The configured free OpenRouter model was
  unavailable during testing. The pipeline itself is covered by the stub-model tests and by the
  Streamlit runs.
- **The deployed stack.** No hosting accounts exist yet.

## What would change our mind

- **More than one API instance, or more than a handful of users at once:** move storage to
  Postgres and object storage, and runs to a queue.
- **Testers prefer the old app:** keep `ui-streamlit-v1` as the main app; decision 028 already
  allows this.
