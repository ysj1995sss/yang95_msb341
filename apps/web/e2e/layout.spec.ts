import { expect, test } from "@playwright/test";
import { PAGES, expectAccessible } from "./helpers";

// Phone layout (Pixel 7): nothing scrolls sideways, and the bottom bar is there.
for (const path of PAGES) {
  test(`fits a phone screen: ${path}`, async ({ page }) => {
    await page.goto(path);
    await page.waitForLoadState("networkidle");
    const { scroll, width } = await page.evaluate(() => ({ scroll: document.documentElement.scrollWidth, width: window.innerWidth }));
    expect(scroll, `${path} scrolls sideways`).toBeLessThanOrEqual(width);
    await expect(page.getByRole("navigation", { name: "Main" }).last()).toBeVisible();
    await expectAccessible(page, `${path} on a phone`);
  });
}
