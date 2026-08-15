#!/usr/bin/env python3
"""Pull CFB FBS game opens/closes into the warehouse odds lake.

Usage:
  python scripts/cfb/pull_cfb_game_odds.py
  python scripts/cfb/pull_cfb_game_odds.py --weeks 0-2
  python scripts/cfb/pull_cfb_game_odds.py --repo-fallback

Sport key: americanfootball_ncaaf (The Odds API).
Markets: spreads, totals, h2h. No props. No KEI. used_in_spread stays false.

Writes snapshots under HD ``/Volumes/KosEdgeData/clean/odds/cfb/live/`` when
mounted, else gitignored ``data/cfb/warehouse/clean/odds_cfb/live/``.
Does not dump into Railway Postgres.

Empty API results are recorded honestly (n_opens=0, n_closes=0).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))

ENV_CANDIDATES = [
    ROOT / "apps" / "web" / ".env.local",
    ROOT / "apps" / "web" / ".env",
    Path("/Users/ryankos/kosedge/apps/web/.env.local"),
    Path("/Users/ryankos/kosedge/apps/web/.env"),
    ROOT / ".env",
]


def _load_odds_key() -> None:
    if (os.environ.get("ODDS_API_KEY") or "").strip():
        return
    if (os.environ.get("ODDS_API_KEY_BACKUP") or "").strip():
        return
    for path in ENV_CANDIDATES:
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("ODDS_API_KEY=") and not line.startswith("ODDS_API_KEY_"):
                key = line.split("=", 1)[1].strip().strip('"').strip("'")
                if key:
                    os.environ["ODDS_API_KEY"] = key
                    return


def _parse_weeks(raw: str) -> list[int]:
    raw = (raw or "").strip()
    if not raw:
        return []
    if "-" in raw and "," not in raw:
        a, b = raw.split("-", 1)
        return list(range(int(a), int(b) + 1))
    return [int(s.strip()) for s in raw.split(",") if s.strip()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--weeks", default="0-2", help="Slate weeks to count as opens (default 0-2)")
    parser.add_argument("--repo-fallback", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="Do not call Odds API")
    parser.add_argument(
        "--replay",
        default="",
        help="Re-map a saved snapshots JSON (no API call)",
    )
    args = parser.parse_args(argv)

    os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
    from src.services.cfb_warehouse.open_ingest import (  # noqa: E402
        USED_IN_SPREAD,
        fetch_ncaaf_odds,
        ingest_events,
        load_official_slate_games,
    )

    weeks = _parse_weeks(args.weeks)
    slate = load_official_slate_games(2026)
    prefer_hd = not args.repo_fallback

    if args.dry_run:
        written = ingest_events(
            [],
            slate,
            weeks=weeks or None,
            prefer_hd=prefer_hd,
            note="dry-run — no Odds API call",
        )
        print(json.dumps({**written.get("inventory", written), "dry_run": True}, indent=2, default=str))
        return 0

    if args.replay:
        raw = json.loads(Path(args.replay).read_text(encoding="utf-8"))
        events = raw if isinstance(raw, list) else raw.get("events") or []
        written = ingest_events(
            events,
            slate,
            weeks=weeks or None,
            prefer_hd=prefer_hd,
            note="Replay of saved snapshot — no Odds API call",
        )
        print(json.dumps(written.get("inventory") or written, indent=2, default=str))
        return 0

    _load_odds_key()
    try:
        pulled = fetch_ncaaf_odds()
        events = pulled.get("events") or []
        note = ""
        if not events:
            note = (
                "Honest empty — Odds API returned 0 americanfootball_ncaaf events. "
                "Books may not have posted Week 0–2 yet."
            )
        written = ingest_events(
            events,
            slate,
            pulled_at=pulled.get("pulled_at"),
            weeks=weeks or None,
            prefer_hd=prefer_hd,
            note=note,
        )
        inv = dict(written.get("inventory") or {})
        inv["x_requests_remaining"] = pulled.get("x_requests_remaining")
        inv["odds_key_source"] = pulled.get("source")
        inv["used_in_spread"] = USED_IN_SPREAD
        inv["kei"] = False
        print(json.dumps(inv, indent=2, default=str))
        return 0
    except Exception as exc:
        written = ingest_events(
            [],
            slate,
            weeks=weeks or None,
            prefer_hd=prefer_hd,
            note=f"Pull failed: {type(exc).__name__}: {exc}",
        )
        inv = dict(written.get("inventory") or {})
        inv["status"] = "error"
        inv["error_type"] = type(exc).__name__
        inv["used_in_spread"] = USED_IN_SPREAD
        inv["kei"] = False
        print(json.dumps(inv, indent=2, default=str))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
