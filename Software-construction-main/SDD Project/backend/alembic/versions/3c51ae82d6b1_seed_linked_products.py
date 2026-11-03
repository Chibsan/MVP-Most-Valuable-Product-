"""Seed the 16 product links provided by the user.

Revision ID: 3c51ae82d6b1
Revises: 077d95a7b22d
"""
from typing import Sequence, Union
from uuid import UUID

from alembic import op
import sqlalchemy as sa

revision: str = "3c51ae82d6b1"
down_revision: Union[str, None] = "077d95a7b22d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

MILK = UUID("6b62fefe-3c11-4f4f-9f7c-7494de893901")
MINCED_MEAT = UUID("6b62fefe-3c11-4f4f-9f7c-7494de893902")
SOFTDRINKS = UUID("6b62fefe-3c11-4f4f-9f7c-7494de893903")
SNACKS = UUID("6b62fefe-3c11-4f4f-9f7c-7494de893904")

PRODUCTS = [
    (1, MILK, "Kotimaista rasvaton maito", "Kotimaista", "6415712506032", None, "1 l", "kotimaista-rasvaton-maito-1l"),
    (2, MILK, "Kotimaista laktoositon kevytmaitojuoma", "Kotimaista", "6414893385672", None, "1 l", "kotimaista-laktoositon-kevytmaitojuoma-1-l"),
    (3, MILK, "Kotimaista laktoositon rasvaton maitojuoma", "Kotimaista", "6414893385658", None, "1 l", "kotimaista-laktoositon-1-l-rasvaton-maitojuoma"),
    (4, MILK, "Valio luomutm kevytmaito", "Valio", "6408430000142", None, "1 l", "valio-luomutm-kevytmaito-1-l"),
    (5, MINCED_MEAT, "Atria Parempi nauta jauheliha 10", "Atria", "6407840041172", 400, "400 g", "atria-parempi-nauta-jauheliha-10-400g"),
    (6, MINCED_MEAT, "Kotimaista kanan jauheliha 4", "Kotimaista", "6414891801488", 400, "400 g", "kotimaista-kanan-jauheliha-4-400-g"),
    (7, MINCED_MEAT, "Kotimaista naudan jauheliha 17", "Kotimaista", "6414893500167", 700, "700 g", "kotimaista-naudan-jauheliha-17-700-g"),
    (8, MINCED_MEAT, "Atria kevyt nauta-possu jauheliha 9-5", "Atria", "6407830032586", 400, "400 g", "atria-kevyt-nauta-possu-jauheliha-9-5-400g"),
    (9, SOFTDRINKS, "2-pack Coca-Cola Zero Sugar virvoitusjuoma", "Coca-Cola", "6415600502108", None, "2-pack, 1.5 l", "2-pack-coca-cola-zero-sugar-virvoitusjuoma-muovipullo-1-5-l"),
    (10, SOFTDRINKS, "6-pack Coca-Cola Original virvoitusjuoma", "Coca-Cola", "5449000000965", None, "6-pack, 0.33 l", "6-pack-coca-cola-original-virvoitusjuoma-tolkki-0-33-l"),
    (11, SOFTDRINKS, "San Pellegrino Limonata", "San Pellegrino", "8002270506918", None, "33 cl", "san-pellegrino-limonata-33cl"),
    (12, SOFTDRINKS, "6-pack 7up Zero Sugar virvoitusjuoma", "7up", "6413605254411", None, "6-pack, 0.33 l", "6-x-7up-zero-sugar-virvoitusjuoma-0-33-l"),
    (13, SNACKS, "Elovena tumma suklaa täysjyvä välipalakeksi 100% kauraa", "Elovena", "6411200212317", 300, "10 × 30 g", "elovena-10x30g-tumma-suklaa-taysjyva-valipalakeksi-100-kauraa"),
    (14, SNACKS, "Corny Havre Banana kaurapatukka", "Corny", "4011800002077", 50, "50 g", "corny-havre-banana-kaurapatukka-50g"),
    (15, SNACKS, "Elovena piparkakku täysjyvävälipalakeksi 100% kauraa", "Elovena", "6411200004622", 300, "10 × 30 g", "elovena-10x30g-piparkakku-taysjyvavalipalakeksi-100-kauraa"),
    (16, SNACKS, "Corny Havre Chocolate kaurapatukka", "Corny", "4011800002053", 50, "50 g", "corny-havre-chocolate-kaurapatukka-50g"),
]


def upgrade() -> None:
    op.add_column(
        "products",
        sa.Column("package_size_label", sa.String(length=120), nullable=True),
    )
    product_table = sa.table(
        "products",
        sa.column("id", sa.Uuid()),
        sa.column("category_id", sa.Uuid()),
        sa.column("name", sa.String(length=500)),
        sa.column("brand", sa.String(length=250)),
        sa.column("barcode", sa.String(length=32)),
        sa.column("package_size_g", sa.Numeric(12, 3)),
        sa.column("package_size_label", sa.String(length=120)),
        sa.column("source_url", sa.String(length=2048)),
    )
    op.bulk_insert(
        product_table,
        [
            {
                "id": UUID(f"b4b2186e-1fb4-4db4-bbac-{number:012d}"),
                "category_id": category_id,
                "name": name,
                "brand": brand,
                "barcode": barcode,
                "package_size_g": package_size_g,
                "package_size_label": package_size_label,
                "source_url": f"https://www.s-kaupat.fi/tuote/{slug}/{barcode}",
            }
            for (
                number,
                category_id,
                name,
                brand,
                barcode,
                package_size_g,
                package_size_label,
                slug,
            ) in PRODUCTS
        ],
    )


def downgrade() -> None:
    product_table = sa.table(
        "products",
        sa.column("id", sa.Uuid()),
    )
    op.execute(
        product_table.delete().where(
            product_table.c.id.in_(
                [
                    UUID(f"b4b2186e-1fb4-4db4-bbac-{number:012d}")
                    for number, *_ in PRODUCTS
                ]
            )
        )
    )
    op.drop_column("products", "package_size_label")
