import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";
import * as api from "./api/client";
import type { Category, Comparison, Preference } from "./types/api";

vi.mock("./api/client", async () => {
  const actual = await vi.importActual<typeof import("./api/client")>("./api/client");
  return {
    ...actual,
    getCategories: vi.fn(),
    getPreference: vi.fn(),
    savePreference: vi.fn(),
    compare: vi.fn(),
  };
});

const categories: Category[] = [
  {
    slug: "cheese",
    name: "Cheese",
    product_count: 1,
    is_active: true,
    source_url: null,
  },
];

const defaultPreference: Preference = {
  category: "cheese",
  preference_mode: "default",
  primary_metric: "calories",
  primary_direction: "least",
  criteria: [],
};

const comparison: Comparison = {
  category: "cheese",
  preference_mode: "default",
  primary_metric: "calories",
  primary_direction: "least",
  criteria: [],
  unranked_count: 0,
  items: [
    {
      id: "00000000-0000-0000-0000-000000000001",
      name: "Test Cheese",
      category: "cheese",
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
      metrics: {
        calories: {
          value: 100,
          unit: "kcal/100g",
          direction: "least",
          rank: 1,
          quality_status: "reliable",
          reason: null,
          source_url: null,
          observed_at: null,
        },
        carbohydrates: {
          value: 1,
          unit: "g/100g",
          direction: "least",
          rank: 1,
          quality_status: "reliable",
          reason: null,
          source_url: null,
          observed_at: null,
        },
        protein: {
          value: 20,
          unit: "g/100g",
          direction: "most",
          rank: 1,
          quality_status: "reliable",
          reason: null,
          source_url: null,
          observed_at: null,
        },
        fat: {
          value: 10,
          unit: "g/100g",
          direction: "least",
          rank: 1,
          quality_status: "reliable",
          reason: null,
          source_url: null,
          observed_at: null,
        },
        fibre: {
          value: 0,
          unit: "g/100g",
          direction: "most",
          rank: 1,
          quality_status: "reliable",
          reason: null,
          source_url: null,
          observed_at: null,
        },
        price: {
          value: 1.25,
          unit: "EUR/100g",
          direction: "least",
          rank: 1,
          quality_status: "reliable",
          reason: null,
          source_url: null,
          observed_at: null,
        },
      },
    },
  ],
};

describe("comparison application", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.getCategories).mockResolvedValue({ items: categories });
    vi.mocked(api.getPreference).mockResolvedValue(defaultPreference);
    vi.mocked(api.savePreference).mockResolvedValue(defaultPreference);
    vi.mocked(api.compare).mockResolvedValue(comparison);
  });

  it("renders product metrics and the active default preference", async () => {
    render(<App />);
    expect(await screen.findByRole("heading", { name: "Test Cheese" })).toBeInTheDocument();
    expect(screen.getByText("€1.25")).toBeInTheDocument();
    expect(screen.getAllByText("Rank 1 · ↑ Ascending").length).toBeGreaterThan(1);
    expect(screen.getByRole("button", { name: "Use default preferences" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });

  it("saves a chosen primary metric and direction before comparing", async () => {
    render(<App />);
    await screen.findByRole("heading", { name: "Test Cheese" });
    fireEvent.change(screen.getByRole("combobox", { name: "Priority metric" }), {
      target: { value: "protein" },
    });
    fireEvent.change(screen.getByRole("combobox", { name: "Priority direction" }), {
      target: { value: "most" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Apply priority" }));
    await waitFor(() =>
      expect(api.savePreference).toHaveBeenLastCalledWith({
        category: "cheese",
        preference_mode: "custom",
        primary_metric: "protein",
        primary_direction: "most",
      }),
    );
    expect(api.compare).toHaveBeenLastCalledWith({
      category: "cheese",
      preference_mode: "custom",
      primary_metric: "protein",
      primary_direction: "most",
    });
  });

  it("shows a clear empty-catalog state", async () => {
    vi.mocked(api.getCategories).mockResolvedValue({ items: [] });
    render(<App />);
    expect(
      await screen.findByText(/Categories and product information must be supplied/),
    ).toBeInTheDocument();
  });

  it("clears previous products and reports comparison errors", async () => {
    render(<App />);
    await screen.findByRole("heading", { name: "Test Cheese" });
    vi.mocked(api.savePreference).mockRejectedValueOnce(new api.ApiError("Could not save.", 500));
    fireEvent.click(screen.getByRole("button", { name: "Use default preferences" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Could not save.");
    expect(screen.queryByRole("heading", { name: "Test Cheese" })).not.toBeInTheDocument();
  });
});
