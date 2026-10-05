# Job Copilot form helper (browser extension)

Fills an employer's application form from your Job Copilot kit, when you ask, and never
submits (spec 006, decision 027).

## What it does

- Runs only when you click **Fill this page** in the extension. It has no host permissions and
  no content scripts, so it never reads or changes a page by itself.
- Fills only values from your kit: confirmed Career Profile facts, your work-authorization and
  sponsorship answers, and answers you approved in Job Copilot. Nothing is guessed.
- Outlines what it filled in green and the required fields it left for you in amber, then
  shows a summary.
- Never touches voluntary self-identification questions (gender, race, veteran, disability),
  CAPTCHAs, or anything you've already typed.
- Never submits. It never calls submit and never clicks a button. The only clicks are on the
  radio option or dropdown option it chose.
- Attaches your tailored resume to the form's resume field when the helper code includes it
  (Apply adds it once your tailored resume is ready). If a site's upload control doesn't accept
  it, the field is outlined amber so you attach the PDF yourself.

Your kit is stored only in this browser (`chrome.storage.local`). **Forget my kit** removes it.

## Install (Chrome or Edge, unpacked)

1. Open `chrome://extensions` (or `edge://extensions`) and turn on **Developer mode**.
2. Click **Load unpacked** and choose this `extension` folder.
3. In Job Copilot, open **Apply** for a job, expand **Fill the form for me with the browser
   helper**, and copy the helper code.
4. Click the extension's icon, paste the code and click **Save kit**.
5. Open the employer's application page and click **Fill this page**.

## Tested

- Against a local page built from the live structure of a Greenhouse form (text fields labelled
  by `aria-label`, React dropdowns) and a Lever form (named fields, radio questions):
  `extension/test/fixture.html`.
- Not yet run on a live employer form. That should be done by a person, on their own
  application.
- Forms a company embeds from Greenhouse, Lever, Ashby, Workday or SmartRecruiters in its own
  careers page sit in a frame from another site. The first time the helper sees one, it offers
  **Allow embedded forms**, an optional permission for those six sites only. Without it, it fills
  what it can reach and says so.
- Not yet loaded into a real Chrome profile by a test: the fill script and the address matching
  are tested in a normal page (`apps/web/e2e/extension.spec.ts`).

## Publishing

`python extension/build.py` draws the icons and writes the store zip to `dist/`. `STORE.md` has
the listing text and the privacy-tab answers. The privacy policy is the web app's `/privacy` page.
