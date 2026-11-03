from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from app.models import Category, NutritionFact, PriceObservation, Product
from app.services.ranking import DEFAULT_CRITERIA, build_comparison, criteria_for


def make_product(
    name: str,
    *,
    protein: str | None,
    calories: str = "100",
    protein_status: str = "reliable",
) -> Product:
    category = Category(id=uuid4(), slug="cheese", name="Cheese", is_active=True)
    product = Product(
        id=uuid4(),
        category_id=category.id,
        category=category,
        name=name,
        package_size_g=Decimal("100"),
        prices=[
            PriceObservation(
                id=uuid4(),
                package_price=Decimal("1.00"),
                currency="EUR",
                source_name="S-kaupat",
                quality_status="reliable",
                observed_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            )
        ],
        nutrition_facts=[],
    )
    for metric, value in (("calories", calories), ("protein", protein)):
        if value is not None or metric == "protein":
            product.nutrition_facts.append(
                NutritionFact(
                    id=uuid4(),
                    product_id=product.id,
                    metric=metric,
                    value=Decimal(value) if value is not None else None,
                    unit="kcal" if metric == "calories" else "g",
                    basis_g=Decimal("100"),
                    source_name="S-kaupat",
                    quality_status=(
                        ("missing" if value is None else protein_status)
                        if metric == "protein"
                        else "reliable"
                    ),
                )
            )
    return product


def test_default_criteria_are_canonical() -> None:
    assert [(item.metric, item.direction) for item in criteria_for("calories", "least")] == list(DEFAULT_CRITERIA)


def test_custom_priority_keeps_other_default_order_and_direction() -> None:
    assert [(item.metric, item.direction) for item in criteria_for("protein", "least")] == [
        ("protein", "least"),
        ("calories", "least"),
        ("carbohydrates", "least"),
        ("fat", "least"),
        ("fibre", "most"),
        ("price", "least"),
    ]


def test_dense_ranks_and_primary_tie_order_are_independent() -> None:
    products = [
        make_product("Beta", protein="5", calories="100"),
        make_product("Alpha", protein="5", calories="120"),
        make_product("Gamma", protein="3", calories="80"),
    ]
    result = build_comparison(products, "cheese", "custom", "protein", "most")
    assert [item.name for item in result.items] == ["Alpha", "Beta", "Gamma"]
    assert [item.metrics.protein.rank for item in result.items] == [1, 1, 2]
    assert [item.metrics.calories.rank for item in result.items] == [3, 2, 1]
    assert [item.display_position for item in result.items] == [1, 2, 3]


def test_missing_or_unreliable_primary_values_follow_reliable_products() -> None:
    products = [
        make_product("Missing", protein=None, calories="80"),
        make_product("Unreliable", protein="20", calories="110", protein_status="unreliable"),
        make_product("Reliable", protein="2", calories="130"),
    ]
    result = build_comparison(products, "cheese", "custom", "protein", "most")
    assert [item.name for item in result.items] == ["Reliable", "Missing", "Unreliable"]
    assert result.items[0].metrics.protein.rank == 1
    assert result.items[1].metrics.protein.rank is None
    assert result.items[2].metrics.protein.rank is None
    assert result.unranked_count == 2
    assert result.items[1].metrics.protein.quality_status == "missing"
    assert result.items[2].metrics.protein.quality_status == "unreliable"


def test_unrounded_price_decides_rank() -> None:
    first = make_product("Package A", protein="1")
    second = make_product("Package B", protein="1")
    first.prices[0].package_price = Decimal("1.0001")
    second.prices[0].package_price = Decimal("1.0002")
    result = build_comparison([second, first], "cheese", "custom", "price", "least")
    assert [item.name for item in result.items] == ["Package A", "Package B"]
    assert [item.metrics.price.rank for item in result.items] == [1, 2]


def test_non_euro_price_is_invalid_and_never_ranked() -> None:
    product = make_product("Non-euro", protein="1")
    product.prices[0].currency = "USD"
    result = build_comparison([product], "cheese", "custom", "price", "least")
    assert result.items[0].metrics.price.value is None
    assert result.items[0].metrics.price.rank is None
    assert result.items[0].metrics.price.quality_status == "invalid"


def test_invalid_nutrition_value_is_not_ranked() -> None:
    product = make_product("Invalid nutrition", protein="3")
    protein_fact = next(
        fact for fact in product.nutrition_facts if fact.metric == "protein"
    )
    protein_fact.quality_status = "invalid"
    result = build_comparison([product], "cheese", "custom", "protein", "most")
    metric = result.items[0].metrics.protein
    assert metric.value is None
    assert metric.rank is None
    assert metric.quality_status == "invalid"
    assert metric.reason


def test_each_supported_default_direction_orders_values_correctly() -> None:
    first = make_product("Alpha", protein="1", calories="90")
    second = make_product("Beta", protein="2", calories="110")
    values = {
        "carbohydrates": (Decimal("1"), Decimal("2")),
        "fat": (Decimal("1"), Decimal("2")),
        "fibre": (Decimal("1"), Decimal("2")),
    }
    for product, index in ((first, 0), (second, 1)):
        for metric, pair in values.items():
            product.nutrition_facts.append(
                NutritionFact(
                    id=uuid4(),
                    product_id=product.id,
                    metric=metric,
                    value=pair[index],
                    unit="g",
                    basis_g=Decimal("100"),
                    source_name="S-kaupat",
                    quality_status="reliable",
                )
            )
        product.prices[0].package_price = Decimal("1") if index == 0 else Decimal("2")

    for metric, direction, expected in (
        ("calories", "least", ["Alpha", "Beta"]),
        ("carbohydrates", "least", ["Alpha", "Beta"]),
        ("protein", "most", ["Beta", "Alpha"]),
        ("fat", "least", ["Alpha", "Beta"]),
        ("fibre", "most", ["Beta", "Alpha"]),
        ("price", "least", ["Alpha", "Beta"]),
    ):
        comparison = build_comparison(
            [second, first], "cheese", "custom", metric, direction
        )
        assert [item.name for item in comparison.items] == expected
