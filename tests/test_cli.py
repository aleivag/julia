import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from julia_cookbook.cli import _inject_live_reload, _parser, _project_signature, main


class CliTests(TestCase):
    def test_watch_flag_is_available_for_both_serve_commands(self) -> None:
        self.assertTrue(_parser().parse_args(["serve", "--watch"]).watch)
        self.assertTrue(_parser().parse_args(["feast", "serve", "--watch"]).watch)

    def test_watch_signature_tracks_recipe_changes(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            recipes = root / "recipes"
            recipes.mkdir()
            recipe = recipes / "soup.md"
            recipe.write_text("first", encoding="utf-8")
            before = _project_signature(root)
            recipe.write_text("second version", encoding="utf-8")
            self.assertNotEqual(before, _project_signature(root))

    def test_live_reload_is_injected_once(self) -> None:
        with TemporaryDirectory() as directory:
            output = Path(directory)
            page = output / "index.html"
            page.write_text("<html><body>Hello</body></html>", encoding="utf-8")
            _inject_live_reload(output)
            _inject_live_reload(output)
            self.assertEqual(page.read_text(encoding="utf-8").count("data-julia-live-reload"), 1)

    def test_imports_and_deduplicates_events(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            export = root / "export.json"
            export.write_text(json.dumps({"schema": 1, "events": [{"id": "event-1", "completedAt": "2026-01-01"}]}), encoding="utf-8")
            self.assertEqual(main(["import-events", str(export), str(root)]), 0)
            self.assertEqual(main(["import-events", str(export), str(root)]), 0)
            saved = json.loads((root / ".julia-data" / "cook-events.json").read_text(encoding="utf-8"))
            self.assertEqual(len(saved["events"]), 1)
