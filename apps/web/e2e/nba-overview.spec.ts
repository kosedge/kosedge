import { expect, test } from "@playwright/test";

test("NBA overview loads desk without error boundary", async ({ page }) => {
  const res = await page.goto("/pro/nba/overview", {
    waitUntil: "domcontentloaded",
  });
  expect(res?.ok()).toBeTruthy();
  await expect(
    page.getByRole("heading", { name: /NBA Overview/i }),
  ).toBeVisible();
  await expect(page.getByText(/Something Went Wrong/i)).toHaveCount(0);
  await expect(
    page.locator("h2").filter({ hasText: "Betting Desk" }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: /Open Live Edgeboard/i }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: /Open fantasy/i }).first(),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: /Open props/i }).first(),
  ).toBeVisible();
});
