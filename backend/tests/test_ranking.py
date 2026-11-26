from dataclasses import dataclass
from services.ranking import calculate_rankings


@dataclass
class MockFact:
    metric: str
    value: float | None
    unit: str = "g"
    quality_status: str = "reliable"
    quality_note: str | None = None


@dataclass
class MockProduct:
    id: int
    barcode: str
    name: str
    brand: str = "TestBrand"
    category: str = "cheese"
    image_url: str | None = None
    nutrition_facts: list[MockFact] = None

    def __post_init__(self):
        if self.nutrition_facts is None:
            self.nutrition_facts = []


def test_dense_ranking_with_ties():
    # Three products: A and B have 25g protein, C has 20g protein
    p1 = MockProduct(
        id=1,
        barcode="111",
        name="Beta Cheese",
        nutrition_facts=[MockFact("protein", 25.0), MockFact("calories", 300.0)],
    )
    p2 = MockProduct(
        id=2,
        barcode="222",
        name="Alpha Cheese",
        nutrition_facts=[MockFact("protein", 25.0), MockFact("calories", 310.0)],
    )
    p3 = MockProduct(
        id=3,
        barcode="333",
        name="Gamma Cheese",
        nutrition_facts=[MockFact("protein", 20.0), MockFact("calories", 250.0)],
    )

    ranked = calculate_rankings([p1, p2, p3], primary_metric="protein", primary_direction="most")

    # Alpha and Beta tie at 25g -> rank #1, Alpha first alphabetically
    assert ranked[0].name == "Alpha Cheese"
    assert ranked[0].rank == 1
    assert ranked[0].primary_value == 25.0

    assert ranked[1].name == "Beta Cheese"
    assert ranked[1].rank == 1
    assert ranked[1].primary_value == 25.0

    # Gamma has next distinct value -> rank #2 (dense ranking, not rank 3)
    assert ranked[2].name == "Gamma Cheese"
    assert ranked[2].rank == 2
    assert ranked[2].primary_value == 20.0


def test_ranking_direction_least():
    # Lower calories should rank higher
    p1 = MockProduct(
        id=1,
        barcode="111",
        name="High Calorie",
        nutrition_facts=[MockFact("calories", 400.0)],
    )
    p2 = MockProduct(
        id=2,
        barcode="222",
        name="Low Calorie",
        nutrition_facts=[MockFact("calories", 150.0)],
    )

    ranked = calculate_rankings([p1, p2], primary_metric="calories", primary_direction="least")

    assert ranked[0].name == "Low Calorie"
    assert ranked[0].rank == 1
    assert ranked[1].name == "High Calorie"
    assert ranked[1].rank == 2


def test_unranked_placed_after_reliable():
    # Product with missing protein placed after ranked product
    p_valid = MockProduct(
        id=1,
        barcode="111",
        name="Valid Product",
        nutrition_facts=[MockFact("protein", 10.0)],
    )
    p_missing = MockProduct(
        id=2,
        barcode="222",
        name="Missing Protein",
        nutrition_facts=[MockFact("protein", None, quality_status="missing")],
    )

    ranked = calculate_rankings([p_missing, p_valid], primary_metric="protein", primary_direction="most")

    assert ranked[0].name == "Valid Product"
    assert ranked[0].rank == 1

    assert ranked[1].name == "Missing Protein"
    assert ranked[1].rank is None
    assert ranked[1].display_position == 2
