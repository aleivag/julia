from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
import json

from julia_cookbook.builder import _search_key, build


ROOT = Path(__file__).parents[1]
RECIPES = ROOT / "tests" / "fixtures" / "recipes"
GUIDES = ROOT / "tests" / "fixtures" / "guides"


class BuilderTests(TestCase):
    def test_search_key_is_case_and_diacritic_insensitive(self) -> None:
        self.assertEqual(_search_key("Crème Brûlée"), "creme brulee")
        self.assertEqual(_search_key("CRÈME"), "creme")

    def test_builds_static_site(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "recipes").symlink_to(RECIPES)
            (root / "guides").symlink_to(GUIDES)
            (root / ".julia").write_text('[site]\ntitle="Test"\noutput="site"\n[author]\nname="Cook"\ninstagram="@cook"\n', encoding="utf-8")
            output, recipes = build(root)
            self.assertGreaterEqual(len(recipes), 3)
            self.assertTrue((output / "index.html").exists())
            self.assertTrue((output / "assets" / "app.js").exists())
            self.assertTrue((output / "assets" / "icon.svg").exists())
            self.assertTrue((output / "sw.js").exists())
            self.assertTrue((output / "sources" / "indoor-smoke-ribs.html").exists())
            self.assertTrue((output / "guides" / "turkey.html").exists())
            self.assertTrue((output / "guides" / "index.html").exists())
            self.assertTrue((output / "feasts" / "index.html").exists())
            guide_html = (output / "guides" / "turkey.html").read_text(encoding="utf-8")
            self.assertIn('data-page="guide"', guide_html)
            self.assertIn('data-guide-unit="international"', guide_html)
            self.assertIn('<table>', guide_html)
            self.assertIn('../recipes/indoor-smoke-ribs.html', guide_html)
            index_html = (output / "index.html").read_text(encoding="utf-8")
            guides_index = (output / "guides" / "index.html").read_text(encoding="utf-8")
            self.assertNotIn('href="guides/turkey.html"', index_html)
            self.assertIn('href="turkey.html"', guides_index)
            self.assertIn('href="guides/index.html"', index_html)
            self.assertIn('href="../guides/index.html" aria-current="page">Guides</a>', guide_html)
            html = (output / "recipes" / "indoor-smoke-ribs.html").read_text(encoding="utf-8")
            self.assertIn('href="../index.html" aria-current="page">Recipes</a>', html)
            self.assertIn("Make this recipe", html)
            self.assertIn("Show source", html)
            self.assertIn("data-scale-anchor", html)
            self.assertIn('data-anchor-original="2"', html)
            self.assertIn("By Cook", html)
            self.assertIn("https://www.instagram.com/cook/", html)
            self.assertIn('aria-label="Instagram"', html)
            self.assertIn('href="https://github.com/aleivag/julia"', html)
            scaling = (output / "recipes" / "scaling.html").read_text(encoding="utf-8")
            self.assertIn('data-anchor-original="5"', scaling)
            self.assertIn('data-anchor-original="6"', scaling)
            self.assertIn('<details class="scale-panel">', scaling)
            self.assertIn("Scale &amp; units", scaling)
            self.assertIn('"units":"international"', scaling)
            self.assertIn("A short note introducing the recipe", scaling)
            self.assertIn('../recipes/meringue.html', scaling)
            self.assertIn('../index.html?q=egg-whites', scaling)
            self.assertIn('<section class="variations">', scaling)
            self.assertIn('vanilla-custard.html', scaling)
            self.assertIn('data-kind="timer"', html)
            payloads = json.loads((output / "recipes.json").read_text(encoding="utf-8"))
            croque = next(recipe for recipe in payloads if recipe["id"] == "croque")
            ingredients = croque["shoppingIngredients"]
            self.assertEqual(
                [item["sourceId"] for item in ingredients],
                ["bechamel", "bechamel", "bechamel", "mornay", "croque"],
            )
            self.assertEqual(ingredients[0]["quantity"], "1")
            self.assertEqual(ingredients[3]["quantity"], "2")
            croque_html = (output / "recipes" / "croque.html").read_text(encoding="utf-8")
            self.assertEqual(croque_html.count('class="recipe-step dependency-step"'), 2)
            self.assertIn("Included preparation", croque_html)
            self.assertIn("Bechamel", croque_html)
            self.assertIn('href="mornay.html"', croque_html)
            self.assertIn('<span class="step-number">1.1</span>', croque_html)
            self.assertIn('<span class="step-number">1.1.1</span>', croque_html)
            self.assertIn('<span class="step-number">1.1.2</span>', croque_html)
            self.assertIn('<span class="step-number">1.2</span>', croque_html)
            self.assertEqual(croque_html.count('data-check="dependency-ingredient"'), 4)
            self.assertIn('data-embedded-check="croque/step-1/mornay/step-2:ingredient:0"', croque_html)
            self.assertIn('data-embedded-check="croque/step-1/mornay/step-1/bechamel/step-1:ingredient:0"', croque_html)
            self.assertIn('data-embedded-toggle="croque/step-1/mornay/step-1/bechamel/step-1:ingredient:0"', croque_html)
            products = next(recipe for recipe in payloads if recipe["id"] == "step-products")
            self.assertEqual(
                [item["name"] for item in products["shoppingIngredients"]],
                ["eggs", "sugar"],
            )
            product_html = (output / "recipes" / "step-products.html").read_text(encoding="utf-8")
            self.assertIn("From step 1, separate", product_html)
            self.assertIn("From step 2, mix", product_html)
            self.assertEqual(product_html.count("From earlier steps"), 2)
            self.assertEqual(product_html.count("Produces"), 2)
            self.assertEqual(product_html.count('data-check="input"'), 2)
            self.assertIn('data-input-index="0"', product_html)
            self.assertIn('href="#step-1">From step 1, separate</a>', product_html)
            self.assertIn('href="#step-2">From step 2, mix</a>', product_html)
            self.assertIn('<span class="input-origin">(from step 1)</span>', product_html)
            self.assertIn('<span class="input-origin">(from step 2)</span>', product_html)
            self.assertIn('<span class="measure"></span> <span>custard</span>', product_html)
            self.assertNotIn('<span class="measure" data-quantity="" data-unit="">as needed</span> <span>custard</span>', product_html)
            choice_html = (output / "recipes" / "choice.html").read_text(encoding="utf-8")
            self.assertIn('data-choice-step="yeast"', choice_html)
            self.assertIn('data-choice-panel="instant"', choice_html)
            self.assertIn('data-choice-panel="fresh" hidden', choice_html)
            self.assertEqual(choice_html.count('class="choice-dependencies"'), 2)
            self.assertIn('id="choice-instant-embedded-step-1-1"', choice_html)
            self.assertIn('id="choice-fresh-embedded-step-1-1"', choice_html)
            self.assertEqual(choice_html.count('data-ratio-options="65|70|75"'), 2)
            choice_payload = next(recipe for recipe in payloads if recipe["id"] == "choice")
            choice_items = [item for item in choice_payload["shoppingIngredients"] if item.get("choice")]
            self.assertEqual(
                [(item["name"], item["option"], item["default"]) for item in choice_items],
                [
                    ("instant yeast", "instant", True), ("water", "instant", True),
                    ("fresh yeast", "fresh", False), ("water", "fresh", False),
                ],
            )
            compound_html = (output / "recipes" / "compound-yield.html").read_text(encoding="utf-8")
            self.assertIn("data-compound-yield", compound_html)
            self.assertIn('data-original-count="4"', compound_html)
            self.assertIn('data-original-each="100"', compound_html)
            self.assertIn('data-scale-mode="count"', compound_html)
            self.assertIn('data-bakers-formula', compound_html)
            self.assertIn('data-original-flour="240"', compound_html)
            self.assertIn('<option value="70">70%</option>', compound_html)
