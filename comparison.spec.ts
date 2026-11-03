import { expect, test } from "@playwright/test";
import type { Direction, Metric, PreferenceMode } from "../src/types/api";

const directions: Record<Metric, Direction> = {
  calories: "least",
  carbohydrates: "least",
  protein: "most",
  fat: "least",
  fibre: "most",
  price: "least",
};

const values: Record<Metric, { value: number; unit: string }> = {
  calories: { value: 100, unit: "kcal/100g" },
  carbohydrates: { value: 1, unit: "g/100g" },
  protein: { value: 20, unit: "g/100g" },
  fat: { value: 10, unit: "g/100g" },
  fibre: { value: 0, unit: "g/100g" },
  price: { value: 1.25, unit: "EUR/100g" },
};

test("category, priority, default reset, ranks, and browser preference survive reload", async ({
  page,
}) => {
  let preference: {
    category: string | null;
    preference_mode: PreferenceMode;
    primary_metric: Metric;
    primary_direction: Direction;
  } = {
    category: "cheese",
    preference_mode: "default",
    primary_metric: "calories",
    primary_direction: "least",
  };
  let cookieSeenAfterReload = false;

  await page.route("**/api/v1/**", async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    if (path.endsWith("/categories")) {
      await route.fulfill({
        json: {
          items: [
            {
              slug: "cheese",
              name: "Cheese",
              product_count: 1,
              is_active: true,
              source_url: null,
            },
            {
              slug: "dairy",
              name: "Dairy",
              product_count: 1,
              is_active: true,
              source_url: null,
            },
          ],
        },
      });
      return;
    }
    if (path.endsWith("/preferences") && request.method() === "GET") {
      if (request.headers().cookie) cookieSeenAfterReload = true;
      await route.fulfill({
        headers: {
          "set-cookie":
            "nutrition_session=opaque-browser-test; Path=/; HttpOnly; SameSite=Lax",
        },
        json: {
          ...preference,
          category: preference.category,
          criteria: [],
        },
      });
      return;
    }
    if (path.endsWith("/preferences") && request.method() === "PUT") {
      const update = request.postDataJSON();
      preference = {
        category: update.category,
        preference_mode: update.preference_mode,
        primary_metric:
          update.preference_mode === "default"
            ? "calories"
            : update.primary_metric,
        primary_direction:
          update.preference_mode === "default"
            ? "least"
            : update.primary_direction,
      };
      await route.fulfill({
        json: { ...preference, criteria: [] },
      });
      return;
    }
    if (path.endsWith("/comparisons") && request.method() === "POST") {
      const category = request.postDataJSON().category as string;
      const name = category === "dairy" ? "Dairy Cheese" : "Test Cheese";
      const metrics = Object.fromEntries(
        Object.entries(values).map(([metric, datum]) => [
          metric,
          {
            ...datum,
            direction:
              preference.preference_mode === "custom" &&
              preference.primary_metric === metric
                ? preference.primary_direction
                : directions[metric as Metric],
            rank: 1,
            quality_status: "reliable",
            reason: null,
            source_url: null,
            observed_at: null,
          },
        ]),
      );
      await route.fulfill({
        json: {
          category,
          preference_mode: preference.preference_mode,
          primary_metric: preference.primary_metric,
          primary_direction: preference.primary_direction,
          criteria: [],
          unranked_count: 0,
          items: [
            {
              id: `test-${category}`,
              name,
              category,
              brand: "Test Brand",
              barcode: "0000000000000",
              display_position: 1,
              package_size_g: 200,
              package_size_label: "200 g",
              package_price: 2.5,
              currency: "EUR",
              price_per_100g: 1.25,
              price_source: "S-kaupat",
              price_observed_at: null,
              source_url: null,
              metrics,
            },
          ],
        },
      });
      return;
    }
    await route.fulfill({ status: 404, json: { code: "not_found", message: "Not found." } });
  });

  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Test Cheese" })).toBeVisible();
  await page.keyboard.press("Tab");
  await expect(page.getByLabel("Food category")).toBeFocused();
  await expect(page.getByRole("button", { name: "Use default preferences" })).toHaveAttribute(
    "aria-pressed",
    "true",
  );

  await page.getByLabel("Priority metric").selectOption("protein");
  await page.getByLabel("Priority direction").selectOption("most");
  await page.getByRole("button", { name: "Apply priority" }).click();
  await expect(page.getByText("Prioritizing Protein ↓ Descending")).toBeVisible();
  const proteinTile = page.locator(".metric-tile").filter({ hasText: "Protein" });
  await expect(proteinTile.getByText("Rank 1 · ↓ Descending")).toBeVisible();

  await page.getByRole("button", { name: "Use default preferences" }).click();
  await expect(page.getByText("Default order")).toBeVisible();
  await page.getByLabel("Food category").selectOption("dairy");
  await expect(page.getByRole("heading", { name: "Dairy Cheese" })).toBeVisible();

  await page.reload();
  await expect(page.getByRole("heading", { name: "Dairy Cheese" })).toBeVisible();
  expect(cookieSeenAfterReload).toBe(true);

  await page.setViewportSize({ width: 375, height: 812 });
  const columnCount = await page
    .locator(".metric-grid")
    .first()
    .evaluate((element) => getComputedStyle(element).gridTemplateColumns.split(" ").length);
  expect(columnCount).toBe(1);
});
