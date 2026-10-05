// Browser tests (decision 030): the real web app and the real workspace API, with the job
// boards, the writing model and the PDF converter replaced by stand-ins
// (apps/api/tests/e2e_server.py). Run: npx playwright test
import { defineConfig, devices } from "@playwright/test";
import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const dataDir = process.env.E2E_DATA_DIR ?? mkdtempSync(join(tmpdir(), "jc-e2e-"));
process.env.E2E_DATA_DIR = dataDir; // the same folder for every worker
const python = process.env.PYTHON ?? "python";

export default defineConfig({
  testDir: "e2e",
  timeout: 90_000,
  expect: { timeout: 15_000 },
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["list"], ["html", { open: "never" }]] : "list",
  use: { baseURL: "http://127.0.0.1:3100", trace: "retain-on-failure" },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 900 } }, testIgnore: /layout\.spec/ },
    // Runs after the journey, so every page has data to lay out.
    { name: "phone", use: { ...devices["Pixel 7"] }, testMatch: /layout\.spec/, dependencies: ["desktop"] },
  ],
  webServer: [
    {
      command: `${python} ../api/tests/e2e_server.py "${dataDir}" 8100`,
      url: "http://127.0.0.1:8100/health",
      timeout: 60_000,
      reuseExistingServer: false,
    },
    {
      command: "npm run build && npx next start -p 3100",
      url: "http://127.0.0.1:3100/api/backend/me",
      env: { API_URL: "http://127.0.0.1:8100" },
      timeout: 300_000,
      reuseExistingServer: false,
    },
  ],
});
