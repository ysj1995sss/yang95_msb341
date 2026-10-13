import { expect, test } from "@playwright/test";
import { expectAccessible } from "./helpers";

const first = {
  id: "paragraph:1", title: "1. Work experience · Built weekly reports → Built weekly SQL dashboards",
  category: "REPHRASED", section_label: "Work experience",
  requirement: "SQL reporting", full_requirement: "SQL reporting for regional business partners",
  fact: "Your original bullet: Built weekly reports", reason: "Clarifies an existing result",
  original: "Built weekly reports for sales teams",
  proposed: "Built weekly SQL dashboards used by regional sales teams",
  check: "Verified", decision: null, decision_label: "Not reviewed yet", decision_origin: null,
  decision_reason: "", manual_text: "",
};
const second = {
  ...first, id: "paragraph:2", title: "2. Work experience · Led surveys → Led customer research",
  original: "Led customer surveys for product teams",
  proposed: "Led customer research that informed product planning across regional teams",
};
const review = {
  version: 2, review_revision: 0, review_mode: "manual", status: "FAIL", status_text: "Failed validation: not usable",
  status_tone: "blocked", findings: ["PDF has 2 pages, exceeding the 1-page target."],
  fidelity: "Rebuilt layout", page_count: 2, preview_pages: 0, has_pdf: false, has_docx: false,
  tailored_text: "Synthetic resume", alignment: { before: null, after: null }, overlap_note: "Not an employer score.",
  sync_summary: "", requirement_review: null, readability: { note: "", items: [] }, keyword_report: null,
  pages_before_after: [1, 2], unsupported_claims: [],
  progress: { reviewed: 0, total: 2, needs_rebuild: false, can_continue: false,
              blocker: "This resume failed validation. Fix the blocked items and rebuild.", label: "0 of 2 meaningful changes reviewed" },
  next_undecided: first.id, changes: [first, second], empty_message: "", turned_down: [], true_gaps: [], blocked: [],
  show_all: false, verbs: { ACCEPTED: "Accept change", MANUALLY_EDITED: "Edit manually", REJECTED: "Keep original" },
};
const pageData = (currentReview: typeof review | null) => ({
  job: { job_id: "synthetic-job", title: "Data Analyst", company: "Example Co", fit: 72 },
  resume: { label: "Synthetic resume", one_off: false }, model_ready: true, custom_api_base_allowed: false,
  ats_explainer: { title: "About ATS checks", paragraphs: [], terms_note: "", overlap_note: "" },
  run: { status: "idle" }, review: currentReview, existing: null, stale_message: "",
});

test("review mode is chosen before tailoring starts", async ({ page }) => {
  let sent: unknown = null;
  await page.route("**/api/backend/tailor", (route) => route.fulfill({ json: pageData(null) }));
  await page.route("**/api/backend/tailor/run", async (route) => {
    sent = route.request().postDataJSON();
    await route.fulfill({ json: { status: "running", job_id: "synthetic-job", step: "Starting" } });
  });
  await page.goto("/tailor");
  await expect(page.getByRole("radio", { name: "I'll review changes" })).toBeChecked();
  await page.getByRole("radio", { name: "AI-assisted review" }).check();
  await page.getByRole("button", { name: "Tailor my resume" }).click();
  await expect.poll(() => sent).toMatchObject({ review_mode: "assisted" });
});

test("full changes are readable and selected changes are decided together", async ({ page }) => {
  let sent: unknown = null;
  await page.route("**/api/backend/tailor", (route) => route.fulfill({ json: pageData(review) }));
  await page.route("**/api/backend/tailor/decisions/batch", async (route) => {
    sent = route.request().postDataJSON();
    await route.fulfill({ json: { ...review, review_revision: 1,
      changes: review.changes.map((change) => ({ ...change, decision: "ACCEPTED", decision_label: "Accepted",
        decision_origin: "person", decision_reason: "Chosen by you" })),
      progress: { ...review.progress, reviewed: 2, label: "2 of 2 meaningful changes reviewed", needs_rebuild: true } } });
  });
  await page.goto("/tailor");
  await expect(page.getByRole("button", { name: /Built weekly reports → Built weekly SQL dashboards/ })).toBeVisible();
  await expect(page.getByRole("button", { name: /Led surveys → Led customer research/ })).toBeVisible();
  await page.getByRole("button", { name: "Show all changes" }).click();
  await expect(page.getByText(first.proposed, { exact: true })).toBeVisible();
  await expect(page.getByText(second.proposed, { exact: true })).toBeVisible();
  await expect(page.getByText(first.full_requirement, { exact: true }).first()).toBeVisible();
  await page.getByRole("checkbox", { name: /^Select 1\. / }).check();
  await page.getByRole("checkbox", { name: /^Select 2\. / }).check();
  await expect(page.getByText("2 selected", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Accept selected" }).click();
  await expect.poll(() => sent).toEqual({ expected_revision: 0, decisions: [
    { change_id: first.id, decision: "ACCEPTED" }, { change_id: second.id, decision: "ACCEPTED" },
  ] });
  await expect(page.getByText("AI-assisted", { exact: true })).toHaveCount(0);
  await expect(page.getByText("Chosen by you", { exact: true }).first()).toBeVisible();
  await expect(page.getByRole("link", { name: /Download PDF/ })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Continue to application" })).toBeDisabled();
  await expectAccessible(page, "tailor batch review");
});

test("selection is explicit, reversible, and rejects only the selected changes", async ({ page }) => {
  let sent: unknown = null;
  await page.route("**/api/backend/tailor", (route) => route.fulfill({ json: pageData(review) }));
  await page.route("**/api/backend/tailor/decisions/batch", async (route) => {
    sent = route.request().postDataJSON();
    await route.fulfill({ json: { ...review, review_revision: 1,
      changes: [first, { ...second, decision: "REJECTED", decision_label: "Original kept", decision_origin: "person" }],
      progress: { ...review.progress, reviewed: 1 } } });
  });
  await page.goto("/tailor");
  await page.getByRole("button", { name: "Select all unreviewed" }).click();
  await expect(page.getByText("2 selected", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Clear selection" }).click();
  await expect(page.getByText("0 selected", { exact: true })).toBeVisible();
  await page.getByRole("checkbox", { name: /^Select 2\. / }).focus();
  await page.keyboard.press("Space");
  await page.getByRole("button", { name: "Keep original for selected" }).click();
  await expect.poll(() => sent).toEqual({ expected_revision: 0,
    decisions: [{ change_id: second.id, decision: "REJECTED" }] });
  await expect(page.getByText("0 selected", { exact: true })).toBeVisible();
});

test("a stale batch decision reloads rather than reporting success", async ({ page }) => {
  let latest = review;
  await page.route("**/api/backend/tailor", (route) => route.fulfill({ json: pageData(latest) }));
  await page.route("**/api/backend/tailor/decisions/batch", async (route) => {
    latest = { ...review, review_revision: 1,
      changes: [{ ...first, decision: "REJECTED", decision_label: "Original kept", decision_origin: "person" }, second] } as typeof review;
    await route.fulfill({ status: 409, json: { detail: "Review changed elsewhere" } });
  });
  await page.goto("/tailor");
  await page.getByRole("checkbox", { name: /^Select 1\. / }).check();
  await page.getByRole("button", { name: "Accept selected" }).click();
  await expect(page.getByText("This review changed elsewhere. The latest decisions are loading; select changes again.")).toBeVisible();
  await expect(page.getByText("0 selected", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: /Built weekly reports → Built weekly SQL dashboards — Original kept/ })).toBeVisible();
});

test("legacy decisions do not claim a known decision-maker", async ({ page }) => {
  const oldReview = { ...review, changes: [{ ...first, decision: "REJECTED", decision_label: "Original kept" }, second] };
  await page.route("**/api/backend/tailor", (route) => route.fulfill({ json: pageData(oldReview as typeof review) }));
  await page.goto("/tailor");
  await expect(page.getByText("Origin not recorded", { exact: true })).toBeVisible();
  await expect(page.getByText("Chosen by you", { exact: true })).toHaveCount(0);
});

test("skills added by code say which ones you have and which are adjacent", async ({ page }) => {
  const skills = {
    ...first, id: "paragraph:9", category: "SKILLS_ADDED", section_label: "Skills",
    title: "1. Skills · SQL, Excel → SQL, Excel, Tableau, PostgreSQL",
    original: "SQL, Excel", proposed: "SQL, Excel, Tableau, PostgreSQL",
    added_skills: [
      { term: "Tableau", level: 2, reason: "Your experience shows Tableau (Data Analyst at Acme, bullet 1), but your skills line doesn't list it." },
      { term: "PostgreSQL", level: 3, reason: "You have SQL; the job asks for PostgreSQL, a closely related skill." },
    ],
  };
  const withSkills = { ...review, status: "PASS", status_text: "Passed validation", status_tone: "verified", findings: [],
                       next_undecided: skills.id, changes: [skills] };
  await page.route("**/api/backend/tailor", (route) => route.fulfill({ json: pageData(withSkills as typeof review) }));
  await page.goto("/tailor");
  const added = page.getByRole("list", { name: "Skills added to your skills line" });
  await expect(added.getByText("Added skill: you have it", { exact: true })).toBeVisible();
  await expect(added.getByText("Added skill: adjacent", { exact: true })).toBeVisible();
  await expect(added.getByText("You have SQL; the job asks for PostgreSQL, a closely related skill.")).toBeVisible();
  await expectAccessible(page, "tailor added skills");
});

test("unconfirmed facts are explained before tailoring, with both ways forward", async ({ page }) => {
  let confirmed = false;
  await page.route("**/api/backend/tailor", (route) => route.fulfill({ json: { ...pageData(null), facts_confirmed: confirmed } }));
  await page.route("**/api/backend/profile/confirm", (route) => { confirmed = true; return route.fulfill({ json: { confirmed: 6 } }); });
  await page.goto("/tailor");
  const alert = page.getByRole("status").filter({ hasText: "Your facts aren't confirmed yet" });
  await expect(alert).toBeVisible();
  await expect(alert.getByRole("link", { name: "Review and confirm my facts" })).toHaveAttribute("href", "/profile");
  await alert.getByRole("button", { name: "Use my facts as imported" }).click();
  await expect.poll(() => confirmed).toBe(true);
  await expect(page.getByText("Your facts aren't confirmed yet")).toHaveCount(0);
  await expectAccessible(page, "tailor unconfirmed facts");
});
