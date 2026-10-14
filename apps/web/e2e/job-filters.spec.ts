import { expect, test } from "@playwright/test";
import { expectAccessible } from "./helpers";

// Job search filters as dropdowns (2026-10-13): Location suggests places; Level, Job type and Industry
// open a list of tick boxes, so several can still be chosen.
const setup = {
  form: {
    job_title: "", location: "", remote_preference: "any", experience_level: [], industries: [], min_salary: 0,
    employment_type: [], sponsorship_required: false, relocation_willing: false, target_companies: "",
    exclude_companies: "", sources: ["greenhouse"], include_custom: true, work_mode_stated_only: false,
  },
  has_goals: false, searched: false, summary_line: "", suggested_titles: [], board_count: 63, all_curated_count: 63,
  saved_count: 0, custom_boards: [], max_custom_boards: 25,
  help: { sources: "", add_board: "", company_filter: "", title_rule: "", sponsorship: "", paste: "", limit: "" },
  options: {
    experience_levels: ["internship", "entry", "mid", "senior", "lead", "executive"],
    industries: ["Finance", "Retail", "Technology"], employment_types: ["Full-Time", "Part-Time", "Contract"],
    locations: ["San Francisco", "United States", "Remote"],
    work_modes: [{ value: "any", label: "No preference" }, { value: "remote", label: "Remote" }],
    sources: [{ value: "greenhouse", label: "Greenhouse", curated_count: 63 }],
  },
};

test("filters are dropdowns, and several levels can still be chosen", async ({ page }) => {
  let sent: Record<string, unknown> | null = null;
  await page.route("**/api/backend/jobs/setup", (route) => route.fulfill({ json: setup }));
  await page.route("**/api/backend/jobs/search", async (route) => {
    sent = route.request().postDataJSON();
    await route.fulfill({ status: 400, json: { detail: "Stubbed search" } });
  });
  await page.goto("/jobs");
  await page.getByLabel("Target role").fill("Data Analyst");

  // Location: type freely, with suggestions from real postings.
  const location = page.getByLabel("Location");
  await expect(location).toHaveAttribute("list", /.+/);
  await expect(page.locator("datalist option[value='San Francisco']")).toHaveCount(1);
  await location.fill("San Francisco");

  const level = page.getByRole("button", { name: /^Level/ });
  await expect(level).toHaveText(/Any/);
  await expect(level).toHaveAttribute("aria-expanded", "false");
  await level.click();
  await expect(level).toHaveAttribute("aria-expanded", "true");
  await page.getByRole("checkbox", { name: "Senior" }).check();
  await page.getByRole("checkbox", { name: "Mid" }).check();
  await expectAccessible(page, "level dropdown open");
  await page.keyboard.press("Escape");
  await expect(level).toHaveAttribute("aria-expanded", "false");
  await expect(level).toBeFocused();
  await expect(level).toHaveText(/Mid, Senior/); // list order, whichever was ticked first (dogfood round 5)

  const jobType = page.getByRole("button", { name: /^Job type/ });
  await jobType.click();
  await page.getByRole("checkbox", { name: "Part-Time" }).check();
  await page.getByRole("button", { name: "Clear job type" }).click();
  await expect(jobType).toBeFocused(); // not dropped to the top of the page
  await expect(jobType).toHaveText(/Any/);
  await page.getByRole("checkbox", { name: "Contract" }).check();
  await page.getByRole("heading", { name: "Find a role worth preparing for" }).click(); // a click outside closes it
  await expect(page.getByRole("checkbox", { name: "Contract" })).toHaveCount(0);

  // Tabbing away closes it too; left open, it covered the next fields (dogfood round 5).
  const industry = page.getByRole("button", { name: /^Industry/ });
  await industry.click();
  await page.getByRole("checkbox", { name: "Technology" }).focus();
  await page.keyboard.press("Tab"); // past the last choice: out of the list
  await expect(industry).toHaveAttribute("aria-expanded", "false");

  await page.getByRole("button", { name: "Find matching jobs" }).click();
  await expect.poll(() => sent).toMatchObject({
    location: "San Francisco", experience_level: ["mid", "senior"], employment_type: ["Contract"], industries: [],
  });
});
