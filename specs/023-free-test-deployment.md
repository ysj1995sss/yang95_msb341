# Spec 023: Free online deployment for supervised testing

**Status:** Deployed (2026-10-13), for supervised testing only, with no sign-in and one shared
workspace (decision 045).
- **Website:** Vercel.
- **Backend:** Google Cloud Run.
- **Model:** Groq.

The first plan was Render (the free plan restarted the backend and kept returning 502 errors). It
was replaced by Cloud Run on 2026-10-13, so the old Render service can be turned off.
**Builds on:** decision 043 (online, free, 3 testers first), decision 044 (free hosting, data may be
wiped, the provider may train on resumes), decision 045 (no sign-in), spec 009 ("Deploying").

## What runs where

| Part | Where | Settings (names only; values live in the hosts, never in this repo) |
|---|---|---|
| Website (`apps/web`) | Vercel project `yang95-msb341`; root directory `apps/web` | `API_URL` (the Cloud Run address, Config type), `AUTH_SECRET`, `WORKSPACE_TOKEN_SECRET`, `SHARED_TEST_WORKSPACE=yes` |
| Backend (`apps/api`) | Google Cloud Run service `job-copilot-api`, region `us-west1`, project `job-copilot-511505` | env `APP_ENV=production`, `LEGACY_ROUTES=false`, `LLM_MODEL=groq/openai/gpt-oss-120b`, `TAILOR_RUNS_PER_DAY`; secrets `WORKSPACE_TOKEN_SECRET`, `LLM_API_KEY` (Secret Manager, `:latest`) |
| Backend image | Artifact Registry `us-west1-docker.pkg.dev/job-copilot-511505/job-copilot/api:latest`, built by `cloudbuild.yaml` | |

- **The secrets:** `WORKSPACE_TOKEN_SECRET` must be the same value on Vercel and Cloud Run.
- **Production branch:** Vercel deploys whatever branch is set as its Production Branch. Set it to
  `main` so there is one branch.

## Free-plan limits

| What | Effect on testers |
|---|---|
| Cloud Run scales to zero when idle (`--min-instances 0`), and the container has no disk | **Everything is wiped** when the backend has been idle for a while (roughly 15 minutes) or is redeployed. Testers finish in one sitting. The first request after idle takes about 20–30 seconds. |
| One shared workspace (decision 045) | Everyone using the address sees and overwrites the same data. **Test one person at a time.** "Delete everything in this shared test" on Career Profile resets it between testers. |
| `TAILOR_RUNS_PER_DAY` (default 15) | The limit is shared by all testers because they're one owner. Set about 60. |
| The model provider's free tier | It may keep or use what is sent, including resume text (decision 044). Testers are told before they upload. |
| Vercel Hobby | Personal, non-commercial use. Charging money later needs the Pro plan. |

## Update the backend (after pushing code)

In Google Cloud Shell:

```bash
cd ~/yang95_msb341 && git pull
```

```bash
gcloud builds submit --config cloudbuild.yaml .
```

```bash
gcloud run deploy job-copilot-api --image us-west1-docker.pkg.dev/job-copilot-511505/job-copilot/api:latest --region us-west1 --memory 2Gi --cpu 1 --max-instances 1 --min-instances 0 --allow-unauthenticated --set-env-vars APP_ENV=production,LEGACY_ROUTES=false,LLM_MODEL=groq/openai/gpt-oss-120b,TAILOR_RUNS_PER_DAY=60 --set-secrets WORKSPACE_TOKEN_SECRET=WORKSPACE_TOKEN_SECRET:latest,LLM_API_KEY=LLM_API_KEY:latest
```

**Check:**
1. Open `<service address>/health`. It should say `{"status":"ok"}`.
2. Tailor one job on the website.

**Never paste a key or secret into chat or into this repository: it is public.**

## The website

Vercel deploys on every push to its production branch. If you change a setting, use **Redeploy**
on the newest deployment.

## Before any tester

1. **YOU:** open the site. The header badge should say **Shared test**.
2. **YOU:** import a resume, search, tailor one job and download the PDF. This also confirms
   Word-to-PDF conversion works on the server (LibreOffice in the image), which hasn't been checked
   online yet.
3. **YOU:** delete everything in the shared test, so the tester starts empty.

## What to tell each tester, before they start

> This is a supervised test of an early product with no sign-in: **everyone using this address
> sees and overwrites the same data, so we test one person at a time.** The free test server
> forgets everything after a short idle time, so please finish in one sitting. The AI service we
> use on its free plan **may use what you send, including your resume text.** If you're not
> comfortable with that, please don't upload your real resume. Nothing is ever sent to an employer
> without you.

## Rejected or deferred

- **Render free plan:** it restarted and returned 502 errors under the app's memory use; replaced.
- **A disk or database so data survives restarts:** costs money or needs a real storage build.
  Revisit after the 3 testers.
- **Google sign-in:** deferred by decision 045.
