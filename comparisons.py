from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.session import get_db
from app.models import Category, Product
from app.schemas.comparison import ComparisonOut, ComparisonRequest
from app.services.ranking import build_comparison

router = APIRouter(prefix="/comparisons", tags=["comparisons"])


@router.post("", response_model=ComparisonOut)
def compare(
    request: ComparisonRequest,
    db: Session = Depends(get_db),
) -> ComparisonOut:
    category = db.scalar(
        select(Category).where(
            Category.slug == request.category,
            Category.is_active.is_(True),
        )
    )
    if category is None:
        raise HTTPException(status_code=404, detail="Active category was not found.")
    if request.preference_mode == "default":
        metric, direction = "calories", "least"
    else:
        metric = request.primary_metric
        direction = request.primary_direction
    products = db.scalars(
        select(Product)
        .where(Product.category_id == category.id)
        .options(selectinload(Product.prices), selectinload(Product.nutrition_facts))
        .order_by(Product.name, Product.id)
    ).all()
    return build_comparison(
        products, category.slug, request.preference_mode, metric, direction
    )
