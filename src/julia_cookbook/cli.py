from __future__ import annotations

import argparse
import contextlib
import functools
import http.server
import json
import os
import shutil
import tempfile
import threading
import time
from pathlib import Path

from . import __version__
from .builder import build
from .models import RecipeSyntaxError


class ReloadState:
    def __init__(self) -> None:
        self.generation = 0
        self.lock = threading.Lock()

    def advance(self) -> None:
        with self.lock:
            self.generation += 1

    def value(self) -> int:
        with self.lock:
            return self.generation


class DevelopmentHandler(http.server.SimpleHTTPRequestHandler):
    reload_state: ReloadState | None = None

    def do_GET(self) -> None:
        if self.path.split("?", 1)[0] == "/__julia_reload":
            payload = json.dumps({"generation": self.reload_state.value() if self.reload_state else 0}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        super().do_GET()

    def log_request(self, code: int | str = "-", size: int | str = "-") -> None:
        if self.path.split("?", 1)[0] != "/__julia_reload":
            super().log_request(code, size)

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
    serve.add_argument("--watch", action="store_true", help="Rebuild and reload the browser when source files change")
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
    feast_serve.add_argument("--watch", action="store_true", help="Rebuild and reload the browser when source files change")
    return parser


LIVE_RELOAD_SCRIPT = '''<script data-julia-live-reload>
(() => {
  let generation;
  const poll = async () => {
    try {
      const response = await fetch('/__julia_reload', {cache: 'no-store'});
      const current = (await response.json()).generation;
      if (generation === undefined) generation = current;
      else if (current !== generation) location.reload();
    } catch (_) {}
    setTimeout(poll, 500);
  };
  poll();
})();
</script>'''


def _inject_live_reload(output: Path) -> None:
    for path in output.rglob("*.html"):
        text = path.read_text(encoding="utf-8")
        if "data-julia-live-reload" not in text:
            text = text.replace("</body>", f"{LIVE_RELOAD_SCRIPT}</body>")
            path.write_text(text, encoding="utf-8")


def _project_signature(root: Path) -> tuple[tuple[str, int, int], ...]:
    paths = [root / ".julia"]
    for directory, suffixes in ((root / "recipes", {".md"}), (root / "feasts", {".toml", ".md"})):
        if directory.is_dir():
            paths.extend(path for path in directory.rglob("*") if path.is_file() and path.suffix.lower() in suffixes)
    signature = []
    for path in paths:
        if path.exists():
            stat = path.stat()
            signature.append((str(path.relative_to(root)), stat.st_mtime_ns, stat.st_size))
    return tuple(sorted(signature))


def _restore_output(output: Path, backup: Path) -> None:
    if output.exists():
        shutil.rmtree(output)
    if backup.exists():
        shutil.copytree(backup, output)


def _watch(root: Path, output: Path, reload_state: ReloadState, stop: threading.Event) -> None:
    signature = _project_signature(root)
    while not stop.wait(0.25):
        current = _project_signature(root)
        if current == signature:
            continue
        time.sleep(0.2)
        current = _project_signature(root)
        with tempfile.TemporaryDirectory(prefix="julia-watch-") as directory:
            backup = Path(directory) / "build"
            if output.exists():
                shutil.copytree(output, backup)
            try:
                rebuilt_output, recipes = build(root)
                _inject_live_reload(rebuilt_output)
            except Exception as error:
                _restore_output(output, backup)
                signature = current
                print(f"\nRebuild failed: {error}\nWatching for changes...", flush=True)
            else:
                signature = current
                reload_state.advance()
                print(f"\nRebuilt {len(recipes)} recipes", flush=True)


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
    except (RecipeSyntaxError, FileNotFoundError, ValueError) as error:
        print(f"error: {error}")
        return 2
    print(f"Built {len(recipes)} recipes in {output}")
    if args.command == "serve":
        reload_state = ReloadState()
        if getattr(args, "watch", False):
            _inject_live_reload(output)
        handler_class = type("JuliaDevelopmentHandler", (DevelopmentHandler,), {"reload_state": reload_state})
        handler = functools.partial(handler_class, directory=str(output))
        server = http.server.ThreadingHTTPServer(("127.0.0.1", args.port), handler)
        print(f"Serving at http://127.0.0.1:{args.port}")
        stop = threading.Event()
        watcher = None
        if getattr(args, "watch", False):
            root = Path(args.path).resolve()
            watcher = threading.Thread(target=_watch, args=(root, output, reload_state, stop), daemon=True)
            watcher.start()
            print("Watching .julia, recipes/, and feasts/ for changes")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            stop.set()
            with contextlib.suppress(KeyboardInterrupt):
                server.server_close()
                if watcher:
                    watcher.join(timeout=1)
    return 0
