// The browser helper (extension/fill.js) on a page built from live Greenhouse and Lever form
// structures (extension/test/fixture.html). It must fill only from the kit, attach the resume,
// leave voluntary and already-filled fields alone, and never submit.
import { expect, test } from "@playwright/test";
import { pathToFileURL } from "node:url";
import { resolve } from "node:path";

const EXTENSION = resolve(__dirname, "../../../extension");
const PDF = Buffer.from("%PDF-1.4\n% synthetic\n").toString("base64");
const KIT = {
  jobCopilotKit: 1,
  fields: {
    first_name: "Riley", last_name: "Park", full_name: "Riley Park", email: "riley@example.com", phone: "555-0100",
    linkedin: "https://linkedin.example/riley", current_company: "Northwind", authorized_to_work: "Yes", needs_sponsorship: "No",
  },
  answers: [{ question: "Why do you want to work at Acme?", answer: "Your analytics platform." }],
  resume: { filename: "tailored_resume_v2.pdf", data: PDF },
};

test("the browser helper fills from the kit, attaches the resume and never submits", async ({ page }) => {
  await page.goto(pathToFileURL(resolve(EXTENSION, "test/fixture.html")).href);
  await page.addScriptTag({ path: resolve(EXTENSION, "fill.js") });
  const result = await page.evaluate((kit) => (window as unknown as { __jobCopilotFill: (k: unknown) => Promise<{ filled: number; left: string[] }> }).__jobCopilotFill(kit), KIT);

  const value = (selector: string) => page.locator(selector).inputValue();
  expect(await value("#first_name")).toBe("Riley");
  expect(await value("#last_name")).toBe("Park");
  expect(await value("#email")).toBe("riley@example.com");
  expect(await value("#q1")).toBe("https://linkedin.example/riley");
  expect(await value("#q4")).toBe("Your analytics platform.");
  expect(await page.locator("#q3-value").textContent()).toBe("No"); // the React-style dropdown
  expect(await value('[name="name"]')).toBe("Riley Park");
  expect(await value('[name="org"]')).toBe("Northwind");
  await expect(page.locator('[name="cards[x][field4]"][value="Yes"]')).toBeChecked();
  expect(await page.locator("#resume").evaluate((el: HTMLInputElement) => el.files?.[0]?.name)).toBe("tailored_resume_v2.pdf");

  // Left alone: preferred name, voluntary self-identification, what was already typed.
  expect(await value("#q2")).toBe("");
  expect(await value("#gender")).toBe("");
  expect(await value('[name="location"]')).toBe("Already typed");
  // Unknown required questions are left for the person, and nothing was submitted.
  expect(result.left.join(" ")).toMatch(/previously worked at Acme/);
  expect(result.left.join(" ")).toMatch(/How did you hear/);
  expect(await page.evaluate(() => (window as unknown as { __submitted?: boolean }).__submitted ?? false)).toBe(false);
  await expect(page.getByRole("status")).toContainText("Nothing was submitted.");
});
