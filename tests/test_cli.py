import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from julia_cookbook.cli import main


class CliTests(TestCase):
    def test_imports_and_deduplicates_events(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            export = root / "export.json"
            export.write_text(json.dumps({"schema": 1, "events": [{"id": "event-1", "completedAt": "2026-01-01"}]}), encoding="utf-8")
            self.assertEqual(main(["import-events", str(export), str(root)]), 0)
            self.assertEqual(main(["import-events", str(export), str(root)]), 0)
            saved = json.loads((root / ".julia-data" / "cook-events.json").read_text(encoding="utf-8"))
            self.assertEqual(len(saved["events"]), 1)
