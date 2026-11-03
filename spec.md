# Feature Specification: Nutrition Comparer

**Feature Branch**: `001-nutrition-comparer`
**Created**: 2026-11-01
**Status**: In progress; Open Food Facts offline-export enrichment is implemented. Prices are intentionally null and unranked for now.
**Input**: User description: "Develop Nutrition comparer, a grocery planning platform where users can check which cheese for example is the one that has the most protein or cheapest. Each user should be able to change their preference while looking at the category of food."

## Clarifications

- Every supported metric is compared and receives its own rank. The user's selected metric/direction is the primary ranking criterion; the other criteria retain their default relative order and directions.
- Default metric directions and priority are: calories — least; carbohydrates — least; protein — most; fat — least; fibre — most; price per 100 g — least. The priority order is calories, carbohydrates, protein, fat, fibre, then price.
- A default-preference control restores the default metric order/directions. A separate priority control lets the shopper select the metric and direction to prioritize.
- Metric ranks use dense ranking: equal values share a rank and the next distinct value gets the next consecutive rank (for example, 1, 1, 2). Products tied on a value are displayed alphabetically by product name.
- Products with no reliable value for the selected metric appear after the last product with a reliable selected-metric value, with a one-based overall display position. They are ordered using subsequent default criteria; each metric remains independently ranked, and a product with no reliable value for a metric has no rank for that metric.
- Values marked unreliable, unverified, missing, or invalid are unavailable for ranking. Only reliable values are rankable.
- S-kaupat (https://www.s-kaupat.fi/) is the source for categories, product identity, and euro prices. Open Food Facts (https://world.openfoodfacts.org/) is permitted only for nutritional facts looked up by the exact product barcode. The Open Food Facts API's published use requirements, attribution, and rate limits must be followed.
- Preferences are stored for an anonymous browser session using a server-issued session identifier; accounts and cross-browser synchronization are not part of this feature.

## User Scenarios & Testing

### User Story 1 - Compare products by a chosen priority (Priority: P1)

As a grocery shopper, I want to choose a food category and rank its products by a nutritional value or price, so I can quickly find the option that best matches my current need.

**Why this priority**: Ranking products within a category by a shopper-selected value is the core purpose of Nutrition Comparer.

**Independent Test**: Load source-backed products with known values. Verify independent dense ranks for every metric, alphabetical ordering for equal values, the default criteria order, and the selected metric/direction as the primary criterion.

**Acceptance Scenarios**:

1. **Given** a category contains products with reliable values, **When** the comparison is displayed with default preferences, **Then** each supported metric has its own dense rank and the criteria are least calories, least carbohydrates, most protein, least fat, most fibre, then least price per 100 g.
2. **Given** a shopper chooses "most protein", **When** the comparison updates, **Then** protein becomes the primary ranking criterion in descending order, other criteria retain their default order and directions, and all metric values and ranks remain visible.
3. **Given** a shopper chooses "least price", **When** the comparison updates, **Then** price per 100 g becomes the primary ranking criterion in ascending order, other criteria retain their default order and directions, and package prices remain visible.
4. **Given** two or more products have the same reliable value for a metric, **When** that metric is ranked, **Then** they share a dense rank and are displayed alphabetically by product name within the tie.
5. **Given** a product has no reliable value for the primary criterion, **When** the comparison is ordered, **Then** it receives an overall display position after the last product with a reliable primary value and is ordered using subsequent default criteria; it has no rank for the unavailable metric.

### User Story 2 - Change priorities while browsing (Priority: P1)

As a grocery shopper, I want to change the category, metric, or whether I want the most or least of it without leaving the comparison, so I can adapt the results to my needs as I shop.

**Why this priority**: The user explicitly needs to adjust their preference while looking at a food category.

**Independent Test**: Use the default-preference control, choose a primary nutrition metric/direction with the separate priority control, then change category; verify highlighted preference and updated comparison without restarting.

**Acceptance Scenarios**:

1. **Given** a category comparison is displayed, **When** the shopper uses the priority control to select a metric and direction, **Then** that criterion becomes primary, the remaining criteria retain their default order and directions, and the results update.
2. **Given** a shopper has customized a priority, **When** they press the default-preference control, **Then** the canonical default order and directions are restored and visibly highlighted.
3. **Given** a category comparison is displayed, **When** the shopper selects another category, **Then** only products from the newly selected category are compared.
4. **Given** the shopper opens the selection controls and cancels, **When** the controls close, **Then** the currently applied category and ranking remain unchanged.
5. **Given** a new category or ranking is selected, **When** its results cannot be loaded or calculated, **Then** the interface explains that the comparison could not be updated and does not present stale results as if they match the new selection.

### User Story 3 - Understand product price and package size (Priority: P1)

As a grocery shopper, I want to see both the price of a package and its size alongside a normalized unit price, so I can distinguish the cheapest package from the best unit-price value.

**Why this priority**: Package sizes vary, and comparing only package prices can mislead shoppers about relative value.

**Independent Test**: Compare different package sizes with known package prices and verify the displayed unit price and "least price" order use the same per-100-g calculation.

**Acceptance Scenarios**:

1. **Given** a product has a valid package price and size, **When** its comparison is displayed, **Then** the package price, package size, and price per 100 g are shown with clear units.
2. **Given** products have different package sizes, **When** the shopper chooses "least price", **Then** ranking is based on price per 100 g, not package price, and package price remains visible.
3. **Given** a product does not have a valid package size or price, **When** the comparison is displayed, **Then** the unavailable unit-price value is clearly indicated and the product is not assigned a misleading position in a price ranking.

### User Story 4 - Identify missing or uncertain information (Priority: P1)

As a grocery shopper, I want missing or uncertain product information to be clearly marked, so I can judge how much confidence to place in a comparison.

**Why this priority**: Rankings are useful only when shoppers can distinguish known values from incomplete or unreliable data.

**Independent Test**: Load source-backed records with reliable, unreliable, missing, and invalid values and verify only reliable values receive ranks.

**Acceptance Scenarios**:

1. **Given** a product has no reliable value for the selected ranking metric, **When** results are shown, **Then** it appears after products with a reliable selected value, has no rank for that metric, and displays the reason when known.
2. **Given** a nutritional value or price is missing, invalid, or unreliable, **When** product details are shown, **Then** it is not ranked for that metric and the interface clearly indicates the data limitation without inventing a value.
3. **Given** source or freshness information is available for a product, **When** product details are shown, **Then** that information is visible; **And given** it is unavailable, **Then** the interface does not imply the data is verified or current.
4. **Given** products lack reliable values for one or more metrics, **When** results are shown, **Then** they remain in the comparison with an overall display position after products ranked on the active criterion, are ordered using subsequent default criteria, and have no rank for each unavailable metric.

### User Story 5 - Browse an available category (Priority: P2)

As a grocery shopper, I want to see which product categories are available and whether a category has comparable products, so I can choose what to compare.

**Why this priority**: Category discovery makes comparison useful beyond a single example such as cheese.

**Independent Test**: Load a catalog with multiple categories, an empty catalog, and a category with no products; verify category choices and empty states are accurate.

**Acceptance Scenarios**:

1. **Given** the application receives its category data from S-kaupat, **When** the shopper opens category selection, **Then** categories supplied by that source can be selected, including configured categories with no products yet.
2. **Given** a selected category has no products, **When** it is displayed, **Then** the interface explains that there are no products to compare instead of showing an empty or misleading ranking.
3. **Given** the catalog has no usable products, **When** the shopper opens the comparer, **Then** the interface explains that product data is unavailable and does not imply that products were compared.

## Requirements

### Functional Requirements

- **FR-001**: The system MUST present products grouped by food category and compare only products belonging to the selected category.
- **FR-001a**: The system MUST obtain product categories and category membership from S-kaupat. The selector MUST include active configured categories supplied by the source, even when a category currently has no products; selecting an empty category MUST show the specified empty state.
- **FR-002**: The system MUST let the shopper choose a supported ranking metric and choose whether to see the most or least of that metric. The chosen metric/direction MUST become the primary ranking criterion.
- **FR-003**: The system MUST support ranking by price and by available nutrition metrics, including protein, calories, carbohydrates, fat, and fibre.
- **FR-004**: The system MUST allow the shopper to change the category, metric, and ranking direction while viewing results. Applying a change MUST refresh the comparison without requiring an application restart.
- **FR-005**: The system MUST display all supported metric values and a separate rank for each metric. Each metric's current direction (most or least) MUST be visible with its value and rank. The active category and primary metric MUST also be visible with the results.
- **FR-005a**: Products MUST be shown as a compact list with one row per product, stacked directly under each other. Each row MUST show the product name, brand, package size, the shop name ("S-market", the only supported shop) and all six metric values with ranks. The shopper's primary metric MUST appear first in each row. Directions are shown with arrows: least as "↑ ascending" and most as "↓ descending". Barcodes, observation times, source notes and data-quality notes are not shown per row; unavailable values are labelled "Unavailable" and "Not ranked". Source attribution remains in the page footer.
- **FR-006**: The system MUST use nutrition values per 100 g for product comparison and MUST label units consistently.
- **FR-007**: The system MUST show package price and package size when available, as well as price per 100 g when it can be calculated from valid package data.
- **FR-008**: "Least price" MUST rank by the lowest price per 100 g so differently sized packages can be compared consistently. The package price MUST NOT be substituted silently for the unit-price ranking.
- **FR-009**: The system MUST calculate normalized price deterministically from package price and package size. Displayed precision MUST NOT change the underlying ranking order.
- **FR-010**: For each metric, products with a missing, invalid, unverified, or unreliable value MUST NOT be assigned a rank for that metric. The system MUST identify them as unranked for that metric and indicate why when known; unavailable data for one metric MUST NOT be represented as a measured value or rank for another.
- **FR-011**: The system MUST make missing, invalid, or unreliable product fields distinguishable from measured zero values and MUST NOT silently invent or substitute product data.
- **FR-012**: The system MUST use S-kaupat as the source for category, product identity, and price data. It MUST retain and display source provenance and observation time when supplied and MUST NOT imply that unknown provenance or freshness has been verified.
- **FR-012a**: The system MAY retrieve nutrition facts from Open Food Facts by exact barcode using its official API or offline data export. A fact is rankable only when its source field explicitly identifies a per-100-g value, its numeric value is finite and within supported bounds, and the source record barcode exactly matches the product barcode. The system MUST store and display Open Food Facts provenance, use its source-record update time only as an update time (not a label observation time), and attribute its database license. Live API requests MUST comply with the published usage form, custom User-Agent, and rate limits; offline export imports MUST use local data without making product API requests. Missing or invalid facts MUST remain unranked.
- **FR-013**: Each metric MUST be ranked independently using its own current direction. Ranks MUST be dense: equal values share a rank, and the next distinct value receives the next consecutive rank. Products tied on a value MUST be displayed in alphabetical product-name order, with a stable identifier as a final tie-break for identical names.
- **FR-014**: The system MUST validate user selections against available categories, supported metrics, and allowed directions. Invalid selections MUST produce a clear error and MUST NOT silently fall back to another ranking.
- **FR-015**: The system MUST provide clear empty, loading, and error states for unavailable catalog data, empty categories, and failed comparison updates.
- **FR-016**: The comparison view MUST remain usable on supported desktop and mobile screen sizes. Controls, product details, ranking labels, and data-quality messages MUST have understandable text labels and accessible interaction states.
- **FR-017**: The default metric directions and priority MUST be: calories — least; carbohydrates — least; protein — most; fat — least; fibre — most; price per 100 g — least. Their priority order MUST be calories, carbohydrates, protein, fat, fibre, then price.
- **FR-018**: Provide a "Use default preferences" control that restores the default criterion order/directions and a separate control to select the metric and direction to prioritize. Highlight the applied preference.
- **FR-019**: When the shopper chooses a metric/direction, that criterion MUST become primary and all other criteria MUST retain their relative default order and directions. Products with a reliable primary value MUST precede products without one. Products lacking a reliable primary value MUST receive an overall display position after the last product with a reliable primary value, then be ordered using subsequent default criteria; they MUST have no rank for the unavailable metric. Products with equal values MUST share that metric's dense rank and be alphabetized by product name.
- **FR-020**: All prices MUST be represented and compared in euros (EUR/€). Values in another currency MUST be rejected or marked invalid and MUST NOT be ranked.

### Key Entities

- **Product**: A grocery item with a name, category, package size, package price, nutritional values, and any available source or freshness details.
- **Category**: A grouping used to limit a comparison to like products, such as cheese.
- **Nutrition value**: A metric and numeric value on a per-100-g basis, with its unit and whether the value is available and reliable.
- **Ranking preference**: The selected category and primary metric/direction, together with the ordered ranking criteria and each criterion's direction.
- **Metric rank**: A product's rank for one metric only. Equal values share a rank, regardless of the product's overall position under multiple criteria.
- **Comparison result**: Products with overall display positions, all metric values and independent ranks, and explanations for products that could not be ranked. Missing primary-metric values get positions after the last reliably ranked product and use subsequent default criteria for ordering.

## Success Criteria

- **SC-001**: A shopper can choose a category and a metric/direction and see a correctly ordered comparison without restarting the application; the selected metric/direction is the primary criterion.
- **SC-002**: For every product with valid price and size, the comparison shows package price, package size, and price per 100 g; "least price" results agree with the unrounded per-100-g values.
- **SC-003**: Every supported metric is displayed with its own rank and visible direction. Default directions are calories — least; carbohydrates — least; protein — most; fat — least; fibre — most; price per 100 g — least. Displayed values, directions, and units match the actual ranks.
- **SC-004**: No product missing a reliable value for a metric is shown with a rank for that metric; all such cases have a visible explanation.
- **SC-005**: Users can restore default preferences or choose a prioritized metric/direction while remaining in the comparison flow; visible controls and results correspond to the applied preference.
- **SC-006**: Empty catalogs, empty categories, invalid selections, and failed updates each produce an explicit state rather than a blank or stale comparison.
- **SC-007**: Products with equal values share a dense rank for that metric and are alphabetically ordered within the tie; products missing the active metric receive a display position after the last reliably ranked product and are ordered using subsequent default criteria.
- **SC-008**: All ranked prices are in euros. Category/product/price provenance identifies S-kaupat and nutrition provenance identifies Open Food Facts where available.

## Assumptions

- Category and product identity come from S-kaupat or user-supplied S-kaupat URLs. Nutrition facts may come only from an exact-barcode Open Food Facts API lookup or official offline export. Prices are intentionally null and unranked in the current release. The system records source details when provided and does not fabricate values.
- "Cheapest" means lowest price per 100 g to account for different package sizes. Package price and size are also shown so shoppers can consider the upfront cost.
- A ranking preference is stored for the current anonymous browser session. User accounts and cross-browser preference synchronization are not required by this specification.
- Products are comparable by weight in grams. Products sold only by volume or by count require an explicit conversion or are marked unavailable for per-100-g price comparison; the system does not guess a conversion.
- S-kaupat product records may omit price, provenance, or freshness information, and Open Food Facts records may omit nutrition values. The system must communicate those limitations rather than fabricate data.
- Default directions are calories — least; carbohydrates — least; protein — most; fat — least; fibre — most; price per 100 g — least, in that priority order. A shopper-selected metric/direction becomes the primary criterion; remaining criteria keep their relative default order and directions.

## Out of Scope

- Personalized health advice, dietary recommendations, or a combined opaque "best product" score.
- Shopping carts, grocery lists, checkout, store inventory guarantees, or purchase transactions.
- User registration, account management, and cross-session preference synchronization.
- Product category, identity, and price data from sources other than S-kaupat.
- Nutritional facts from sources other than Open Food Facts.
- Product prices in currencies other than euros.
