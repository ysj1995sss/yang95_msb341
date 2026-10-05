# Chrome Web Store listing (draft)

Everything the Chrome Web Store developer dashboard asks for, ready to paste. Publishing needs
the builder's developer account (a one-time US$5 fee) and the web app deployed, so the privacy
policy has a public address.

## Package

```bash
python extension/build.py
```

This writes `dist/job-copilot-helper-<version>.zip` (with icons, without tests). Upload that file.
The same zip also works on the Microsoft Edge Add-ons site.

## Store listing

- **Name:** Job Copilot form helper
- **Summary (132 characters max):** Fills an employer's job application form from your Job Copilot kit when you click. Never submits anything.
- **Category:** Tools (Workflow & Planning)
- **Language:** English
- **Description:**

  > Job Copilot prepares your application: a resume tailored to the job from facts you confirmed,
  > and answers you approved. This helper copies them into the employer's application form for
  > you, so you don't have to retype them.
  >
  > - Runs only when you click **Fill this page**, on that tab only.
  > - Fills only what's in your kit: confirmed Career Profile facts, your work-authorization
  >   answers, answers you approved, and your tailored resume file.
  > - Outlines what it filled in green, and the required questions it left for you in amber.
  > - Never touches voluntary self-identification questions (gender, race, veteran status,
  >   disability) or anything you already typed.
  > - **Never submits.** You check every field and submit on the employer's site yourself.
  >
  > Your kit stays in your browser. **Forget my kit** removes it.
  >
  > Works with forms from Greenhouse, Lever, Ashby, Workday and SmartRecruiters, including forms a
  > company embeds in its own careers page (you're asked first).

- **Screenshots (1280×800):** take two once the web app is deployed: the Apply page's "Fill the
  form for me" section, and a filled form with the green and amber outlines and the summary.
- **Small promo tile (440×280):** optional.
- **Icon:** `extension/icons/icon128.png`.

## Privacy practices tab

- **Single purpose:** Fill a job application form on the current page with the person's own
  Job Copilot answers when they click, without submitting it.
- **activeTab:** reads and fills the form on the tab where the person clicked **Fill this page**,
  and only then.
- **scripting:** injects the fill script into that tab after the click.
- **storage:** keeps the person's kit (their answers and tailored resume) in their own browser
  between uses.
- **Optional host permissions** (boards.greenhouse.io, job-boards.greenhouse.io, jobs.lever.co,
  jobs.ashbyhq.com, *.myworkdayjobs.com, jobs.smartrecruiters.com): asked for only when the
  person clicks **Allow embedded forms**, because some company career pages embed the application
  form from one of these sites in a frame that activeTab can't reach. Still used only on the
  person's click.
- **Remote code:** No. All code is in the package.
- **Data use:** tick "Personally identifiable information" (name, email, phone) only. It is
  stored locally, never sent to the developer or anyone else, never sold, and never used for
  anything but filling the form.
- **Certifications:** tick all three (not sold, not used for unrelated purposes, not used for
  creditworthiness).
- **Privacy policy URL:** `<web app address>/privacy`.

## Before submitting

- Load the zip unpacked once (`chrome://extensions` → Developer mode → Load unpacked on the
  unzipped folder) and fill one real application form you're actually applying to, without
  submitting. That's the one check that can't be automated here.
