import { useCallback, useEffect, useMemo, useState } from "react";

import {
  ApiError,
  compare,
  getCategories,
  getPreference,
  metricLabels,
  savePreference,
} from "./api/client";
import type {
  Category,
  ComparedProduct,
  Comparison,
  Direction,
  Metric,
  Preference,
  PreferenceUpdate,
} from "./types/api";

const metrics: Metric[] = [
  "calories",
  "carbohydrates",
  "protein",
  "fat",
  "fibre",
  "price",
];

const directions: Direction[] = ["least", "most"];

const directionLabels: Record<Direction, string> = {
  least: "↑ Ascending",
  most: "↓ Descending",
};

function describeError(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  return "The comparison could not be updated. Please try again.";
}

function preferencePayload(
  category: string,
  preference: Pick<Preference, "preference_mode" | "primary_metric" | "primary_direction">,
): PreferenceUpdate {
  if (preference.preference_mode === "default") {
    return { category, preference_mode: "default" };
  }
  return {
    category,
    preference_mode: "custom",
    primary_metric: preference.primary_metric,
    primary_direction: preference.primary_direction,
  };
}

function displayNumber(value: number | null, digits = 2): string {
  if (value === null) return "Unavailable";
  return new Intl.NumberFormat(undefined, { maximumFractionDigits: digits }).format(value);
}

function MetricTile({
  product,
  metric,
}: {
  product: ComparedProduct;
  metric: Metric;
}) {
  const result = product.metrics[metric];
  const value =
    metric === "price"
      ? result.value === null
        ? "Unavailable"
        : `€${displayNumber(result.value)}`
      : displayNumber(result.value);
  const rank = result.rank === null ? "Not ranked" : `Rank ${result.rank}`;
  return (
    <div className="metric-tile">
      <div className="metric-heading">
        <span>{metricLabels[metric]}</span>
        <span>{result.unit}</span>
      </div>
      <strong>{value}</strong>
      <span className="metric-rank">
        {rank} · {directionLabels[result.direction]}
      </span>
    </div>
  );
}

function ProductCard({
  product,
  primary,
}: {
  product: ComparedProduct;
  primary: Metric;
}) {
  const ordered = [primary, ...metrics.filter((metric) => metric !== primary)];
  return (
    <article className="product-card">
      <header className="product-header">
        <h3>{product.name}</h3>
        <p className="product-brand">
          {product.brand ? `${product.brand} · ` : ""}
          {product.package_size_label ??
            (product.package_size_g === null ? "" : `${displayNumber(product.package_size_g, 3)} g`)}
        </p>
        <p className="shop-name">
          Shop:{" "}
          {product.source_url ? (
            <a href={product.source_url} target="_blank" rel="noreferrer">
              S-market
            </a>
          ) : (
            "S-market"
          )}
        </p>
      </header>
      <div className="metric-grid">
        {ordered.map((metric) => (
          <MetricTile key={metric} product={product} metric={metric} />
        ))}
      </div>
    </article>
  );
}

export default function App() {
  const [categories, setCategories] = useState<Category[]>([]);
  const [preference, setPreference] = useState<Preference | null>(null);
  const [comparison, setComparison] = useState<Comparison | null>(null);
  const [category, setCategory] = useState("");
  const [draftMetric, setDraftMetric] = useState<Metric>("calories");
  const [draftDirection, setDraftDirection] = useState<Direction>("least");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const updateAndCompare = useCallback(
    async (update: PreferenceUpdate) => {
      setLoading(true);
      setError(null);
      setComparison(null);
      try {
        const saved = await savePreference(update);
        const result = await compare(update);
        setPreference(saved);
        setCategory(update.category);
        setDraftMetric(saved.primary_metric);
        setDraftDirection(saved.primary_direction);
        setComparison(result);
      } catch (cause) {
        setError(describeError(cause));
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  useEffect(() => {
    let active = true;
    async function initialize() {
      setLoading(true);
      setError(null);
      try {
        const [categoryResponse, savedPreference] = await Promise.all([
          getCategories(),
          getPreference(),
        ]);
        if (!active) return;
        const available = categoryResponse.items.filter((item) => item.is_active);
        setCategories(available);
        setPreference(savedPreference);
        const selectedCategory =
          available.find((item) => item.slug === savedPreference.category)?.slug ??
          available[0]?.slug;
        if (!selectedCategory) {
          setLoading(false);
          return;
        }
        const update = preferencePayload(selectedCategory, savedPreference);
        setCategory(selectedCategory);
        setDraftMetric(savedPreference.primary_metric);
        setDraftDirection(savedPreference.primary_direction);
        if (savedPreference.category === selectedCategory) {
          const result = await compare(update);
          if (active) setComparison(result);
        } else {
          const saved = await savePreference(update);
          const result = await compare(update);
          if (active) {
            setPreference(saved);
            setComparison(result);
          }
        }
      } catch (cause) {
        if (active) setError(describeError(cause));
      } finally {
        if (active) setLoading(false);
      }
    }
    void initialize();
    return () => {
      active = false;
    };
  }, []);

  const selectedCategory = useMemo(
    () => categories.find((item) => item.slug === category),
    [categories, category],
  );

  function chooseCategory(value: string) {
    setCategory(value);
    if (!preference) return;
    void updateAndCompare(preferencePayload(value, preference));
  }

  function applyPriority() {
    if (!category) return;
    void updateAndCompare({
      category,
      preference_mode: "custom",
      primary_metric: draftMetric,
      primary_direction: draftDirection,
    });
  }

  function restoreDefaults() {
    if (!category) return;
    void updateAndCompare({ category, preference_mode: "default" });
  }

  const isDefault = preference?.preference_mode === "default";

  return (
    <main className="app-shell">
      <header className="hero">
        <p className="eyebrow">Nutrition first. Budget conscious.</p>
        <h1>Nutrition Comparer</h1>
        <p>
          Compare grocery products using transparent nutrition values and euro
          unit prices.
        </p>
      </header>

      <section className="controls-panel" aria-label="Comparison preferences">
        <label className="field">
          <span>Food category</span>
          <select
            aria-label="Food category"
            value={category}
            onChange={(event) => chooseCategory(event.target.value)}
            disabled={categories.length === 0 || loading}
          >
            {categories.length === 0 && <option value="">No categories available</option>}
            {categories.map((item) => (
              <option key={item.slug} value={item.slug}>
                {item.name} ({item.product_count})
              </option>
            ))}
          </select>
        </label>

        <div className="priority-controls">
          <label className="field">
            <span>Prioritize</span>
            <select
              aria-label="Priority metric"
              value={draftMetric}
              onChange={(event) => setDraftMetric(event.target.value as Metric)}
              disabled={!category || loading}
            >
              {metrics.map((metric) => (
                <option key={metric} value={metric}>
                  {metricLabels[metric]}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>Direction</span>
            <select
              aria-label="Priority direction"
              value={draftDirection}
              onChange={(event) => setDraftDirection(event.target.value as Direction)}
              disabled={!category || loading}
            >
              {directions.map((direction) => (
                <option key={direction} value={direction}>
                  {direction === "least" ? "Least ↑ (ascending)" : "Most ↓ (descending)"}
                </option>
              ))}
            </select>
          </label>
          <button
            className="button button-primary"
            onClick={applyPriority}
            disabled={!category || loading}
          >
            Apply priority
          </button>
        </div>

        <button
          className={`button ${isDefault ? "button-active" : "button-secondary"}`}
          onClick={restoreDefaults}
          disabled={!category || loading}
          aria-pressed={isDefault}
        >
          Use default preferences
        </button>
      </section>

      <section className="results-section" aria-live="polite">
        <div className="results-heading">
          <div>
            <p className="eyebrow">Comparison</p>
            <h2>{selectedCategory?.name ?? "Product catalog"}</h2>
          </div>
          {comparison && (
            <p className="active-preference">
              {isDefault
                ? "Default order"
                : `Prioritizing ${metricLabels[comparison.primary_metric]} ${directionLabels[comparison.primary_direction]}`}
            </p>
          )}
        </div>

        {loading && <p className="status-message">Loading comparison…</p>}
        {!loading && error && (
          <div className="status-message status-error" role="alert">
            <p>{error}</p>
            {category && preference && (
              <button
                className="button button-secondary"
                onClick={() => updateAndCompare(preferencePayload(category, preference))}
              >
                Try again
              </button>
            )}
          </div>
        )}
        {!loading && !error && categories.length === 0 && (
          <p className="status-message">
            Product data is currently unavailable. Categories and product
            information must be supplied through an approved S-kaupat data
            access method.
          </p>
        )}
        {!loading && !error && categories.length > 0 && comparison?.items.length === 0 && (
          <p className="status-message">
            No products are available to compare in this category yet.
          </p>
        )}
        {!loading && !error && comparison && comparison.items.length > 0 && (
          <>
            <p className="ranking-note">
              All metric ranks are independent. Equal values share a rank;
              unavailable values are not ranked.{" "}
              {comparison.unranked_count > 0 &&
                `${comparison.unranked_count} product(s) have no reliable value for the primary metric and appear after ranked products.`}
            </p>
            <div className="product-list">
              {comparison.items.map((product) => (
                <ProductCard
                  key={product.id}
                  product={product}
                  primary={comparison.primary_metric}
                />
              ))}
            </div>
          </>
        )}
      </section>
      <footer>
        Product identity and prices: S-kaupat. Nutrition data, where available:
        {" "}
        <a href="https://world.openfoodfacts.org/" target="_blank" rel="noreferrer">
          Open Food Facts
        </a>
        {" "}under the{" "}
        <a
          href="https://opendatacommons.org/licenses/odbl/1.0/"
          target="_blank"
          rel="noreferrer"
        >
          Open Database License (ODbL)
        </a>
        . Product data and price freshness depend on the source observation
        time shown when available.
      </footer>
    </main>
  );
}
