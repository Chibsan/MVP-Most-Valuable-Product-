import argparse
import csv
import gzip
import sys
import time
from pathlib import Path
from typing import TextIO

import httpx
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models import Product
from app.services.openfoodfacts import (
    METRIC_FIELDS,
    OpenFoodFactsDataError,
    OpenFoodFactsRateLimitError,
    lookup_barcode,
    parse_export_row,
    persist_lookup,
    validate_contact_email,
)

MIN_REQUEST_INTERVAL_SECONDS = 4.1
USAGE_FORM_URL = (
    "https://docs.google.com/forms/d/e/"
    "1FAIpQLSdIE3D8qvjC_zRJw1W8OmuHhsWJ_NSckiiniAHlfaVwUZCziQ/viewform"
)


def sync_openfoodfacts() -> int:
    settings = get_settings()
    if not settings.openfoodfacts_usage_form_completed:
        print(
            f"Complete the Open Food Facts API usage form first: {USAGE_FORM_URL}",
            file=sys.stderr,
        )
        return 2
    try:
        email = validate_contact_email(settings.openfoodfacts_contact_email)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    user_agent = f"NutritionComparer/1.0 ({email})"
    with SessionLocal() as db:
        products = db.scalars(
            select(Product)
            .where(Product.barcode.is_not(None))
            .options(selectinload(Product.nutrition_facts))
            .order_by(Product.barcode)
        ).all()
        if not products:
            print("No products with barcodes are available for nutrition lookup.")
            return 0

        updated_count = 0
        missing_count = 0
        with httpx.Client(
            headers={"User-Agent": user_agent},
            timeout=httpx.Timeout(15.0, connect=5.0),
            follow_redirects=False,
        ) as client:
            try:
                for index, product in enumerate(products):
                    if index:
                        time.sleep(MIN_REQUEST_INTERVAL_SECONDS)
                    lookup = lookup_barcode(client, product.barcode)
                    if not lookup.found:
                        missing_count += 1
                        print(f"{product.barcode}: {lookup.message}")
                        continue
                    updated_count += persist_lookup(product, lookup)
                    db.commit()
            except OpenFoodFactsRateLimitError as exc:
                db.rollback()
                print(str(exc), file=sys.stderr)
                return 1
            except OpenFoodFactsDataError as exc:
                db.rollback()
                print(str(exc), file=sys.stderr)
                return 1
            except ValueError as exc:
                db.rollback()
                print(str(exc), file=sys.stderr)
                return 1
            except httpx.HTTPStatusError as exc:
                db.rollback()
                print(
                    f"Open Food Facts returned HTTP {exc.response.status_code}; "
                    "sync stopped without retrying.",
                    file=sys.stderr,
                )
                return 1
            except httpx.RequestError as exc:
                db.rollback()
                print(f"Open Food Facts request failed: {exc}", file=sys.stderr)
                return 1
    print(
        f"Processed {updated_count} nutrition facts; "
        f"{missing_count} barcode(s) had no matching Open Food Facts record."
    )
    return 0


def import_openfoodfacts_export(path: Path) -> int:
    if not path.is_file():
        print(f"Open Food Facts export file does not exist: {path}", file=sys.stderr)
        return 2
    try:
        source: TextIO = (
            gzip.open(path, "rt", encoding="utf-8", newline="")
            if path.suffix == ".gz"
            else path.open("r", encoding="utf-8", newline="")
        )
        with source:
            csv.field_size_limit(max(csv.field_size_limit(), 10_000_000))
            reader = csv.DictReader(source, delimiter="\t")
            required_columns = {"code", "last_modified_t"} | {
                field for field, _, _maximum in METRIC_FIELDS.values()
            }
            if not reader.fieldnames or not required_columns.issubset(reader.fieldnames):
                raise ValueError(
                    "Export must be the tab-separated Open Food Facts products dump "
                    "with code and last_modified_t columns."
                )
            products_by_barcode: dict[str, Product] = {}
            with SessionLocal() as db:
                products = db.scalars(
                    select(Product)
                    .where(Product.barcode.is_not(None))
                    .options(selectinload(Product.nutrition_facts))
                    .order_by(Product.barcode)
                ).all()
                products_by_barcode = {
                    product.barcode: product for product in products if product.barcode
                }
                if not products_by_barcode:
                    print("No products with barcodes are available for import.")
                    return 0

                latest_rows: dict[str, dict[str, str]] = {}
                latest_times: dict[str, int] = {}
                for row in reader:
                    barcode = row.get("code", "")
                    if barcode not in products_by_barcode:
                        continue
                    try:
                        modified = int(row.get("last_modified_t", ""))
                    except (TypeError, ValueError):
                        modified = -1
                    if barcode not in latest_rows or modified > latest_times[barcode]:
                        latest_rows[barcode] = row
                        latest_times[barcode] = modified

                updated_count = 0
                for barcode, row in latest_rows.items():
                    lookup = parse_export_row(row, barcode)
                    updated_count += persist_lookup(products_by_barcode[barcode], lookup)
                db.commit()
        print(
            f"Imported {updated_count} nutrition facts for "
            f"{len(latest_rows)} of {len(products_by_barcode)} product barcodes "
            "from the offline export."
        )
        unmatched = sorted(set(products_by_barcode) - set(latest_rows))
        if unmatched:
            print(f"No exact export record found for {len(unmatched)} barcode(s).")
        return 0
    except (OSError, EOFError, gzip.BadGzipFile, UnicodeDecodeError, csv.Error, ValueError) as exc:
        print(f"Could not import Open Food Facts export: {exc}", file=sys.stderr)
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Nutrition Comparer catalog tools")
    parser.add_argument(
        "command",
        choices=("sync-openfoodfacts", "import-openfoodfacts-export"),
        help="Sync via API or import a downloaded Open Food Facts CSV/TSV export.",
    )
    parser.add_argument(
        "export_path",
        nargs="?",
        type=Path,
        help="Path to the downloaded .csv, .tsv, or .gz export.",
    )
    args = parser.parse_args()
    if args.command == "sync-openfoodfacts":
        return sync_openfoodfacts()
    if args.command == "import-openfoodfacts-export":
        if args.export_path is None:
            parser.error("import-openfoodfacts-export requires an export file path.")
        return import_openfoodfacts_export(args.export_path)
    parser.error("Unknown catalog command.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
