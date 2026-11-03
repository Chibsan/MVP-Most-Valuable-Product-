from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.db.session import get_db
from app.models import Category, Product
from app.schemas.comparison import CategoryOut, CategoryPage, ProductOut, ProductPage
from app.services.ranking import product_data

router = APIRouter(tags=["catalog"])


@router.get("/categories", response_model=CategoryPage)
def list_categories(db: Session = Depends(get_db)) -> CategoryPage:
    rows = db.execute(
        select(Category, func.count(Product.id))
        .outerjoin(Product, Product.category_id == Category.id)
        .where(Category.is_active.is_(True))
        .group_by(Category.id)
        .order_by(Category.name, Category.slug)
    ).all()
    return CategoryPage(
        items=[
            CategoryOut(
                slug=category.slug,
                name=category.name,
                product_count=count,
                is_active=category.is_active,
                source_url=category.source_url,
            )
            for category, count in rows
        ]
    )


def _product_out(product: Product, category: Category) -> ProductOut:
    data = product_data(product)
    return ProductOut(
        id=product.id,
        name=product.name,
        category=category.slug,
        brand=product.brand,
        barcode=product.barcode,
        package_size_g=product.package_size_g,
        package_size_label=product.package_size_label,
        package_price=data.package_price,
        currency=data.package_currency,
        price_per_100g=data.metrics["price"].value,
        price_source=data.price_source,
        price_observed_at=data.price_observed_at,
        source_url=product.source_url,
        metrics={
            metric: {
                "value": datum.value,
                "unit": datum.unit,
                "quality_status": datum.quality_status,
                "reason": datum.reason,
                "source_url": datum.source_url,
                "observed_at": datum.observed_at,
            }
            for metric, datum in data.metrics.items()
        },
    )


@router.get("/products", response_model=ProductPage)
def list_products(
    category: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> ProductPage:
    statement = (
        select(Product)
        .join(Category)
        .options(selectinload(Product.prices), selectinload(Product.nutrition_facts))
        .order_by(Product.name, Product.id)
        .limit(limit)
        .offset(offset)
    )
    if category is not None:
        category_row = db.scalar(
            select(Category).where(Category.slug == category, Category.is_active.is_(True))
        )
        if category_row is None:
            raise HTTPException(status_code=404, detail="Category was not found.")
        statement = statement.where(Product.category_id == category_row.id)
    products = db.scalars(statement).all()
    categories = {
        category_row.id: category_row
        for category_row in db.scalars(select(Category)).all()
    }
    return ProductPage(
        items=[_product_out(item, categories[item.category_id]) for item in products],
        limit=limit,
        offset=offset,
    )
