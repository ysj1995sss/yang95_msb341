# Spec 006: Browser-based Assist mode

**Status:** v0.1 built 2026-10-04 as a browser extension (`extension/`, decision 027). The open
questions below were decided by Claude at the builder's request; see "Decisions" at the end.

## Problem

Assist and Auto mode parse an application form from its raw HTML. Real ATS forms (Greenhouse,
Lever, Ashby, Workday) are built by JavaScript in the browser, so the raw page has almost no form
fields (decision 012). Today Assist mode cannot fill a real application, and Manual mode is the
only dependable path. Users still retype the same contact details and answers on every
application.

## What we're making

A browser-driven helper that fills a real application form and **always stops before Submit**.

1. The helper opens the job's application page in a real browser (Playwright) on the user's own
   computer, where the user is present and signed in.
2. It reads the rendered form, including labels, and fills only:
   - contact facts from the verified Career Truth Profile;
   - the tailored resume file that Tailoring Studio handed off for this job;
   - answers from the user's approved answer bank (see decision 022).
3. It highlights every field it did not fill, and every field whose value it is unsure of, then
   hands control to the user. The user reviews the form and clicks Submit on the employer's site
   themselves.
4. The run is recorded as an Assist attempt: which fields were filled, from which source, and
   which were left for the user.

## Out of scope

- Clicking Submit, ever. A real submission stays gated on a platform proving
  `final_submission` (decision 016), and even then it needs its own spec.
- Solving CAPTCHAs, bypassing bot detection, or automating logins.
- Running in Streamlit Community Cloud or on any shared server. A hosted browser would act from
  a data-center IP on the user's behalf, which employers' ATS terms and bot protection treat as
  automation.
- Drafting answers to free-text questions.

## Open questions to resolve before building

- **Terms of service:** each target ATS's terms on assisted form filling by the applicant.
- **Packaging:** a local companion app or a browser extension. An extension avoids shipping a
  browser binary.
- **Selectors:** how to keep per-platform selectors maintained as ATS markup changes, and how
  to detect a broken selector instead of mis-filling a field.

## Definition of done

- [ ] On live Greenhouse and Lever postings, the helper fills contact fields and uploads the
      tailored resume, then stops with the Submit button untouched.
- [ ] Every filled value traces back to the profile, the handed-off resume or the answer bank.
      Nothing is guessed.
- [ ] Shipped: 2 testers completed real applications with it on their own computers.
- [ ] Measured: fields filled automatically versus fields left for the user, per platform.

## Decisions (2026-10-04)

- **Packaging:** a Chrome/Edge extension (manifest v3, `activeTab` + `scripting` + `storage`
  only). There is no browser binary to ship, and it runs in the user's own browser with the
  user present.
- **Terms of service:** the helper only does what a password manager or autofill does: it types
  the user's own answers into a page the user opened, when the user clicks, and never submits.
  No automation runs unattended, from a server or at scale. This is a judgment, not legal
  advice; the builder should re-check if an ATS objects.
- **Selectors:** labels, not per-site selectors (`aria-label`, `aria-labelledby`, `label[for]`,
  then the question container). A field it can't place is left amber for the user instead of
  being guessed.
- **Getting data into the extension:** the user copies a helper code from Apply into the
  extension. The hosted app exposes no API to it.

## Definition of done, current state

- [x] Fills contact fields and stops with Submit untouched: verified on a local page built from
      live Greenhouse and Lever form structures. Not yet on a live form.
- [x] Every value traces to the kit (profile, authorization answers, approved answers).
- [ ] Resume upload (left to the user in v0.1).
- [ ] Shipped: 2 testers used it on real applications.
- [ ] Measured: fields filled versus left, per platform.
