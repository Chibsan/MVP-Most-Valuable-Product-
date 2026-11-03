from decimal import Decimal

from app.services.pricing import price_per_100g


def test_price_per_100g_uses_full_decimal_precision() -> None:
    assert price_per_100g(Decimal("2.50"), Decimal("250")) == Decimal("1.00")
    assert price_per_100g(Decimal("1.00"), Decimal("300")) == Decimal(100) / Decimal(300)


def test_price_per_100g_rejects_missing_or_invalid_inputs() -> None:
    assert price_per_100g(None, Decimal("200")) is None
    assert price_per_100g(Decimal("1"), None) is None
    assert price_per_100g(Decimal("-1"), Decimal("200")) is None
    assert price_per_100g(Decimal("1"), Decimal("0")) is None

