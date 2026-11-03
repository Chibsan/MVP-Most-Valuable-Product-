import argparse
import csv
import json
import shlex
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from math import isfinite
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
import webbrowser


NUTRIENTS = {
    "calories_kcal": ("Calories", "kcal"),
    "protein_g": ("Protein", "g"),
    "carbohydrate_g": ("Carbohydrate", "g"),
    "sugars_g": ("Sugars", "g"),
    "fat_g": ("Fat", "g"),
    "saturated_fat_g": ("Saturated fat", "g"),
    "fiber_g": ("Fiber", "g"),
    "sodium_mg": ("Sodium", "mg"),
}
RANKING_METRICS = {
    "calories": ("calories_kcal", "Calories", "kcal", False),
    "carbohydrates": ("carbohydrate_g", "Carbohydrates", "g", False),
    "protein": ("protein_g", "Protein", "g", True),
    "fat": ("fat_g", "Fat", "g", False),
    "fiber": ("fiber_g", "Fiber", "g", True),
    "price": ("price_per_100g", "Price / 100 g", "", False),
}


@dataclass(frozen=True)
class Product:
    category: str
    name: str
    nutrients: dict[str, float | None]
    package_size_g: float
    product_price_eur: float
    price_per_100g: float


def load_products(csv_path: Path) -> list[Product]:
    required_columns = {
        "category",
        "name",
        "package_size_g",
        "product_price_eur",
        "price_per_100g",
        *NUTRIENTS,
    }
    products = []
    seen_names = set()

    with csv_path.open(encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        missing_columns = required_columns - set(reader.fieldnames or [])
        if missing_columns:
            missing = ", ".join(sorted(missing_columns))
            raise ValueError(f"CSV is missing required columns: {missing}")

        for line_number, row in enumerate(reader, start=2):
            category = (row.get("category") or "").strip()
            name = (row.get("name") or "").strip()
            if not category:
                raise ValueError(f"Row {line_number} has no product category")
            if not name:
                raise ValueError(f"Row {line_number} has no product name")
            if name.casefold() in seen_names:
                raise ValueError(f"Duplicate product name on row {line_number}: {name}")

            try:
                package_size = float(row["package_size_g"])
            except (TypeError, ValueError):
                raise ValueError(
                    f"Row {line_number} has an invalid value for package_size_g"
                ) from None
            if not isfinite(package_size) or package_size <= 0:
                raise ValueError(
                    f"Row {line_number} has an invalid package size; "
                    "it must be finite and greater than zero"
                )

            nutrients = {}
            for key in NUTRIENTS:
                raw_value = (row[key] or "").strip()
                if not raw_value:
                    nutrients[key] = None
                    continue
                try:
                    value = float(raw_value)
                except (TypeError, ValueError):
                    raise ValueError(
                        f"Row {line_number} has an invalid value for {key}"
                    ) from None
                if not isfinite(value) or value < 0:
                    raise ValueError(
                        f"Row {line_number} has an invalid value for {key}; "
                        "values must be finite and non-negative"
                    )
                nutrients[key] = value

            try:
                product_price = float(row["product_price_eur"])
            except (TypeError, ValueError):
                raise ValueError(
                    f"Row {line_number} has an invalid value for product_price_eur"
                ) from None
            if not isfinite(product_price) or product_price < 0:
                raise ValueError(
                    f"Row {line_number} has an invalid product price; "
                    "values must be finite and non-negative"
                )

            try:
                price = float(row["price_per_100g"])
            except (TypeError, ValueError):
                raise ValueError(
                    f"Row {line_number} has an invalid value for price_per_100g"
                ) from None
            if not isfinite(price) or price < 0:
                raise ValueError(
                    f"Row {line_number} has an invalid price; "
                    "values must be finite and non-negative"
                )

            seen_names.add(name.casefold())
            products.append(
                Product(
                    category=category,
                    name=name,
                    nutrients=nutrients,
                    package_size_g=package_size,
                    product_price_eur=product_price,
                    price_per_100g=price,
                )
            )

    if not products:
        raise ValueError("CSV contains no products")
    return products


def format_table(headers: list[str], rows: list[list[str]]) -> str:
    widths = [
        max(len(header), *(len(row[index]) for row in rows))
        for index, header in enumerate(headers)
    ]
    lines = [
        " | ".join(value.ljust(widths[index]) for index, value in enumerate(headers)),
        "-+-".join("-" * width for width in widths),
    ]
    lines.extend(
        " | ".join(value.ljust(widths[index]) for index, value in enumerate(row))
        for row in rows
    )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compare product nutrition per 100 g using a CSV file."
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=Path(__file__).with_name("products.csv"),
        help="path to a product CSV file (default: products.csv)",
    )
    parser.add_argument(
        "--log",
        type=Path,
        default=Path(__file__).with_name("nutrition_history.log"),
        help="path for the prompt and answer history log",
    )
    commands = parser.add_subparsers(dest="command")
    commands.add_parser("web", help="open the visual web app")
    commands.add_parser("interactive", help="choose a category, metric, and direction interactively")
    commands.add_parser("list", help="list products in the CSV")

    compare_parser = commands.add_parser("compare", help="compare selected products")
    compare_parser.add_argument("products", nargs="+", help="product names")

    rank_parser = commands.add_parser(
        "rank", help="rank products in a category across nutrition and price"
    )
    rank_parser.add_argument("category", help="product category, such as cheese")
    rank_parser.add_argument("priority", choices=RANKING_METRICS)
    rank_parser.add_argument("direction", choices=("most", "least"))
    return parser


def prompt_for_choice(prompt: str, choices: list[str]) -> str:
    options = ", ".join(choices)
    while True:
        answer = input(f"{prompt} ({options}): ").strip().casefold()
        if answer in choices:
            return answer
        print(f"Choose one of: {options}")


def prompt_for_numbered_choice(prompt: str, choices: list[str]) -> str:
    print(prompt)
    for number, choice in enumerate(choices, start=1):
        print(f"{number}. {choice}")

    while True:
        answer = input(f"Enter a number (1-{len(choices)}): ").strip()
        if answer.isdigit() and 1 <= int(answer) <= len(choices):
            return choices[int(answer) - 1]
        print(f"Enter a number from 1 to {len(choices)}.")


def build_ranking_choices() -> list[str]:
    return [
        f"{direction} {metric}"
        for metric in RANKING_METRICS
        for direction in ("most", "least")
    ]


def get_metric_value(product: Product, metric_key: str) -> float | None:
    if metric_key == "price_per_100g":
        return product.price_per_100g
    return product.nutrients[metric_key]


def dense_ranks(
    products: list[Product], metric_key: str, highest_first: bool
) -> dict[str, int]:
    products_with_values = [
        (get_metric_value(product, metric_key), product)
        for product in products
        if get_metric_value(product, metric_key) is not None
    ]
    ordered = sorted(
        products_with_values,
        key=lambda item: (
            -item[0] if highest_first else item[0],
            item[1].name.casefold(),
        ),
    )
    ranks = {}
    previous_value = None
    current_rank = 0
    for value, product in ordered:
        if previous_value is None or value != previous_value:
            current_rank += 1
            previous_value = value
        ranks[product.name] = current_rank
    return ranks


def create_ranking_table(
    products: list[Product], category: str, priority: str, direction: str
) -> tuple[str, list[str], list[list[str]]]:
    category_products = [
        product for product in products if product.category.casefold() == category.casefold()
    ]
    if not category_products:
        raise ValueError(f"No products found in category: {category}")

    priority_key, priority_label, _, _ = RANKING_METRICS[priority]
    priority_highest_first = direction == "most"
    overall_ranks = dense_ranks(
        category_products, priority_key, priority_highest_first
    )
    ranked = sorted(
        category_products,
        key=lambda product: (
            get_metric_value(product, priority_key) is None,
            (
                -get_metric_value(product, priority_key)
                if priority_highest_first
                else get_metric_value(product, priority_key)
            )
            if get_metric_value(product, priority_key) is not None
            else 0,
            product.name.casefold(),
        ),
    )

    metric_ranks = {}
    for metric, (key, _, _, preferred_highest) in RANKING_METRICS.items():
        highest_first = (
            priority_highest_first if metric == priority else preferred_highest
        )
        metric_ranks[metric] = dense_ranks(category_products, key, highest_first)

    ordered_metrics = [
        priority,
        *(metric for metric in RANKING_METRICS if metric != priority),
    ]
    rows = []
    for product in ranked:
        row = [str(overall_ranks.get(product.name, "NO-Rank")), product.name]
        for metric in ordered_metrics:
            key, _, unit, _ = RANKING_METRICS[metric]
            value = get_metric_value(product, key)
            if value is None:
                row.append("null (NO-Rank)")
                continue
            formatted_value = (
                f"{value:.2f}" if metric == "price" else f"{value:g} {unit}"
            )
            row.append(f"#{metric_ranks[metric][product.name]} ({formatted_value})")
        row.append(f"€{product.product_price_eur:.2f}/{product.package_size_g:g}g")
        rows.append(row)

    headers = [
        "Priority rank",
        "Product",
        *(RANKING_METRICS[metric][1] for metric in ordered_metrics),
        "Product price / size",
    ]
    direction_label = "most" if priority_highest_first else "least"
    title = f"{category_products[0].category}: {direction_label} {priority_label}"
    return title, headers, rows


def create_answer(args: argparse.Namespace) -> str:
    products = load_products(args.csv)

    if args.command == "list":
        return "\n".join(f"{product.category}: {product.name}" for product in products)

    if args.command == "compare":
        products_by_name = {product.name.casefold(): product for product in products}
        selected = []
        for name in args.products:
            product = products_by_name.get(name.casefold())
            if product is None:
                raise ValueError(f"Unknown product: {name}")
            selected.append(product)

        rows = []
        for key, (label, unit) in NUTRIENTS.items():
            values = [f"{product.nutrients[key]:g} {unit}" for product in selected]
            rows.append([label, *values])
        rows.append(
            [
                "Price / 100 g",
                *(f"{product.price_per_100g:.2f}" for product in selected),
            ]
        )
        rows.append(
            [
                "Product price / size",
                *(
                    f"€{product.product_price_eur:.2f}/{product.package_size_g:g}g"
                    for product in selected
                ),
            ]
        )
        return format_table(["Nutrient", *(product.name for product in selected)], rows)

    title, headers, rows = create_ranking_table(
        products, args.category, args.priority, args.direction
    )
    return f"{title}\n{format_table(headers, rows)}"


def append_history(log_path: Path, prompt: str, answer: str) -> None:
    timestamp = datetime.now(timezone.utc).isoformat()
    with log_path.open("a", encoding="utf-8") as log_file:
        log_file.write(f"[{timestamp}]\nPrompt: {prompt}\nAnswer:\n{answer}\n\n")


def create_web_server(
    csv_path: Path,
    log_path: Path,
    host: str = "0.0.0.0",
    port: int = 8765,
) -> ThreadingHTTPServer:
    products = load_products(csv_path)
    categories = sorted({product.category for product in products}, key=str.casefold)
    page_path = Path(__file__).with_name("nutrition_app.html")

    class NutritionRequestHandler(BaseHTTPRequestHandler):
        def send_json(self, status: int, payload: dict) -> None:
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self) -> None:
            request = urlsplit(self.path)
            if request.path == "/":
                try:
                    data = page_path.read_bytes()
                except OSError as error:
                    self.send_json(500, {"error": str(error)})
                    return
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return

            if request.path == "/api/options":
                self.send_json(
                    200,
                    {
                        "categories": categories,
                        "rankings": build_ranking_choices(),
                        "default_category": categories[0],
                        "default_ranking": "most protein",
                    },
                )
                return

            if request.path == "/api/rank":
                query = parse_qs(request.query)
                category = query.get("category", [""])[0]
                ranking = query.get("ranking", [""])[0]
                if category.casefold() not in {item.casefold() for item in categories}:
                    self.send_json(400, {"error": "Choose a valid product category."})
                    return
                if ranking not in build_ranking_choices():
                    self.send_json(400, {"error": "Choose a valid ranking option."})
                    return

                direction, priority = ranking.split(maxsplit=1)
                try:
                    title, headers, rows = create_ranking_table(
                        products, category, priority, direction
                    )
                except ValueError as error:
                    self.send_json(400, {"error": str(error)})
                    return

                prompt = (
                    f"web category={category} priority={priority} direction={direction}"
                )
                answer = f"{title}\n{format_table(headers, rows)}"
                try:
                    append_history(log_path, prompt, answer)
                except OSError as error:
                    self.send_json(500, {"error": f"Could not write history log: {error}"})
                    return
                self.send_json(
                    200,
                    {"title": title, "headers": headers, "rows": rows},
                )
                return

            self.send_json(404, {"error": "Not found."})

        def log_message(self, format: str, *args) -> None:
            return

    return ThreadingHTTPServer((host, port), NutritionRequestHandler)


def launch_web_app(csv_path: Path, log_path: Path) -> int:
    try:
        server = create_web_server(csv_path, log_path)
    except (OSError, ValueError) as error:
        print(f"Could not start nutrition app: {error}", file=sys.stderr)
        return 1

    url = f"http://localhost:{server.server_port}/"
    print(f"Nutrition comparison app running at {url}", flush=True)
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


def run_interactive(args: argparse.Namespace) -> int:
    try:
        products = load_products(args.csv)
        categories = sorted({product.category for product in products}, key=str.casefold)
        if len(categories) == 1:
            category = categories[0]
        else:
            category_choices = [item.casefold() for item in categories]
            selected_category = prompt_for_choice("Food category", category_choices)
            category = next(
                item for item in categories if item.casefold() == selected_category
            )

        ranking_choices = build_ranking_choices()
        selected_ranking = prompt_for_numbered_choice("Choose ranking:", ranking_choices)
        direction, priority = selected_ranking.split(maxsplit=1)
        prompt = (
            f"interactive category={category} priority={priority} direction={direction}"
        )
        rank_args = argparse.Namespace(
            csv=args.csv,
            command="rank",
            category=category,
            priority=priority,
            direction=direction,
        )
        answer = create_answer(rank_args)
    except (OSError, ValueError, EOFError) as error:
        prompt = "interactive"
        answer = f"Error: {error}"
        exit_code = 1
    else:
        exit_code = 0

    print(answer)
    try:
        append_history(args.log, prompt, answer)
    except OSError as error:
        print(f"Could not write history log: {error}", file=sys.stderr)
        return 1
    return exit_code


def main(argv: list[str] | None = None) -> int:
    requested_args = list(sys.argv[1:] if argv is None else argv)
    parser = build_parser()
    args = parser.parse_args(requested_args)
    if args.command is None or args.command == "web":
        return launch_web_app(args.csv, args.log)
    if args.command == "interactive":
        return run_interactive(args)

    prompt = shlex.join(["nutrition_compare.py", *requested_args])

    try:
        answer = create_answer(args)
    except (OSError, ValueError) as error:
        answer = f"Error: {error}"
        exit_code = 1
    else:
        exit_code = 0

    print(answer)
    try:
        append_history(args.log, prompt, answer)
    except OSError as error:
        print(f"Could not write history log: {error}", file=sys.stderr)
        return 1
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())