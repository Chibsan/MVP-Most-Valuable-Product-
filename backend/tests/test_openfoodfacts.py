import pytest
import httpx
from services.openfoodfacts import (
    lookup_barcode,
    OpenFoodFactsNotFoundError,
    OpenFoodFactsRateLimitError,
)


def test_invalid_barcode_pattern():
    with pytest.raises(ValueError, match="Invalid barcode format"):
        lookup_barcode("abc1234")

    with pytest.raises(ValueError, match="Invalid barcode format"):
        lookup_barcode("12345")  # Less than 8 digits


def test_successful_lookup_parsing():
    mock_payload = {
        "status": 1,
        "product": {
            "code": "7340191149779",
            "product_name": "Coop Mozzarella",
            "brands": "Coop",
            "image_front_url": "https://example.com/img.jpg",
            "nutriments": {
                "energy-kcal_100g": 298.0,
                "proteins_100g": 21.0,
                "carbohydrates_100g": 1.5,
                "fat_100g": 23.0,
                "fiber_100g": 0.0,
            },
        },
    }

    def handler(request: httpx.Request):
        return httpx.Response(200, json=mock_payload)

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as mock_client:
        product = lookup_barcode("7340191149779", client=mock_client)

    assert product.name == "Coop Mozzarella"
    assert product.brand == "Coop"
    assert product.barcode == "7340191149779"
    assert product.image_url == "https://example.com/img.jpg"

    facts = {f.metric: f for f in product.nutrients}
    assert facts["protein"].value == 21.0
    assert facts["protein"].quality_status == "reliable"
    assert facts["calories"].value == 298.0
    assert facts["fat"].value == 23.0


def test_missing_and_invalid_nutrients():
    mock_payload = {
        "status": 1,
        "product": {
            "code": "12345678",
            "product_name": "Incomplete Product",
            "nutriments": {
                "proteins_100g": -5.0,  # Invalid negative
                "energy-kcal_100g": 2000.0,  # Exceeds max 900
                # carbs, fat, fiber missing
            },
        },
    }

    def handler(request: httpx.Request):
        return httpx.Response(200, json=mock_payload)

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as mock_client:
        product = lookup_barcode("12345678", client=mock_client)

    facts = {f.metric: f for f in product.nutrients}
    assert facts["protein"].quality_status == "invalid"
    assert facts["calories"].quality_status == "invalid"
    assert facts["carbohydrates"].quality_status == "missing"
    assert facts["carbohydrates"].value is None


def test_not_found_handling():
    def handler(request: httpx.Request):
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as mock_client:
        with pytest.raises(OpenFoodFactsNotFoundError):
            lookup_barcode("99999999", client=mock_client)


def test_rate_limit_handling():
    def handler(request: httpx.Request):
        return httpx.Response(429)

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as mock_client:
        with pytest.raises(OpenFoodFactsRateLimitError):
            lookup_barcode("12345678", client=mock_client)
