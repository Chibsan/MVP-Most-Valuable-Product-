# Data Model: Nutrition Comparer

## Entities and Relationships

```text
Category 1 ─── * Product 1 ─── * PriceObservation
                        └───── * NutritionFact

AnonymousSession 1 ─── 0..1 UserPreference
Category 1 ─────────── * UserPreference (optional selected category)
```

## Tables

### `categories`

| Column | Type | Constraints / meaning |
|---|---|---|
| `id` | UUID | Primary key |
| `slug` | TEXT | Required, unique, stable API identifier |
| `name` | TEXT | Required, displayed name |
| `is_active` | BOOLEAN | Required; controls whether category appears in the selector |
| `source_url` | TEXT | S-kaupat category URL when available |
| `created_at` | TIMESTAMPTZ | Required |

Obtain category records from S-kaupat. Configured active categories remain selectable when empty; the comparison endpoint returns an empty result for a category without products.

### `products`

| Column | Type | Constraints / meaning |
|---|---|---|
| `id` | UUID | Primary key |
| `category_id` | UUID | Required foreign key to `categories` |
| `name` | TEXT | Required, non-empty |
| `brand` | TEXT | Optional |
| `barcode` | TEXT | Optional; unique when supplied |
| `package_size_g` | NUMERIC(12, 3) | Optional; positive when supplied |
| `package_size_label` | TEXT | Optional source-backed package-size display text; preserve volume units without guessing a grams conversion |
| `source_url` | TEXT | S-kaupat product listing URL when available |
| `source_observed_at` | TIMESTAMPTZ | Optional source observation time; not import time |
| `created_at` | TIMESTAMPTZ | Required |
| `updated_at` | TIMESTAMPTZ | Required |

### `price_observations`

| Column | Type | Constraints / meaning |
|---|---|---|
| `id` | UUID | Primary key |
| `product_id` | UUID | Required foreign key to `products` |
| `package_price` | NUMERIC(12, 4) | Nullable; nonnegative when supplied |
| `currency` | CHAR(3) | Required `EUR` when price is available; enforce with a database check |
| `source_name` | TEXT | Required `S-kaupat` |
| `source_url` | TEXT | Optional source link |
| `observed_at` | TIMESTAMPTZ | Optional timestamp from source |
| `quality_status` | TEXT | Required: `reliable`, `unreliable`, `unverified`, `missing`, or `invalid` |
| `quality_note` | TEXT | Optional explanation |
| `created_at` | TIMESTAMPTZ | Required import/record time; not a substitute for source observation time |

Price per 100 g is derived as `package_price / package_size_g * 100` only when both inputs are valid and currency is EUR. Do not round before ranking. A missing timestamp must remain unknown. Only `reliable` price observations participate in price ranks or price-based ordering.

A price observation is `reliable` only when its source is S-kaupat and its euro amount and positive package weight are valid. Unreliable, unverified, missing, or invalid observations do not rank. Missing observation time is shown as unknown, not replaced with the database import time.

Until source-backed S-kaupat prices are explicitly provided, products have no price observation. The API returns `null` for package price, currency, and price per 100 g, and the price metric is unavailable and unranked; do not create placeholder observations or substitute another source.

### `nutrition_facts`

| Column | Type | Constraints / meaning |
|---|---|---|
| `id` | UUID | Primary key |
| `product_id` | UUID | Required foreign key to `products` |
| `metric` | TEXT | Required supported metric key |
| `value` | NUMERIC(12, 4) | Nullable; nonnegative when supplied |
| `unit` | TEXT | Required canonical unit for the metric |
| `basis_g` | NUMERIC(8, 3) | Required positive basis; normalized API facts use 100 g |
| `source_name` | TEXT | Required `S-kaupat` or `Open Food Facts`; Open Food Facts facts require an exact product barcode match |
| `observed_at` | TIMESTAMPTZ | Optional source timestamp |
| `quality_status` | TEXT | Required: `reliable`, `unreliable`, `unverified`, `missing`, or `invalid` |
| `quality_note` | TEXT | Optional explanation |

Facts are retained by source. An Open Food Facts sync updates its current record for each product and metric, making repeated syncs idempotent; other observations may be retained as history. The API selects the current fact by `observed_at`, then `created_at`, then stable record ID, with missing source timestamps sorting before dated observations. Supported metrics and units:

| Metric key | Unit | Default direction |
|---|---|---|
| `calories` | `kcal` per 100 g | `least` |
| `carbohydrates` | `g` per 100 g | `least` |
| `protein` | `g` per 100 g | `most` |
| `fat` | `g` per 100 g | `least` |
| `fibre` | `g` per 100 g | `most` |

Only `reliable` facts participate in metric ranks or ordering. An Open Food Facts fact is reliable only when its barcode exactly matches the product, the API or official export provides the metric's explicit `_100g` field, and the numeric value is finite and within the supported range. The fact's `source_url` points to its Open Food Facts record. `observed_at` records the source's record update timestamp, not a package-label observation; missing timestamps remain unknown and are never replaced with the import time. The offline importer processes the official export locally and does not make product API requests. Treat `unreliable`, `unverified`, `missing`, and `invalid` as unavailable; they have no rank. Missing facts should be represented as an explicit missing status or absent fact with an API-level missing-data explanation; never encode missing as zero.

Open Food Facts data is community-contributed. The UI must attribute Open Food Facts and link the source record. The API client must identify the application with a custom User-Agent, respect the published maximum of 15 product reads per minute per IP, stop on HTTP 429 without retrying, and be used only after its API usage form is completed. Database use is subject to the Open Database License (ODbL) and Database Contents License (DBCL).

### `anonymous_sessions`

| Column | Type | Constraints / meaning |
|---|---|---|
| `id` | UUID | Primary key generated server-side |
| `token_hash` | TEXT | Required, unique hash of the opaque cookie token; never store the raw token |
| `created_at` | TIMESTAMPTZ | Required |
| `last_seen_at` | TIMESTAMPTZ | Required |
| `expires_at` | TIMESTAMPTZ | Required; retention policy controlled by configuration |

The browser receives an opaque session token in an HTTP-only, SameSite cookie. Look up sessions by the hash of the token, never the raw token. Cookie lifetime and session expiration must be aligned.

### `user_preferences`

| Column | Type | Constraints / meaning |
|---|---|---|
| `session_id` | UUID | Primary key and foreign key to `anonymous_sessions` |
| `category_id` | UUID | Optional foreign key to selected category |
| `primary_metric` | TEXT | Supported metric key; default `calories` |
| `primary_direction` | TEXT | `most` or `least`; default `least` |
| `preference_mode` | TEXT | Required: `default` or `custom`; determines whether the default criterion sequence or custom primary criterion is active |
| `updated_at` | TIMESTAMPTZ | Required |

The default-preference control sets `preference_mode=default` and restores canonical criteria. The separate priority control sets `preference_mode=custom` and stores its selected primary metric/direction. The API computes all remaining criteria from the stable default list; this avoids storing stale or conflicting copies of ranking rules.

## Comparison Response Projection

Comparison responses are computed projections, not persisted rankings:

- Product identity and category.
- Package size and latest reliable euro price, source, and observation time.
- Derived price per 100 g, if computable.
- Each nutrition value per 100 g and its unit.
- Each metric's direction and independent dense rank, or `null` rank plus a missing/unreliable reason.
- Ordered criterion list and selected primary criterion.
- A one-based display position after placing products without a reliable primary value after products with a value, applying subsequent default criteria to that fallback group, and alphabetizing ties. This position does not replace independent metric ranks.

## Integrity and Indexing

- Add foreign keys and non-empty/positive-value checks where applicable.
- Index `products(category_id, name)`, `price_observations(product_id, observed_at DESC)`, and `nutrition_facts(product_id, metric, observed_at DESC)`.
- Reject or mark prices outside EUR as invalid; never compare unlike currencies.
- Apply retention/cleanup to expired anonymous sessions and their preferences.
