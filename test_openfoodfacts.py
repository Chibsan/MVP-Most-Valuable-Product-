import csv
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4
from types import SimpleNamespace

import httpx
import pytest
from sqlalchemy.orm import sessionmaker

from app.models import Category, NutritionFact, Product
from app.services.ranking import build_comparison
from app.services.openfoodfacts import (
    OpenFoodFactsRateLimitError,
    lookup_barcode,
    parse_export_row,
    persist_lookup,
    validate_contact_email,
)


BARCODE = "6415712506032"


def api_client(payload: dict, status_code: int = 200) -> httpx.Client:
    def handle(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, json=payload)

    return httpx.Client(transport=httpx.MockTransport(handle))


def test_exact_barcode_lookup_accepts_explicit_per_100g_values_and_missing_facts() -> None:
    with api_client(
        {
            "status": 1,
            "product": {
                "code": BARCODE,
                "last_modified_t": 1785262712,
                "nutriments": {
                    "energy-kcal_100g": 33,
                    "carbohydrates_100g": 4.9,
                    "proteins_100g": 3.4,
                    "fat_100g": 0,
                    "fiber_100g": 0,
                },
            },
        }
    ) as client:
        result = lookup_barcode(client, BARCODE)

    assert result.found
    assert result.observed_at == datetime.fromtimestamp(1785262712, timezone.utc)
    assert {fact.metric: fact.value for fact in result.facts} == {
        "calories": Decimal("33"),
        "carbohydrates": Decimal("4.9"),
        "protein": Decimal("3.4"),
        "fat": Decimal("0"),
        "fibre": Decimal("0"),
    }
    assert all(fact.quality_status == "reliable" for fact in result.facts)


def test_lookup_does_not_accept_values_without_explicit_100g_fields() -> None:
    with api_client(
        {
            "status": 1,
            "product": {
                "code": BARCODE,
                "nutriments": {"proteins": 20, "energy-kcal_value": 50},
            },
        }
    ) as client:
        result = lookup_barcode(client, BARCODE)

    assert all(fact.value is None for fact in result.facts)
    assert all(fact.quality_status == "missing" for fact in result.facts)


def test_lookup_rejects_mismatched_barcode_and_handles_unknown_products() -> None:
    with api_client(
        {
            "status": 1,
            "product": {"code": "0000000000000", "nutriments": {}},
        }
    ) as client:
        mismatch = lookup_barcode(client, BARCODE)
    assert not mismatch.found
    assert "did not exactly match" in mismatch.message

    with api_client({"status": 0, "status_verbose": "product not found"}) as client:
        missing = lookup_barcode(client, BARCODE)
    assert not missing.found
    assert "no product record" in missing.message


def test_lookup_marks_out_of_range_nonfinite_and_non_numeric_values_invalid() -> None:
    with api_client(
        {
            "status": 1,
            "product": {
                "code": BARCODE,
                "nutriments": {
                    "energy-kcal_100g": "NaN",
                    "carbohydrates_100g": 101,
                    "proteins_100g": "not-a-number",
                },
            },
        }
    ) as client:
        result = lookup_barcode(client, BARCODE)

    facts = {fact.metric: fact for fact in result.facts}
    for metric in ("calories", "carbohydrates", "protein"):
        assert facts[metric].value is None
        assert facts[metric].quality_status == "invalid"
        assert facts[metric].quality_note


def test_rate_limit_is_explicit_and_never_retried() -> None:
    calls = 0

    def handle(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(429)

    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        with pytest.raises(OpenFoodFactsRateLimitError):
            lookup_barcode(client, BARCODE)
    assert calls == 1


def test_invalid_barcode_is_rejected_before_network_request() -> None:
    calls = 0

    def handle(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json={})

    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        with pytest.raises(ValueError, match="8- to 14-digit"):
            lookup_barcode(client, "barcode/path")
    assert calls == 0


def test_contact_email_is_required_and_validated() -> None:
    assert validate_contact_email("nutrition@example.org") == "nutrition@example.org"
    with pytest.raises(ValueError, match="OPENFOODFACTS_CONTACT_EMAIL"):
        validate_contact_email(None)
    with pytest.raises(ValueError, match="OPENFOODFACTS_CONTACT_EMAIL"):
        validate_contact_email("not-an-email")


def test_persisted_facts_keep_exact_barcode_and_openfoodfacts_provenance() -> None:
    product = Product(
        id=uuid4(),
        barcode=BARCODE,
        nutrition_facts=[],
    )
    with api_client(
        {
            "status": 1,
            "product": {
                "code": BARCODE,
                "last_modified_t": 1785262712,
                "nutriments": {
                    "energy-kcal_100g": 33,
                    "proteins_100g": 3.4,
                },
            },
        }
    ) as client:
        result = lookup_barcode(client, BARCODE)

    assert persist_lookup(product, result) == 5
    facts_by_metric = {fact.metric: fact for fact in product.nutrition_facts}
    assert facts_by_metric["protein"].value == Decimal("3.4")
    assert facts_by_metric["protein"].basis_g == Decimal("100")
    assert facts_by_metric["protein"].source_name == "Open Food Facts"
    assert facts_by_metric["protein"].source_url == (
        f"https://world.openfoodfacts.org/product/{BARCODE}"
    )
    assert facts_by_metric["protein"].observed_at == result.observed_at
    assert facts_by_metric["fibre"].quality_status == "missing"

    assert persist_lookup(product, result) == 5
    assert len(product.nutrition_facts) == 5


def test_persist_lookup_refuses_a_mismatched_product_barcode() -> None:
    product = Product(id=uuid4(), barcode="6415712506032", nutrition_facts=[])
    result = lookup_result_for("6414893385672")
    assert persist_lookup(product, result) == 0
    assert product.nutrition_facts == []


def test_offline_export_row_requires_exact_barcode_and_per_100g_values() -> None:
    row = {
        "code": BARCODE,
        "last_modified_t": "1785262712",
        "energy-kcal_100g": "33",
        "carbohydrates_100g": "4.9",
        "proteins_100g": "3.4",
        "fat_100g": "0",
        "fiber_100g": "",
    }

    lookup = parse_export_row(row, BARCODE)
    mismatch = parse_export_row(row, "6414893385672")

    assert lookup.found
    assert lookup.observed_at == datetime.fromtimestamp(1785262712, timezone.utc)
    assert {fact.metric: fact.value for fact in lookup.facts}["protein"] == Decimal("3.4")
    assert next(fact for fact in lookup.facts if fact.metric == "fibre").quality_status == "missing"
    assert not mismatch.found


def test_offline_export_import_updates_only_exact_seeded_barcode(
    tmp_path, monkeypatch, db_session
) -> None:
    from app import catalog

    category = db_session.query(Category).filter_by(slug="milk").one()
    product = Product(
        category_id=category.id,
        name="Seeded milk",
        barcode=BARCODE,
        nutrition_facts=[],
        prices=[],
    )
    db_session.add(product)
    db_session.commit()
    session_factory = sessionmaker(
        bind=db_session.get_bind(), expire_on_commit=False
    )
    monkeypatch.setattr(catalog, "SessionLocal", session_factory)

    export_path = tmp_path / "products.tsv"
    fieldnames = [
        "code",
        "last_modified_t",
        "energy-kcal_100g",
        "carbohydrates_100g",
        "proteins_100g",
        "fat_100g",
        "fiber_100g",
    ]
    with export_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerow(
            {
                "code": BARCODE,
                "last_modified_t": "100",
                "energy-kcal_100g": "50",
                "proteins_100g": "4",
            }
        )
        writer.writerow(
            {
                "code": BARCODE,
                "last_modified_t": "200",
                "energy-kcal_100g": "60",
                "proteins_100g": "5",
            }
        )
        writer.writerow(
            {
                "code": "6414893385672",
                "last_modified_t": "300",
                "energy-kcal_100g": "1",
            }
        )

    assert catalog.import_openfoodfacts_export(export_path) == 0
    db_session.expire_all()
    imported = (
        db_session.query(NutritionFact)
        .filter_by(product_id=product.id, source_name="Open Food Facts")
        .all()
    )
    facts_by_metric = {fact.metric: fact for fact in imported}
    assert len(imported) == 5
    assert facts_by_metric["calories"].value == Decimal("60")
    assert facts_by_metric["protein"].value == Decimal("5")
    assert facts_by_metric["calories"].observed_at == datetime.fromtimestamp(
        200, timezone.utc
    ).replace(tzinfo=None)
    assert all(
        fact.source_url == f"https://world.openfoodfacts.org/product/{BARCODE}"
        for fact in imported
    )


def test_openfoodfacts_facts_participate_in_ranking_with_provenance() -> None:
    products = []
    category = Category(id=uuid4(), slug="milk", name="Milk", is_active=True)
    for name, value in (("Alpha", "12"), ("Beta", "20")):
        product = Product(
            id=uuid4(),
            category_id=category.id,
            category=category,
            name=name,
            nutrition_facts=[],
            prices=[],
        )
        product.nutrition_facts.append(
            NutritionFact(
                id=uuid4(),
                product_id=product.id,
                metric="protein",
                value=Decimal(value),
                unit="g",
                basis_g=Decimal("100"),
                source_name="Open Food Facts",
                source_url=f"https://world.openfoodfacts.org/product/{BARCODE}",
                quality_status="reliable",
            )
        )
        products.append(product)

    comparison = build_comparison(products, "milk", "custom", "protein", "most")

    assert [item.name for item in comparison.items] == ["Beta", "Alpha"]
    assert [item.metrics.protein.rank for item in comparison.items] == [1, 2]
    assert all(
        item.metrics.protein.source_url
        == f"https://world.openfoodfacts.org/product/{BARCODE}"
        for item in comparison.items
    )


def test_sync_refuses_to_run_before_usage_form_completion(monkeypatch, capsys) -> None:
    from app import catalog

    monkeypatch.setattr(
        catalog,
        "get_settings",
        lambda: SimpleNamespace(openfoodfacts_usage_form_completed=False),
    )

    assert catalog.sync_openfoodfacts() == 2
    assert "Complete the Open Food Facts API usage form first" in capsys.readouterr().err


def lookup_result_for(barcode: str):
    with api_client(
        {"status": 1, "product": {"code": barcode, "nutriments": {}}}
    ) as client:
        return lookup_barcode(client, barcode)
