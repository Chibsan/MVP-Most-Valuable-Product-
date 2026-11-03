from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_serializer, model_validator

Metric = Literal["calories", "carbohydrates", "protein", "fat", "fibre", "price"]
Direction = Literal["most", "least"]
QualityStatus = Literal["reliable", "unreliable", "unverified", "missing", "invalid"]
PreferenceMode = Literal["default", "custom"]


class Criterion(BaseModel):
    metric: Metric
    direction: Direction
    unit: str


class ApiModel(BaseModel):
    @field_serializer("*", when_used="json")
    def serialize_decimal(self, value: object) -> object:
        if isinstance(value, Decimal):
            return float(value)
        return value


class CategoryOut(ApiModel):
    slug: str
    name: str
    product_count: int
    is_active: bool
    source_url: str | None = None


class CategoryPage(ApiModel):
    items: list[CategoryOut]


class PreferenceUpdate(BaseModel):
    category: str
    preference_mode: PreferenceMode
    primary_metric: Metric | None = None
    primary_direction: Direction | None = None

    @model_validator(mode="after")
    def require_custom_priority(self) -> "PreferenceUpdate":
        if self.preference_mode == "custom" and (
            self.primary_metric is None or self.primary_direction is None
        ):
            raise ValueError("Custom preferences require a metric and direction.")
        return self


class ComparisonRequest(PreferenceUpdate):
    pass


class PreferenceOut(ApiModel):
    category: str | None
    preference_mode: PreferenceMode
    primary_metric: Metric
    primary_direction: Direction
    criteria: list[Criterion]


class MetricResult(ApiModel):
    value: Decimal | None
    unit: str
    direction: Direction
    rank: int | None
    quality_status: QualityStatus
    reason: str | None = None
    source_url: str | None = None
    observed_at: datetime | None = None


class MetricValue(ApiModel):
    value: Decimal | None
    unit: str
    quality_status: QualityStatus
    reason: str | None = None
    source_url: str | None = None
    observed_at: datetime | None = None


class ProductMetrics(ApiModel):
    calories: MetricValue | MetricResult
    carbohydrates: MetricValue | MetricResult
    protein: MetricValue | MetricResult
    fat: MetricValue | MetricResult
    fibre: MetricValue | MetricResult
    price: MetricValue | MetricResult


class ProductMetricResults(ApiModel):
    calories: MetricResult
    carbohydrates: MetricResult
    protein: MetricResult
    fat: MetricResult
    fibre: MetricResult
    price: MetricResult


class ProductOut(ApiModel):
    id: UUID
    name: str
    category: str
    brand: str | None
    barcode: str | None
    package_size_g: Decimal | None
    package_size_label: str | None
    package_price: Decimal | None
    currency: Literal["EUR"] | None
    price_per_100g: Decimal | None
    price_source: str | None
    price_observed_at: datetime | None
    source_url: str | None
    metrics: ProductMetrics


class ProductPage(ApiModel):
    items: list[ProductOut]
    limit: int
    offset: int


class ProductComparison(ProductOut):
    display_position: int
    metrics: ProductMetricResults


class ComparisonOut(ApiModel):
    category: str
    preference_mode: PreferenceMode
    primary_metric: Metric
    primary_direction: Direction
    criteria: list[Criterion]
    items: list[ProductComparison]
    unranked_count: int


class ErrorOut(ApiModel):
    code: str
    message: str
    details: list[dict[str, object]] | None = None


class ORMModel(ApiModel):
    model_config = ConfigDict(from_attributes=True)
