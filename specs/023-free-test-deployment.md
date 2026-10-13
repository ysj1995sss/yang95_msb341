# Spec 023: Free online deployment for supervised testing

**Status:** Draft for the builder's approval (2026-10-12). Nothing is deployed. No account has been
created or touched.
**Builds on:** decision 043 (online, free, sign-in, 3 testers first), decision 044 (free hosting,
data may be wiped, the model provider may train on resumes), spec 009 ("Deploying").

## Goal and limits

Put the website online for **3 supervised testers**, at no cost. The goal is that each of them
finishes search → tailor → apply once, in one sitting.

**Free-plan limits, checked on 2026-10-12:**

| What | Limit | Effect on testers |
|---|---|---|
| Render free service | Sleeps after 15 idle minutes (wake-up about 1 minute); **no persistent disk**, so files are wiped on sleep, restart and redeploy. [Render docs](https://render.com/docs/free) | Their profile and tailored resumes can vanish between visits. They must finish in one sitting. |
| Memory | The backend alone uses about **285 MB** (measured on the builder's PC). One third-party source says free Render has 512 MB; unverified. LibreOffice, which turns **Word** files into PDFs, needs more and wasn't measured. | **Word resumes may fail with an out-of-memory error. Testers should upload PDF resumes.** |
| Vercel Hobby | Personal, non-commercial use only. [Vercel docs](https://vercel.com/docs/plans/hobby) | Fine for testing; charging money later needs the Pro plan. |
| Gemini free tier | Google may use prompts and responses to improve its products, and human reviewers may read them. [Google forum](https://discuss.ai.google.dev/t/clarification-on-gemini-api-free-tier-vs-paid-tier-after-billing-activation/96995) | Testers must be told before they upload a resume (note at the end). |
| The app | 15 tailoring runs per person per day | Plenty for one sitting. |

**Not tested here:** Docker isn't installed on the builder's PC, so the backend image has not been
built. Render's first build is the first real test.

## What changed in the repo

`render.yaml` is now the **free** plan with no disk (the paid variant is in its comments).
Nothing else changed; the Dockerfile already runs production mode, which refuses to start
without a private `WORKSPACE_TOKEN_SECRET`.

## How to deploy (step by step)

Do these in order. Anything marked **YOU** needs your hands. I can't create accounts, sign in, or
see your passwords and keys. **Never paste a key or secret into chat or into any file in this
repository: it is public.**

### A. Accounts and keys (all free)

**A1. YOU: a GitHub account that can see the repo.** It's public (`ysj1995sss/yang95_msb341`), so
Vercel and Render can read it. Use the same GitHub login for both sites below.

**A2. YOU: make two private random secrets.** On your PC, in a terminal, run this twice:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Save the two results in a password manager or a private note. First = `AUTH_SECRET`; second =
`WORKSPACE_TOKEN_SECRET`. Each is 64 characters.

**A3. YOU: a model key.** Go to **aistudio.google.com**, sign in with a Google account, choose
**Get API key → Create API key**, and save it privately. This is the free tier (see the limits
above). The app is already set up for Gemini, so `LLM_MODEL` will be `gemini/gemini-2.5-flash`
(the app's own fallback list uses this name; if Google has retired it, the first tailoring run
will say so and we pick the current name).

**A4. YOU: Google sign-in** (it makes each tester see only their own data):
1. Go to **console.cloud.google.com** and create a project (any name).
2. **APIs & Services → OAuth consent screen:** choose **External**, give the app a name and your
   email, and save. Leave publishing status as **Testing**.
3. On that screen, under **Test users**, click **Add users** and enter the Gmail address of **each
   tester and yourself**. Only listed people can sign in.
4. **APIs & Services → Credentials → Create credentials → OAuth client ID**, application type
   **Web application**. Leave the address boxes empty for now and click Create.
5. Copy the **Client ID** and **Client secret** into your private note. They are
   `AUTH_GOOGLE_ID` and `AUTH_GOOGLE_SECRET`.

### B. The backend on Render

**B1. YOU: Render → New → Blueprint.** Connect GitHub, choose the repo, and choose the branch
**`codex/truthful-tailoring-sources-publication`** (you don't need to merge into `main`).

**B2. YOU:** Render reads `render.yaml` and shows `job-copilot-api` on the **Free** plan. It asks
for the secret values:
- `WORKSPACE_TOKEN_SECRET` = your second secret from A2;
- `LLM_MODEL` = `gemini/gemini-2.5-flash`;
- `LLM_API_KEY` = your key from A3;
- leave `LLM_FALLBACK_MODELS`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` and `ERROR_WEBHOOK_URL`
  empty.

**B3. YOU:** click **Apply**. The first build takes several minutes (it installs LibreOffice).
When it says **Live**, copy the service address (like `https://job-copilot-api-xxxx.onrender.com`).
Open `<that address>/health` in a browser. You should see a short "ok".

**B4.** If the build fails, or the service crashes with a memory error, copy the last 30 lines
of the Render log to me (they contain no secrets) and I fix it.

### C. The website on Vercel

**C1. YOU: Vercel → Add New → Project,** import the same repo.
- **Root Directory:** `apps/web`. Framework should show **Next.js**.
- Open **Settings → Git → Production Branch** afterwards and set it to
  `codex/truthful-tailoring-sources-publication`, so it deploys from that branch.
- Project name: pick something simple; the site address will be `https://<name>.vercel.app`.

**C2. YOU:** before the first deploy, open **Environment Variables** and add:
- `API_URL` = the Render address from B3, with no slash at the end;
- `AUTH_SECRET` = your first secret from A2;
- `WORKSPACE_TOKEN_SECRET` = your **second** secret (the same one as on Render);
- `AUTH_GOOGLE_ID` and `AUTH_GOOGLE_SECRET` from A4.

**C3. YOU:** click **Deploy** and copy the site address.

### D. Finish Google sign-in

**D1. YOU:** back in Google Cloud, open your OAuth client and add:
- **Authorized JavaScript origins:** `https://<name>.vercel.app`
- **Authorized redirect URIs:** `https://<name>.vercel.app/api/auth/callback/google`

Save, and wait about a minute. If Vercel was deployed before D1, click **Redeploy** there.

### E. Check it before any tester sees it

1. **YOU:** open the site in a private browser window and click sign in with Google.
2. **YOU:** import a **PDF** resume, run a search, and tailor one job. The first request after
   idle takes about a minute (Render waking up).
3. **YOU:** sign in as a second Google account from your test users, in another private window.
   **Confirm it can't see the first account's resume.**
4. Tell me the result.

### F. What to tell each tester, before they sign in

> This is a supervised test of an early product. Please upload your resume as a **PDF**. The free
> test server forgets everything after about 15 minutes of inactivity, so please finish in one
> sitting. The AI service we use on its free plan **may use what you send, including your resume
> text, to improve its products, and its staff may read it.** If you're not comfortable with
> that, please don't upload your real resume. Nothing is ever sent to an employer without you.

## What I can do next, and what I can't

**I can** (after you approve this spec): keep `render.yaml` and this guide up to date, read build
logs you paste, fix whatever Render's first build or the memory limit turns up, and add a visible
notice in the app telling testers about the data wipe. **I can't** create accounts, sign in, enter
or see keys, press Deploy, or edit Google Cloud, Render or Vercel settings.

## Rejected or deferred

- **Render paid plan** (about $7 a month plus a disk) keeps data, but is not free; revisit after
  the 3 testers.
- **A free external database** so data survives restarts: a real build, deferred.
- **Hugging Face Spaces** (more free memory): its docs suggest a Docker Space may need a paid plan
  to create; unverified.
- **Merging to `main` first:** not needed; both hosts can deploy from the branch.
