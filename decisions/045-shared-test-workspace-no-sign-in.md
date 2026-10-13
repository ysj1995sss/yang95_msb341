# Decision 045: A shared test workspace, with no sign-in, for the online test

**Date:** 2026-10-12
**Status:** Active for the supervised test only.
**Overrides:** the "sign-in required" part of decision 043 and the sign-in steps of spec 023.

## Decision

The builder chose to put the test online **with no sign-in and no access code**, as one shared
workspace, against the recommendation to use an access code with a private workspace per browser.

**How it works:**
- With `SHARED_TEST_WORKSPACE=yes` on the website and Google sign-in not configured, the website
  acts for one fixed owner (`shared-test-workspace`) on every request.
- It never turns on by default, and never when Google sign-in is configured.
- The backend still runs in production mode and still refuses any request without a signed token.
- The badge in the header reads "Shared test" and says what it means.

## Consequences the builder accepted

- **Everyone using the address sees and overwrites the same resume, profile, jobs and reviews.**
  Testers must go one at a time.
- **Anyone who has the address can use the app and spend the model key.** The free Gemini limits
  and the app's per-owner limit (15 tailoring runs a day for everybody combined) are the only caps.
- **Data can be wiped at any time** (free hosting) and the model provider may train on it.
- **Testers must not use a resume they want kept private.** Synthetic or throwaway resumes are
  better.

## Rejected

- **An access code with a private workspace per browser:** recommended, not chosen. It remains the
  next step if the address is shared beyond the 3 testers.
- **Leaving the backend open without a token:** the backend still demands a signed token.

## Evidence

An end-to-end run of the backend in production mode and the website, using throwaway test secrets:
with the setting on, the website reached the backend (200) and showed "Shared test"; with it off, the
website refused (401) and showed "Local demo"; the backend itself refused any call without a token
(401) in both cases.
