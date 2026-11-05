import re
from dataclasses import dataclass
from typing import Any
import httpx

API_BASE_URL = "https://world.openfoodfacts.org/api/v2/product"
DEFAULT_USER_AGENT = "MVP4U - GroceryComparisonPlatform/1.0 (https://github.com/example/mvp4u)"
BARCODE_PATTERN = re.compile(r"^\d{8,14}$")

METRIC_CONFIG = {
    "calories": {"field": "energy-kcal_100g", "unit": "kcal", "max": 900.0},
    "protein": {"field": "proteins_100g", "unit": "g", "max": 100.0},
    "carbohydrates": {"field": "carbohydrates_100g", "unit": "g", "max": 100.0},
    "fat": {"field": "fat_100g", "unit": "g", "max": 100.0},
    "fibre": {"field": "fiber_100g", "unit": "g", "max": 100.0},
}


class OpenFoodFactsRateLimitError(RuntimeError):
    pass


class OpenFoodFactsNotFoundError(RuntimeError):
    pass


@dataclass(frozen=True)
class ParsedNutrient:
    metric: str
    value: float | None
    unit: str
    quality_status: str
    quality_note: str | None = None


@dataclass(frozen=True)
class OpenFoodFactsProduct:
    barcode: str
    name: str | None
    brand: str | None
    image_url: str | None
    package_size_g: float | None
    nutrients: list[ParsedNutrient]
    detected_category: str = "general"
    categories_tags: tuple[str, ...] = ()


def infer_category(
    pnns_groups_1: str | None = None,
    pnns_groups_2: str | None = None,
    food_groups_tags: list[str] | tuple[str, ...] | None = None,
    categories_tags: list[str] | tuple[str, ...] | None = None,
    product_name: str | None = None,
) -> str:
    """Infer high-level category using Open Food Facts official PNNS / food groups taxonomy.

    Standardized taxonomies provided natively by Open Food Facts:
    - pnns_groups_2: Specific food group (e.g., 'Cheese', 'Meat', 'Bread', 'Milk and yogurt')
    - pnns_groups_1: Broad food group (e.g., 'Milk and dairy products', 'Fish Meat Eggs', 'Beverages')
    - food_groups_tags: Machine-readable tags (e.g., 'en:cheese', 'en:meat', 'en:beverages')
    """
    p2 = (pnns_groups_2 or "").lower()
    p1 = (pnns_groups_1 or "").lower()
    fg_tags = set(food_groups_tags or [])
    cat_tags = set(categories_tags or [])
    all_tags = fg_tags | cat_tags

    # 1. Cheese (specific subset of dairy)
    if "cheese" in p2 or "en:cheese" in all_tags or "en:cheeses" in all_tags:
        return "cheese"

    # 2. Meat, Poultry, Fish & Seafood
    if (
        any(k in p2 for k in ("meat", "poultry", "fish", "seafood"))
        or "en:meat" in all_tags
        or "en:meats" in all_tags
        or "en:poultries" in all_tags
        or "en:chickens" in all_tags
        or "en:fishes" in all_tags
    ):
        return "meat"

    # 3. Dairy & Milk
    if (
        any(k in p2 for k in ("milk", "yogurt", "dairy"))
        or "en:milk-and-dairy-products" in all_tags
        or "en:dairies" in all_tags
        or "en:milks" in all_tags
    ):
        return "dairy"

    # 4. Bakery & Bread
    if (
        any(k in p2 for k in ("bread", "pastr", "biscuit", "cake", "cereal"))
        or "en:cereals-and-potatoes" in all_tags
        or "en:breads" in all_tags
        or "en:bakeries" in all_tags
    ):
        return "bakery"

    # 5. Beverages & Drinks
    if (
        "beverage" in p1
        or "drink" in p1
        or "beverage" in p2
        or "en:beverages" in all_tags
        or "en:drinks" in all_tags
    ):
        return "drinks"

    # 6. Snacks & Sweets
    if (
        "snack" in p1
        or any(k in p2 for k in ("sweet", "chocolate", "appetizer"))
        or "en:sugary-snacks" in all_tags
        or "en:salty-snacks" in all_tags
        or "en:snacks" in all_tags
    ):
        return "snacks"

    # 7. Fallback for unclassified/custom products via name keywords
    if product_name:
        p_name = product_name.lower()
        if any(w in p_name for w in ("juusto", "cheese", "mozzarella")):
            return "cheese"
        if any(w in p_name for w in ("kana", "liha", "possu", "nauta", "kala", "lohi", "meat", "chicken", "beef", "pork")):
            return "meat"
        if any(w in p_name for w in ("maito", "jogurtti", "rahka", "piimä", "milk", "dairy")):
            return "dairy"
        if any(w in p_name for w in ("leipä", "pulla", "kakku", "keksi", "bread", "pastry")):
            return "bakery"
        if any(w in p_name for w in ("mehu", "vesi", "limsa", "juice", "soda", "drink")):
            return "drinks"
        if any(w in p_name for w in ("sipsi", "suklaa", "karkki", "snack", "chips", "candy")):
            return "snacks"

    return "general"


def _parse_numeric(val: Any) -> float | None:
    if val is None or val == "":
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _extract_nutrients(nutriments: dict[str, Any]) -> list[ParsedNutrient]:
    facts: list[ParsedNutrient] = []
    for metric, config in METRIC_CONFIG.items():
        raw = nutriments.get(config["field"])
        parsed = _parse_numeric(raw)

        if parsed is None:
            facts.append(
                ParsedNutrient(
                    metric=metric,
                    value=None,
                    unit=config["unit"],
                    quality_status="missing",
                    quality_note="Not provided by Open Food Facts.",
                )
            )
        elif parsed < 0 or parsed > config["max"]:
            facts.append(
                ParsedNutrient(
                    metric=metric,
                    value=None,
                    unit=config["unit"],
                    quality_status="invalid",
                    quality_note="Value outside valid per-100g range.",
                )
            )
        else:
            facts.append(
                ParsedNutrient(
                    metric=metric,
                    value=round(parsed, 2),
                    unit=config["unit"],
                    quality_status="reliable",
                )
            )
    return facts


def lookup_barcode(
    barcode: str,
    client: httpx.Client | None = None,
    user_agent: str = DEFAULT_USER_AGENT,
) -> OpenFoodFactsProduct:
    """Synchronous barcode lookup against Open Food Facts API."""
    barcode = barcode.strip()
    if not BARCODE_PATTERN.fullmatch(barcode):
        raise ValueError("Invalid barcode format. Expected 8-14 numeric digits.")

    headers = {"User-Agent": user_agent}
    params = {
        "fields": "code,product_name,product_name_en,brands,nutriments,image_front_url,quantity,categories,categories_tags,pnns_groups_1,pnns_groups_2,food_groups_tags"
    }

    own_client = False
    if client is None:
        client = httpx.Client(timeout=10.0)
        own_client = True

    try:
        response = client.get(
            f"{API_BASE_URL}/{barcode}.json",
            headers=headers,
            params=params,
        )

        if response.status_code == 429:
            raise OpenFoodFactsRateLimitError(
                "Open Food Facts rate limit reached. Please wait before retrying."
            )
        if response.status_code == 404:
            raise OpenFoodFactsNotFoundError(
                f"Product with barcode {barcode} was not found on Open Food Facts."
            )

        response.raise_for_status()
        data = response.json()

        if data.get("status") != 1 or "product" not in data:
            raise OpenFoodFactsNotFoundError(
                f"No product record exists for barcode {barcode}."
            )

        product_raw = data["product"]
        name = product_raw.get("product_name") or product_raw.get("product_name_en")
        brand = product_raw.get("brands")
        image_url = product_raw.get("image_front_url")
        nutriments = product_raw.get("nutriments") or {}
        pnns_groups_1 = product_raw.get("pnns_groups_1")
        pnns_groups_2 = product_raw.get("pnns_groups_2")
        food_groups_tags = tuple(product_raw.get("food_groups_tags") or [])
        categories_tags = tuple(product_raw.get("categories_tags") or [])

        nutrients = _extract_nutrients(nutriments)
        detected_category = infer_category(
            pnns_groups_1=pnns_groups_1,
            pnns_groups_2=pnns_groups_2,
            food_groups_tags=food_groups_tags,
            categories_tags=categories_tags,
            product_name=name,
        )

        return OpenFoodFactsProduct(
            barcode=barcode,
            name=name.strip() if name else None,
            brand=brand.strip() if brand else None,
            image_url=image_url,
            package_size_g=None,
            nutrients=nutrients,
            detected_category=detected_category,
            categories_tags=categories_tags,
        )
    finally:
        if own_client:
            client.close()
