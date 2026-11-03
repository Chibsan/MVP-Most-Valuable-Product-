# Implementation Plan: Nutrition Comparer

**Branch**: `001-nutrition-comparer` | **Date**: 2026-11-01 | **Spec**: [spec.md](./spec.md)

## Summary

Implement a browser-based grocery comparison application with a React frontend, a Python/FastAPI backend, and PostgreSQL persistence. The API supplies S-kaupat categories and products, accepts a shopper's default/custom preference, and returns all metric values and independent ranks. Reliable primary values sort first; tied values are alphabetical; products missing the primary value follow using subsequent default criteria.

PostgreSQL is the source of truth for the web application's catalog and anonymous browser-session preferences. S-kaupat supplies category, product identity, and euro price data. Open Food Facts supplies nutritional facts only through exact barcode matches, with source attribution and API usage requirements enforced.

## Technical Context

**Language/Version**: Python 3.11+ for the API; TypeScript for React
**Primary Dependencies**: FastAPI, Pydantic, SQLAlchemy 2, Alembic, psycopg, httpx; React, Vite, TypeScript
**Storage**: PostgreSQL
**Testing**: pytest and FastAPI TestClient; Vitest and React Testing Library; PostgreSQL-backed integration tests
**Target Platform**: Browser client and Python ASGI server
**Project Type**: Web application (separate API and frontend)
**Performance Goals**: No measured latency target is specified. Benchmark category comparisons up to 500 products during implementation and record results before setting a production service-level objective.
**Constraints**: Use consistent per-100-g nutrition values and calculated unit prices when source-backed prices are later enabled; preserve unrounded values for ranking; only rank reliable values; use EUR only; leave prices null and unranked for now; do not add authentication for this feature. Seed only user-supplied S-kaupat URLs; query Open Food Facts only by exact barcode, with a registered custom User-Agent and a maximum 15 product reads per minute.
**Scale/Scope**: Use the user-supplied S-kaupat category/product links and exact-barcode Open Food Facts nutrition from the official offline export or approved API. Prices remain null and unranked in the current release. Categories remain selectable when empty; the schema permits adding categories and products without code changes.

## Constitution Check

| Principle | Plan application |
|---|---|
| Nutrition-first and budget-conscious | Return all supported nutritional and price values and ranks; show package price and size as well as normalized price. |
| Accurate, comparable data | Store nutrition basis/units and euro package price, source, and observation time; calculate price per 100 g from unrounded package price and size. |
| User-directed transparent ranking | Provide separate default-preference and prioritized-metric controls. Return the active priority and directions in the API response. |
| Honest missing-data handling | Rank only reliable facts. Include products with unavailable values after ranked products, order them using subsequent default criteria, and return no rank plus a reason for each unavailable metric. |
| Validated inputs | Validate preference identifiers, supported metrics, directions, sizes, and numeric ranges at the API boundary and database constraints. |
| Clear responsive UI | Provide category and ranking controls, show direction and per-metric ranks, and adapt the comparison table/cards to mobile. |
| Maintainable, documented, tested | Separate API/domain/persistence and UI concerns; document setup and API; test normalization, ranking, missing data, and user preference changes. |

No constitution violations are planned. Database-backed anonymous preferences clarify the specification's existing current-session preference assumption; user accounts and cross-browser synchronization remain out of scope.

## Project Structure

### Specification artifacts

```text
SDD Project/
├── .specify/memory/constitution.md
└── specs/001-nutrition-comparer/
    ├── spec.md
    ├── plan.md
    ├── research.md
    ├── data-model.md
    ├── quickstart.md
    └── contracts/openapi.yaml
```

### Planned implementation layout

```text
backend/
├── pyproject.toml
├── alembic.ini
├── alembic/versions/
├── app/
│   ├── main.py
│   ├── api/routes/
│   ├── core/config.py
│   ├── db/
│   ├── models/
│   ├── schemas/
│   └── services/
└── tests/
    ├── unit/
    └── integration/
frontend/
├── package.json
├── vite.config.ts
├── src/
│   ├── api/
│   ├── components/
│   ├── features/comparison/
│   ├── hooks/
│   ├── types/
│   └── main.tsx
└── tests/
docker-compose.yml
```

The backend and frontend are separate deployable applications. The four supplied categories and sixteen user-supplied product links seed URL-backed product identity and explicit package labels. Prices remain unavailable until source-backed values are supplied or approved S-kaupat access is available. The approved Open Food Facts API may enrich nutrition facts by exact barcode, but its API usage form and contact-identifying User-Agent are prerequisites. Do not fetch S-kaupat pages again or evade rate limits.

## Implementation Phases

### Phase 1 - Establish web app and database

- Add backend and frontend package manifests and minimal app entry points.
- Configure FastAPI settings from environment variables, PostgreSQL connectivity, and a local Docker Compose database.
- Add SQLAlchemy models and Alembic initial migration for categories, products, prices, nutrition facts, anonymous sessions, and preferences.
- Keep the four user-supplied S-kaupat category records available in the category endpoint and seed the sixteen user-provided product links with URL-backed fields.
- Add an Open Food Facts nutrition sync command keyed by exact barcode; identify the app, enforce the published rate limit, retain per-record provenance, and never retry HTTP 429.
- Support an offline Open Food Facts data export import for local exact-barcode matching without live API requests; preserve attribution, license, source URLs, and record update times.
- Keep S-kaupat price data unpopulated in this release; price ingestion is deferred unless the user requests it.
- Validate ingested categories, product sizes, euro prices, nutrition bases/units, and reliability states; report rejected records with actionable reasons.
- Add health/readiness endpoints and configuration documentation.

**Exit**: Backend starts against PostgreSQL; migrations apply to an empty database and provide the four supplied categories and sixteen linked product records with null price observations. Open Food Facts facts can be imported from the official offline export by exact barcode without API credentials; live API sync runs only after its published usage requirements are met.

### Phase 2 - Implement comparison domain and REST API

- Implement supported metrics, default directions, default/custom preference modes, dense metric-specific ranks with shared ties, alphabetical tie ordering, and deterministic fallback ordering for missing primary values.
- Calculate euro price per 100 g from valid package price and weight; use full precision for comparisons and round only for display.
- Add category/product retrieval and comparison endpoints as specified in the OpenAPI contract.
- Validate category, metric, direction, and product values; report missing/unreliable metric data with per-field warnings and null ranks. Only reliable facts participate in ranks or sorting.
- Add anonymous-session preference read/update endpoints using an opaque, HTTP-only session cookie; do not accept a client-supplied arbitrary user identifier.
- Add focused unit and API/database integration tests.

**Exit**: API contract tests prove category filtering, default/custom preference behavior, dense ranks, alphabetical ties, fallback ordering for missing primary values, invalid input handling, euro price normalization, and unreliable-data handling.

### Phase 3 - Implement responsive React comparison UI

- Build a category dropdown populated from S-kaupat category data, including configured empty categories.
- Provide separate controls for restoring default preferences and choosing a metric/direction to prioritize; visually identify the active selection.
- Render all nutritional values, package price/size, unit price, independent metric ranks, and data-quality warnings.
- Handle loading, empty, API error, and no-rank states without showing stale comparisons as current.
- Restore preference from the anonymous session endpoint. On selection, persist it with `PUT /preferences`, then refresh results with `POST /comparisons`.
- Add component and interaction tests for changing category/preferences, visible active state, rank rendering, and responsive states.

**Exit**: A shopper can browse a S-kaupat-backed category, inspect all values and ranks, and change preference without leaving or restarting the comparison view.

### Phase 4 - End-to-end verification and handoff

- Add browser-level tests for S-kaupat-backed category-to-ranking flow, default preference restoration, custom priority selection, and anonymous preference continuity within the session.
- Verify startup, migrations, user-supplied catalog seeding, optional Open Food Facts offline import, tests, and API docs using the quickstart guide.
- Document catalog maintenance and explain that product price/freshness depends on its source and observation time.
- Review accessibility basics, narrow-screen behavior, error visibility, and source/observation-time disclosure.

**Exit**: Acceptance scenarios in the spec are covered and setup is reproducible.

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Stale or store-specific prices are mistaken for current universal prices | Store source and observation time with each price; render these when available and make freshness limitations visible. |
| Nutrient facts are mixed across package and per-100-g bases | Require an explicit basis and unit in persistence; normalize at import/API boundaries and reject unsupported conversions. |
| Session identity is lost or preference state is exposed | Use opaque random session identifiers in HTTP-only, SameSite cookies; do not store identity in frontend-managed local storage or log cookie values. |
| Missing metrics create misleading overall ranks | Compute independent ranks only where that metric is valid; use missing-last behavior for overall sorting and expose a reason in the response. |
| Multi-criteria sort is mistaken for a combined nutritional score | Expose ordered criteria and individual ranks; label the selected primary criterion and avoid an aggregate score. |
| Price data is not in the current release scope | Keep package price, currency, and price-per-100-g response values null, with no price rank; do not implement price ingestion unless requested. |
| Open Food Facts rate limits or community data quality affect nutrition lookups | Require exact barcode matches, validate explicit per-100-g facts, attribute each record, throttle to the published limit, and stop on HTTP 429 without retries. |

## Decisions Needed During Implementation

- Set supported runtime versions and dependency versions according to the deployment environment.
- Confirm production hosting, database provisioning, TLS, and secret-management mechanisms before deployment.
- Confirm S-kaupat's permitted data access and refresh workflow before implementing automated price ingestion; do not assume scraping or an undocumented API is permitted.
- Complete the Open Food Facts API usage form and configure the required contact-bearing User-Agent before running barcode nutrition sync.
