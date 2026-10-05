# Job Copilot web app (spec 009)

The new frontend: Next.js (App Router), TypeScript and Tailwind CSS. It only presents data;
every decision comes from the workspace API in `apps/api` (`/v2/...`), which reuses the
shared Python modules in `product/resume_tailorer`. The Streamlit app in `product/` stays
available (tag `ui-streamlit-v1`), and both read and write the same data folder.

## Run locally

1. Start the API (from `apps/api`):

   ```bash
   PYTHONPATH="../../product:." uvicorn app.main:app --port 8000
   ```

2. Start the web app (from `apps/web`):

   ```bash
   npm install
   npm run dev
   ```

3. Open http://localhost:3000. With no Google settings it runs in local single-user mode,
   like the Streamlit app without sign-in.

## Settings

Copy `.env.example` to `.env.local`. For Google sign-in, set `AUTH_GOOGLE_ID`,
`AUTH_GOOGLE_SECRET`, `AUTH_SECRET`, and the same `WORKSPACE_TOKEN_SECRET` on the web app and
the API (spec 009, appendix A).

## Checks

```bash
npx eslint src && npx tsc --noEmit && npm run build
```
