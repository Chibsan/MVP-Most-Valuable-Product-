from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Any

import models
from database import engine, SessionLocal
from services import openfoodfacts, ranking

# Ensure tables exist
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="MVP4U Backend",
    description="FastAPI service for barcode product scanning and dense nutritional ranking.",
    version="1.0.0",
)

# Allow client connections (including Expo on LAN/Tailscale)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Pydantic Schemas
class ProductCreate(BaseModel):
    barcode: str
    category: str = "general"


class NutritionFactOut(BaseModel):
    metric: str
    value: float | None
    unit: str
    quality_status: str
    quality_note: str | None = None

    class Config:
        from_attributes = True


class ProductResponse(BaseModel):
    id: int
    barcode: str
    name: str | None
    brand: str | None
    category: str
    image_url: str | None
    score: float = 0.0
    nutrition_facts: list[NutritionFactOut] = []

    class Config:
        from_attributes = True


class RankedItemOut(BaseModel):
    id: int
    barcode: str
    name: str | None
    brand: str | None
    category: str
    image_url: str | None
    score: float = 0.0
    rank: int | None
    display_position: int
    primary_metric: str
    primary_direction: str
    primary_value: float | None
    metrics: dict[str, Any]


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "MVP4U Backend"}


@app.post("/products", response_model=ProductResponse)
def add_product(payload: ProductCreate, db: Session = Depends(get_db)):
    barcode = payload.barcode.strip()
    category = payload.category.strip().lower() if payload.category else "general"

    # 1. Return existing product if already scanned and cached in DB
    existing = db.query(models.Product).filter(models.Product.barcode == barcode).first()
    if existing:
        return existing

    # 2. Query Open Food Facts for real product identity and nutrients
    name = None
    brand = None
    image_url = None
    nutrient_facts = []

    try:
        off_product = openfoodfacts.lookup_barcode(barcode)
        name = off_product.name
        brand = off_product.brand
        image_url = off_product.image_url
        nutrient_facts = off_product.nutrients
    except (openfoodfacts.OpenFoodFactsNotFoundError, ValueError):
        # Fallback when product is not in Open Food Facts catalog
        name = f"Scanned Product ({barcode})"
    except openfoodfacts.OpenFoodFactsRateLimitError:
        raise HTTPException(
            status_code=429,
            detail="Open Food Facts rate limit reached. Please try again shortly.",
        )
    except Exception as exc:
        name = f"Scanned Product ({barcode})"

    # 3. Create and persist product
    new_product = models.Product(
        barcode=barcode,
        name=name,
        brand=brand,
        category=category,
        image_url=image_url,
        score=0.0,
    )
    db.add(new_product)
    db.flush()

    # 4. Persist parsed nutrition facts
    for fact in nutrient_facts:
        db.add(
            models.NutritionFact(
                product_id=new_product.id,
                metric=fact.metric,
                value=fact.value,
                unit=fact.unit,
                quality_status=fact.quality_status,
                quality_note=fact.quality_note,
            )
        )

    db.commit()
    db.refresh(new_product)
    return new_product


@app.get("/products/ranking", response_model=list[RankedItemOut])
def get_ranking(
    category: str | None = Query(None, description="Filter ranking by product category"),
    metric: str = Query("protein", description="Primary metric: protein, calories, fat, fibre, carbohydrates"),
    direction: str = Query("most", description="Direction: most or least"),
    db: Session = Depends(get_db),
):
    query = db.query(models.Product)
    if category and category.strip().lower() not in ("all", ""):
        query = query.filter(models.Product.category == category.strip().lower())

    products = query.all()
    if not products:
        return []

    ranked = ranking.calculate_rankings(
        products=products,
        primary_metric=metric,
        primary_direction=direction,
    )

    results = []
    for item in ranked:
        results.append(
            RankedItemOut(
                id=item.id,
                barcode=item.barcode,
                name=item.name,
                brand=item.brand,
                category=item.category,
                image_url=item.image_url,
                score=item.primary_value if item.primary_value is not None else 0.0,
                rank=item.rank,
                display_position=item.display_position,
                primary_metric=item.primary_metric,
                primary_direction=item.primary_direction,
                primary_value=item.primary_value,
                metrics=item.metrics,
            )
        )

    return results


@app.get("/products/{barcode}", response_model=ProductResponse)
def get_product(barcode: str, db: Session = Depends(get_db)):
    product = db.query(models.Product).filter(models.Product.barcode == barcode.strip()).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found in local database.")
    return product
