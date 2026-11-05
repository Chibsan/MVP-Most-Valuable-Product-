from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from database import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    barcode = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=True)
    brand = Column(String, nullable=True)
    category = Column(String, index=True, default="general")
    package_size_g = Column(Float, nullable=True)
    image_url = Column(String, nullable=True)
    score = Column(Float, default=0.0)
    created_at = Column(DateTime, server_default=func.now())

    nutrition_facts = relationship(
        "NutritionFact",
        back_populates="product",
        cascade="all, delete-orphan",
        lazy="joined",
    )


class NutritionFact(Base):
    __tablename__ = "nutrition_facts"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    metric = Column(String, nullable=False, index=True)
    value = Column(Float, nullable=True)
    unit = Column(String, nullable=False)
    quality_status = Column(String, default="reliable")
    quality_note = Column(String, nullable=True)

    product = relationship("Product", back_populates="nutrition_facts")
