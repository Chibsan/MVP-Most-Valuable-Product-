from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib

from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.main import app
from app.models import (
    AnonymousSession,
    Category,
    NutritionFact,
    PriceObservation,
    Product,
    UserPreference,
)


def add_product(
    db: Session,
    *,
    name: str,
    protein: str | None,
    calories: str,
    package_price: str,
    package_size: str = "100",
    protein_status: str = "reliable",
) -> Product:
    category = db.query(Category).filter_by(slug="cheese").one()
    product = Product(
        category_id=category.id,
        name=name,
        package_size_g=Decimal(package_size),
        package_size_label=f"{package_size} g",
        source_url="https://www.s-kaupat.fi/",
    )
    db.add(product)
    db.flush()
    db.add(
        PriceObservation(
            product_id=product.id,
            package_price=Decimal(package_price),
            currency="EUR",
            source_name="S-kaupat",
            source_url="https://www.s-kaupat.fi/",
            observed_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            quality_status="reliable",
        )
    )
    for metric, value, unit, status in (
        ("calories", calories, "kcal", "reliable"),
        ("protein", protein, "g", protein_status),
    ):
        db.add(
            NutritionFact(
                product_id=product.id,
                metric=metric,
                value=Decimal(value) if value is not None else None,
                unit=unit,
                basis_g=Decimal("100"),
                source_name="S-kaupat",
                quality_status=status,
            )
        )
    return product


def test_category_endpoint_includes_configured_empty_categories(
    client: TestClient,
) -> None:
    response = client.get("/api/v1/categories")
    assert response.status_code == 200
    assert [
        (item["slug"], item["name"], item["product_count"])
        for item in response.json()["items"]
    ] == [
        ("cheese", "Cheese", 0),
        ("empty", "Empty category", 0),
        ("milk", "Milk", 0),
        ("minced-meat", "Minced meat", 0),
        ("snack-bars-biscuits", "Snack bars and biscuits", 0),
        ("softdrinks", "Softdrinks", 0),
    ]
    assert response.json()["items"][2]["source_url"] == (
        "https://www.s-kaupat.fi/tuotteet/maito-munat-ja-rasvat/maidot-ja-piimat"
    )


def test_category_counts_include_only_products_in_that_category(
    client: TestClient, db_session: Session
) -> None:
    add_product(db_session, name="Cheese", protein="5", calories="100", package_price="1")
    db_session.commit()
    counts = {item["slug"]: item["product_count"] for item in client.get("/api/v1/categories").json()["items"]}
    assert counts == {
        "cheese": 1,
        "empty": 0,
        "milk": 0,
        "minced-meat": 0,
        "snack-bars-biscuits": 0,
        "softdrinks": 0,
    }


def test_custom_comparison_returns_metric_specific_dense_ranks(
    client: TestClient, db_session: Session
) -> None:
    add_product(db_session, name="Beta", protein="5", calories="100", package_price="2")
    add_product(db_session, name="Alpha", protein="5", calories="120", package_price="1")
    add_product(db_session, name="Gamma", protein="3", calories="80", package_price="3")
    db_session.commit()

    response = client.post(
        "/api/v1/comparisons",
        json={
            "category": "cheese",
            "preference_mode": "custom",
            "primary_metric": "protein",
            "primary_direction": "most",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert [item["name"] for item in body["items"]] == ["Alpha", "Beta", "Gamma"]
    assert [item["metrics"]["protein"]["rank"] for item in body["items"]] == [1, 1, 2]
    assert [item["metrics"]["calories"]["rank"] for item in body["items"]] == [3, 2, 1]
    assert body["criteria"][0] == {
        "metric": "protein",
        "direction": "most",
        "unit": "g/100g",
    }


def test_default_comparison_uses_canonical_priority_and_directions(
    client: TestClient, db_session: Session
) -> None:
    add_product(db_session, name="Higher protein", protein="20", calories="150", package_price="2")
    add_product(db_session, name="Lower calories", protein="10", calories="100", package_price="2")
    db_session.commit()
    response = client.post(
        "/api/v1/comparisons",
        json={"category": "cheese", "preference_mode": "default"},
    )
    body = response.json()
    assert [item["name"] for item in body["items"]] == [
        "Lower calories",
        "Higher protein",
    ]
    assert [(item["metric"], item["direction"]) for item in body["criteria"]] == [
        ("calories", "least"),
        ("carbohydrates", "least"),
        ("protein", "most"),
        ("fat", "least"),
        ("fibre", "most"),
        ("price", "least"),
    ]


def test_unreliable_primary_values_are_unranked_and_follow_reliable_values(
    client: TestClient, db_session: Session
) -> None:
    add_product(
        db_session,
        name="Unreliable",
        protein="20",
        calories="110",
        package_price="1",
        protein_status="unreliable",
    )
    add_product(db_session, name="Reliable", protein="2", calories="130", package_price="2")
    db_session.commit()
    response = client.post(
        "/api/v1/comparisons",
        json={
            "category": "cheese",
            "preference_mode": "custom",
            "primary_metric": "protein",
            "primary_direction": "most",
        },
    )
    items = response.json()["items"]
    assert [item["name"] for item in items] == ["Reliable", "Unreliable"]
    assert items[1]["metrics"]["protein"]["rank"] is None
    assert items[1]["metrics"]["protein"]["quality_status"] == "unreliable"
    assert response.json()["unranked_count"] == 1


def test_empty_category_comparison_and_unknown_category(client: TestClient) -> None:
    empty = client.post(
        "/api/v1/comparisons",
        json={"category": "empty", "preference_mode": "default"},
    )
    assert empty.status_code == 200
    assert empty.json()["items"] == []
    assert empty.json()["unranked_count"] == 0

    missing = client.post(
        "/api/v1/comparisons",
        json={"category": "unknown", "preference_mode": "default"},
    )
    assert missing.status_code == 404
    assert missing.json()["code"] == "not_found"


def test_missing_price_is_null_and_unranked(
    client: TestClient, db_session: Session
) -> None:
    category = db_session.query(Category).filter_by(slug="cheese").one()
    db_session.add(
        Product(
            category_id=category.id,
            name="No source-backed price",
            package_size_g=Decimal("100"),
            package_size_label="100 g",
            prices=[],
            nutrition_facts=[],
        )
    )
    db_session.commit()

    response = client.post(
        "/api/v1/comparisons",
        json={
            "category": "cheese",
            "preference_mode": "custom",
            "primary_metric": "price",
            "primary_direction": "least",
        },
    )

    assert response.status_code == 200
    product = response.json()["items"][0]
    assert product["package_price"] is None
    assert product["currency"] is None
    assert product["price_per_100g"] is None
    assert product["metrics"]["price"]["value"] is None
    assert product["metrics"]["price"]["rank"] is None
    assert product["metrics"]["price"]["quality_status"] == "missing"


def test_price_comparison_uses_unit_price_and_product_endpoint_is_paginated(
    client: TestClient, db_session: Session
) -> None:
    add_product(
        db_session,
        name="Larger pack",
        protein="5",
        calories="100",
        package_price="2.00",
        package_size="200",
    )
    add_product(
        db_session,
        name="Smaller pack",
        protein="5",
        calories="100",
        package_price="1.50",
        package_size="100",
    )
    db_session.commit()

    comparison = client.post(
        "/api/v1/comparisons",
        json={
            "category": "cheese",
            "preference_mode": "custom",
            "primary_metric": "price",
            "primary_direction": "least",
        },
    ).json()
    assert [item["name"] for item in comparison["items"]] == [
        "Larger pack",
        "Smaller pack",
    ]
    assert [item["metrics"]["price"]["rank"] for item in comparison["items"]] == [1, 2]
    assert comparison["items"][0]["package_price"] == 2.0
    assert comparison["items"][0]["package_size_g"] == 200.0
    assert comparison["items"][0]["package_size_label"] == "200 g"
    assert comparison["items"][0]["price_per_100g"] == 1.0

    page = client.get("/api/v1/products?category=cheese&limit=1&offset=0")
    assert page.status_code == 200
    assert len(page.json()["items"]) == 1
    assert page.json()["limit"] == 1
    assert page.json()["offset"] == 0
    assert page.json()["items"][0]["currency"] == "EUR"
    assert page.json()["items"][0]["price_source"] == "S-kaupat"


def test_product_listing_is_category_filtered(client: TestClient, db_session: Session) -> None:
    add_product(db_session, name="Cheese", protein="5", calories="100", package_price="1")
    db_session.commit()
    assert len(client.get("/api/v1/products?category=cheese").json()["items"]) == 1
    assert len(client.get("/api/v1/products?category=empty").json()["items"]) == 0
    assert client.get("/api/v1/products?category=unknown").status_code == 404


def test_database_constraints_reject_invalid_package_weight_and_currency(
    db_session: Session,
) -> None:
    category = db_session.query(Category).filter_by(slug="cheese").one()
    db_session.add(
        Product(category_id=category.id, name="Invalid size", package_size_g=Decimal("0"))
    )
    try:
        db_session.flush()
        raise AssertionError("A zero package weight must violate the database constraint.")
    except IntegrityError:
        db_session.rollback()

    product = Product(category_id=category.id, name="Currency test")
    db_session.add(product)
    db_session.flush()
    db_session.add(
        PriceObservation(
            product_id=product.id,
            package_price=Decimal("1"),
            currency="USD",
            source_name="S-kaupat",
            quality_status="invalid",
        )
    )
    try:
        db_session.flush()
        raise AssertionError("A non-EUR price must violate the database constraint.")
    except IntegrityError:
        db_session.rollback()


def test_measured_zero_is_ranked_but_unverified_and_missing_facts_are_not(
    client: TestClient, db_session: Session
) -> None:
    add_product(
        db_session,
        name="Measured zero",
        protein="0",
        calories="100",
        package_price="1",
    )
    add_product(
        db_session,
        name="Missing",
        protein=None,
        calories="100",
        package_price="1",
        protein_status="missing",
    )
    unknown_source = add_product(
        db_session,
        name="Unknown source",
        protein="9",
        calories="100",
        package_price="1",
    )
    db_session.flush()
    protein_fact = next(
        fact for fact in unknown_source.nutrition_facts if fact.metric == "protein"
    )
    protein_fact.source_name = "unknown"
    db_session.commit()

    response = client.post(
        "/api/v1/comparisons",
        json={
            "category": "cheese",
            "preference_mode": "custom",
            "primary_metric": "protein",
            "primary_direction": "most",
        },
    ).json()
    by_name = {item["name"]: item for item in response["items"]}
    assert by_name["Measured zero"]["metrics"]["protein"]["value"] == 0
    assert by_name["Measured zero"]["metrics"]["protein"]["rank"] == 1
    assert by_name["Missing"]["metrics"]["protein"]["rank"] is None
    assert by_name["Missing"]["metrics"]["protein"]["quality_status"] == "missing"
    assert by_name["Missing"]["metrics"]["protein"]["reason"]
    assert by_name["Unknown source"]["metrics"]["protein"]["rank"] is None
    assert by_name["Unknown source"]["metrics"]["protein"]["quality_status"] == "unverified"
    assert by_name["Unknown source"]["metrics"]["protein"]["reason"]
    assert by_name["Unknown source"]["metrics"]["protein"]["observed_at"] is None
    assert response["unranked_count"] == 2


def test_all_products_missing_primary_metric_keep_positions_but_no_metric_ranks(
    client: TestClient, db_session: Session
) -> None:
    add_product(
        db_session,
        name="Second",
        protein=None,
        calories="100",
        package_price="1",
        protein_status="missing",
    )
    add_product(
        db_session,
        name="First",
        protein=None,
        calories="100",
        package_price="1",
        protein_status="missing",
    )
    db_session.commit()
    response = client.post(
        "/api/v1/comparisons",
        json={
            "category": "cheese",
            "preference_mode": "custom",
            "primary_metric": "protein",
            "primary_direction": "most",
        },
    ).json()
    assert [item["name"] for item in response["items"]] == ["First", "Second"]
    assert [item["display_position"] for item in response["items"]] == [1, 2]
    assert all(item["metrics"]["protein"]["rank"] is None for item in response["items"])
    assert response["unranked_count"] == 2


def test_invalid_preference_is_not_silently_defaulted(client: TestClient) -> None:
    response = client.post(
        "/api/v1/comparisons",
        json={
            "category": "cheese",
            "preference_mode": "custom",
            "primary_metric": "not-a-metric",
            "primary_direction": "least",
        },
    )
    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"
    assert response.json()["details"]


def test_preference_route_rejects_unknown_category_and_missing_custom_fields(
    client: TestClient,
) -> None:
    unknown = client.put(
        "/api/v1/preferences",
        json={"category": "unknown", "preference_mode": "default"},
    )
    assert unknown.status_code == 404
    incomplete = client.put(
        "/api/v1/preferences",
        json={"category": "cheese", "preference_mode": "custom"},
    )
    assert incomplete.status_code == 422
    assert incomplete.json()["code"] == "validation_error"


def test_preference_cookie_is_opaque_http_only_and_persisted(
    client: TestClient, db_session: Session
) -> None:
    initial = client.get("/api/v1/preferences")
    assert initial.status_code == 200
    cookie = initial.cookies.get("nutrition_session")
    assert cookie
    assert len(cookie) > 30
    assert "httponly" in initial.headers["set-cookie"].lower()
    assert "samesite=lax" in initial.headers["set-cookie"].lower()
    assert cookie not in str(initial.json())
    session = db_session.query(AnonymousSession).one()
    assert session.token_hash == hashlib.sha256(cookie.encode()).hexdigest()
    assert session.token_hash != cookie

    updated = client.put(
        "/api/v1/preferences",
        json={"category": "cheese", "preference_mode": "custom", "primary_metric": "protein", "primary_direction": "most"},
    )
    assert updated.status_code == 200
    assert updated.json()["preference_mode"] == "custom"
    assert updated.json()["primary_metric"] == "protein"
    restored = client.get("/api/v1/preferences")
    assert restored.json()["primary_metric"] == "protein"
    assert "set-cookie" in restored.headers


def test_expired_session_is_replaced_and_preference_deleted(
    client: TestClient, db_session: Session
) -> None:
    initial = client.get("/api/v1/preferences")
    old_cookie = initial.cookies.get("nutrition_session")
    session = db_session.query(AnonymousSession).one()
    old_session_id = session.id
    session.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db_session.commit()

    renewed = client.get("/api/v1/preferences")
    new_cookie = renewed.cookies.get("nutrition_session")
    assert new_cookie and new_cookie != old_cookie
    assert db_session.get(AnonymousSession, old_session_id) is None
    assert db_session.get(UserPreference, old_session_id) is None


def test_readiness_returns_service_unavailable_when_database_fails(
    client: TestClient,
) -> None:
    class UnavailableDatabase:
        def execute(self, _statement):
            raise OperationalError("SELECT 1", {}, RuntimeError("offline"))

    app.dependency_overrides[get_db] = lambda: UnavailableDatabase()
    try:
        response = client.get("/health/ready")
    finally:
        app.dependency_overrides.pop(get_db, None)
    assert response.status_code == 503
    assert response.json()["message"] == "Database is unavailable."


def test_readiness_checks_database(client: TestClient) -> None:
    assert client.get("/health/live").json() == {"status": "ok"}
    assert client.get("/health/ready").json() == {"status": "ok"}
