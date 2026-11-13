import { expect, test } from "@playwright/test";

test("searches the local catalog and adds a real product to the bag", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /dress like/i })).toBeVisible();
  await page
    .getByRole("textbox", { name: "Ask StyleSpeak" })
    .fill("Show black men's cargo pants under €100");
  await page.getByRole("textbox", { name: "Ask StyleSpeak" }).press("Enter");

  const cards = page.locator(".product-card");
  await expect(cards.first()).toBeVisible();
  await expect(cards).toHaveCount(1);
  await cards.first().getByRole("button", { name: /add .* to bag/i }).click();
  await expect(page.getByRole("complementary", { name: /shopping bag/i })).toBeVisible();
  await expect(page.getByRole("heading", { name: /your bag/i })).toBeVisible();
  await expect(page.locator(".cart-lines article")).toHaveCount(1);
});

test("keeps the catalog readable on mobile", async ({ page }, testInfo) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /find your next pair/i })).toBeVisible();
  await expect(page.locator(".product-card").first()).toBeVisible();
  await page.screenshot({ path: `../artifacts/screenshots/${testInfo.project.name}-storefront.png`, fullPage: true });
});
