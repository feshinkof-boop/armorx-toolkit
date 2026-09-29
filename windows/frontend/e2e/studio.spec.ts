import { expect, test } from "@playwright/test";
import { mkdir } from "node:fs/promises";
import path from "node:path";

const output = path.resolve("visual-output");

async function shot(page: import("@playwright/test").Page, name: string) {
  await mkdir(output, { recursive: true });
  await page.screenshot({ path: path.join(output, name), fullPage: false });
}

test.beforeEach(async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
});

test("dashboard, theme and contextual help", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await expect(page.getByText("Controller ready.")).toBeVisible();
  await shot(page, "01-dashboard-dark.png");

  await page.getByTitle("Toggle theme").click();
  await expect.poll(() => page.evaluate(() => document.documentElement.dataset.theme)).toBe("light");

  await page.getByRole("button", { name: "Sticks" }).click();
  const help = page.locator(".helpTip").first();
  await help.hover();
  await expect(page.locator(".helpBubble").first()).toBeVisible();
  await shot(page, "02-sticks-light-help.png");
});

test("button test emphasizes L3 R3 and analog triggers", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.getByRole("button", { name: "Button Test", exact: true }).click();
  await expect(page.getByText("Controller detected")).toBeVisible();
  await expect(page.locator(".l3Callout")).toContainText("CLICKED");
  await expect(page.locator(".triggerReadout").nth(0)).toContainText("58%");
  await expect(page.locator(".triggerReadout").nth(1)).toContainText("84%");
  await expect(page.locator(".controllerSvg")).toBeVisible();
  await shot(page, "03-button-test-l3-triggers.png");
});

test("macro timeline supports adding and drag reordering", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.getByRole("button", { name: "Macro Studio", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Build combos like a timeline." })).toBeVisible();

  const before = await page.locator(".macroStep").count();
  await page.getByRole("button", { name: /Add another beat/ }).click();
  await expect(page.locator(".macroStep")).toHaveCount(before + 1);

  const first = page.locator(".macroStep").nth(0);
  const second = page.locator(".macroStep").nth(1);
  await first.dragTo(second);
  await expect(page.locator(".macroValidation.good")).toBeVisible();
  await shot(page, "04-macro-studio.png");
});

test("compact layout has no horizontal overflow", async ({ page }) => {
  await page.setViewportSize({ width: 760, height: 720 });
  await page.getByRole("button", { name: "Button Test", exact: true }).click();
  const fits = await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1);
  expect(fits).toBe(true);
  await shot(page, "05-compact-button-test.png");
});
