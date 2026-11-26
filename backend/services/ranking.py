from dataclasses import dataclass
from typing import Any

SUPPORTED_METRICS = ("protein", "calories", "carbohydrates", "fat", "fibre")

METRIC_UNITS = {
    "calories": "kcal/100g",
    "protein": "g/100g",
    "carbohydrates": "g/100g",
    "fat": "g/100g",
    "fibre": "g/100g",
}

DEFAULT_DIRECTIONS = {
    "calories": "least",
    "protein": "most",
    "carbohydrates": "least",
    "fat": "least",
    "fibre": "most",
}

DEFAULT_CRITERIA = (
    ("protein", "most"),
    ("calories", "least"),
    ("carbohydrates", "least"),
    ("fat", "least"),
    ("fibre", "most"),
)


@dataclass
class RankedProductItem:
    id: int
    barcode: str
    name: str | None
    brand: str | None
    category: str
    image_url: str | None
    rank: int | None
    display_position: int
    primary_metric: str
    primary_direction: str
    primary_value: float | None
    metrics: dict[str, dict[str, Any]]


def _get_metric_dict(product: Any) -> dict[str, dict[str, Any]]:
    result = {}
    facts_by_metric = {f.metric: f for f in getattr(product, "nutrition_facts", [])}
    for metric in SUPPORTED_METRICS:
        fact = facts_by_metric.get(metric)
        if fact and fact.quality_status == "reliable" and fact.value is not None:
            result[metric] = {
                "value": fact.value,
                "unit": fact.unit,
                "quality_status": "reliable",
                "quality_note": None,
                "rank": None,
            }
        elif fact:
            result[metric] = {
                "value": None,
                "unit": fact.unit,
                "quality_status": fact.quality_status,
                "quality_note": fact.quality_note,
                "rank": None,
            }
        else:
            result[metric] = {
                "value": None,
                "unit": METRIC_UNITS[metric].split("/")[0],
                "quality_status": "missing",
                "quality_note": "No value supplied.",
                "rank": None,
            }
    return result


def _compute_dense_ranks(
    items: list[tuple[Any, dict[str, dict[str, Any]]]],
    metric: str,
    direction: str,
) -> dict[int, int | None]:
    valid_items = [
        (prod.id, metrics[metric]["value"])
        for prod, metrics in items
        if metrics[metric]["quality_status"] == "reliable"
        and metrics[metric]["value"] is not None
    ]
    if not valid_items:
        return {prod.id: None for prod, _ in items}

    distinct_values = sorted(
        {val for _, val in valid_items},
        reverse=(direction == "most"),
    )
    val_to_rank = {val: idx + 1 for idx, val in enumerate(distinct_values)}

    return {
        prod.id: val_to_rank.get(metrics[metric]["value"])
        for prod, metrics in items
    }


def calculate_rankings(
    products: list[Any],
    primary_metric: str = "protein",
    primary_direction: str = "most",
) -> list[RankedProductItem]:
    if primary_metric not in SUPPORTED_METRICS:
        primary_metric = "protein"
    if primary_direction not in ("most", "least"):
        primary_direction = DEFAULT_DIRECTIONS.get(primary_metric, "most")

    items = [(prod, _get_metric_dict(prod)) for prod in products]

    # Calculate independent dense ranks for each metric
    dense_ranks_by_metric: dict[str, dict[int, int | None]] = {}
    for metric in SUPPORTED_METRICS:
        dir_to_use = primary_direction if metric == primary_metric else DEFAULT_DIRECTIONS[metric]
        dense_ranks_by_metric[metric] = _compute_dense_ranks(items, metric, dir_to_use)

    # Apply computed ranks to item metric dictionaries
    for prod, metrics in items:
        for metric in SUPPORTED_METRICS:
            metrics[metric]["rank"] = dense_ranks_by_metric[metric].get(prod.id)

    # Sort items: reliable primary metric first, followed by unranked items
    reliable_items = [
        (prod, metrics)
        for prod, metrics in items
        if metrics[primary_metric]["quality_status"] == "reliable"
        and metrics[primary_metric]["value"] is not None
    ]
    unranked_items = [
        (prod, metrics)
        for prod, metrics in items
        if metrics[primary_metric]["quality_status"] != "reliable"
        or metrics[primary_metric]["value"] is None
    ]

    def _safe_name(prod: Any) -> str:
        return (prod.name or "").casefold()

    # Sort reliable items by primary metric value, then alphabetical by name
    reliable_items.sort(
        key=lambda pair: (
            -pair[1][primary_metric]["value"]
            if primary_direction == "most"
            else pair[1][primary_metric]["value"],
            _safe_name(pair[0]),
        )
    )

    # Sort fallback/unranked items by default secondary criteria, then name
    secondary_criteria = [
        (m, d) for m, d in DEFAULT_CRITERIA if m != primary_metric
    ]

    def _fallback_sort_key(pair: tuple[Any, dict[str, dict[str, Any]]]):
        _, metrics = pair
        key = []
        for m, d in secondary_criteria:
            val = metrics[m]["value"]
            if val is None:
                key.append(1)
                key.append(0.0)
            else:
                key.append(0)
                key.append(-val if d == "most" else val)
        key.append(_safe_name(pair[0]))
        return tuple(key)

    unranked_items.sort(key=_fallback_sort_key)

    final_ordered = reliable_items + unranked_items

    ranked_results: list[RankedProductItem] = []
    for idx, (prod, metrics) in enumerate(final_ordered):
        primary_val = metrics[primary_metric]["value"]
        assigned_rank = metrics[primary_metric]["rank"]

        ranked_results.append(
            RankedProductItem(
                id=prod.id,
                barcode=prod.barcode,
                name=prod.name,
                brand=prod.brand,
                category=prod.category,
                image_url=prod.image_url,
                rank=assigned_rank,
                display_position=idx + 1,
                primary_metric=primary_metric,
                primary_direction=primary_direction,
                primary_value=primary_val,
                metrics=metrics,
            )
        )

    return ranked_results
