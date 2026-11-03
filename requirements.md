# Requirements Quality Checklist: Nutrition Comparer

**Purpose**: Review the feature specification for completeness, clarity, consistency, and testability before implementation. This checklist evaluates requirements, not implementation status.
**Created**: 2026-11-01
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [x] CHK001 - Is it clear that available category names and category membership come from S-kaupat, including configured empty categories? [Completeness, Spec §FR-001a]
- [x] CHK002 - Does the specification define all product values that must be displayed, including package size, package price, normalized price, and each supported nutrition value? [Completeness, Spec §FR-003, §FR-005–FR-007]
- [x] CHK003 - Does each supported metric have an explicit unit, comparison basis, and default direction? [Completeness, Spec §FR-006, §FR-017]
- [x] CHK004 - Are source, freshness, and reliability expectations stated for both prices and nutrition facts? [Completeness, Spec §FR-010–FR-012]
- [x] CHK005 - Are empty catalog, empty category, loading, invalid selection, and failed-update outcomes all specified? [Completeness, Spec §FR-015]
- [x] CHK006 - Are anonymous-session preference persistence and account/cross-browser exclusions clear? [Completeness, Clarifications and Assumptions]
- [x] CHK007 - Are the limits of the feature explicit, including product sourcing, checkout, health advice, and purchasing? [Completeness, Out of Scope]

## Requirement Clarity

- [x] CHK008 - Is it unambiguous that every metric receives an independent rank, rather than only the selected metric being ranked? [Clarity, Clarifications, Spec §FR-005]
- [x] CHK009 - Is the default ranking order and direction explicit for every metric, and does the default-preference control restore it? [Clarity, Spec §FR-017–FR-018]
- [x] CHK010 - Is the separate priority control's effect clear: selected criterion first, remaining criteria retaining their default relative order and directions? [Clarity, Spec §FR-018–FR-019]
- [x] CHK011 - Is dense rank numbering defined, with tied products sharing a rank and alphabetically ordered? [Clarity, Spec §FR-013, §FR-019]
- [x] CHK012 - Is "cheapest" consistently defined as least price per 100 g, while package price remains visible? [Clarity, Spec §FR-008, Assumptions]
- [x] CHK013 - Is the distinction between an unknown value and a measured zero clear for every metric? [Clarity, Spec §FR-010–FR-011]
- [x] CHK014 - Are the terms "unreliable", "unranked", and "data source/freshness" sufficiently clear for consistent interpretation? [Clarity, Spec §FR-010–FR-012]

## Requirement Consistency

- [x] CHK015 - Do the user scenarios, functional requirements, and success criteria agree on default metric directions, dense ties, and alphabetical tie ordering? [Consistency, User Story 1, Spec §FR-013, §FR-017, Success Criteria]
- [x] CHK016 - Do all relevant sections agree that selecting a new category or preference refreshes the comparison without restarting or implying stale results? [Consistency, User Story 2, Spec §FR-004, §FR-015]
- [x] CHK017 - Do the specification and stated assumptions consistently describe category choices as selectable even when empty? [Consistency, User Story 5, Spec §FR-001a, Assumptions]
- [x] CHK018 - Are the anonymous-session preference requirements consistent with the exclusion of accounts and cross-browser synchronization? [Consistency, Clarifications, Assumptions, Out of Scope]

## Acceptance Criteria and Measurability

- [x] CHK019 - Can a test verify that a selected metric/direction becomes the primary sort criterion and that remaining criteria retain the specified order? [Acceptance Criteria, Spec §SC-001, §SC-005]
- [x] CHK020 - Can a test verify EUR price-per-100-g ranking from package price and size without display rounding affecting order? [Acceptance Criteria, Spec §FR-008–FR-009, §FR-020, §SC-002]
- [x] CHK021 - Can a test verify equal metric values receive dense shared ranks and alphabetical display order? [Acceptance Criteria, Spec §FR-013, §SC-007]
- [x] CHK022 - Can a test verify missing or unreliable values have no rank for that metric and expose an explanation? [Acceptance Criteria, Spec §FR-010–FR-012, §SC-004]
- [x] CHK023 - Are the success criteria observable and objectively passable without relying on subjective descriptions such as "easy" or "intuitive"? [Measurability, Success Criteria]
- [x] CHK024 - Is the required comparison product limit or target scale stated consistently wherever performance is discussed? [Measurability, Plan Technical Context]

## Edge Cases and Dependencies

- [x] CHK025 - Does the specification explain what happens when all products lack the selected metric or when only some products can be ranked? [Edge Case, User Story 4, Spec §FR-010, §FR-015]
- [x] CHK026 - Is behavior defined for products missing different metrics, so a missing value in one metric does not create a false rank for another? [Edge Case, Spec §FR-010, §FR-019]
- [x] CHK027 - Is behavior defined for non-EUR prices, unsupported package units, and non-positive or otherwise invalid package sizes? [Edge Case, Spec §FR-008–FR-009, §FR-020, Assumptions]
- [x] CHK028 - Are category selection and preference validation requirements clear for deleted, inactive, or unknown category identifiers? [Edge Case, Spec §FR-014]
- [x] CHK029 - Are source timestamps that are missing or stale distinguished from the time a value was imported into the system? [Dependency, Spec §FR-012]
- [x] CHK030 - Is current-release price behavior defined, including null values, no price ranks, and deferred price ingestion? [Scope, Spec §FR-010–FR-012, Assumptions]
- [x] CHK031 - Are unreliable, unverified, missing, and invalid values consistently excluded from ranks while remaining visible with explanations? [Consistency, Spec §FR-010–FR-012]
- [x] CHK032 - Is fallback ordering for products missing the primary value clear, without changing the rank for unavailable metrics? [Edge Case, Spec §FR-019, §SC-007]

**Review outcome**: All 32 requirements-quality checks pass. Prices are intentionally `null` and unranked for now; price ingestion is deferred and is not required for this release.
