import { expect, test } from "@playwright/test";

test("NBA overview loads desk without error boundary", async ({ page }) => {
  const res = await page.goto("/pro/nba/overview", {
    waitUntil: "domcontentloaded",
  });
  expect(res?.ok()).toBeTruthy();
  await expect(page.getByRole("heading", { name: /^Overview$/i })).toBeVisible();
  await expect(page.getByText(/^NBA$/).first()).toBeVisible();
  await expect(page.getByText(/Something Went Wrong/i)).toHaveCount(0);
  await expect(
    page.getByRole("heading", { name: /^Edge Board$/i }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: /Full Edge Board/i }),
  ).toBeVisible();
  await expect(
    page.locator("h3").filter({ hasText: "Betting Desk" }),
  ).toBeVisible();
  await expect(page.getByRole("link", { name: /^Fantasy$/i }).first()).toBeVisible();
  await expect(
    page.getByRole("link", { name: /Props \(dark\)/i }).first(),
  ).toBeVisible();
});
