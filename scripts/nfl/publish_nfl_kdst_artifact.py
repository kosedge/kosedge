#!/usr/bin/env python3
"""Write the nfl_kdst_publish artifact from launch-research player totals.

Named kickers come from ``nfl_dp_rosters`` (one primary K per team). FG/XP
volume comes from ``kicker_layer.kicking_points_for_season_production`` using
player-path offensive TDs (pass + rush). DST counting rates come from
``nfl_dp_team_defense_weekly`` — the same history remat already uses.

Does not invent kicker names. Teams without a roster K are listed as gaps.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))

from src.services.nfl_kdst_publish import default_kdst_artifact_path  # noqa: E402
from src.services.nfl_kicker_dst_projections import (  # noqa: E402
    compute_dst_season_fantasy_points,
)
from src.services.nfl_season_engine.kicker_layer import (  # noqa: E402
    GAMES_PER_TEAM_SEASON,
    kicking_points_for_season_production,
)


def _sqlalchemy_database_url(raw: str) -> str:
    url = (raw or "").strip().strip('"').strip("'")
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://") :]
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://") :]
    return url


def _canon(team: str) -> str:
    code = str(team or "").strip().upper()
    if code in {"LA", "LAR"}:
        return "LAR"
    return code


def _engine():
    from sqlalchemy import create_engine

    raw = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://ryankos:postgres@127.0.0.1:5432/kosedge",
    )
    return create_engine(
        _sqlalchemy_database_url(raw),
        pool_pre_ping=True,
        connect_args={"connect_timeout": 5},
    )


def _primary_kickers(engine, season: int) -> List[Dict[str, Any]]:
    from sqlalchemy import text

    sql = """
        SELECT team, player_id, player_name FROM nfl_dp_rosters
        WHERE season = :season AND position = 'K'
    """
    career_sql = """
        SELECT player_id, season, SUM(fg_att) AS att
        FROM nfl_dp_kicker_weekly
        GROUP BY player_id, season
    """
    with engine.connect() as conn:
        roster = conn.execute(text(sql), {"season": season}).mappings().all()
        career_rows = conn.execute(text(career_sql)).mappings().all()

    recent: Dict[str, Dict[str, float]] = {}
    for row in career_rows:
        pid = row["player_id"]
        season_n = int(row["season"] or -1)
        att = float(row["att"] or 0.0)
        prev = recent.get(pid)
        if prev is None or season_n > int(prev["season"]):
            recent[pid] = {"season": float(season_n), "att": att}

    by_team: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in roster:
        stats = recent.get(row["player_id"]) or {"season": -1.0, "att": 0.0}
        by_team[_canon(row["team"])].append(
            {
                "team": _canon(row["team"]),
                "player_id": row["player_id"],
                "player_name": row["player_name"] or row["player_id"],
                "most_recent_season": int(stats["season"]),
                "most_recent_season_attempts": float(stats["att"]),
            }
        )
    selected: List[Dict[str, Any]] = []
    for team, cands in by_team.items():
        best = sorted(
            cands,
            key=lambda c: (
                -c["most_recent_season"],
                -c["most_recent_season_attempts"],
                str(c["player_id"]),
            ),
        )[0]
        selected.append(
            {
                "team": team,
                "player_id": best["player_id"],
                "player_name": best["player_name"],
            }
        )
    selected.sort(key=lambda r: r["team"])
    return selected


def _dst_history(engine) -> List[Dict[str, Any]]:
    from sqlalchemy import text

    sql = """
        SELECT
          team, COUNT(*) AS games,
          SUM(points_allowed) AS points_allowed_total,
          SUM(sacks) AS sacks_total,
          SUM(interceptions) AS interceptions_total,
          SUM(fumble_recoveries) AS fumble_recoveries_total,
          SUM(defensive_tds + special_teams_tds) AS defensive_tds_total,
          SUM(safeties) AS safeties_total
        FROM nfl_dp_team_defense_weekly
        GROUP BY team
    """
    std_sql = "SELECT STDDEV(points_allowed) AS lg_std FROM nfl_dp_team_defense_weekly"
    with engine.connect() as conn:
        rows = conn.execute(text(sql)).mappings().all()
        lg_std = float(conn.execute(text(std_sql)).scalar() or 10.0)
    out: List[Dict[str, Any]] = []
    for row in rows:
        games = float(row["games"] or 0.0)
        if games <= 0:
            continue
        team = _canon(row["team"])
        pa = float(row["points_allowed_total"] or 0.0) / games
        sacks_g = float(row["sacks_total"] or 0.0) / games
        ints_g = float(row["interceptions_total"] or 0.0) / games
        fr_g = float(row["fumble_recoveries_total"] or 0.0) / games
        td_g = float(row["defensive_tds_total"] or 0.0) / games
        saf_g = float(row["safeties_total"] or 0.0) / games
        scored = compute_dst_season_fantasy_points(
            points_allowed_mean_per_game=pa,
            points_allowed_std_per_game=lg_std,
            sacks_per_game=sacks_g,
            interceptions_per_game=ints_g,
            fumble_recoveries_per_game=fr_g,
            defensive_tds_per_game=td_g,
            safeties_per_game=saf_g,
            games=GAMES_PER_TEAM_SEASON,
        )
        out.append(
            {
                "team": team,
                "points_allowed_mean": round(pa, 4),
                "sacks": round(sacks_g * GAMES_PER_TEAM_SEASON, 3),
                "fantasy_points": round(float(scored["total_points"]), 3),
            }
        )
    by_team = {r["team"]: r for r in sorted(out, key=lambda r: r["team"])}
    return [by_team[t] for t in sorted(by_team)]


def _offensive_tds_by_team(players: List[Dict[str, Any]]) -> Dict[str, float]:
    totals: Dict[str, float] = defaultdict(float)
    for row in players:
        team = _canon(str(row.get("team") or ""))
        if not team:
            continue
        totals[team] += float(row.get("pass_tds_mean") or 0.0) + float(
            row.get("rush_tds_mean") or 0.0
        )
    return dict(totals)


def build_artifact(
    *,
    season: int,
    source_dir: Path,
    engine,
    source_label: str,
) -> Tuple[Dict[str, Any], List[str]]:
    players_path = source_dir / "player_season_totals.json"
    players: List[Dict[str, Any]] = []
    if players_path.is_file():
        raw = json.loads(players_path.read_text(encoding="utf-8"))
        players = raw if isinstance(raw, list) else list(raw.get("player_season_totals") or [])
    tds = _offensive_tds_by_team(players)
    kickers_named = _primary_kickers(engine, season)
    gaps: List[str] = []
    if not kickers_named:
        gaps.append("no_roster_kickers")

    kickers: List[Dict[str, Any]] = []
    for kicker in kickers_named:
        team = kicker["team"]
        off_tds = tds.get(team, 0.0)
        if team == "LAR":
            off_tds = off_tds or tds.get("LA", 0.0)
        vol = kicking_points_for_season_production(
            team=team,
            offensive_tds=off_tds if off_tds > 0 else 38.0,
            games=GAMES_PER_TEAM_SEASON,
        )
        if off_tds <= 0:
            gaps.append(f"kicker_tds_prior:{team}")
        kickers.append(
            {
                "player_id": kicker["player_id"],
                "player_name": kicker["player_name"],
                "team": team,
                "fg_attempts": round(float(vol["fg_att"]), 3),
                "xp_attempts": round(float(vol["xp_att"]), 3),
                "fantasy_points": round(float(vol["points_from_kicking"]), 3),
            }
        )

    dst = _dst_history(engine)
    if len(dst) < 32:
        gaps.append(f"dst_teams={len(dst)}")

    payload = {
        "season": int(season),
        "source": source_label,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "research_dir": str(source_dir),
        "n_player_rows": len(players),
        "kickers": kickers,
        "dst": dst,
        "gaps": gaps,
    }
    return payload, gaps


def main() -> None:
    ap = argparse.ArgumentParser(description="Publish nfl_kdst_publish JSON artifact")
    ap.add_argument("--season", type=int, default=2026)
    ap.add_argument("--source", type=Path, required=True, help="Launch research out_dir")
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument(
        "--source-label",
        default="player-production-v3-phase3c-100k",
        help="Artifact source identity string",
    )
    args = ap.parse_args()
    source = args.source.resolve()
    if not source.is_dir():
        raise SystemExit(f"missing source dir: {source}")
    out = args.out or default_kdst_artifact_path(args.season)
    engine = _engine()
    payload, gaps = build_artifact(
        season=args.season,
        source_dir=source,
        engine=engine,
        source_label=args.source_label,
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(
        f"WROTE {out} kickers={len(payload['kickers'])} dst={len(payload['dst'])} "
        f"gaps={gaps or 'none'}"
    )


if __name__ == "__main__":
    main()
