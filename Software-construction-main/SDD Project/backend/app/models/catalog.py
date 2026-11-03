from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(250), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    source_url: Mapped[str | None] = mapped_column(String(2048))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    products: Mapped[list["Product"]] = relationship(back_populates="category")

    __table_args__ = (
        CheckConstraint("length(trim(slug)) > 0", name="ck_category_slug_nonempty"),
        CheckConstraint("length(trim(name)) > 0", name="ck_category_name_nonempty"),
    )


class Product(Base):
    __tablename__ = "products"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    category_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    brand: Mapped[str | None] = mapped_column(String(250))
    barcode: Mapped[str | None] = mapped_column(String(32), unique=True)
    package_size_g: Mapped[Decimal | None] = mapped_column(Numeric(12, 3))
    package_size_label: Mapped[str | None] = mapped_column(String(120))
    source_url: Mapped[str | None] = mapped_column(String(2048))
    source_observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    category: Mapped[Category] = relationship(back_populates="products")
    prices: Mapped[list["PriceObservation"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )
    nutrition_facts: Mapped[list["NutritionFact"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint("length(trim(name)) > 0", name="ck_product_name_nonempty"),
        CheckConstraint("package_size_g IS NULL OR package_size_g > 0", name="ck_product_size_positive"),
        Index("ix_products_category_name", "category_id", "name"),
    )


class PriceObservation(Base):
    __tablename__ = "price_observations"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    product_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    package_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="EUR")
    source_name: Mapped[str] = mapped_column(String(120), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(2048))
    observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    quality_status: Mapped[str] = mapped_column(String(16), nullable=False)
    quality_note: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    product: Mapped[Product] = relationship(back_populates="prices")

    __table_args__ = (
        CheckConstraint(
            "package_price IS NULL OR package_price >= 0",
            name="ck_price_nonnegative",
        ),
        CheckConstraint("currency = 'EUR'", name="ck_price_eur_only"),
        CheckConstraint(
            "quality_status IN ('reliable', 'unreliable', 'unverified', 'missing', 'invalid')",
            name="ck_price_quality_status",
        ),
        Index("ix_prices_product_observed", "product_id", "observed_at"),
    )


class NutritionFact(Base):
    __tablename__ = "nutrition_facts"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    product_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    metric: Mapped[str] = mapped_column(String(32), nullable=False)
    value: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    unit: Mapped[str] = mapped_column(String(16), nullable=False)
    basis_g: Mapped[Decimal] = mapped_column(Numeric(8, 3), nullable=False)
    source_name: Mapped[str] = mapped_column(String(120), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(2048))
    observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    quality_status: Mapped[str] = mapped_column(String(16), nullable=False)
    quality_note: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    product: Mapped[Product] = relationship(back_populates="nutrition_facts")

    __table_args__ = (
        CheckConstraint("metric IN ('calories', 'carbohydrates', 'protein', 'fat', 'fibre')", name="ck_fact_metric"),
        CheckConstraint("value IS NULL OR value >= 0", name="ck_fact_nonnegative"),
        CheckConstraint("basis_g > 0", name="ck_fact_basis_positive"),
        CheckConstraint(
            "quality_status IN ('reliable', 'unreliable', 'unverified', 'missing', 'invalid')",
            name="ck_fact_quality_status",
        ),
        Index("ix_facts_product_metric_observed", "product_id", "metric", "observed_at"),
    )
