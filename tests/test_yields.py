from unittest import TestCase

from julia_cookbook.yields import parse_yield


class YieldTests(TestCase):
    def test_parses_approximate_each_weight(self) -> None:
        spec = parse_yield("4 dough balls [each=~250 g]")

        self.assertEqual((spec.count, spec.item, spec.each, spec.unit), (4, "dough balls", 250, "g"))
        self.assertTrue(spec.approximate)
        self.assertEqual(spec.total, 1000)

    def test_parses_ascii_and_unicode_tolerances(self) -> None:
        for value in ("4 dough balls [each=250 g +/- 2 g]", "4 dough balls [each=250 g ± 2 g]"):
            with self.subTest(value=value):
                spec = parse_yield(value)
                self.assertEqual(spec.tolerance, 2)
                self.assertFalse(spec.approximate)
