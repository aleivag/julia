from __future__ import annotations

import argparse
import functools
import http.server
import json
import os
from pathlib import Path

from . import __version__
from .builder import build
from .models import RecipeSyntaxError


class DevelopmentHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="julia", description="Build and cook from a local-first cookbook")
    parser.add_argument("--version", action="version", version=f"julia {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)
    build_command = commands.add_parser("build", help="Build the static cookbook")
    build_command.add_argument("path", nargs="?", default=".")
    serve = commands.add_parser("serve", help="Build and serve the cookbook locally")
    serve.add_argument("path", nargs="?", default=".")
    serve.add_argument("--port", type=int, default=8000)
    ingest = commands.add_parser("import-events", help="Import exported cook events into the project")
    ingest.add_argument("export", help="JSON file exported by the web app")
    ingest.add_argument("path", nargs="?", default=".")
    feast = commands.add_parser("feast", help="Build or serve feast documents")
    feast_commands = feast.add_subparsers(dest="feast_command", required=True)
    feast_build = feast_commands.add_parser("build", help="Build cookbook and feast documents")
    feast_build.add_argument("path", nargs="?", default=".")
    feast_serve = feast_commands.add_parser("serve", help="Build and serve feast documents")
    feast_serve.add_argument("path", nargs="?", default=".")
    feast_serve.add_argument("--port", type=int, default=8000)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "import-events":
        source = Path(args.export)
        try:
            data = json.loads(source.read_text(encoding="utf-8"))
            if data.get("schema") != 1 or not isinstance(data.get("events"), list):
                raise ValueError("unsupported Julia export")
        except (OSError, json.JSONDecodeError, ValueError) as error:
            print(f"error: {error}")
            return 2
        target = Path(args.path).resolve() / ".julia-data"
        target.mkdir(parents=True, exist_ok=True)
        destination = target / "cook-events.json"
        existing = json.loads(destination.read_text(encoding="utf-8")) if destination.exists() else {"schema": 1, "events": []}
        merged = {event["id"]: event for event in existing["events"]}
        merged.update({event["id"]: event for event in data["events"]})
        existing["events"] = sorted(merged.values(), key=lambda event: event.get("completedAt", ""))
        destination.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")
        print(f"Imported {len(data['events'])} events; {len(existing['events'])} total in {destination}")
        return 0
    if args.command == "feast":
        args.command = "serve" if args.feast_command == "serve" else "build"
    try:
        output, recipes = build(args.path)
    except (RecipeSyntaxError, FileNotFoundError) as error:
        print(f"error: {error}")
        return 2
    print(f"Built {len(recipes)} recipes in {output}")
    if args.command == "serve":
        handler = functools.partial(DevelopmentHandler, directory=str(output))
        server = http.server.ThreadingHTTPServer(("127.0.0.1", args.port), handler)
        print(f"Serving at http://127.0.0.1:{args.port}")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
    return 0
