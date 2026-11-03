from sqlalchemy import create_engine, text

from alembic import command
from alembic.config import Config

from app.core.config import get_settings


def test_fresh_migrations_seed_only_user_supplied_catalog_links(
    tmp_path, monkeypatch
) -> None:
    database_path = tmp_path / "catalog.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")
    get_settings.cache_clear()
    try:
        command.upgrade(Config("alembic.ini"), "head")
        engine = create_engine(f"sqlite:///{database_path}")
        with engine.connect() as connection:
            categories = connection.execute(
                text("SELECT slug, source_url FROM categories")
            ).all()
            products = connection.execute(
                text(
                    """
                    SELECT p.name, p.brand, p.barcode, p.package_size_g,
                           p.package_size_label, p.source_url,
                           p.source_observed_at,
                           c.slug AS category,
                           (SELECT count(*) FROM price_observations po
                            WHERE po.product_id = p.id) AS price_count,
                           (SELECT count(*) FROM nutrition_facts nf
                            WHERE nf.product_id = p.id) AS fact_count
                    FROM products p
                    JOIN categories c ON c.id = p.category_id
                    """
                )
            ).mappings().all()
        engine.dispose()
    finally:
        get_settings.cache_clear()

    assert len(categories) == 4
    assert len(products) == 16
    assert {product["category"] for product in products} == {
        "milk",
        "minced-meat",
        "softdrinks",
        "snack-bars-biscuits",
    }
    assert all(product["barcode"] for product in products)
    assert all(product["source_url"].startswith("https://www.s-kaupat.fi/tuote/") for product in products)
    assert all("?" not in product["source_url"] for product in products)
    assert all(product["source_observed_at"] is None for product in products)
    assert all(product["price_count"] == 0 for product in products)
    assert all(product["fact_count"] == 0 for product in products)

    milk = [product for product in products if product["category"] == "milk"]
    assert len(milk) == 4
    assert {product["brand"] for product in milk} == {"Kotimaista", "Valio"}
    assert all(product["package_size_g"] is None for product in milk)
    assert all(product["package_size_label"] == "1 l" for product in milk)
    meat = [product for product in products if product["category"] == "minced-meat"]
    assert {product["package_size_g"] for product in meat} == {400, 700}
    snacks = [
        product
        for product in products
        if product["category"] == "snack-bars-biscuits"
    ]
    assert sum(product["package_size_g"] == 300 for product in snacks) == 2
    assert {product["package_size_label"] for product in snacks} == {
        "10 × 30 g",
        "50 g",
    }
