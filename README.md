# Software-construction

## Nutrition comparison

A small command-line tool for ranking products within a food category by a
chosen priority. It uses only the Python standard library and reads product data
from a CSV file.

The included `products.csv` contains the four linked cheese products and example
prices from the supplied S-kaupat screenshots. Product prices are shown per
package with its size (for example, `€2.49/140g`) as well as normalized per 100 g
for fair price ranking. Prices can vary by store. Fiber is blank where the
product listing did not provide a value; the app displays it as
`null (NO-Rank)`.

Product listings:

- [Coop mozzarella juustoraaste 150 g](https://www.s-kaupat.fi/tuote/coop-mozzarella-juustoraaste-150-g/7340191149779)
- [Valio Hyva suomalainen Arki juustoraaste 170 g](https://www.s-kaupat.fi/tuote/valio-hyva-suomalainen-arkir-juustoraaste-e170-g/6408430341917)
- [Kuusamon Juusto Erankavija 10% raaste 140 g](https://www.s-kaupat.fi/tuote/kuusamon-juusto-erankavija-10-raaste-140-g/6405020031777)
- [Xtra juustoraaste 15% rasvaa 500 g](https://www.s-kaupat.fi/tuote/xtra-juustoraaste-15-rasvaa-500g/7340011300106)

```bash
python3 nutrition_compare.py
python3 nutrition_compare.py list
python3 nutrition_compare.py rank cheese protein most
python3 nutrition_compare.py rank cheese price least
```

Running with no command starts the visual app and opens it in your browser at
`http://localhost:8765`. Click the hamburger button to open the selection popup,
choose a category, and select one of the numbered ranking options. Choices cover
most and least calories, carbohydrates, protein, fat, fiber, and price. Stop the
server with Ctrl+C. For terminal prompts instead, run
`python3 nutrition_compare.py interactive`.

Each ranking filters to the requested category, orders products by the chosen
priority, and displays the value and rank for carbohydrates, protein, fat, fiber,
calories, and price per 100 g, plus the product's package price. Ties share a
rank. The default metric order is calories, carbohydrates, protein, fat, fiber,
then price. Other metrics use these defaults: lower calories, carbohydrates,
fat, and price are better; higher protein and fiber are better.

To use another CSV, pass `--csv` before the command:

```bash
python3 nutrition_compare.py --csv my_products.csv list
```

Each command and its displayed result is appended to `nutrition_history.log`.
Choose a different history file with `--log /path/to/history.log`. The log may
contain product names and nutrition values, so store it accordingly.

CSV files need `category`, `name`, `package_size_g`, `product_price_eur`, and
`price_per_100g`, plus the nutrition columns `calories_kcal`, `protein_g`,
`carbohydrate_g`, `sugars_g`, `fat_g`, `saturated_fat_g`, `fiber_g`, and
`sodium_mg`. Nutrition values are per 100 g, and `fiber_g` may be left blank when
unknown. Run the tests with `python3 -m unittest`.
