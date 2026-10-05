# 023: Multi-user safety — sign-in, per-user data, production config

**Date:** 2026-09-29
**Status:** Accepted — built and tested locally; deliberately not deployed yet

## Context

The audit found that the deployed Streamlit app kept every visitor's jobs, applications and
statuses in shared, relative SQLite files. One visitor could see or change another's data, and
Streamlit Cloud deletes those files on every restart. The API also started with the publicly
known JWT secret `dev-secret-change-me`.

The user chose:

- Google sign-in, using Streamlit's built-in login.
- Build it, but don't deploy it yet.

## Decisions

### Sign-in

`resume_tailorer/identity.py` works out who is using the app; `ui/auth_gate.py` runs the check
on every page.

- **When `[auth]` is set in Streamlit secrets**, every page requires Google sign-in.
- **The owner ID is a hash of the Google account's subject.** The email address never appears
  in paths or file names.
- **Without `[auth]`, the app runs in local single-user mode.** A permanent sidebar warning
  says the link must not be shared. The live app shows this until it is deployed with sign-in.
- **Switching accounts in the same browser session clears the previous account's session
  state.**

### Per-user data

- **Every owner has their own folder:** `JOB_COPILOT_DATA_DIR/users/<owner_id>/`. It holds that
  owner's `job_search.db`, `applications.db` (applications, statuses, attempts and answer bank)
  and `artifacts/` (tailored PDFs handed to Launchpad).
- **Isolation comes from the storage layout, not from query filters.** A page only ever opens
  its own owner's files, so a forgotten `WHERE owner = ?` clause cannot leak data. Owner IDs
  are validated so they cannot escape the data directory.
- **Nothing is written to the working directory anymore.**
- **Rejected: rewriting both SQLite layers onto a shared Postgres with an `owner_id` column
  everywhere.** That would mean a large rewrite of raw-SQL code, and every query would carry a
  data-leak risk. Per-owner files give the same ownership guarantee with far less code. A
  durable disk (`JOB_COPILOT_DATA_DIR`) is the only hosting requirement.

### API production config

- **New `APP_ENV` setting.** With `APP_ENV=production`, the API refuses to start unless:
  - `JWT_SECRET` is not the default and is at least 32 characters;
  - `DATABASE_URL` is not a local SQLite file.
- **CORS origins come from `ALLOWED_ORIGINS`.**
- **Fact Vault reads the API address from `JOB_COPILOT_API_BASE`** instead of hard-coding
  localhost.

## Deployment checklist (when the user decides to deploy)

1. **Google sign-in.**
   - Create a Google OAuth client (web application).
   - Set its redirect URI to `https://<app>.streamlit.app/oauth2callback`.
   - Add to Streamlit secrets:
     ```toml
     [auth]
     redirect_uri = "https://<app>.streamlit.app/oauth2callback"
     cookie_secret = "<long random string>"
     [auth.google]
     client_id = "..."
     client_secret = "..."
     server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"
     ```
2. **Durable storage.** Streamlit Community Cloud has no persistent disk. Host the Streamlit app
   on a service with a mounted volume (Render, Railway or Fly.io) and set
   `JOB_COPILOT_DATA_DIR` to the mount path.
3. **API**, if Fact Vault is used:
   - Deploy `apps/api` with `APP_ENV=production`, a generated `JWT_SECRET`, a hosted Postgres
     `DATABASE_URL`, and `ALLOWED_ORIGINS` set to the app's address.
   - Set `JOB_COPILOT_API_BASE` in the Streamlit app to the API's URL.
4. **Model settings.** Set `LLM_MODEL` and `LLM_API_KEY` in the app's secrets.
5. **Check it:** sign in as two different Google accounts, and confirm neither can see the
   other's jobs or applications.

Until steps 1–2 are done, the live link is for supervised demos only.

## Known limitation

Fact Vault still signs in to the API with its own email and password, separate from the Google
identity. Linking the two (sending the Google identity to the API) is the next step once the
API is deployed.

**Resolved 2026-10-04 (decision 027).** Since spec 007 the Streamlit app keeps the Career
Profile itself (`profile_store.py`) and never calls the API, so this separate login could no
longer be reached. The unused client (`profile_review/api_client.py`) and the
`JOB_COPILOT_API_BASE` setting were removed. Step 3 of the checklist above applies only if the
API is deployed for its own clients.

## Review after the first real-resume run (2026-09-30)

- **Per-user storage works as designed.** Jobs, applications, the answer bank and the tailored
  PDF all landed under `~/.job_copilot/users/local/`; nothing was written to the working
  directory.
- **Still untested live:** Google sign-in and a second account. Neither is configured, so the
  "two accounts cannot see each other's data" check in the deployment checklist has not been
  run. Only the unit tests cover it.
