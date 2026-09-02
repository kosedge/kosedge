#!/usr/bin/env python3
"""Local dark Ch6 props board for /pro/nhl/props screenshots."""

from __future__ import annotations

import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))

from src.services.nhl_season_engine.nhl_props import (  # noqa: E402
    PROPS_VERSION,
    build_dark_props_board,
)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        u = urlparse(self.path)
        path = u.path.rstrip("/") or "/"
        if path == "/nhl/props/board":
            qs = parse_qs(u.query)
            lim = int((qs.get("limit") or ["40"])[0])
            board = build_dark_props_board(limit=lim)
            lines = board.get("lines") or []
            body = json.dumps(
                {
                    "as_of_date": board.get("as_of_date"),
                    "model_version": board.get("props_version") or PROPS_VERSION,
                    "worker_build_id": PROPS_VERSION,
                    "count": len(lines),
                    "lines": lines,
                    "play_n": 0,
                    "lean_n": 0,
                    "phase": "ch6_dark",
                    "dark_only": True,
                    "STARTER_GATE": board.get("STARTER_GATE"),
                }
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if path == "/health":
            body = b'{"ok":true}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_response(404)
        self.end_headers()

    def log_message(self, *_args) -> None:
        return


if __name__ == "__main__":
    print("listening 8000", flush=True)
    HTTPServer(("127.0.0.1", 8000), Handler).serve_forever()
