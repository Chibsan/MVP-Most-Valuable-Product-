from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from app.models import NutritionFact, PriceObservation, Product
from app.schemas.comparison import (
    ComparisonOut,
    Criterion,
    MetricResult,
    ProductComparison,
    ProductMetricResults,
)
from app.services.pricing import price_per_100g

NUTRITION_METRICS = ("calories", "carbohydrates", "protein", "fat", "fibre")
METRIC_UNITS = {
    "calories": "kcal/100g",
    "carbohydrates": "g/100g",
    "protein": "g/100g",
    "fat": "g/100g",
    "fibre": "g/100g",
    "price": "EUR/100g",
}
DEFAULT_CRITERIA = (
    ("calories", "least"),
    ("carbohydrates", "least"),
    ("protein", "most"),
    ("fat", "least"),
    ("fibre", "most"),
    ("price", "least"),
)


@dataclass(frozen=True)
class MetricDatum:
    value: Decimal | None
    unit: str
    quality_status: str
    reason: str | None = None
    source_url: str | None = None
    observed_at: datetime | None = None


@dataclass(frozen=True)
class ProductData:
    product: Product
    metrics: dict[str, MetricDatum]
    package_price: Decimal | None
    package_currency: str | None
    price_source: str | None
    price_observed_at: datetime | None


def criteria_for(primary_metric: str, primary_direction: str) -> list[Criterion]:
    ordered = [(primary_metric, primary_direction)] + [
        item for item in DEFAULT_CRITERIA if item[0] != primary_metric
    ]
    return [
        Criterion(metric=metric, direction=direction, unit=METRIC_UNITS[metric])
        for metric, direction in ordered
    ]


def _time_key(value: datetime | None) -> datetime:
    if value is None:
        return datetime.min.replace(tzinfo=timezone.utc)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _latest(records: list[Any]) -> Any | None:
    if not records:
        return None
    return max(
        records,
        key=lambda item: (
            _time_key(item.observed_at),
            _time_key(item.created_at),
            str(item.id),
        ),
    )


def _unavailable_status(
    status: str,
    source_name: str,
    value: Decimal | None,
    allowed_sources: frozenset[str] = frozenset({"S-kaupat"}),
) -> tuple[str, str | None]:
    if status != "reliable":
        reasons = {
            "unreliable": "The source marked this value unreliable.",
            "unverified": "This value has not been verified.",
            "missing": "No value supplied.",
            "invalid": "The supplied value failed validation.",
        }
        return status, reasons.get(status, "The value is unavailable.")
    if source_name not in allowed_sources:
        return "unverified", "The value is from an unrecognized source."
    if value is None:
        return "invalid", "The source marked this value reliable but supplied no value."
    return "reliable", None


def _nutrition_data(product: Product, metric: str) -> MetricDatum:
    fact: NutritionFact | None = _latest(
        [fact for fact in product.nutrition_facts if fact.metric == metric]
    )
    unit = METRIC_UNITS[metric]
    if fact is None:
        return MetricDatum(None, unit, "missing", "No value supplied.")
    status, reason = _unavailable_status(
        fact.quality_status,
        fact.source_name,
        fact.value,
        frozenset({"S-kaupat", "Open Food Facts"}),
    )
    if status != "reliable":
        return MetricDatum(None, unit, status, fact.quality_note or reason, fact.source_url, fact.observed_at)
    expected_unit = "kcal" if metric == "calories" else "g"
    if fact.unit != expected_unit or fact.basis_g <= 0:
        return MetricDatum(None, unit, "invalid", fact.quality_note or "Unsupported unit or basis.", fact.source_url, fact.observed_at)
    normalized = fact.value * Decimal(100) / fact.basis_g
    return MetricDatum(normalized, unit, "reliable", fact.quality_note, fact.source_url, fact.observed_at)


def _price_data(product: Product) -> tuple[MetricDatum, Decimal | None, str | None, datetime | None, str | None]:
    observation: PriceObservation | None = _latest(product.prices)
    if observation is None:
        return MetricDatum(None, METRIC_UNITS["price"], "missing", "No price supplied."), None, None, None, None
    status, reason = _unavailable_status(
        observation.quality_status, observation.source_name, observation.package_price
    )
    package_price = observation.package_price
    currency = observation.currency if observation.currency == "EUR" else None
    price = price_per_100g(package_price, product.package_size_g)
    if status == "reliable" and currency != "EUR":
        status, reason = "invalid", "Only euro prices can be compared."
    if status == "reliable" and price is None:
        status, reason = "invalid", "A nonnegative euro price and positive package weight are required."
    if status != "reliable":
        price = None
    datum = MetricDatum(
        price,
        METRIC_UNITS["price"],
        status,
        observation.quality_note or reason,
        observation.source_url,
        observation.observed_at,
    )
    return datum, package_price, currency, observation.observed_at, observation.source_name


def product_data(product: Product) -> ProductData:
    metrics = {metric: _nutrition_data(product, metric) for metric in NUTRITION_METRICS}
    price, package_price, currency, observed_at, source = _price_data(product)
    metrics["price"] = price
    return ProductData(
        product,
        metrics,
        package_price,
        currency,
        source,
        observed_at,
    )


def _rank_maps(products: list[ProductData], criteria: list[Criterion]) -> dict[UUID, dict[str, int | None]]:
    result = {item.product.id: {} for item in products}
    for criterion in criteria:
        values = sorted(
            {
                item.metrics[criterion.metric].value
                for item in products
                if item.metrics[criterion.metric].quality_status == "reliable"
                and item.metrics[criterion.metric].value is not None
            },
            reverse=criterion.direction == "most",
        )
        ranks = {value: index + 1 for index, value in enumerate(values)}
        for item in products:
            datum = item.metrics[criterion.metric]
            result[item.product.id][criterion.metric] = (
                ranks[datum.value]
                if datum.quality_status == "reliable" and datum.value is not None
                else None
            )
    return result


def _name_key(product: Product) -> tuple[str, str]:
    return product.name.casefold(), str(product.id)


def _display_order(
    products: list[ProductData], primary_metric: str, primary_direction: str
) -> list[ProductData]:
    primary_values = [
        item.metrics[primary_metric].value
        for item in products
        if item.metrics[primary_metric].quality_status == "reliable"
        and item.metrics[primary_metric].value is not None
    ]
    reliable_sorted = sorted(
        (
            item
            for item in products
            if item.metrics[primary_metric].quality_status == "reliable"
            and item.metrics[primary_metric].value is not None
        ),
        key=lambda item: (
            -item.metrics[primary_metric].value
            if primary_direction == "most"
            else item.metrics[primary_metric].value,
            *_name_key(item.product),
        ),
    )
    fallback = [
        item
        for item in products
        if item.metrics[primary_metric].quality_status != "reliable"
        or item.metrics[primary_metric].value is None
    ]
    fallback_criteria = [
        item for item in DEFAULT_CRITERIA if item[0] != primary_metric
    ]

    def fallback_key(item: ProductData) -> tuple[Any, ...]:
        values: list[Any] = []
        for metric, direction in fallback_criteria:
            datum = item.metrics[metric]
            if datum.quality_status != "reliable" or datum.value is None:
                values.extend((1, Decimal(0)))
            else:
                values.extend(
                    (
                        0,
                        -datum.value if direction == "most" else datum.value,
                    )
                )
        values.extend(_name_key(item.product))
        return tuple(values)

    fallback.sort(key=fallback_key)
    return reliable_sorted + fallback


def _metric_result(
    data: ProductData,
    metric: str,
    direction: str,
    rank: int | None,
) -> MetricResult:
    datum = data.metrics[metric]
    return MetricResult(
        value=datum.value,
        unit=datum.unit,
        direction=direction,
        rank=rank,
        quality_status=datum.quality_status,
        reason=datum.reason,
        source_url=datum.source_url,
        observed_at=datum.observed_at,
    )


def _comparison_product(
    data: ProductData,
    category: str,
    position: int,
    criteria: list[Criterion],
    ranks: dict[str, int | None],
) -> ProductComparison:
    product = data.product
    result_metrics = {
        criterion.metric: _metric_result(
            data, criterion.metric, criterion.direction, ranks[criterion.metric]
        )
        for criterion in criteria
    }
    return ProductComparison(
        id=product.id,
        name=product.name,
        category=category,
        brand=product.brand,
        barcode=product.barcode,
        display_position=position,
        package_size_g=product.package_size_g,
        package_size_label=product.package_size_label,
        package_price=data.package_price,
        currency=data.package_currency,
        price_per_100g=data.metrics["price"].value,
        price_source=data.price_source,
        price_observed_at=data.price_observed_at,
        source_url=product.source_url,
        metrics=ProductMetricResults(**result_metrics),
    )


def build_comparison(
    products: list[Product],
    category: str,
    preference_mode: str,
    primary_metric: str,
    primary_direction: str,
) -> ComparisonOut:
    criteria = criteria_for(primary_metric, primary_direction)
    rows = [product_data(product) for product in products]
    ranks = _rank_maps(rows, criteria)
    ordered = _display_order(rows, primary_metric, primary_direction)
    items = [
        _comparison_product(
            row, category, index + 1, criteria, ranks[row.product.id]
        )
        for index, row in enumerate(ordered)
    ]
    unranked_count = sum(
        1
        for row in rows
        if row.metrics[primary_metric].quality_status != "reliable"
        or row.metrics[primary_metric].value is None
    )
    return ComparisonOut(
        category=category,
        preference_mode=preference_mode,
        primary_metric=primary_metric,
        primary_direction=primary_direction,
        criteria=criteria,
        items=items,
        unranked_count=unranked_count,
    )
