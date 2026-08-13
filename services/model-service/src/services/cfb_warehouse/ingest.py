"""Pull SportsDataverse CFB history once → raw cache → clean parquet.

Does not query CFBD/cfbfastR at request time. Optional CFBD overlay is a
future ingest flag, not a live path.
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from src.services.cfb_season_engine.conferences import conference_for
from src.services.cfb_warehouse.identity import (
    alias_rows,
    known_engine_codes,
    resolve_team_code,
)
from src.services.cfb_warehouse.leakage import era_tag
from src.services.cfb_warehouse.odds_lake import (
    export_odds_lake,
    load_odds_lake,
    overlay_closing_lines,
)
from src.services.cfb_warehouse.paths import clean_dir, ensure_dirs, hd_mounted, raw_dir
from src.services.cfb_warehouse.pbp import PBP_SEASONS, ingest_pbp
from src.services.cfb_warehouse.sdv import fetch_sdv_csv

DEFAULT_SEASONS = tuple(range(2020, 2026))


def _parse_float(raw: Any) -> Optional[float]:
    if raw in (None, ""):
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _parse_int(raw: Any) -> Optional[int]:
    if raw in (None, ""):
        return None
    try:
        return int(float(raw))
    except (TypeError, ValueError):
        return None


def _sum_linescores(rows: Sequence[Mapping[str, str]]) -> Dict[Tuple[str, str], int]:
    out: Dict[Tuple[str, str], int] = defaultdict(int)
    for r in rows:
        try:
            out[(str(r["game_id"]), str(r["team_id"]))] += int(float(r["value"]))
        except (KeyError, TypeError, ValueError):
            continue
    return out


def _write_parquet(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    import pandas as pd

    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(list(rows)).to_parquet(path, index=False)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def materialize_identity(*, clean: Path) -> Dict[str, int]:
    known = known_engine_codes()
    teams = [
        {
            "team_id": code,
            "espn_abbr": code,
            "conference": conference_for(code),
            "conference_source": "packaged_2026_approx",
            "conference_season": 0,
        }
        for code in sorted(known)
    ]
    aliases = alias_rows()
    _write_parquet(clean / "teams.parquet", teams)
    _write_parquet(clean / "team_aliases.parquet", aliases)
    return {"teams": len(teams), "team_aliases": len(aliases)}


def ingest_season(
    season: int,
    *,
    cache_dir: Path,
    known: Mapping[str, Any],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
    skipped = {
        "missing_sides": 0,
        "missing_score": 0,
        "missing_line": 0,
        "same_team": 0,
        "not_final": 0,
    }
    try:
        betting = fetch_sdv_csv(
            "espn_cfb_betting", f"betting_{season}.csv.gz", cache_dir=cache_dir
        )
        box = fetch_sdv_csv(
            "espn_cfb_team_box", f"team_box_{season}.csv.gz", cache_dir=cache_dir
        )
        lines = fetch_sdv_csv(
            "espn_cfb_linescores", f"linescores_{season}.csv.gz", cache_dir=cache_dir
        )
        schedules = fetch_sdv_csv(
            "espn_cfb_schedules",
            f"cfb_schedule_{season}.csv.gz",
            cache_dir=cache_dir,
        )
    except Exception as exc:  # noqa: BLE001 — season may be unpublished
        return [], [], [], {"fetch_failed": 1, "error": str(exc)[:200]}

    scores = _sum_linescores(lines)
    by_game: Dict[str, Dict[str, Dict[str, str]]] = defaultdict(dict)
    for row in box:
        by_game[str(row.get("game_id") or "")][str(row.get("home_away") or "")] = row
    by_sched: Dict[str, Dict[str, str]] = {
        str(row.get("game_id") or ""): row for row in schedules if row.get("game_id")
    }

    games: List[Dict[str, Any]] = []
    closes: List[Dict[str, Any]] = []
    snapshots: List[Dict[str, Any]] = []

    for b in betting:
        gid = str(b.get("game_id") or "")
        if not gid:
            continue
        sides = by_game.get(gid) or {}
        home = sides.get("home")
        away = sides.get("away")
        if not home or not away:
            skipped["missing_sides"] += 1
            continue
        sched = by_sched.get(gid) or {}
        status = str(sched.get("status") or "").upper()
        if status and status not in {"STATUS_FINAL", "STATUS_COMPLETED", "FINAL"}:
            skipped["not_final"] += 1
            continue
        hs = scores.get((gid, str(home.get("team_id") or "")))
        aws = scores.get((gid, str(away.get("team_id") or "")))
        if hs is None:
            hs = _parse_int(sched.get("home_score") or home.get("home_score"))
        if aws is None:
            aws = _parse_int(sched.get("away_score") or away.get("away_score"))
        if hs is None or aws is None:
            skipped["missing_score"] += 1
            continue

        home_code = resolve_team_code(
            abbr=home.get("team_abbreviation", ""),
            name=home.get("team_name", ""),
            known_codes=known,
        )
        away_code = resolve_team_code(
            abbr=away.get("team_abbreviation", ""),
            name=away.get("team_name", ""),
            known_codes=known,
        )
        fcs_home = home_code is None
        fcs_away = away_code is None
        home_id = home_code or f"espn:{home.get('team_id')}"
        away_id = away_code or f"espn:{away.get('team_id')}"
        if home_id == away_id:
            skipped["same_team"] += 1
            continue

        week = _parse_int(b.get("week") or sched.get("week")) or 0
        kickoff = str(
            sched.get("game_date")
            or b.get("start_date")
            or b.get("game_date")
            or home.get("game_date")
            or ""
        )
        game_date = kickoff[:10] if kickoff else ""
        spread = _parse_float(b.get("home_team_spread") or b.get("game_spread"))
        total = _parse_float(b.get("over_under"))
        open_spread = _parse_float(b.get("home_team_spread_open") or b.get("open_spread"))
        open_total = _parse_float(b.get("over_under_open") or b.get("open_total"))
        ml_home = _parse_float(b.get("home_moneyline") or b.get("home_ml"))
        ml_away = _parse_float(b.get("away_moneyline") or b.get("away_ml"))
        if spread is None and total is None:
            skipped["missing_line"] += 1

        games.append(
            {
                "game_id": gid,
                "season": int(season),
                "week": week,
                "game_date": str(game_date)[:32],
                "kickoff": str(kickoff)[:64],
                "home_team_id": home_id,
                "away_team_id": away_id,
                "home_espn_id": str(home.get("team_id") or ""),
                "away_espn_id": str(away.get("team_id") or ""),
                "home_name": str(home.get("team_name") or ""),
                "away_name": str(away.get("team_name") or ""),
                "fcs_home": fcs_home,
                "fcs_away": fcs_away,
                "fcs_opponent": fcs_home or fcs_away,
                "neutral": str(
                    sched.get("neutral_site")
                    or b.get("neutral_site")
                    or home.get("neutral_site")
                    or ""
                ).lower()
                in {"1", "true", "t", "yes"},
                "home_score": int(hs),
                "away_score": int(aws),
                "era_tag": era_tag(season),
                "source": "sportsdataverse_espn",
            }
        )
        closes.append(
            {
                "game_id": gid,
                "season": int(season),
                "week": week,
                "home_team_id": home_id,
                "away_team_id": away_id,
                "close_spread_home": spread,
                "close_total": total,
                "close_ml_home": ml_home,
                "close_ml_away": ml_away,
                "open_spread_home": open_spread,
                "open_total": open_total,
                "book": str(b.get("provider") or b.get("book") or "espn_sdv"),
                "source": "sportsdataverse_espn_cfb_betting",
                "line_fidelity": "close_ish_resolved"
                if spread is not None
                else "missing",
            }
        )
        snapshots.append(
            {
                "game_id": gid,
                "season": int(season),
                "captured_at": str(kickoff or game_date),
                "available_at": str(kickoff or game_date),
                "book": str(b.get("provider") or "espn_sdv"),
                "market": "spread",
                "spread_home": spread,
                "total_points": total,
                "price_home": ml_home,
                "price_away": ml_away,
                "source": "sportsdataverse_espn_cfb_betting",
                "snapshot_kind": "close_ish",
            }
        )

    return games, closes, snapshots, skipped


def run_ingest(
    *,
    seasons: Sequence[int] = DEFAULT_SEASONS,
    prefer_hd: bool = True,
    ingest_odds: bool = True,
    ingest_pbp_seasons: Sequence[int] | None = PBP_SEASONS,
) -> Dict[str, Any]:
    raw, clean = ensure_dirs(prefer_hd=prefer_hd)
    cache_dir = raw / "sdv"
    cache_dir.mkdir(parents=True, exist_ok=True)
    known = known_engine_codes()
    identity_counts = materialize_identity(clean=clean)

    all_games: List[Dict[str, Any]] = []
    all_closes: List[Dict[str, Any]] = []
    all_snaps: List[Dict[str, Any]] = []
    by_season: Dict[str, Any] = {}
    fetch_errors: Dict[str, str] = {}

    for season in seasons:
        games, closes, snaps, skipped = ingest_season(
            int(season), cache_dir=cache_dir, known=known
        )
        if "fetch_failed" in skipped:
            fetch_errors[str(season)] = str(skipped.get("error") or "fetch_failed")
            by_season[str(season)] = {"status": "fetch_failed", **skipped}
            continue
        all_games.extend(games)
        all_closes.extend(closes)
        all_snaps.extend(snaps)
        by_season[str(season)] = {
            "status": "ok",
            "games": len(games),
            "with_close_spread": sum(
                1 for c in closes if c.get("close_spread_home") is not None
            ),
            "with_kickoff": sum(1 for g in games if g.get("kickoff")),
            "fcs_flagged": sum(1 for g in games if g.get("fcs_opponent")),
            "skipped": skipped,
        }

    if all_games:
        _write_parquet(clean / "games.parquet", all_games)
        _write_parquet(clean / "closing_lines.parquet", all_closes)
        _write_parquet(clean / "odds_snapshots.parquet", all_snaps)

    odds_meta: Dict[str, Any] = {"status": "skipped"}
    if ingest_odds and all_games:
        try:
            export_meta = export_odds_lake(prefer_hd=prefer_hd)
            lake_snaps = load_odds_lake(prefer_hd=prefer_hd)
            merged, join_stats = overlay_closing_lines(all_games, all_closes, lake_snaps)
            all_closes = merged
            _write_parquet(clean / "closing_lines.parquet", all_closes)
            odds_meta = {"export": export_meta, "join": join_stats, "status": "ok"}
            for season, payload in by_season.items():
                if not isinstance(payload, dict) or payload.get("status") != "ok":
                    continue
                payload["with_close_spread"] = sum(
                    1
                    for c in all_closes
                    if str(c.get("season")) == str(season)
                    and c.get("close_spread_home") is not None
                )
                payload["with_open_spread"] = sum(
                    1
                    for c in all_closes
                    if str(c.get("season")) == str(season)
                    and c.get("open_spread_home") is not None
                )
                payload["lake_primary"] = sum(
                    1
                    for c in all_closes
                    if str(c.get("season")) == str(season)
                    and c.get("source") == "odds_api_lake"
                )
        except Exception as exc:  # noqa: BLE001 — lake is overlay, games still valid
            odds_meta = {"status": "failed", "error": str(exc)[:240]}

    pbp_meta: Dict[str, Any] = {"status": "skipped"}
    if ingest_pbp_seasons:
        try:
            pbp_meta = ingest_pbp(seasons=ingest_pbp_seasons, prefer_hd=prefer_hd)
            pbp_meta["status"] = "ok" if pbp_meta.get("plays") else pbp_meta.get("status", "ok")
        except Exception as exc:  # noqa: BLE001
            pbp_meta = {"status": "failed", "error": str(exc)[:240]}
    else:
        pbp_readme = clean / "pbp" / "README.md"
        if not pbp_readme.exists():
            pbp_readme.write_text(
                "# CFB PBP\n\nRun ingest with PBP enabled to download season parquet.\n"
                "Do not live-query CFBD/cfbfastR from model-service.\n",
                encoding="utf-8",
            )

    inventory = {
        "as_of": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "source": (
            "sportsdataverse schedules/box/linescores + odds_api_lake primary "
            "+ sdv betting fill + espn_cfb_pbp"
        ),
        "hd_mounted": hd_mounted(),
        "raw_dir": str(raw),
        "clean_dir": str(clean),
        "seasons": list(seasons),
        "identity": identity_counts,
        "games": len(all_games),
        "closing_lines": len(all_closes),
        "odds_snapshots": len(all_snaps),
        "season_range": {
            "min": min((g["season"] for g in all_games), default=None),
            "max": max((g["season"] for g in all_games), default=None),
        },
        "by_season": by_season,
        "fetch_errors": fetch_errors,
        "owned_odds_api_cfb_inventory": odds_meta,
        "pbp": {
            "plays": pbp_meta.get("plays"),
            "games": pbp_meta.get("games"),
            "seasons": pbp_meta.get("seasons"),
            "by_season": {
                k: {
                    "plays": v.get("plays"),
                    "games": v.get("games"),
                    "raw_cols": v.get("raw_cols"),
                    "status": v.get("status"),
                }
                for k, v in (pbp_meta.get("by_season") or {}).items()
            }
            if isinstance(pbp_meta.get("by_season"), dict)
            else pbp_meta,
        },
        "leakage_rule": "strictly_before_kickoff",
        "engine_read_path": "none — season-engine does not live-query this warehouse",
    }
    _write_json(clean / "inventory.json", inventory)
    return inventory
