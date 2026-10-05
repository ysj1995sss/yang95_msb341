import AxeBuilder from "@axe-core/playwright";
import { expect, type Page } from "@playwright/test";

/** No WCAG 2.2 A/AA violations on what is on screen now. */
export async function expectAccessible(page: Page, where: string) {
  const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"]).analyze();
  const problems = results.violations.map((v) => `${where}: ${v.id} (${v.impact}) on ${v.nodes.map((n) => n.target.join(" ")).slice(0, 3).join(", ")}`);
  expect(problems).toEqual([]);
}

export const PAGES = ["/", "/profile", "/jobs", "/tailor", "/apply", "/tracker"];
