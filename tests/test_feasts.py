from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from julia_cookbook.builder import build


ROOT = Path(__file__).parents[1]


class FeastTests(TestCase):
    def test_builds_feast_documents(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "recipes").symlink_to(ROOT / "tests" / "fixtures" / "recipes")
            (root / "feasts").mkdir()
            (root / ".julia").write_text('[site]\ntitle="Test"\noutput="site"\n', encoding="utf-8")
            (root / "feasts" / "supper.toml").write_text('''title = "Supper"
serves = 8

[[dishes]]
course = "Main"
recipe = "scaling"
servings = 8

[[dishes]]
course = "Dessert"
name = "Ice Cream"
description = "A frozen finish."
''', encoding="utf-8")
            output, _ = build(root)
            target = output / "feasts" / "supper"
            for name in ("index.html", "menu.html", "shopping.html", "booklet.html"):
                self.assertTrue((target / name).exists())
            self.assertIn("Scaling Fixture", (target / "menu.html").read_text())
            shopping = (target / "shopping.html").read_text()
            self.assertIn("6 2/3  egg yolks", shopping)
            self.assertIn("Recipes still needed", shopping)
            self.assertIn(">6 2/3</span> egg yolks", (target / "booklet.html").read_text())
