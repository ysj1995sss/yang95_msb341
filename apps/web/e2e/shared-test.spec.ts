// The shared test workspace (decision 045): no sign-in, and every visitor acts as one owner, so
// nothing one visitor clicks may lock the others out. It has its own web app and API on 3101/8101
// (playwright.config.ts).
import fs from "node:fs";
import { expect, test } from "@playwright/test";

const SHARED = "http://127.0.0.1:3101";

test("one visitor can't lock everyone out of the shared test", async ({ page }) => {
  const upload = await page.request.post(`${SHARED}/api/backend/profile/resume`, {
    multipart: {
      file: {
        name: "resume.docx",
        mimeType: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        buffer: fs.readFileSync("e2e/fixtures/resume.docx"),
      },
    },
  });
  expect(upload.ok()).toBeTruthy();

  await page.goto(`${SHARED}/profile`);
  await expect(page.getByText("Shared test", { exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Your data" })).toBeVisible();
  await expect(page.getByRole("button", { name: /Sign out on every device/ })).toHaveCount(0);
  await expect(page.getByText("Delete everything in this shared test")).toBeVisible();

  // Even a direct request can't sign the shared owner out, so the workspace keeps answering.
  const refused = await page.request.post(`${SHARED}/api/backend/account/sign-out-everywhere`);
  expect(refused.status()).toBe(400);
  expect((await page.request.get(`${SHARED}/api/backend/profile`)).ok()).toBeTruthy();
});
