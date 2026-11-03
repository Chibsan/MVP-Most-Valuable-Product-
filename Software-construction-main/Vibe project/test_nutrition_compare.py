import contextlib
import csv
import io
import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen
from unittest.mock import patch

from nutrition_compare import create_web_server, main


HEADERS = [
    "category",
    "name",
    "package_size_g",
    "product_price_eur",
    "price_per_100g",
    "calories_kcal",
    "protein_g",
    "carbohydrate_g",
    "sugars_g",
    "fat_g",
    "saturated_fat_g",
    "fiber_g",
    "sodium_mg",
]


class NutritionCompareTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.csv_path = Path(self.temporary_directory.name) / "products.csv"
        self.log_path = Path(self.temporary_directory.name) / "history.log"
        with self.csv_path.open("w", encoding="utf-8", newline="") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=HEADERS)
            writer.writeheader()
            writer.writerow(
                {
                    "category": "cheese",
                    "name": "Alpha",
                    "package_size_g": 100,
                    "product_price_eur": 5.0,
                    "price_per_100g": 5.0,
                    "calories_kcal": 100,
                    "protein_g": 4,
                    "carbohydrate_g": 10,
                    "sugars_g": 2,
                    "fat_g": 3,
                    "saturated_fat_g": 1,
                    "fiber_g": 2,
                    "sodium_mg": 50,
                }
            )
            writer.writerow(
                {
                    "category": "cheese",
                    "name": "Beta",
                    "package_size_g": 100,
                    "product_price_eur": 4.5,
                    "price_per_100g": 4.5,
                    "calories_kcal": 200,
                    "protein_g": 8,
                    "carbohydrate_g": 20,
                    "sugars_g": 4,
                    "fat_g": 6,
                    "saturated_fat_g": 2,
                    "fiber_g": 4,
                    "sodium_mg": 100,
                }
            )
            writer.writerow(
                {
                    "category": "cereal",
                    "name": "Gamma",
                    "package_size_g": 100,
                    "product_price_eur": 3.0,
                    "price_per_100g": 3.0,
                    "calories_kcal": 150,
                    "protein_g": 6,
                    "carbohydrate_g": 25,
                    "sugars_g": 5,
                    "fat_g": 2,
                    "saturated_fat_g": 0.5,
                    "fiber_g": 3,
                    "sodium_mg": 80,
                }
            )

    def tearDown(self):
        self.temporary_directory.cleanup()

    def command(self, *arguments):
        return [
            "--csv",
            str(self.csv_path),
            "--log",
            str(self.log_path),
            *arguments,
        ]

    def test_compare_displays_and_logs_selected_products(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            main(self.command("compare", "Alpha", "Beta"))

        self.assertIn("Alpha", output.getvalue())
        self.assertIn("Beta", output.getvalue())
        self.assertIn("4 g", output.getvalue())
        self.assertIn("Product price / size", output.getvalue())
        self.assertIn("€5.00/100g", output.getvalue())
        history = self.log_path.read_text(encoding="utf-8")
        self.assertIn("Prompt: nutrition_compare.py", history)
        self.assertIn("compare Alpha Beta", history)
        self.assertIn("Answer:", history)
        self.assertIn("4 g", history)

    def test_rank_filters_category_and_ranks_every_metric(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            main(self.command("rank", "cheese", "protein", "most"))

        result = output.getvalue()
        self.assertLess(result.index("Beta"), result.index("Alpha"))
        self.assertNotIn("Gamma", result)
        header = result.splitlines()[1]
        metric_columns = [
            header.index("Protein"),
            header.index("Calories"),
            header.index("Carbohydrates"),
            header.index("Fat"),
            header.index("Fiber"),
            header.index("Price / 100 g"),
        ]
        self.assertEqual(metric_columns, sorted(metric_columns))
        self.assertIn("#1 (8 g)", result)
        self.assertIn("#1 (4.50)", result)
        self.assertIn("Product price / size", result)
        self.assertIn("€4.50/100g", result)

    def test_invalid_csv_value_is_reported_and_logged(self):
        with self.csv_path.open("a", encoding="utf-8") as csv_file:
            csv_file.write("cheese,Invalid cheese,100,1.00,1.00,-1,1,1,1,1,1,1,1\n")

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            exit_code = main(self.command("list"))

        self.assertEqual(exit_code, 1)
        self.assertIn("non-negative", output.getvalue())
        self.assertIn("non-negative", self.log_path.read_text(encoding="utf-8"))

    def test_missing_fiber_displays_null_without_a_rank(self):
        with self.csv_path.open("w", encoding="utf-8", newline="") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=HEADERS)
            writer.writeheader()
            writer.writerow(
                {
                    "category": "cheese",
                    "name": "Missing fiber",
                    "package_size_g": 100,
                    "product_price_eur": 1,
                    "price_per_100g": 1,
                    "calories_kcal": 100,
                    "protein_g": 5,
                    "carbohydrate_g": 1,
                    "sugars_g": 0,
                    "fat_g": 2,
                    "saturated_fat_g": 1,
                    "fiber_g": "",
                    "sodium_mg": 25,
                }
            )
            writer.writerow(
                {
                    "category": "cheese",
                    "name": "Fiber listed",
                    "package_size_g": 100,
                    "product_price_eur": 1.2,
                    "price_per_100g": 1.2,
                    "calories_kcal": 110,
                    "protein_g": 4,
                    "carbohydrate_g": 2,
                    "sugars_g": 0,
                    "fat_g": 3,
                    "saturated_fat_g": 1,
                    "fiber_g": 1,
                    "sodium_mg": 30,
                }
            )

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            main(self.command("rank", "cheese", "fiber", "most"))

        result = output.getvalue()
        self.assertIn("null (NO-Rank)", result)
        self.assertIn("NO-Rank", result)
        self.assertLess(result.index("Fiber listed"), result.index("Missing fiber"))

    def test_running_without_command_prompts_for_combined_ranking_choice(self):
        output = io.StringIO()
        with patch("builtins.input", side_effect=["cheese", "5"]):
            with contextlib.redirect_stdout(output):
                exit_code = main(self.command("interactive"))

        self.assertEqual(exit_code, 0)
        self.assertIn("cheese: most Protein", output.getvalue())
        self.assertIn("1. most calories\n2. least calories", output.getvalue())
        self.assertIn("3. most carbohydrates\n4. least carbohydrates", output.getvalue())
        self.assertIn("5. most protein\n6. least protein", output.getvalue())
        self.assertIn("11. most price\n12. least price", output.getvalue())
        self.assertIn("Prompt: interactive category=cheese priority=protein direction=most", self.log_path.read_text(encoding="utf-8"))

    def test_web_app_serves_clickable_page_and_ranking_api(self):
        server = create_web_server(
            self.csv_path,
            self.log_path,
            host="127.0.0.1",
            port=0,
        )
        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.start()
        base_url = f"http://127.0.0.1:{server.server_port}"
        try:
            with urlopen(f"{base_url}/") as response:
                page = response.read().decode("utf-8")
            self.assertIn('aria-label="Open ranking choices"', page)
            self.assertIn("selection-dialog", page)

            with urlopen(f"{base_url}/api/options") as response:
                options = json.load(response)
            self.assertIn("most calories", options["rankings"])
            self.assertIn(options["default_category"], {"cheese", "cereal"})

            query = urlencode({"category": "cheese", "ranking": "most protein"})
            with urlopen(f"{base_url}/api/rank?{query}") as response:
                ranking = json.load(response)
            self.assertEqual(ranking["title"], "cheese: most Protein")
            self.assertIn("Product price / size", ranking["headers"])
            self.assertTrue(any("Beta" in row for row in ranking["rows"]))
            self.assertIn("web", self.log_path.read_text(encoding="utf-8"))
        finally:
            server.shutdown()
            server.server_close()
            server_thread.join(timeout=2)

if __name__ == "__main__":
    unittest.main()