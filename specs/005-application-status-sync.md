# Spec 005: Application status sync

**Status:** Slice 1 (email paste) built 2026-10-04 (decision 027). Slice 2 (Gmail) still deferred: it
needs Google's restricted-scope security review, which only the builder can apply for.
**Date:** 2026-09-29

## Problem

Once someone applies, the tracker only knows what they type into it. Recruiter emails ("we'd
like to schedule a screen", "we've decided to move forward with other candidates") arrive in
their inbox, and nothing links them to the application. Statuses go stale, and the dashboard
stops showing where each application really stands.

## What we're making

A way for a real email to update an application's status, with the user confirming every change.

1. **Email paste (first slice).** The user pastes a recruiter email into the Application
   Tracker. The app finds the matching application (by company and role) and proposes a
   status, for example "Rejected" or "Recruiter screen". Nothing changes until the user
   confirms. The confirmed update is recorded with `StatusSource.EMAIL_INTEGRATION` and the
   email's date (in the history note; the subject line is kept as evidence).
2. **Gmail connection (second slice).** The user connects Gmail with read-only access limited to
   messages from known ATS senders (greenhouse.io, lever.co, ashbyhq.com, myworkdayjobs.com).
   The same matching and confirmation flow runs on new messages.

Matching is deterministic first: the sender domain, company name and role title. A model may
summarize an email, but it never sets a status on its own.

## Out of scope

- Automatic status changes without the user confirming them.
- Sending email or replying to recruiters.
- Reading any mail that isn't from a known ATS sender.
- Portal scraping (logging into Workday or Greenhouse candidate portals).

## Why deferred

Gmail read access is a restricted scope. Until Google completes a security review (weeks, and
it needs a privacy policy and a hosted, verified domain), the app can only be used by accounts
listed as test users. The email-paste slice has no such dependency, and it is the recommended
first step when this is scheduled.

## Definition of done

- [ ] Pasting a real rejection email and a real screen invite proposes the correct application
      and status. Confirming records `StatusSource.EMAIL` with the email date.
- [ ] An email that matches no application, or matches several, is never applied
      automatically. The user picks the application or dismisses the email.
- [ ] Shipped: at least 2 testers used it on their own recruiter emails.
- [ ] Measured: confirmed versus dismissed suggestions, as a signal of matching accuracy.
