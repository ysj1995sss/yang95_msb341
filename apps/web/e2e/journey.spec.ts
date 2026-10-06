import { expect, test } from "@playwright/test";
import { PAGES, expectAccessible } from "./helpers";

test.describe.configure({ mode: "serial" });

const REJECTION = `From: GitLab Recruiting <no-reply@greenhouse.io>
Date: Thu, 1 Oct 2026 09:30:00 -0700
Subject: Your application to GitLab

Thank you for applying for the Senior Data Analyst role at GitLab. After careful review, we have decided to move forward with other candidates.`;

test("resume → profile → goals → jobs → tailor → apply → tracker", async ({ page }) => {
  // Home, first visit: import the resume right there.
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Import your resume" })).toBeVisible();
  await expectAccessible(page, "home, first visit");
  await page.locator('input[type="file"]').setInputFiles("e2e/fixtures/resume.docx");
  await page.getByRole("button", { name: "Import resume" }).click();
  await expect(page.getByRole("heading", { name: "Confirm your important facts" })).toBeVisible();

  // Career Profile: confirm the facts.
  await page.getByRole("link", { name: "Review my profile" }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Career Profile" })).toBeVisible();
  await expectAccessible(page, "career profile");
  await page.getByRole("button", { name: "Confirm the rest" }).click();
  await expect(page.getByText(/Confirmed \d+ facts/)).toBeVisible();
  await expect(page.getByRole("button", { name: "Confirm the rest" })).toHaveCount(0);

  // Home: the goals questions, one at a time.
  await page.goto("/");
  await page.getByLabel("Job title").fill("Data Analyst");
  for (let i = 0; i < 6; i++) await page.getByRole("button", { name: "Continue" }).click();
  await expectAccessible(page, "goals, last question");
  await page.getByRole("button", { name: "Save goals and continue" }).click();
  await expect(page.getByRole("heading", { name: "Choose a real role" })).toBeVisible();

  // Jobs: search, read a role, prepare it.
  await page.getByRole("link", { name: "Find jobs" }).click();
  await page.getByRole("button", { name: "Find matching jobs" }).click();
  await expect(page.getByRole("button", { name: /Senior Data Analyst/ })).toBeVisible();
  await expect(page.getByRole("button", { name: /Data Analyst, Growth/ })).toBeVisible();
  await expect(page.getByRole("button", { name: /Account Executive/ })).toHaveCount(0);
  await expect(page.getByRole("heading", { name: "Why this role may fit you" })).toBeVisible();
  // Spec 010: honest wording, a requirement summary and the ATS explanation.
  await expect(page.getByText("In your Career Profile", { exact: true })).toBeVisible();
  await expect(page.getByText(/Requirement review:/)).toBeVisible();
  await page.getByText("About ATS checks").click();
  await expect(page.getByText(/There is no universal ATS score/)).toBeVisible();
  await expect(page.getByText(/on your resume/i)).toHaveCount(0);
  await expectAccessible(page, "jobs, results");
  await page.getByRole("button", { name: "Prepare this application" }).click();

  // Tailor: run, review every change, rebuild.
  await expect(page).toHaveURL(/\/tailor$/);
  await page.getByRole("button", { name: "Tailor my resume" }).click();
  await expect(page.getByRole("heading", { name: "Proposed changes" })).toBeVisible({ timeout: 60_000 });
  // Spec 010: the requirement review with linked evidence, and the local readability check.
  await expect(page.getByRole("heading", { name: "Requirement review" })).toBeVisible();
  const firstRow = page.getByRole("region", { name: "Requirement review" }).locator("details").first();
  await firstRow.locator("summary").click();
  await expect(firstRow.locator("blockquote").first()).toBeVisible();
  await expect(page.getByText("Readability check", { exact: true })).toBeVisible();
  await expect(page.getByText(/Resume alignment/)).toHaveCount(0);
  await expectAccessible(page, "tailor, review");
  const status = page.getByRole("status").filter({ hasText: /meaningful changes reviewed|No changes need/ });
  for (let i = 0; i < 12; i++) {
    if (await status.getByText(/Rebuild the resume|ready for Apply/).count()) break;
    await page.getByRole("button", { name: "Accept change" }).click();
    await page.waitForTimeout(400);
  }
  const rebuild = page.getByRole("button", { name: "Rebuild resume" });
  if (await rebuild.isEnabled()) await rebuild.click();
  await expect(status.getByText("Your resume is ready for Apply.")).toBeVisible();
  await page.getByRole("link", { name: "Continue to application" }).click();

  // Apply: ready, track, mark as applied.
  await expect(page).toHaveURL(/\/apply$/);
  await expect(page.getByText("Ready. Open the employer's application")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Assist: your application kit" })).toBeVisible();
  await expectAccessible(page, "apply, ready");
  await page.getByRole("button", { name: "Track this application" }).click();
  await expect(page.getByText(/Tracked as ready to apply/).first()).toBeVisible();
  await page.getByRole("button", { name: "Mark as applied" }).click();
  await expect(page.getByText("Marked as applied. Follow it in Tracker.")).toBeVisible();

  // Tracker: a recruiter email moves it to Rejected only after confirming.
  await page.getByRole("link", { name: "Open Tracker" }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Tracker" })).toBeVisible();
  await page.getByText("Update a status from a recruiter email").click();
  await page.getByLabel("Recruiter email").fill(REJECTION);
  await page.getByRole("button", { name: "Read the email" }).click();
  await expect(page.getByText(/Suggested status: Rejected/)).toBeVisible();
  await expectAccessible(page, "tracker, email suggestion");
  await page.getByRole("button", { name: "Confirm update" }).click();
  await expect(page.getByRole("button", { name: /Closed \(1\)/ })).toBeVisible();
});

test("Gmail suggestions change nothing until confirmed (Google's answers are stubbed)", async ({ page }) => {
  let connected = false;
  const confirmed: unknown[] = [];
  const dismissed: unknown[] = [];
  await page.route("**/api/backend/gmail", (route) => {
    if (route.request().method() === "DELETE") connected = false;
    return route.fulfill({ json: { available: true, connected, connected_at: null, last_scan: connected ? "2026-10-05T09:00:00Z" : null } });
  });
  await page.route("**/api/backend/gmail/scan", (route) => route.fulfill({ json: { suggestions: [{
    message_id: "m1", subject: "Your application to GitLab", from: "GitLab <no-reply@greenhouse.io>", email_date: "2026-10-01T09:30:00",
    status: "interview", status_label: "Interview", phrase: "schedule an interview", chosen: null,
    options: [{ application_id: "app-1", label: "Data Analyst at GitLab", backwards: false }],
  }] } }));
  await page.route("**/api/backend/tracker/email/confirm", (route) => { confirmed.push(route.request().postDataJSON()); return route.fulfill({ json: {} }); });
  await page.route("**/api/backend/gmail/dismiss", (route) => { dismissed.push(route.request().postDataJSON()); return route.fulfill({ json: { dismissed: true } }); });

  await page.goto("/tracker");
  const card = page.getByRole("region", { name: "Recruiter emails from Gmail" });
  await expect(card.getByRole("link", { name: "Connect Gmail" })).toHaveAttribute("href", "/api/gmail/connect");
  await expect(card).toContainText("never sends or changes email");
  await expectAccessible(page, "tracker, Gmail not connected");

  connected = true;
  await page.goto("/tracker?gmail=connected");
  await expect(card.getByText("Gmail is connected.")).toBeVisible();
  await card.getByRole("button", { name: "Check Gmail now" }).click();
  await expect(card.getByText(/Suggested status: Interview/)).toBeVisible();
  await expectAccessible(page, "tracker, Gmail suggestion");
  const confirm = card.getByRole("button", { name: "Confirm update" });
  await expect(confirm).toBeDisabled(); // the email didn't name one application, so the person chooses
  await card.getByLabel("Which application is this about?").selectOption("app-1");
  await confirm.click();
  await expect(card.getByText(/Suggested status: Interview/)).toHaveCount(0);
  expect(confirmed).toEqual([{ application_id: "app-1", status: "interview", email_date: "2026-10-01T09:30:00", evidence: "Your application to GitLab" }]);
  expect(dismissed).toEqual([{ message_id: "m1" }]);

  await card.getByRole("button", { name: "Disconnect Gmail" }).click();
  await expect(card.getByRole("link", { name: "Connect Gmail" })).toBeVisible();
});

test.describe("in a far-away time zone", () => {
  test.use({ timezoneId: "Pacific/Auckland" });

  test("status history shows the person's own local time", async ({ page }) => {
    await page.goto("/tracker");
    const shown = (await page.getByRole("group").filter({ hasText: "Status history" }).getByRole("listitem").first().textContent()) ?? "";
    // The journey just made this change, so it happened within the last few minutes, Auckland time.
    const recent = await page.evaluate(() => Array.from({ length: 15 }, (_, i) => new Date(Date.now() - i * 60_000)
      .toLocaleString(undefined, { month: "short", day: "numeric", year: "numeric", hour: "numeric", minute: "2-digit" })));
    expect(recent.some((when) => shown.startsWith(when)), `"${shown}" should start with one of ${recent.join(" | ")}`).toBe(true);
  });
});

test("every page can be used by keyboard, with focus always visible", async ({ page }) => {
  for (const path of PAGES) {
    await page.goto(path);
    await page.waitForLoadState("networkidle");
    // The first Tab reaches the skip link, which moves focus into the page.
    await page.keyboard.press("Tab");
    await expect(page.getByRole("link", { name: "Skip to content" }), `${path}: the first Tab should reach the skip link`).toBeFocused();
    const seen = new Set<string>();
    for (let i = 0; i < 40; i++) {
      await page.keyboard.press("Tab");
      const focus = await page.evaluate(() => {
        const el = document.activeElement as HTMLElement | null;
        if (!el || el === document.body) return null;
        const style = getComputedStyle(el);
        const box = el.getBoundingClientRect();
        return {
          id: `${el.tagName}:${el.textContent?.trim().slice(0, 40)}:${el.getAttribute("aria-label") ?? ""}`,
          outlined: style.outlineStyle !== "none" && parseFloat(style.outlineWidth) >= 2,
          visible: box.width > 0 && box.height > 0,
        };
      });
      if (focus === null) {
        // Past the last control, Tab moves into the browser's own toolbar: the end of the page.
        expect(seen.size, `${path}: focus left the page after only ${i + 1} tabs`).toBeGreaterThan(5);
        break;
      }
      expect(focus!.visible, `${path}: ${focus!.id} is focused but not visible`).toBe(true);
      expect(focus!.outlined, `${path}: ${focus!.id} has no visible focus outline`).toBe(true);
      if (seen.has(focus!.id)) break; // wrapped around
      seen.add(focus!.id);
    }
    expect(seen.size, `${path}: too few keyboard stops`).toBeGreaterThan(5);
  }
});

test("the privacy page is public, readable and accessible", async ({ page }) => {
  await page.goto("/privacy");
  await expect(page.getByRole("heading", { level: 1, name: "Privacy" })).toBeVisible();
  await expect(page.getByText(/Limited Use requirements/)).toBeVisible();
  await expectAccessible(page, "privacy");
  await page.goto("/");
  await expect(page.getByRole("contentinfo").getByRole("link", { name: "Privacy" })).toHaveAttribute("href", "/privacy");
});
