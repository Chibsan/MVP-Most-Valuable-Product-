# Research: Nutrition Comparer

## Decisions

### Separate FastAPI and React applications

- **Decision**: Implement a typed FastAPI JSON API and a standalone React + TypeScript frontend.
- **Rationale**: This matches the requested stack and separates validation, database access, and ranking rules from presentation. An explicit JSON contract allows focused API and UI tests.
- **Alternatives considered**: Server-rendered HTML or a monolithic application. The selected architecture matches the requested React frontend and API separation.

### PostgreSQL with SQLAlchemy and Alembic

- **Decision**: Use PostgreSQL as the web application's source of truth, SQLAlchemy 2 for persistence, and Alembic for schema migrations.
- **Rationale**: Relational constraints suit products, categories, price observations, metric facts, sessions, and preferences. Migrations provide a repeatable schema evolution path.
- **Alternatives considered**: Store the catalog in static files or use an embedded database. Those approaches do not meet the PostgreSQL persistence requirement for catalog data and anonymous preferences.

### Explicit metric facts and independent ranks

- **Decision**: Normalize product nutrition facts as metric-specific records with a per-100-g basis, unit, reliability state, and optional source. Build a comparison result with each metric's value and rank. Keep the selected metric/direction first in the ordered criteria, then preserve the relative order and directions of all remaining defaults.
- **Rationale**: A separate rank per metric makes comparisons inspectable and prevents hiding tradeoffs inside one unexplained score. Explicitly modeling missing values prevents unknown values from being confused with zero.
- **Alternatives considered**: A single aggregate score or one mutable rank column. An aggregate score is opaque and can hide tradeoffs; a single rank cannot represent different metrics or directions.

### Package-price observations and normalized unit price

- **Decision**: Record package amount, package price, currency, price source, and observation time. Derive price per 100 g using the package values without rounding before sorting.
- **Rationale**: Package prices vary by store and time; retaining source and timestamp lets the UI communicate limits. Derivation avoids inconsistent copies of normalized price.
- **Alternatives considered**: Persist only a price-per-100-g value, or trust an imported normalized-price column. Those approaches lose package context and may disagree with package price/size.

### Anonymous browser-session preferences

- **Decision**: Give each browser session an opaque server-issued identifier in an HTTP-only cookie and persist that session's preference in PostgreSQL. No accounts, personal profile, or cross-browser sync are included.
- **Rationale**: The requested database stores user preferences while the current feature scope excludes account management. A server-owned anonymous session provides a persistence key without requesting personal identity.
- **Alternatives considered**: Require login, keep preferences only in React state, or accept a user identifier from the client. Login expands scope; in-memory state disappears between requests; client-asserted identities are not trustworthy.

### S-kaupat catalog source; prices deferred

- **Decision**: Source categories and product identity from S-kaupat. The user supplied four category URLs and sixteen product URLs; seed their linked identity fields (URL-derived name, brand, barcode, and explicitly stated package size) only. Prices are intentionally null and unranked in the current release; do not seed price observations. Store product source URLs and observation times when supplied; do not infer missing values.
- **Rationale**: The user specified S-kaupat as the source, and product comparisons require transparent provenance and freshness information.
- **Access result and constraint**: Direct requests to the S-kaupat homepage, `robots.txt`, and privacy page returned HTTP 429. Requests were not retried and no proxy, alternate host, user-agent rotation, or undocumented endpoint was attempted. The user-supplied product URLs allow the linked fields above to be recorded, but do not supply current prices, nutrition values, or observation timestamps. Prices are intentionally omitted from the current release; other missing values remain unavailable unless supplied by their approved source.

### Open Food Facts nutrition source

- **Decision**: Use Open Food Facts for nutrition facts only, queried by the exact barcode already supplied for each S-kaupat product. Do not use it as a source of category membership, product identity, or prices.
- **Acceptance rules**: Accept only an exact barcode match from the API response or export and an explicit nutrient field whose key states `_100g`; validate finite, nonnegative values against the supported per-100-g range. Missing and invalid fields stay unavailable and cannot rank. Keep the Open Food Facts product-record URL and its `last_modified_t` value, labeling that timestamp as a record update rather than a nutrition-label observation.
- **Operational and licensing rules**: Complete the published API usage form first, identify the application and contact email in a custom User-Agent, limit requests to at most 15 product reads per minute per IP, and stop without retrying HTTP 429. Attribute Open Food Facts and its record in the UI and respect ODbL/DBCL terms for database use.
- **Implementation**: `python -m app.catalog sync-openfoodfacts` provides an explicit, manually started sync. It is gated by `OPENFOODFACTS_USAGE_FORM_COMPLETED` and `OPENFOODFACTS_CONTACT_EMAIL`; no live sync runs automatically.
- **Offline alternative**: The official data export page provides a nightly compressed TSV/CSV export. Import it locally with `python -m app.catalog import-openfoodfacts-export PATH`; the importer scans the export and retains only exact matches for barcodes already in the catalog. This avoids live API requests and their API usage-form/contact User-Agent prerequisites, but Open Food Facts database licensing and attribution obligations still apply.
- **Import verification**: The official export downloaded on 2026-11-01 matched 13 of the 16 seeded product barcodes. It populated 65 metric records: 59 reliable nutrient values and 6 explicitly missing values. Three products had no exact record. No price observations were added.

## Ranking Contract

Default criterion order and directions:

1. Calories per 100 g — least
2. Carbohydrates per 100 g — least
3. Protein per 100 g — most
4. Fat per 100 g — least
5. Fibre per 100 g — most
6. Price per 100 g — least

The interface offers a default-preference control and a separate custom priority control. Default preferences use the criteria above; custom priority moves the selected metric/direction to the front while other criteria retain their relative order and default directions.

Rank each metric independently over reliable values only. Use dense ranks: values `10, 10, 9` receive ranks `1, 1, 2` (or corresponding reversed ranks for a "least" direction). Equal values share a rank and are displayed alphabetically by product name; use a stable identifier only when names also match. Missing, invalid, unverified, or unreliable values have no rank for that metric. Only values classified as reliable may be used for ranking.

For overall display, sort products with a reliable primary value first, according to the selected direction. Equal primary values keep their shared rank and display alphabetically; do not use other metrics to break a tie between reliable equal primary values. Put products without a reliable primary value after those products; order that group using the subsequent default criteria, skipping the selected criterion. Within this fallback group, continue to the next default criterion when a fallback value is unavailable; equal fallback values share their own dense metric rank and display alphabetically. If no remaining reliable values distinguish products, sort alphabetically. This fallback ordering does not assign a rank for an unavailable metric.

## Assumptions and Constraints

- All nutrition comparisons use values per 100 g. Calories use kcal; macronutrients and fibre use grams.
- Unit price is derived only for products with a valid positive package weight in grams and a valid nonnegative price in EUR. Values in any other currency are invalid and cannot rank.
- Category and product identity data must come from S-kaupat; nutrition facts may come only from an exact-barcode Open Food Facts API lookup or official offline export. Prices remain null by current scope. Source provenance must not be fabricated.
- Category choices are driven by the S-kaupat source data and configured active categories, including empty categories.
- User preferences last for the anonymous browser session and are not linked to personally identifying information.
- Cross-origin behavior is restricted to configured frontend origins; deployment must use HTTPS and appropriate cookie settings.
