from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import re
from typing import Any

import httpx

from app.models import NutritionFact, Product

API_BASE = "https://world.openfoodfacts.org/api/v2/product"
SOURCE_NAME = "Open Food Facts"
PRODUCT_FIELDS = "code,nutriments,last_modified_t"
METRIC_FIELDS = {
    "calories": ("energy-kcal_100g", "kcal", Decimal("900")),
    "carbohydrates": ("carbohydrates_100g", "g", Decimal("100")),
    "protein": ("proteins_100g", "g", Decimal("100")),
    "fat": ("fat_100g", "g", Decimal("100")),
    "fibre": ("fiber_100g", "g", Decimal("100")),
}
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
BARCODE_PATTERN = re.compile(r"^\d{8,14}$")


class OpenFoodFactsRateLimitError(RuntimeError):
    pass


class OpenFoodFactsDataError(RuntimeError):
    pass


@dataclass(frozen=True)
class ImportedFact:
    metric: str
    value: Decimal | None
    unit: str
    quality_status: str
    quality_note: str | None


@dataclass(frozen=True)
class BarcodeLookup:
    barcode: str
    found: bool
    observed_at: datetime | None
    facts: tuple[ImportedFact, ...]
    message: str | None = None


def validate_contact_email(email: str | None) -> str:
    if email is None or not EMAIL_PATTERN.fullmatch(email):
        raise ValueError(
            "Set OPENFOODFACTS_CONTACT_EMAIL to a real contact email before syncing."
        )
    return email


def _source_timestamp(value: Any) -> datetime | None:
    if isinstance(value, str):
        try:
            value = int(value)
        except ValueError:
            return None
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return None
    try:
        return datetime.fromtimestamp(value, timezone.utc)
    except (OverflowError, OSError, ValueError):
        return None


def _parse_fact(
    metric: str, field: str, unit: str, maximum: Decimal, nutriments: dict[str, Any]
) -> ImportedFact:
    raw_value = nutriments.get(field)
    if raw_value is None or raw_value == "":
        return ImportedFact(
            metric, None, unit, "missing", "Not supplied by Open Food Facts."
        )
    if isinstance(raw_value, bool):
        return ImportedFact(
            metric, None, unit, "invalid", "Open Food Facts returned a non-numeric value."
        )
    try:
        value = Decimal(str(raw_value))
    except (InvalidOperation, ValueError):
        return ImportedFact(
            metric, None, unit, "invalid", "Open Food Facts returned a non-numeric value."
        )
    if not value.is_finite() or value < 0 or value > maximum:
        return ImportedFact(
            metric,
            None,
            unit,
            "invalid",
            "The value is outside the valid per-100-g range.",
        )
    return ImportedFact(metric, value, unit, "reliable", None)


def lookup_barcode(
    client: httpx.Client, barcode: str
) -> BarcodeLookup:
    if not BARCODE_PATTERN.fullmatch(barcode):
        raise ValueError("A product lookup requires an 8- to 14-digit barcode.")
    response = client.get(
        f"{API_BASE}/{barcode}.json",
        params={"fields": PRODUCT_FIELDS},
    )
    if response.status_code == 429:
        raise OpenFoodFactsRateLimitError(
            "Open Food Facts rate limit reached. Stop syncing and try later."
        )
    response.raise_for_status()
    try:
        payload = response.json()
    except ValueError as exc:
        raise OpenFoodFactsDataError(
            "Open Food Facts returned a response that was not valid JSON."
        ) from exc
    if not isinstance(payload, dict) or payload.get("status") != 1:
        return BarcodeLookup(
            barcode,
            False,
            None,
            (),
            "Open Food Facts has no product record for this barcode.",
        )
    product = payload.get("product")
    if not isinstance(product, dict) or str(product.get("code", "")) != barcode:
        return BarcodeLookup(
            barcode,
            False,
            None,
            (),
            "The returned Open Food Facts barcode did not exactly match.",
        )
    nutriments = product.get("nutriments")
    if not isinstance(nutriments, dict):
        nutriments = {}
    facts = tuple(
        _parse_fact(metric, field, unit, maximum, nutriments)
        for metric, (field, unit, maximum) in METRIC_FIELDS.items()
    )
    return BarcodeLookup(
        barcode,
        True,
        _source_timestamp(product.get("last_modified_t")),
        facts,
    )


def parse_export_row(row: dict[str, Any], barcode: str) -> BarcodeLookup:
    if str(row.get("code", "")) != barcode:
        return BarcodeLookup(
            barcode,
            False,
            None,
            (),
            "The exported Open Food Facts barcode did not exactly match.",
        )
    return BarcodeLookup(
        barcode,
        True,
        _source_timestamp(row.get("last_modified_t")),
        tuple(
            _parse_fact(metric, field, unit, maximum, row)
            for metric, (field, unit, maximum) in METRIC_FIELDS.items()
        ),
    )


def persist_lookup(product: Product, lookup: BarcodeLookup) -> int:
    if not lookup.found or product.barcode != lookup.barcode:
        return 0
    source_url = f"https://world.openfoodfacts.org/product/{lookup.barcode}"
    for imported in lookup.facts:
        existing = next(
            (
                fact
                for fact in product.nutrition_facts
                if fact.metric == imported.metric
                and fact.source_name == SOURCE_NAME
            ),
            None,
        )
        if existing is None:
            existing = NutritionFact(
                product_id=product.id,
                metric=imported.metric,
                basis_g=Decimal("100"),
                source_name=SOURCE_NAME,
            )
            product.nutrition_facts.append(existing)
        existing.value = imported.value
        existing.unit = imported.unit
        existing.basis_g = Decimal("100")
        existing.source_url = source_url
        existing.observed_at = lookup.observed_at
        existing.quality_status = imported.quality_status
        existing.quality_note = imported.quality_note
    return len(lookup.facts)
