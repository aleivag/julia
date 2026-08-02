from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from julia_cookbook.models import RecipeSyntaxError
from julia_cookbook.parser import parse_recipe


ROOT = Path(__file__).parents[1]
RECIPES = ROOT / "tests" / "fixtures" / "recipes"


class ParserTests(TestCase):
    def test_parses_all_example_recipes(self) -> None:
        recipes = [parse_recipe(path) for path in RECIPES.glob("*.md")]
        self.assertGreaterEqual(len(recipes), 3)
        self.assertIn("indoor-smoke-ribs", {recipe.id for recipe in recipes})
        self.assertTrue(all(recipe.steps for recipe in recipes))

    def test_parses_untitled_step_and_annotations(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "sauce.md"
            path.write_text("""---
title: Sauce
---

== step ==
Heat @milk{1%cup}(warm) in a #pan{} for ~{2%min} at $temp{180%F}.
""", encoding="utf-8")
            recipe = parse_recipe(path)
            step = recipe.steps[0]
            self.assertEqual(step.title, "")
            self.assertEqual(step.ingredients[0].note, "warm")
            self.assertIn('data-ingredient-index="0"', step.html)
            self.assertIn('role="checkbox"', step.html)
            self.assertIn('class="inline-measure"', step.html)
            self.assertIn('>1 cup</span> milk', step.html)
            self.assertEqual(step.timers[0].quantity, "2")
            self.assertEqual(step.parameters[0].unit, "F")

    def test_compound_quantity_is_preserved(self) -> None:
        recipe = parse_recipe(RECIPES / "tk_roast_chicken.md")
        honey = next(item for item in recipe.steps[0].ingredients if item.name == "honey")
        self.assertEqual(honey.quantity, "1/4 cup + 2 tbsp")
        self.assertEqual(honey.unit, "")

    def test_reports_bad_step_marker(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "bad.md"
            path.write_text("---\ntitle: Bad\n---\n== sdtep ==\nNope\n", encoding="utf-8")
            with self.assertRaisesRegex(RecipeSyntaxError, "unknown step marker"):
                parse_recipe(path)

    def test_parses_bakers_ratio_metadata(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "bread.md"
            path.write_text("""---
title: Bread
---
== step dough ==
Mix @flour{500%g}[base=true] and @water{65%bakers}[ratio_of=flour].
""", encoding="utf-8")
            ingredients = parse_recipe(path).steps[0].ingredients
            self.assertEqual(ingredients[0].attributes["base"], "true")
            self.assertEqual(ingredients[1].unit, "bakers")
            self.assertEqual(ingredients[1].attributes["ratio_of"], "flour")

    def test_parses_subrecipe_reference(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "ceviche.md"
            path.write_text("""---
title: Ceviche
---
== step assemble ==
Mix @recipe{leche-de-tigre}{2%cups} with @salmon{1%lb}.
""", encoding="utf-8")
            step = parse_recipe(path).steps[0]
            self.assertEqual(step.subrecipes[0].name, "leche-de-tigre")
            self.assertEqual(step.subrecipes[0].quantity, "2")
            self.assertIn("../recipes/leche-de-tigre.html", step.html)

    def test_parses_step_outputs_and_inputs_separately_from_ingredients(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "custard.md"
            path.write_text("""---
title: Custard
---
== step separate ==
Separate @large eggs{5} into =>egg yolks{5} and =>egg whites{5}.
== step mix ==
Whisk ^egg yolks{5} with @cream{2%cups} to produce =>custard{}.
""", encoding="utf-8")

            recipe = parse_recipe(path)

            self.assertEqual([item.name for item in recipe.steps[0].ingredients], ["large eggs"])
            self.assertEqual([item.name for item in recipe.steps[0].outputs], ["egg yolks", "egg whites"])
            self.assertEqual([item.name for item in recipe.steps[1].inputs], ["egg yolks"])
            self.assertEqual([item.name for item in recipe.steps[1].outputs], ["custard"])
            self.assertIn('data-kind="output"', recipe.steps[0].html)
            self.assertIn('data-kind="input"', recipe.steps[1].html)

    def test_parses_step_choice_attributes(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "dough.md"
            path.write_text("""---
title: Dough
---
== step prepare yeast [choice=yeast, option=instant, default=true] ==
Mix @instant yeast{1%g} to produce =>yeast water{}.
""", encoding="utf-8")

            step = parse_recipe(path).steps[0]

            self.assertEqual(step.title, "prepare yeast")
            self.assertEqual(step.attributes, {"choice": "yeast", "option": "instant", "default": "true"})

    def test_renders_ordered_and_unordered_lists(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "lists.md"
            path.write_text("""---
title: Lists
---

1. First reason.
2. Second reason wraps
   onto another line.

== step serve ==
- Add @salt{}.
- Add pepper.
""", encoding="utf-8")

            recipe = parse_recipe(path)

            self.assertIn("<ol><li>First reason.</li><li>Second reason wraps onto another line.</li></ol>", recipe.blurb_html)
            self.assertIn("<ul><li>Add", recipe.steps[0].html)
            self.assertEqual(recipe.steps[0].ingredients[0].name, "salt")

    def test_renders_safe_youtube_embed_with_options(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "video.md"
            path.write_text("""---
title: Video
---

!youtube{LysF3BGtXt4}[start=1m30s, end=3m, autoplay=false, mute=true, loop=true, controls=false, captions=true, title=Prime rib technique]

== step serve ==
Serve.
""", encoding="utf-8")

            html = parse_recipe(path).blurb_html
            self.assertIn('class="video-embed"', html)
            self.assertIn("youtube-nocookie.com/embed/LysF3BGtXt4", html)
            self.assertIn("start=90&amp;end=180&amp;autoplay=0&amp;mute=1&amp;controls=0", html)
            self.assertIn("loop=1&amp;playlist=LysF3BGtXt4&amp;cc_load_policy=1", html)
            self.assertIn('title="Prime rib technique"', html)

    def test_rejects_unknown_youtube_options(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "video.md"
            path.write_text("---\ntitle: Video\n---\n!youtube{LysF3BGtXt4}[color=red]\n== step ==\nServe.\n", encoding="utf-8")
            with self.assertRaisesRegex(RecipeSyntaxError, "unknown YouTube option 'color'"):
                parse_recipe(path)
