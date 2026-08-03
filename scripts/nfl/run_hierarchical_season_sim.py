#!/usr/bin/env python3
"""CLI entry point for the hierarchical NFL season engine.

Examples
--------
# Offline demo (no DB): 50 season paths + sample future-game boxes
python scripts/nfl/run_hierarchical_season_sim.py --demo --n-sims 50 --sample-game BUF@KC

# With injury path shocks (JSON array)
python scripts/nfl/run_hierarchical_season_sim.py --demo --sample-game SEA@SF --week 6 \\
  --injury-paths '[{"player_name":"C.McCaffrey","team":"SF","status":"out","week_start":4,"week_end":8}]'

# Survivor-pool week evaluation (also: scripts/nfl/run_survivor_evaluate.py)
python scripts/nfl/run_hierarchical_season_sim.py --demo --survivor-week 5 \\
  --already-used KC,BUF --n-sims 300

# DB-backed universe when DATABASE_URL is set
python scripts/nfl/run_hierarchical_season_sim.py --season 2026 --n-sims 100
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))


def _sqlalchemy_database_url(raw: str) -> str:
    url = (raw or "").strip().strip('"').strip("'")
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://") :]
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://") :]
    return url


def _parse_matchup(raw: str) -> tuple[str, str]:
    text = (raw or "").strip().upper().replace(" ", "")
    if "@" in text:
        away, home = text.split("@", 1)
    elif "V" in text and "VS" in text:
        home, away = text.split("VS", 1)
    else:
        raise SystemExit(f"Expected MATCHUP like BUF@KC, got {raw!r}")
    return home, away


def _load_injury_paths(raw: str) -> List[Any]:
    from src.services.nfl_season_engine import parse_injury_paths

    text = (raw or "").strip()
    if not text:
        return []
    path = Path(text)
    if path.exists():
        payload = json.loads(path.read_text(encoding="utf-8"))
    else:
        payload = json.loads(text)
    if isinstance(payload, dict) and "injury_paths" in payload:
        payload = payload["injury_paths"]
    if not isinstance(payload, list):
        raise SystemExit("--injury-paths must be a JSON array or {injury_paths: [...]}")
    return parse_injury_paths(payload)


def main() -> None:
    parser = argparse.ArgumentParser(description="Hierarchical NFL season engine")
    parser.add_argument("--season", type=int, default=2026)
    parser.add_argument("--n-sims", type=int, default=50)
    parser.add_argument("--game-reps", type=int, default=400)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--demo", action="store_true", help="Force offline demo universe")
    parser.add_argument("--sample-game", default="BUF@KC", help="away@home matchup for box sample")
    parser.add_argument("--week", type=int, default=1)
    parser.add_argument(
        "--injury-paths",
        default="",
        help="JSON array/file of injury paths (optional; see injury_paths.py)",
    )
    parser.add_argument(
        "--survivor-week",
        type=int,
        default=0,
        help="If set, run survivor evaluation for this week (skips full player season sim)",
    )
    parser.add_argument(
        "--already-used",
        default="",
        help="Comma-separated already-picked teams for --survivor-week (e.g. KC,BUF)",
    )
    parser.add_argument(
        "--out-dir",
        default="",
        help="Output directory (default data/ops/nfl-season-engine-<ts>)",
    )
    args = parser.parse_args()

    from src.services.nfl_season_engine import (  # noqa: E402
        build_demo_universe,
        evaluate_survivor,
        load_universe_from_db,
        project_game_player_boxes,
        simulate_full_season,
    )

    injury_paths = _load_injury_paths(args.injury_paths)
    already_used = [p.strip().upper() for p in (args.already_used or "").split(",") if p.strip()]

    universe = None
    mode = "demo"
    if not args.demo and os.getenv("DATABASE_URL"):
        try:
            from sqlalchemy import create_engine
            from sqlalchemy.orm import sessionmaker

            os.environ["DATABASE_URL"] = _sqlalchemy_database_url(os.environ["DATABASE_URL"])
            engine = create_engine(os.environ["DATABASE_URL"])
            Session = sessionmaker(bind=engine)
            session = Session()
            try:
                universe = load_universe_from_db(session, season=args.season, as_of_week=args.week)
                mode = "db"
            finally:
                session.close()
        except Exception as exc:  # pragma: no cover - ops fallback
            print(f"DB load failed ({exc}); falling back to demo universe")

    if universe is None:
        universe = build_demo_universe(season=args.season)
        mode = "demo"

    print(
        f"Universe mode={mode} season={universe.season} "
        f"games={len(universe.schedule)} teams={len(universe.teams)} "
        f"players={sum(len(v) for v in universe.rosters.values())} "
        f"calibration={universe.notes.get('calibration', 'n/a')}"
    )
    for k, v in universe.notes.items():
        print(f"  note[{k}]: {v}")

    if injury_paths:
        print(f"Injury paths active: {len(injury_paths)}")
        for p in injury_paths:
            print(
                f"  {p.team} {p.player_name or p.player_key} "
                f"{p.status} W{p.week_start}-{p.week_end}"
            )

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = Path(args.out_dir) if args.out_dir else ROOT / "data" / "ops" / f"nfl-season-engine-{ts}"
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.survivor_week:
        print(
            f"Running survivor eval week={args.survivor_week} "
            f"n_sims={args.n_sims} already_used={already_used or '(none)'}..."
        )
        survivor = evaluate_survivor(
            universe,
            week=args.survivor_week,
            n_sims=args.n_sims,
            seed=args.seed,
            already_used=already_used,
            injury_paths=injury_paths,
            top_n=16,
        )
        payload = survivor.to_dict()
        payload["mode"] = mode
        payload["generated_at_utc"] = datetime.now(timezone.utc).isoformat()
        _write_json(out_dir / "survivor_evaluate.json", payload)
        print(f"engine_version={survivor.engine_version}")
        print("Top ranked remaining picks:")
        for i, row in enumerate(survivor.ranked_picks[:12], 1):
            print(
                f"  {i:2}. {row['team']:3} vs {row.get('opponent') or '?':3} "
                f"wp={row['win_rate']:.3f} save={row['save_score']:.3f} "
                f"pick_now={row['pick_now_score']:.3f}"
            )
        print(f"Wrote artifacts → {out_dir}")
        return

    print(f"Running {args.n_sims} season paths...")
    season_result = simulate_full_season(
        universe,
        n_sims=args.n_sims,
        seed=args.seed,
        progress_every=max(1, args.n_sims // 5),
        injury_paths=injury_paths,
    )
    print(
        f"Season sim done: games/path={season_result.games_per_season} "
        f"mean_wins_sum={season_result.diagnostics.get('mean_wins_sum')}"
    )

    home, away = _parse_matchup(args.sample_game)
    print(f"Projecting sample game {away}@{home} ({args.game_reps} reps)...")
    game_proj = project_game_player_boxes(
        universe,
        home_team=home,
        away_team=away,
        week=args.week,
        n_replicates=args.game_reps,
        seed=args.seed + 1,
        injury_paths=injury_paths,
    )

    team_rows = [
        {"team": team, **stats}
        for team, stats in sorted(season_result.team_wins.items(), key=lambda kv: -kv[1]["mean"])
    ]
    _write_json(out_dir / "run_summary.json", {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "season": season_result.season,
        "n_sims": season_result.n_sims,
        "games_per_season": season_result.games_per_season,
        "engine_version": season_result.engine_version,
        "notes": season_result.notes,
        "diagnostics": season_result.diagnostics,
        "injury_paths": [
            {
                "player_key": p.player_key,
                "player_name": p.player_name,
                "team": p.team,
                "status": p.status,
                "week_start": p.week_start,
                "week_end": p.week_end,
                "availability": p.availability,
            }
            for p in injury_paths
        ],
        "sample_game": {
            "game_id": game_proj.game_id,
            "home_team": game_proj.home_team,
            "away_team": game_proj.away_team,
            "week": game_proj.week,
            "n_replicates": game_proj.n_replicates,
            "game_script_summary": game_proj.game_script_summary,
        },
    })
    _write_json(out_dir / "team_wins.json", team_rows)
    _write_json(out_dir / "player_season_totals_top.json", season_result.player_season_totals[:40])
    _write_json(
        out_dir / "sample_game_player_boxes.json",
        {
            "game_id": game_proj.game_id,
            "home_team": game_proj.home_team,
            "away_team": game_proj.away_team,
            "week": game_proj.week,
            "n_replicates": game_proj.n_replicates,
            "game_script_summary": game_proj.game_script_summary,
            "notes": game_proj.notes,
            "players": game_proj.players,
        },
    )

    print(f"Wrote artifacts → {out_dir}")
    print("Top projected players for sample game:")
    for row in game_proj.players[:8]:
        pe = row["point_estimate"]
        print(f"  {row['team']:3} {row['position']:2} {row['player_name']:<16} {pe}")


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
