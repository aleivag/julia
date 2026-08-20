from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from julia_cookbook.dependencies import validate_step_products, walk_recipe
from julia_cookbook.parser import parse_recipe


class DependencyTests(TestCase):
    def test_expands_nested_dependencies_and_scales_each_level(self) -> None:
        root = Path(__file__).parent / "fixtures" / "recipes"
        recipes = {
            recipe.id: recipe
            for recipe in (parse_recipe(root / name) for name in ("bechamel.md", "mornay.md", "croque.md"))
        }

        expanded = walk_recipe(recipes["croque"], 1.0, recipes)

        self.assertEqual([recipe.id for recipe, _ in expanded], ["bechamel", "mornay", "croque"])
        self.assertEqual([scale for _, scale in expanded], [0.5, 0.5, 1.0])

    def test_fixed_dependency_does_not_follow_parent_scale(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "cordial.md").write_text("""---
title: Cordial
yield: 1 batch
---
== step mix ==
Mix @juice{830%g}.
""")
            (root / "cocktail.md").write_text("""---
title: Cocktail
yield: 1 cocktail
---
== step cordial ==
Prepare @recipe{cordial}{1%batch}[scale=false].
== step mix ==
Add @spirit{25%ml}.
""")
            recipes = {name: parse_recipe(root / f"{name}.md") for name in ("cordial", "cocktail")}

            expanded = walk_recipe(recipes["cocktail"], 6.0, recipes)

            self.assertEqual([recipe.id for recipe, _ in expanded], ["cordial", "cocktail"])
            self.assertEqual([scale for _, scale in expanded], [1.0, 6.0])

    def test_reports_circular_dependency_chain(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "a.md").write_text("---\ntitle: A\nyield: 1 batch\n---\n== step ==\nUse @recipe{b}{1%batch}.\n")
            (root / "b.md").write_text("---\ntitle: B\nyield: 1 batch\n---\n== step ==\nUse @recipe{a}{1%batch}.\n")
            recipes = {name: parse_recipe(root / f"{name}.md") for name in ("a", "b")}

            with self.assertRaisesRegex(ValueError, "circular recipe dependency: a -> b -> a"):
                walk_recipe(recipes["a"], 1.0, recipes)

    def test_rejects_step_input_without_an_earlier_output(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "custard.md"
            path.write_text("---\ntitle: Custard\n---\n== step mix ==\nWhisk ^egg yolks{5}.\n")

            with self.assertRaisesRegex(ValueError, "has no output from an earlier step"):
                validate_step_products(parse_recipe(path))

    def test_allows_choice_options_with_the_same_output_contract(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "dough.md"
            path.write_text("""---
title: Dough
---
== step yeast [choice=yeast, option=instant, default=true] ==
Use @instant yeast{1%g} to produce =>prepared yeast{}.
== step yeast [choice=yeast, option=fresh] ==
Use @fresh yeast{3%g} to produce =>prepared yeast{}.
== step mix ==
Mix ^prepared yeast{} with @flour{100%g}.
""")

            validate_step_products(parse_recipe(path))
