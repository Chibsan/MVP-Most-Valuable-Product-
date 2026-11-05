from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
import models
from database import engine, SessionLocal
from fastapi.middleware.cors import CORSMiddleware

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="MVP4U Backend")

# Allow expo client to connect
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

class ProductCreate(BaseModel):
    barcode: str
    category: str
    score: float = 10.0 # Mock initial score

class ProductResponse(ProductCreate):
    id: int

@app.post("/products", response_model=ProductResponse)
def add_product(product: ProductCreate, db: Session = Depends(get_db)):
    db_product = db.query(models.Product).filter(models.Product.barcode == product.barcode).first()
    if db_product:
        return db_product
    new_product = models.Product(barcode=product.barcode, category=product.category, score=product.score)
    db.add(new_product)
    db.commit()
    db.refresh(new_product)
    return new_product

@app.get("/products/ranking")
def get_ranking(db: Session = Depends(get_db)):
    products = db.query(models.Product).order_by(models.Product.score.desc()).all()
    return products
