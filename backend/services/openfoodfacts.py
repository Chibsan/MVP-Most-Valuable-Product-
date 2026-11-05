import re
from dataclasses import dataclass
from typing import Any
import httpx

API_BASE_URL = "https://world.openfoodfacts.org/api/v2/product"
DEFAULT_USER_AGENT = "MVP4U - GroceryComparisonPlatform/1.0 (https://github.com/example/mvp4u)"
BARCODE_PATTERN = re.compile(r"^\d{8,14}$")

CATEGORY_KEYWORDS = {
    "cheese": [
        "cheese", "cheeses", "juusto", "juustot", "fromage", "fromages", "käse",
        "mozzarella", "cheddar", "gouda", "parmesan", "parmigiano", "brie",
        "camembert", "feta", "edam", "emmental", "halloumi", "ricotta",
        "leipäjuusto", "sulatejuusto", "sinihomejuusto", "valkohomejuusto",
        "juustoraaste",
    ],
    "meat": [
        "meat", "meats", "poultry", "poultries", "chicken", "chickens",
        "kana", "kanan", "broileri", "broilerin", "liha", "lihavalmiste",
        "nauta", "naudan", "sika", "sian", "possu", "possun", "pork", "beef",
        "kalkkuna", "turkey", "kala", "kalat", "fish", "fishes", "lohi", "lohen",
        "salmon", "tuna", "tonnikala", "seafood", "äyriäiset", "makkara",
        "sausage", "nakki", "kinkku", "ham", "bacon", "pekoni", "jauheliha",
        "filee", "fileesuikale", "leikkele",
    ],
    "dairy": [
        "dairy", "dairies", "milk", "milks", "yogurt", "yogurts", "yoghurt",
        "maito", "maidot", "jogurtti", "rahka", "piimä", "viili", "butter",
        "voi", "cream", "kerma", "kermaviili", "skyr", "cottage cheese",
    ],
    "bakery": [
        "bread", "breads", "bakery", "bakeries", "leipä", "leivät", "pulla",
        "pullat", "pastry", "pastries", "croissant", "bagel", "toast", "flour",
        "jauho", "jauhot", "cake", "kakku", "keksi", "keksit", "biscuit",
        "biscuits", "cookie", "cookies", "muffin", "rieska", "sämpylä",
        "näkkileipä",
    ],
    "snacks": [
        "snack", "snacks", "chips", "crisps", "sipsi", "sipsit", "perunalastu",
        "chocolate", "chocolates", "suklaa", "suklaat", "candy", "candies",
        "karkki", "karkit", "makeinen", "makeiset", "sweets", "popcorn",
        "pähkinä", "pähkinät", "nut", "nuts",
    ],
    "drinks": [
        "beverage", "beverages", "drink", "drinks", "juice", "juices", "mehu",
        "mehut", "soda", "soft-drinks", "limsa", "limonadi", "water", "waters",
        "vesi", "kahvi", "coffee", "tea", "tee", "energy-drinks", "olut",
        "beer", "siideri", "cider",
    ],
}

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
    categories_tags: list[str] | tuple[str, ...] | None = None,
    categories_text: str | None = None,
    product_name: str | None = None,
) -> str:
    """Infer high-level category using Open Food Facts tags, categories text, and name.

    Evaluates in precedence order: cheese -> meat -> dairy -> bakery -> snacks -> drinks.
    Returns 'general' if no strong match found.
    """
    tag_tokens: list[str] = []
    if categories_tags:
        for tag in categories_tags:
            cleaned = re.sub(r"^[a-z]{2}:", "", tag.lower())
            cleaned = re.sub(r"[-_]+", " ", cleaned)
            tag_tokens.append(cleaned)
    combined_tags = " ".join(tag_tokens)
    cat_text = (categories_text or "").lower()
    p_name = (product_name or "").lower()

    for cat, keywords in CATEGORY_KEYWORDS.items():
        # 1. Match against standardized taxonomy tags
        for kw in keywords:
            if re.search(rf"(^|\W){re.escape(kw)}(\W|$)", combined_tags):
                return cat

        # 2. Match against free-form categories string
        for kw in keywords:
            if re.search(rf"(^|\W){re.escape(kw)}(\W|$)", cat_text):
                return cat

        # 3. Match against product name (support compound Finnish/German words)
        for kw in keywords:
            if len(kw) >= 4 and kw in p_name:
                return cat
            elif re.search(rf"(^|\W){re.escape(kw)}(\W|$)", p_name):
                return cat

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
        "fields": "code,product_name,product_name_en,brands,nutriments,image_front_url,quantity,categories,categories_tags"
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
        categories_str = product_raw.get("categories")
        categories_tags = tuple(product_raw.get("categories_tags") or [])

        nutrients = _extract_nutrients(nutriments)
        detected_category = infer_category(
            categories_tags=list(categories_tags),
            categories_text=categories_str,
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
