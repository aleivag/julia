from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from julia_cookbook.guides import parse_guide


class GuideTests(TestCase):
    def test_parses_tables_and_smart_measurements(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "turkey.md"
            path.write_text("""---
title: Turkey
---
## Whole bird
| Weight | Temperature | Time |
|---|---|---|
| $weight{8-12%lb} | $temp{325%F} | $time{2.75-3%hours} |
""", encoding="utf-8")

            guide = parse_guide(path)

            self.assertIn("<table>", guide.html)
            self.assertIn('data-name="weight"', guide.html)
            self.assertIn('data-quantity="8-12"', guide.html)
            self.assertEqual([item.name for item in guide.parameters], ["weight", "temp", "time"])
