# Nutrition Comparer Constitution

## Core Principles

### 1. Nutrition-First, Budget-Conscious Decisions
The application MUST help users compare grocery products by nutritional value and price. Product details and comparisons MUST make both dimensions easy to understand; neither MUST be hidden behind an opaque overall score.

### 2. Accurate, Comparable Product Data
Every comparison MUST use consistent units and clearly identified product sizes. Where the source data permits, the application MUST present price per product and normalized price per 100 g, alongside nutrition per 100 g for protein, calories, carbohydrates, fat, and fibre. Unit conversions and calculations MUST be deterministic and testable. The source or basis of displayed values MUST be transparent.

### 3. User-Directed, Transparent Ranking
Users MUST be able to rank products by price or by each supported nutritional metric, choosing whether they want the most or least of that value. The selected metric and direction MUST remain visible in the results. Rankings MUST use the same normalized values shown to users and MUST NOT silently combine unrelated metrics or impose an undisclosed health or value score.

### 4. Honest Treatment of Missing or Unreliable Data
Missing, invalid, or unreliable product information MUST be clearly indicated. The application MUST NOT invent values or present incomplete data as verified. A product lacking a valid value for the selected ranking metric MUST NOT receive a misleading ranked position; the interface MUST explain its unranked status.

### 5. Validated Inputs and Reliable Calculations
All user-provided data MUST be validated at the application boundary for required fields, valid numeric ranges, units, and usable product sizes. Invalid input MUST produce a clear, actionable explanation. Calculation and ranking logic MUST handle invalid or absent values explicitly rather than silently substituting defaults.

### 6. Clear, Responsive User Experience
The interface MUST be clean, intuitive, and responsive across supported screen sizes. Comparison tables or equivalent views MUST make product identity, size, price, nutrition values, selected sort order, and data-quality warnings easy to scan. Accessibility and understandable labels MUST be considered part of correctness.

### 7. Maintainable, Documented, Tested Software
Code MUST be modular and maintainable, with clear separation between data handling, validation, calculations, ranking, and presentation where applicable. Public behavior and non-obvious calculations MUST be documented. Tests MUST cover validation, unit normalization, price and nutrition calculations, ranking directions, and missing or unreliable data. Changes MUST preserve established behavior unless an intentional change is documented.

## Development and Change Requirements
- Features and changes MUST comply with these principles. Any exception MUST be explicit, justified, and approved as part of the change.
- A change affecting comparisons MUST include tests for the relevant calculation, ranking, or data-quality behavior.
- User-visible changes MUST communicate metric definitions, units, ranking direction, and relevant limitations.
- Dependencies and implementation complexity MUST be kept proportionate to the product need.

## Governance
This constitution is the source of truth for product and engineering decisions in Nutrition Comparer. Amendments MUST be made deliberately, with a clear rationale and updates to affected specifications, implementation, and tests. Where a specification or implementation conflicts with this constitution, the conflict MUST be resolved before the work is considered complete.
