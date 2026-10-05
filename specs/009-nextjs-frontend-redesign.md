# Spec 009: A new Job Copilot frontend (Next.js) on one FastAPI backend

**Status:** Draft, awaiting the builder's review
**Date:** 2026-10-05
**Decision:** `decisions/028-new-frontend-on-one-fastapi-backend.md`

## Problem

The builder's verdict on today's UI: it **looks generic**, like a default Streamlit app rather
than a product with its own identity. Streamlit limits how far that can be fixed:

- Every visual change is CSS layered over Streamlit's internal test ids, which can change
  between releases (decision 027 added a test because one rule had already broken silently).
- Interactions are page reruns, so a list/detail workspace, inline editing and fast feedback
  are always approximations.

There is also no sign-in or permanent storage on the live app, and the old `apps/api` backend
has drifted from what the app actually does.

Evidence: the builder's review (2026-10-05); decisions 025–027 record how much styling effort
went into working around Streamlit. No user has tested either UI yet, so the Sprint 2 user
tests should run on the current app in parallel with Phase 1 (see Risks).

## What we're making

### 1. Visual system: calm and trustworthy

| Token | Value | Use |
|---|---|---|
| Heading font | Lexend (600, 700) | Page and card titles |
| Body font | Source Sans 3 (400, 600), 16px base, 1.5 line height | Everything else |
| Primary | `#0F766E` with white text (5.4:1) | The one primary action per screen, links, focus ring |
| Ink / Canvas / Paper | `#0F172A` / `#F8FAFC` / `#FFFFFF` | Text, page background, cards |
| Line / Muted text | `#E2E8F0` / `#475569` | Borders, secondary text |
| Verified / Review / Blocked | `#15803D` / `#B45309` / `#B91C1C` | Status, always paired with a word or icon |

- Flat: no gradients and almost no shadows, 4–6px corner radius, and 8px spacing steps.
- One primary action per screen. Each page opens with "your next step".
- Hover and focus transitions take 150–200ms, and `prefers-reduced-motion` is respected.
  Focus rings are always visible.
- Icons are Lucide SVGs with text labels. No emoji used as icons.
- Navigation has the same six destinations as today (Home, Career Profile, Jobs, Tailor, Apply,
  Tracker): a top bar on desktop and a bottom bar on phones.
- Works at 375, 768, 1024 and 1440px with no horizontal scrolling, and meets WCAG 2.2 AA.

Source: the ui-ux-pro-max design data ("Corporate Trust" font pairing, a flat style for SaaS),
with the palette adjusted so primary text meets AA contrast.

### 2. Architecture

- **`apps/web`:** Next.js (App Router), TypeScript, Tailwind CSS and shadcn/ui components. A pure
  client of the API, with no business logic. Sign-in uses Auth.js with Google (spec 009
  appendix A).
- **`apps/api`** (FastAPI) becomes the only backend. New endpoints port what exists only in
  Streamlit today, reusing the existing Python modules in `product/resume_tailorer` rather than
  rewriting them:
  - the Career Profile store (import, review, provenance, preferences, authorization);
  - Jobs search (Greenhouse, Lever, Ashby, SmartRecruiters), fit and evidence, saved jobs;
  - the Tailor review (changes, decisions, rebuilding the resume, the saved review);
  - Apply (kit, helper code, track, mark as applied);
  - Tracker (views, next actions, status history, status from a pasted email), saved answers.
- **Identity:** the API checks the signed-in user on every request. Each user's data stays
  separate, as in decision 023.
- **Storage:** Postgres for records and a file store for resumes and PDFs. This delivers the
  permanent storage the live app lacks.

### 3. Build order (each phase ships before the next starts)

1. **Phase 1, foundation.** Design tokens and components, the app shell (navigation, sign-in,
   empty and error states), Home and Career Profile, plus their API endpoints.
2. **Phase 2, Jobs.** The list/detail workspace and the search endpoints for all four sources.
3. **Phase 3, Tailor.** Review, decisions, rebuilding the resume, the saved review.
4. **Phase 4, Apply and Tracker.** The kit and helper code, tracking, status from email.

### 4. The current design is kept

- The Streamlit app as of 2026-10-05 is tagged **`ui-streamlit-v1`** (commit `7594b67`). To see
  or restore it: `git checkout ui-streamlit-v1`.
- The Streamlit app is **not deleted**, even after parity: `product/resume_tailorer` stays in
  the repo, keeps its tests, and stays deployable on Streamlit Community Cloud. Going back is a
  matter of pointing users at its address again.
- Both frontends use the same Python modules, so a fix to matching, parsing or tailoring
  improves both.

## Out of scope

- Changing what the product does. Features, safety rules (nothing invented, nothing
  submitted for you) and wording stay as they are; this is a new presentation.
- A public marketing site.
- Dark mode (tokens are named so it can be added later).
- Native mobile apps.
- Removing the Streamlit app.

## Risks

- **Size.** Four phases, several weeks. Mitigation: each phase ships on its own, and Streamlit
  stays live meanwhile.
- **No user evidence yet.** Run the Sprint 2 user tests on the current app now, so Phases 2–4
  fix what users actually struggle with.
- **Two UIs drifting.** Mitigation: all logic lives in the shared Python modules. The
  frontends only present it.

## Decisions only the builder can make (before Phase 1 ships)

- **Hosting and cost:** proposed Vercel (frontend, free tier), Render (API, about $7/month) and a
  free Postgres tier (Neon or Supabase). The builder creates the accounts.
- **Google OAuth client:** see appendix A.

## Definition of done

- [ ] Phase 1: signed in with Google, a new user imports a resume and confirms their Career
      Profile in the new app. The data survives a redeploy.
- [ ] Every phase: no horizontal scrolling at 375px, keyboard-only use works, and contrast is AA
      on all text (automated axe check, no serious violations).
- [ ] Phases 1–4: the full search → tailor → apply → track loop works in the new app, with the
      same safety tests passing against the API.
- [ ] Shipped: 2–3 testers use the new app and say how it compares with the old one.
- [ ] `ui-streamlit-v1` checks out and runs, so the old design can be restored.

## Appendix A: Google OAuth client

1. In Google Cloud, create a project. Set the consent screen to External, in Testing mode, with
   test users listed and only the `openid`, `email` and `profile` scopes.
2. Create a Web application client:
   - JavaScript origin `http://localhost:3000` and redirect
     `http://localhost:3000/api/auth/callback/google`;
   - later, the same two entries for the deployed address;
   - optionally the Streamlit redirect `.../oauth2callback`.
3. Keep the ID and secret out of chat and out of git. They go in `apps/web/.env.local` as
   `AUTH_GOOGLE_ID` and `AUTH_GOOGLE_SECRET`, and in Vercel's environment settings.
