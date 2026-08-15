#!/usr/bin/env python3
"""CFB market diagnostic — pure model vs open/close. Report only.

Usage:
  python scripts/cfb/run_market_diagnostic.py
  python scripts/cfb/run_market_diagnostic.py --seasons 2020-2025
  python scripts/cfb/run_market_diagnostic.py --season 2026
  python scripts/cfb/cfb diagnostic 2026

Does not blend market into fair. Does not write KEI / Edge / used_in_spread.
2026 with n=0 returns ``insufficient_market_rows`` (exit 0), not a crash.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))

from src.services.cfb_season_engine.fbs_universe import is_official_fbs  # noqa: E402
from src.services.cfb_warehouse.market_diagnostic import (  # noqa: E402
    DIAGNOSTIC_ID,
    USED_IN_SPREAD,
    diagnose,
    diagnose_live_2026,
    documentation,
)
from src.services.cfb_warehouse.open_ingest import (  # noqa: E402
    load_mapped,
    load_official_slate_games,
    reduce_mapped_games,
)
from src.services.cfb_warehouse.paths import clean_dir, odds_lake_dir  # noqa: E402
from src.services.cfb_warehouse.walkforward import (  # noqa: E402
    build_program_priors,
    index_week_efficiency,
    walkforward_games,
)

OPS = ROOT / "data" / "ops" / "cfb-market-diagnostic-20260814.json"


def _read(path: Path) -> List[Dict[str, Any]]:
    import pandas as pd

    return pd.read_parquet(path).to_dict(orient="records")


def _parse_seasons(raw: str) -> list[int]:
    raw = raw.strip()
    if "-" in raw and "," not in raw:
        a, b = raw.split("-", 1)
        return list(range(int(a), int(b) + 1))
    return [int(s.strip()) for s in raw.split(",") if s.strip()]


def _join_closes(games: List[Dict[str, Any]], closes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    by_id = {str(c.get("game_id")): c for c in closes}
    joined = []
    for g in games:
        c = by_id.get(str(g.get("game_id")))
        row = dict(g)
        if not c:
            row.setdefault("close_spread_home", None)
            joined.append(row)
            continue
        for k in (
            "close_spread_home",
            "open_spread_home",
            "close_total",
            "open_total",
            "book",
            "source",
            "line_fidelity",
            "close_captured_at",
            "available_at",
        ):
            if c.get(k) is not None:
                row[k] = c.get(k)
        joined.append(row)
    return joined


def _lookup_2026_market(
    home: str, away: str, closes: List[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    home_u, away_u = home.upper(), away.upper()
    for row in closes:
        if int(row.get("season") or 0) != 2026:
            continue
        h = str(row.get("home_team_id") or row.get("home") or "").upper()
        a = str(row.get("away_team_id") or row.get("away") or "").upper()
        if h == home_u and a == away_u:
            close = row.get("close_spread_home")
            open_sp = row.get("open_spread_home")
            if close is None and open_sp is None:
                continue
            return {
                "market_spread_home": close if close is not None else open_sp,
                "open_spread_home": open_sp,
                "close_spread_home": close,
                "source": row.get("source") or row.get("book") or "warehouse_close",
                "kind": "close" if close is not None else "open",
            }
    return None


def _live_2026_table(closes: List[Dict[str, Any]]) -> Dict[str, Any]:
    import os

    os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
    from src.services.cfb_season_engine import (
        build_packaged_universe,
        project_game_preview,
        project_game_to_dict,
    )
    from src.services.cfb_season_engine.official_schedule import (
        games_from_blob,
        load_official_schedule_blob,
    )

    universe = build_packaged_universe(2026)
    games = [
        g
        for g in games_from_blob(load_official_schedule_blob(2026))
        if g.week <= 2
        and is_official_fbs(g.home_team)
        and is_official_fbs(g.away_team)
    ]
    rows = []
    n_with_market = 0
    for g in games:
        proj = project_game_preview(
            universe,
            home_team=g.home_team,
            away_team=g.away_team,
            week=g.week,
            neutral_site=g.neutral_site,
            n_sims=400,
            seed=7,
        )
        payload = project_game_to_dict(proj)
        market = _lookup_2026_market(g.home_team, g.away_team, closes)
        model = float(proj.spread_home)
        mkt = None
        delta = None
        if market:
            mkt = float(market["market_spread_home"])
            delta = round(model - mkt, 2)
            n_with_market += 1
        rows.append(
            {
                "week": g.week,
                "home": g.home_team,
                "away": g.away_team,
                "neutral": bool(g.neutral_site),
                "model_spread_home": round(model, 2),
                "model_sigma": round(float(proj.margin_sd), 2),
                "market_spread_home": mkt,
                "delta_model_minus_market": delta,
                "market_source": (market or {}).get("source"),
                "market_kind": (market or {}).get("kind"),
                "used_in_spread": False,
                "kei": False,
                "research_only": True,
            }
        )
        assert payload["used_in_spread"] is False
    return {
        "n_games": len(rows),
        "n_with_market": n_with_market,
        "n_model_only": len(rows) - n_with_market,
        "used_in_spread": False,
        "kei": False,
        "note": (
            "v0.14 project-game vs warehouse 2026 open/close when present. "
            "closing_lines has no 2026 rows; lake 2026 is Nov futures only. "
            "Missing market is labeled, not invented. No Edge/Tag."
        ),
        "rows": rows,
    }


def _attach_2026_fairs(reduced: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Join research-fair project-game onto reduced open/close rows. No KEI."""
    import os

    os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
    from src.services.cfb_season_engine import (
        build_packaged_universe,
        project_game_preview,
        project_game_to_dict,
    )

    universe = build_packaged_universe(2026)
    out: List[Dict[str, Any]] = []
    for row in reduced:
        home = str(row.get("home_team_id") or "")
        away = str(row.get("away_team_id") or "")
        week = int(row.get("week") or 0)
        if not home or not away:
            continue
        proj = project_game_preview(
            universe,
            home_team=home,
            away_team=away,
            week=week,
            n_sims=80,
            seed=7,
        )
        payload = project_game_to_dict(proj)
        joined = dict(row)
        joined["model_spread_home"] = round(float(proj.spread_home), 2)
        joined["model_fair_present"] = True
        joined["used_in_spread"] = False
        joined["kei"] = False
        assert payload["used_in_spread"] is False
        out.append(joined)
    return out


def _run_2026(*, prefer_hd: bool) -> Dict[str, Any]:
    mapped = load_mapped(prefer_hd=prefer_hd)
    reduced = reduce_mapped_games(mapped, weeks=(0, 1, 2))
    n_opens = sum(1 for r in reduced if r.get("open_spread_home") is not None)
    n_closes = sum(1 for r in reduced if r.get("close_spread_home") is not None)
    extra = {
        "n_mapped_rows": len(mapped),
        "n_slate_games_with_snaps": len(reduced),
        "weeks": [0, 1, 2],
        "cli": "scripts/cfb/cfb diagnostic 2026",
    }
    if n_opens == 0 and n_closes == 0:
        return diagnose_live_2026([], n_opens=0, n_closes=0, extra=extra)
    joined = _attach_2026_fairs(reduced)
    return diagnose_live_2026(joined, n_opens=n_opens, n_closes=n_closes, extra=extra)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seasons", default="2020-2025")
    parser.add_argument("--season", default="", help="If 2026, run live join only (n=0 is OK)")
    parser.add_argument("--repo-fallback", action="store_true")
    args = parser.parse_args(argv)
    prefer_hd = not args.repo_fallback
    if str(args.season).strip() == "2026":
        live = _run_2026(prefer_hd=prefer_hd)
        print(json.dumps(live, indent=2, default=str))
        return 0
    clean = clean_dir(prefer_hd=prefer_hd)
    games_path = clean / "games.parquet"
    closes_path = clean / "closing_lines.parquet"
    week_path = clean / "efficiency" / "team_week_efficiency.parquet"
    season_path = clean / "efficiency" / "team_season_efficiency.parquet"
    missing = [p for p in (games_path, closes_path, week_path, season_path) if not p.is_file()]
    if missing:
        print(f"Missing {missing}", file=sys.stderr)
        return 1

    seasons = _parse_seasons(args.seasons) or list(range(2020, 2026))
    games = [g for g in _read(games_path) if int(g.get("season") or 0) in set(seasons)]
    closes = _read(closes_path)
    joined = _join_closes(games, closes)
    priors = build_program_priors(_read(season_path), seasons)
    graded = walkforward_games(
        joined, priors=priors, eff_idx=index_week_efficiency(_read(week_path))
    )
    hist = diagnose(graded)
    live = _live_2026_table(closes)
    lake = odds_lake_dir(prefer_hd=prefer_hd)
    payload = {
        "diagnostic_id": DIAGNOSTIC_ID,
        "used_in_spread": USED_IN_SPREAD,
        "kei": False,
        "blend": False,
        "documentation": documentation(),
        "odds_lake_dir": str(lake),
        "historical": hist,
        "live_2026_week0_2": live,
    }
    OPS.parent.mkdir(parents=True, exist_ok=True)
    OPS.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "wrote": str(OPS),
                "diagnostic_id": DIAGNOSTIC_ID,
                "used_in_spread": USED_IN_SPREAD,
                "kei": False,
                "hist_overall": hist["overall"],
                "by_diag_week_band": {
                    k: {
                        "n_close": v.get("n_close"),
                        "vs_close": v.get("vs_close"),
                        "vs_open": v.get("vs_open"),
                        "ats_rate": v.get("ats_rate"),
                        "clv_side_rate": v.get("clv_side_rate"),
                        "clv_side_n": v.get("clv_side_n"),
                        "sample_flag": v.get("sample_flag"),
                    }
                    for k, v in hist["by_diag_week_band"].items()
                },
                "by_close_abs_bucket": {
                    k: {
                        "n_close": v.get("n_close"),
                        "vs_close": v.get("vs_close"),
                        "ats_rate": v.get("ats_rate"),
                        "clv_side_rate": v.get("clv_side_rate"),
                        "sample_flag": v.get("sample_flag"),
                    }
                    for k, v in hist["by_close_abs_bucket"].items()
                },
                "by_favorite_home": {
                    k: {
                        "n_close": v.get("n_close"),
                        "vs_close": v.get("vs_close"),
                        "ats_rate": v.get("ats_rate"),
                    }
                    for k, v in hist["by_favorite_home"].items()
                },
                "by_conference_tier": {
                    k: {
                        "n_close": v.get("n_close"),
                        "vs_close": v.get("vs_close"),
                        "ats_rate": v.get("ats_rate"),
                        "sample_flag": v.get("sample_flag"),
                    }
                    for k, v in hist["by_conference_tier"].items()
                },
                "live_2026": {
                    "n_games": live["n_games"],
                    "n_with_market": live["n_with_market"],
                    "n_model_only": live["n_model_only"],
                },
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
