from unittest.mock import patch
from services.openfoodfacts import OpenFoodFactsProduct, ParsedNutrient


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_post_product_and_ranking_flow(client):
    mock_off_product = OpenFoodFactsProduct(
        barcode="7340191149779",
        name="Coop Mozzarella Juustoraaste",
        brand="Coop",
        image_url="https://images.example/coop.jpg",
        package_size_g=150.0,
        nutrients=[
            ParsedNutrient("protein", 21.0, "g", "reliable"),
            ParsedNutrient("calories", 298.0, "kcal", "reliable"),
            ParsedNutrient("carbohydrates", 1.5, "g", "reliable"),
            ParsedNutrient("fat", 23.0, "g", "reliable"),
            ParsedNutrient("fibre", 0.0, "g", "reliable"),
        ],
    )

    with patch("services.openfoodfacts.lookup_barcode", return_value=mock_off_product):
        # 1. Post new product
        post_res = client.post("/products", json={"barcode": "7340191149779", "category": "cheese"})
        assert post_res.status_code == 200
        data = post_res.json()
        assert data["barcode"] == "7340191149779"
        assert data["name"] == "Coop Mozzarella Juustoraaste"
        assert data["brand"] == "Coop"
        assert len(data["nutrition_facts"]) == 5

    # 2. Post same barcode again: should return cached product without calling Open Food Facts
    with patch("services.openfoodfacts.lookup_barcode") as mock_lookup:
        cached_res = client.post("/products", json={"barcode": "7340191149779", "category": "cheese"})
        assert cached_res.status_code == 200
        assert mock_lookup.call_count == 0

    # 3. Add second product with higher protein
    mock_valio = OpenFoodFactsProduct(
        barcode="6408430341917",
        name="Valio Hyvä Suomalainen Arki",
        brand="Valio",
        image_url=None,
        package_size_g=170.0,
        nutrients=[
            ParsedNutrient("protein", 26.0, "g", "reliable"),
            ParsedNutrient("calories", 330.0, "kcal", "reliable"),
            ParsedNutrient("fat", 24.0, "g", "reliable"),
        ],
    )

    with patch("services.openfoodfacts.lookup_barcode", return_value=mock_valio):
        client.post("/products", json={"barcode": "6408430341917", "category": "cheese"})

    # 4. Check ranking by protein (default: most protein)
    rank_res = client.get("/products/ranking?category=cheese&metric=protein&direction=most")
    assert rank_res.status_code == 200
    rankings = rank_res.json()
    assert len(rankings) == 2

    # Valio (26g) should be rank #1
    assert rankings[0]["barcode"] == "6408430341917"
    assert rankings[0]["rank"] == 1
    assert rankings[0]["primary_value"] == 26.0

    # Coop (21g) should be rank #2
    assert rankings[1]["barcode"] == "7340191149779"
    assert rankings[1]["rank"] == 2
    assert rankings[1]["primary_value"] == 21.0

    # 5. Check ranking by calories (least calories)
    cal_res = client.get("/products/ranking?category=cheese&metric=calories&direction=least")
    assert cal_res.status_code == 200
    cal_rankings = cal_res.json()

    # Coop (298 kcal) should rank higher than Valio (330 kcal)
    assert cal_rankings[0]["barcode"] == "7340191149779"
    assert cal_rankings[0]["rank"] == 1
    assert cal_rankings[0]["primary_value"] == 298.0


def test_auto_category_detection(client):
    mock_chicken = OpenFoodFactsProduct(
        barcode="6414891801020",
        name="Kanan Fileesuikale 2.1%",
        brand="Kotimaista",
        image_url="https://images.example/chicken.jpg",
        package_size_g=300.0,
        nutrients=[
            ParsedNutrient("protein", 23.0, "g", "reliable"),
            ParsedNutrient("calories", 110.0, "kcal", "reliable"),
            ParsedNutrient("fat", 2.1, "g", "reliable"),
        ],
        detected_category="meat",
    )

    with patch("services.openfoodfacts.lookup_barcode", return_value=mock_chicken):
        # 1. Post with category="auto" -> should automatically assign "meat"
        res = client.post("/products", json={"barcode": "6414891801020", "category": "auto"})
        assert res.status_code == 200
        data = res.json()
        assert data["barcode"] == "6414891801020"
        assert data["category"] == "meat"
        assert data["name"] == "Kanan Fileesuikale 2.1%"

    # 2. Ranking filtered by category "meat" should include it
    meat_rank = client.get("/products/ranking?category=meat&metric=protein")
    assert meat_rank.status_code == 200
    meat_items = meat_rank.json()
    assert any(item["barcode"] == "6414891801020" for item in meat_items)

    # 3. Ranking filtered by category "cheese" should NOT include the chicken
    cheese_rank = client.get("/products/ranking?category=cheese&metric=protein")
    assert cheese_rank.status_code == 200
    cheese_items = cheese_rank.json()
    assert not any(item["barcode"] == "6414891801020" for item in cheese_items)
