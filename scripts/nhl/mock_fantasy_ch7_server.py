#!/usr/bin/env python3
"""Local Ch7 fantasy board for /pro/nhl/fantasy screenshots."""

from __future__ import annotations

import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))

from src.services.nhl_season_engine.nhl_fantasy import (  # noqa: E402
    FANTASY_VERSION,
    SCORING_MAP,
    SCORING_PROFILE,
    build_fantasy_board,
)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        u = urlparse(self.path)
        path = u.path.rstrip("/") or "/"
        if path == "/nhl/fantasy/board":
            qs = parse_qs(u.query)
            view = (qs.get("view") or ["season"])[0]
            lim = int((qs.get("limit") or ["120"])[0])
            team = (qs.get("team") or [None])[0]
            board = build_fantasy_board(view=view, team=team, limit=lim)
            body = json.dumps(
                {
                    "fantasy_version": board.get("fantasy_version") or FANTASY_VERSION,
                    "engine_version": board.get("engine_version"),
                    "object": "PlayerProjection",
                    "scoring_profile": board.get("scoring_profile") or SCORING_PROFILE,
                    "scoring_map": board.get("scoring_map") or dict(SCORING_MAP),
                    "view": board.get("view"),
                    "count": board.get("count") or 0,
                    "rows": board.get("rows") or [],
                    "season_games": board.get("season_games"),
                    "max_team_g_drift": board.get("max_team_g_drift"),
                    "NHL_TEAM_REBASE_RESIDUAL_CAP": board.get(
                        "NHL_TEAM_REBASE_RESIDUAL_CAP"
                    ),
                    "NHL_TEAM_CARRY_SHRINK_unchanged": board.get(
                        "NHL_TEAM_CARRY_SHRINK_unchanged"
                    ),
                    "goalie_start_share_ok": board.get("goalie_start_share_ok"),
                    "does_not": board.get("does_not") or [],
                    "phase": "ch7_fantasy",
                    "source": "season_engine_ch7",
                    "message": board.get("message"),
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
