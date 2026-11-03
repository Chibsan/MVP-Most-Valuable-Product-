# Tasks: Nutrition Comparer

**Input**: Design documents from `SDD Project/specs/001-nutrition-comparer/`
**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [data-model.md](./data-model.md), [contracts/openapi.yaml](./contracts/openapi.yaml)

**Tests**: Include the focused unit, API, database integration, UI, and end-to-end tests specified below.

**Implementation status**: Core API, ranking, persistence, UI, and browser workflows are implemented. Four user-supplied categories and sixteen product links are seeded with URL-backed identity and package labels. The 2026-11-01 official Open Food Facts offline export was imported locally: 13 exact barcode matches yielded 59 reliable facts and 6 missing nutrient facts; 3 product barcodes were not present. Live API sync remains gated by its usage form and contact email. Prices remain `null` and unranked; no price observations are seeded or imported.

## Phase 1: Project Setup

**Purpose**: Establish separate backend/frontend applications and a local PostgreSQL service.

- [x] T001 Create the backend Python package, development dependencies, and test configuration in `backend/pyproject.toml`.
- [x] T002 [P] Scaffold the React, TypeScript, and Vite application with test scripts in `frontend/`.
- [x] T003 [P] Add a local PostgreSQL service and backend/frontend environment examples in `docker-compose.yml` and the relevant `.env.example` files.
- [x] T004 Add backend settings, database connection/session lifecycle, and a FastAPI application entry point under `backend/app/`.
- [x] T005 [P] Configure the Vite development proxy for `/api` requests to the FastAPI origin in `frontend/vite.config.ts`.
- [x] T006 Add backend liveness/readiness routes and tests for successful health response and unavailable database readiness in `backend/app/api/` and `backend/tests/`.

## Phase 2: Foundational Persistence and Catalog

**Purpose**: Implement persistent catalog, price/nutrition data, migrations, and source-specific enrichment. Required before comparison/API user stories.

- [x] T007 Define SQLAlchemy models and constraints for categories, products, price observations, nutrition facts, anonymous sessions, and user preferences in `backend/app/models/`.
- [x] T008 Create the initial Alembic migration and verify it upgrades an empty PostgreSQL database in `backend/alembic/`.
- [x] T009 Persist the four user-supplied S-kaupat category records and keep the configured categories selectable when empty. Live category discovery remains unavailable until an approved source-access method is confirmed.
- [x] T010 Implement exact-barcode Open Food Facts nutrition import, retain record URLs/update timestamps, validate explicit per-100-g values, and respect live API requirements and rate limits. Prices are intentionally omitted for now.
- [x] T011 Add persistence and catalog tests for seeded categories/products, package labels, source URLs, EUR-only prices, unreliable values, and rejected records in `backend/tests/integration/`. Offline export nutrition was imported for 13 matching barcodes; no API sync was run, and prices remain null by scope.
- [x] T012 Document Open Food Facts usage prerequisites and the intentional null-price behavior.

## Phase 3: User Story 1 - Compare Products by a Chosen Priority (Priority: P1)

**Goal**: Return a category comparison with all supported metrics, independent ranks, and deterministic multi-criteria ordering.

**Independent Test**: Seed products with known values and verify default criteria, a selected primary criterion, metric-specific ranks, shared ties, and deterministic overall ordering.

- [x] T013 [P] [US1] Define supported metric metadata, units, default directions, and default priority in `backend/app/services/ranking.py`.
- [x] T014 [US1] Implement independent dense metric ranks over reliable values, alphabetical tie ordering, and missing-primary fallback through subsequent default criteria in `backend/app/services/ranking.py`.
- [x] T015 [US1] Implement precise EUR per-100-g price derivation from package price and size without rounding before comparison in `backend/app/services/pricing.py`.
- [x] T016 [P] [US1] Add ranking unit tests for each default direction, default/custom preference, independent dense ranks, alphabetical ties, fallback ordering for missing primary values, unreliable values, and unrounded comparisons in `backend/tests/unit/`.
- [x] T017 [US1] Add category listing and paginated product retrieval endpoints matching `contracts/openapi.yaml` in `backend/app/api/routes/`.
- [x] T018 [US1] Add the category-filtered comparison endpoint and response schemas, returning criterion order and per-metric values, units, ranks, and quality status in `backend/app/api/routes/` and `backend/app/schemas/`.
- [x] T019 [US1] Add API/database integration tests for category isolation, default and custom ordering, rank ties, empty categories, and response contract in `backend/tests/integration/`.

## Phase 4: User Story 3 - Understand Product Price and Package Size (Priority: P1)

**Goal**: Clearly compare upfront package costs and size-normalized price.

**Independent Test**: Compare known products with different package weights and verify displayed package price, size, and unrounded unit-price ordering.

- [x] T020 [P] [US3] Add pricing tests for valid, zero, missing, and invalid package sizes/prices, euro-only validation, and per-100-g normalization in `backend/tests/unit/`.
- [x] T021 [US3] Include package price, size, currency, source, observation timestamp, and derived price-per-100-g details in product and comparison API responses.
- [x] T022 [US3] Add API tests proving least-price ranks use price per 100 g, not package price, and invalid price inputs have no price rank.

## Phase 5: User Story 4 - Identify Missing or Uncertain Information (Priority: P1)

**Goal**: Keep incomplete or unreliable facts transparent and prevent misleading ranks.

**Independent Test**: Compare reliable, unreliable, unverified, missing, and invalid facts; verify unavailable values have null ranks and clear explanations per metric.

- [x] T023 [P] [US4] Implement per-fact reliability-state and missing-reason projection for nutrition and price; only reliable facts may receive ranks in `backend/app/services/`.
- [x] T024 [US4] Add tests distinguishing measured zero from missing, invalid, unverified, or unreliable data and ensuring unavailable values are not ranked in `backend/tests/unit/`.
- [x] T025 [US4] Add integration tests for products with partial metric data, all products missing a metric, unknown provenance, and absent source timestamps.
- [x] T026 [US4] Ensure comparison responses include unranked counts and per-metric reasons without dropping products or fabricating values.

## Phase 6: User Story 5 - Browse Grocery Categories (Priority: P2)

**Goal**: Let shoppers choose configured grocery categories, including categories with no products.

**Independent Test**: Verify the category list includes all configured categories and an empty category returns an explicit empty comparison.

- [x] T027 Implement category endpoint behavior and assertions for the four user-supplied category slugs, including empty categories. Dynamic category discovery remains blocked on approved S-kaupat access.
- [x] T028 [P] [US5] Add category API tests for configured categories, product counts, unknown category identifiers, and empty categories.

## Phase 7: User Story 2 - Change Priorities While Browsing (Priority: P1)

**Goal**: Persist anonymous session preferences and update category/ranking in the comparison view.

**Independent Test**: Change category and ranking in a browser session; verify selected control state, ordered results, and preference restoration after a page reload in that same browser session.

- [x] T029 [US2] Implement opaque random session token creation, hashed-token lookup, expiry, and HTTP-only SameSite cookie handling in `backend/app/`.
- [x] T030 [US2] Implement preference GET/PUT routes and persist category, default/custom mode, and custom primary metric/direction for the anonymous session in `backend/app/api/routes/`.
- [x] T031 [US2] Validate category, metric, and direction selections; return explicit validation/not-found errors without silently applying defaults in `backend/app/`.
- [x] T032 [P] [US2] Add API tests for session creation, preference restoration/update, cookie flags, invalid selections, and session expiry in `backend/tests/integration/`.
- [x] T033 [US2] Implement typed frontend API client and comparison/preference data types from the OpenAPI contract in `frontend/src/api/` and `frontend/src/types/`.
- [x] T034 [US2] Build the category dropdown from active S-kaupat categories, including configured empty categories, in `frontend/src/features/comparison/`.
- [x] T035 [US2] Build separate "Use default preferences" and "Choose priority" controls, visually highlight the active mode and metric/direction, and provide accessible labels in `frontend/src/features/comparison/`.
- [x] T036 [US2] Build responsive comparison rows/cards showing package data, every metric value/rank/direction, and quality warnings in `frontend/src/features/comparison/`.
- [x] T037 [US2] Restore preference; persist default/custom preference with `PUT /preferences`, refresh with `POST /comparisons`, and handle category/ranking changes without navigation. Clear stale results and show loading/error/empty states in `frontend/src/`.
- [x] T038 [P] [US2] Add component and interaction tests for dropdown choices, selected preference styling, changed ranking, metric rank rendering, and loading/error/empty states in `frontend/tests/`.

## Phase 8: End-to-End Verification and Handoff

**Purpose**: Verify complete shopper workflows, accessibility, setup reproducibility, and compatibility.

- [x] T039 Add an end-to-end browser test covering category selection, default reset, custom priority, ranking refresh, visible per-metric ranks, and anonymous-session restoration. The browser test uses controlled API fixtures; live external data sync is not part of the browser test.
- [x] T040 Verify database migrations, user-supplied catalog seeding, and the Open Food Facts offline export import using `quickstart.md`. The 2026-11-01 export matched 13 products and imported 65 fact records; prices remain null by scope.
- [x] T041 Review keyboard operation, accessible names/states, narrow-screen layout, and clear handling of API/data-quality errors.
- [x] T042 Validate the implementation: 42 backend tests, 4 frontend tests, production build, and 1 end-to-end browser workflow pass. The browser test passed three consecutive reruns after one intermittent failure. Verified 65 offline-import fact records in PostgreSQL; prices remain null.
- [x] T043 Update `quickstart.md` with final commands, environment variables, API URL, Open Food Facts sync workflow, and intentional null-price behavior.
- [x] T044 Add Open Food Facts provenance, ODbL attribution, API usage-form gate, and nutrition-only source rules to docs and the UI.
- [x] T045 Add unit coverage for barcode validation, exact-match enforcement, per-100-g nutrient parsing and bounds, missing facts, provenance, idempotent persistence, API usage-form gating, ranking valid Open Food Facts facts, and stop-on-429 behavior.
- [x] T046 Add a streaming importer for the official Open Food Facts offline export, restricted to exact catalog barcodes and explicit validated per-100-g values; import and verify matching records from the 2026-11-01 export. Live API sync still requires its separate prerequisites.
- [x] T048 Present products as a compact one-row-per-product list showing name, brand, package size, shop (S-market), primary metric first, and ascending/descending arrows (FR-005a).
- [ ] T047 **DEFERRED: prices intentionally remain `null` for now.** Do not add price observations or price ingestion unless the user later requests price data.

## Dependencies and Execution Order

- Phase 1 precedes all implementation phases.
- Phase 2 precedes API, comparison, and UI work.
- US1 ranking and comparison services precede US3 and US4 API enrichments and the frontend comparison view.
- US3 and US4 response semantics should be established before completing US2's comparison rendering tasks.
- US5 category behavior depends on the category seed and API from Phase 2/US1.
- US2 API session work can proceed after Phase 2; its frontend tasks depend on the comparison API contract and category endpoint.
- Phase 8 depends on all required user-story work.
- Tasks marked `[P]` can run in parallel only when their stated prerequisites and shared-file ownership do not conflict.

## Notes

- `[P]` denotes work that can be performed independently within its phase.
- `[US#]` links implementation work to the user story in `spec.md`.
- Keep ranking logic in the backend as the source of truth; the frontend displays API values and ranks rather than recomputing them.
- Use S-kaupat for categories and product identity; use Open Food Facts only for exact-barcode nutrition facts. Leave prices `null` until the user requests source-backed prices. Do not infer missing data or commit database credentials.
