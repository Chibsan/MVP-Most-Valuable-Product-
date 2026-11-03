# Quickstart: Nutrition Comparer

This guide describes the local development workflow for the FastAPI, React, and PostgreSQL application. The four category URLs and 16 product links supplied by the user are seeded into the local catalog. Seeded records include URL-backed identity fields and explicit package sizes; this workspace also has Open Food Facts nutrition facts imported by exact barcode from its offline export. Direct requests to S-kaupat previously returned HTTP 429, so no page scraping or retries were performed. Prices remain null by scope.

## Prerequisites

- Python 3.11 or newer
- Node.js LTS and npm
- Docker Engine with Docker Compose
- For live Open Food Facts API sync only: a contact email and a completed API usage form. Neither is required to import the offline export.

## Start PostgreSQL

From the repository root:

```bash
cd "SDD Project"
docker compose up -d db
```

In the backend directory, copy `.env.example` to `.env` to use local database settings. Replace the example credentials before exposing the database beyond local development.

## Start the API

```bash
cd "SDD Project/backend"
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

The API is available at `http://localhost:8000`; interactive OpenAPI documentation is available at `http://localhost:8000/docs`.

## Start the React frontend

In another terminal:

```bash
cd "SDD Project/frontend"
npm install
npm run dev
```

Open the Vite URL printed in the terminal. The development proxy forwards `/api` requests to `http://localhost:8000`, so browser requests and the anonymous session cookie use a consistent origin.

## Verify the implementation

```bash
cd "SDD Project/backend"
pytest
```

```bash
cd "SDD Project/frontend"
npm test
npm run build
npx playwright install chromium
npm run test:e2e
```

The browser acceptance test uses controlled API fixtures; it verifies the user flow without making live S-kaupat requests.

## Preference and comparison behavior

- The user-supplied S-kaupat categories Milk, Minced meat, Softdrinks, and Snack bars and biscuits are persisted by the migrations.
- The 16 linked products have names, brands, barcodes, URLs, and package labels taken from their supplied links. Weight values are stored only where the URL explicitly supplies grams. Volume labels such as 1 l are shown as supplied and are not converted to grams. Tracking query parameters are omitted from stored source URLs.
- Prices intentionally remain `null` and unranked for now; no price observations are seeded or imported. Do not substitute values from another source.
- This workspace was enriched from the official Open Food Facts offline export downloaded on 2026-11-01: 13 of 16 product barcodes matched. No exact record was found for barcodes `6411200004622`, `6413605254411`, and `6415600502108`; six matched products had one nutrient field missing. Only exact barcode matches and explicit, valid per-100-g facts were imported.
- On a fresh database, Open Food Facts facts remain unavailable until the offline export command below or the separately gated API sync is run.
- Open Food Facts record update times are not label observation times. Nutrition values link to their source record, and the UI attributes the Open Food Facts database license.
- Initial priority: least calories, least carbohydrates, most protein, least fat, most fibre, least price per 100 g.
- The default-preference button restores this order; the separate priority control selects a metric/direction to prioritize.
- Every metric has an independent dense rank; equal values share a rank and are displayed alphabetically.
- Missing, invalid, unverified, or unreliable values show as unavailable with no rank for that metric.
- Product prices are in euros (€); a price comparison shows package price and size alongside unit price when reliable source data exists.
- Anonymous preference cookies are HTTP-only and same-site; set `SESSION_COOKIE_SECURE=true` when serving the API over HTTPS.
- Category records are limited to the four supplied category URLs. Sixteen linked products are seeded; price fields remain `null` until source-backed prices are explicitly requested.

## Open Food Facts nutrition enrichment

**Offline export (no API contact email or API usage form is required):** Open Food Facts publishes a nightly full products export at [the official data page](https://world.openfoodfacts.org/data). Download its compressed tab-separated export, then import it locally:

```bash
curl -L --fail --output /tmp/openfoodfacts-products.csv.gz \
  https://static.openfoodfacts.org/data/en.openfoodfacts.org.products.csv.gz
cd "SDD Project/backend"
python -m app.catalog import-openfoodfacts-export /tmp/openfoodfacts-products.csv.gz
```

The export is large (about 1.5 GB compressed at the time this workflow was added); the importer streams it and retains only exact barcode matches for products already in the local catalog. It validates explicit per-100-g fields, imports the newest matching record for each barcode, preserves the product-record URL and record-update timestamp, and marks missing or invalid values unavailable. Review Open Food Facts' [data licensing terms](https://world.openfoodfacts.org/data) before distributing database extracts or derived datasets.

The live API sync remains available only after completing the [API usage form](https://docs.google.com/forms/d/e/1FAIpQLSdIE3D8qvjC_zRJw1W8OmuHhsWJ_NSckiiniAHlfaVwUZCziQ/viewform), setting a real `OPENFOODFACTS_CONTACT_EMAIL`, and setting `OPENFOODFACTS_USAGE_FORM_COMPLETED=true` in `backend/.env`. The API command uses a contact-identifying User-Agent and stops without retrying on HTTP 429.

Both methods require PostgreSQL to be running with migrations applied. Neither method imports or changes prices; price fields remain null by design.

## Price data scope (deferred)

Prices intentionally remain `null` and unranked for now; no price observations are seeded or imported, and there is no price sync command. If price data is requested later, use source-backed S-kaupat euro prices, preserve source observation times when provided, reject non-EUR prices, and keep missing or unreliable prices unranked. Do not populate product details from guesses or another project folder.
