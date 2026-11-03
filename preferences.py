from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_or_create_session
from app.db.session import get_db
from app.models import Category
from app.schemas.comparison import PreferenceOut, PreferenceUpdate
from app.services.ranking import criteria_for

router = APIRouter(prefix="/preferences", tags=["preferences"])


def _response(db: Session, preference) -> PreferenceOut:
    category = db.get(Category, preference.category_id) if preference.category_id else None
    metric = preference.primary_metric if preference.preference_mode == "custom" else "calories"
    direction = preference.primary_direction if preference.preference_mode == "custom" else "least"
    return PreferenceOut(
        category=category.slug if category is not None else None,
        preference_mode=preference.preference_mode,
        primary_metric=metric,
        primary_direction=direction,
        criteria=criteria_for(metric, direction),
    )


@router.get("", response_model=PreferenceOut)
def get_preferences(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> PreferenceOut:
    _, preference = get_or_create_session(request, response, db)
    db.commit()
    return _response(db, preference)


@router.put("", response_model=PreferenceOut)
def update_preferences(
    update: PreferenceUpdate,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> PreferenceOut:
    category = db.scalar(
        select(Category).where(
            Category.slug == update.category,
            Category.is_active.is_(True),
        )
    )
    if category is None:
        raise HTTPException(status_code=404, detail="Active category was not found.")
    _, preference = get_or_create_session(request, response, db)
    preference.category_id = category.id
    if update.preference_mode == "default":
        preference.preference_mode = "default"
        preference.primary_metric = "calories"
        preference.primary_direction = "least"
    else:
        preference.preference_mode = "custom"
        preference.primary_metric = update.primary_metric
        preference.primary_direction = update.primary_direction
    db.commit()
    db.refresh(preference)
    return _response(db, preference)
