import { expect, test } from "@playwright/test";

test("homepage renders brand and CTA", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("link", { name: /Kos Edge Analytics Home/i })).toBeVisible();
  await expect(page.getByRole("heading", { name: /Beat the Number with real Edge/i })).toBeVisible();
});

test("edge board route responds", async ({ page }) => {
  await page.goto("/edge-board");
  await expect(page).toHaveURL(/\/edge-board\/ncaam$/);
  await expect(page.getByText("Edge Board")).toBeVisible();
});

