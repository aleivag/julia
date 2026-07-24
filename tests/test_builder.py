from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from julia_cookbook.builder import build


ROOT = Path(__file__).parents[1]
RECIPES = ROOT / "tests" / "fixtures" / "recipes"


class BuilderTests(TestCase):
    def test_builds_static_site(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "recipes").symlink_to(RECIPES)
            (root / ".julia").write_text('[site]\ntitle="Test"\noutput="site"\n[author]\nname="Cook"\ninstagram="@cook"\n', encoding="utf-8")
            output, recipes = build(root)
            self.assertGreaterEqual(len(recipes), 3)
            self.assertTrue((output / "index.html").exists())
            self.assertTrue((output / "assets" / "app.js").exists())
            self.assertTrue((output / "assets" / "icon.svg").exists())
            self.assertTrue((output / "sw.js").exists())
            self.assertTrue((output / "sources" / "indoor-smoke-ribs.html").exists())
            html = (output / "recipes" / "indoor-smoke-ribs.html").read_text(encoding="utf-8")
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
            self.assertIn('data-kind="timer"', html)
