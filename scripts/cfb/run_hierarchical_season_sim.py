#!/usr/bin/env python3
"""CLI entry point for the hierarchical CFB season engine (v0.4 season sim).

Examples
--------
# Packaged priors (no DB): season paths + sample game projection
python scripts/cfb/run_hierarchical_season_sim.py --demo --n-sims 50 --sample-game UGA@ALA

# Status / honesty dump
python scripts/cfb/run_hierarchical_season_sim.py --status-only
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))


def _parse_matchup(raw: str) -> tuple[str, str]:
    text = (raw or "").strip().upper().replace(" ", "")
    if "@" in text:
        away, home = text.split("@", 1)
    elif "VS" in text:
        home, away = text.split("VS", 1)
    else:
        raise SystemExit(f"Expected MATCHUP like UGA@ALA, got {raw!r}")
    return home, away


def main() -> None:
    parser = argparse.ArgumentParser(description="Hierarchical CFB season engine")
    parser.add_argument("--season", type=int, default=2026)
    parser.add_argument("--n-sims", type=int, default=25)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--demo", action="store_true", default=True, help="Packaged universe")
    parser.add_argument("--sample-game", default="UGA@ALA", help="away@home matchup")
    parser.add_argument("--week", type=int, default=1)
    parser.add_argument("--neutral", action="store_true", help="Neutral-site projection")
    parser.add_argument("--status-only", action="store_true")
    parser.add_argument("--skip-sim", action="store_true", help="Only project sample game")
    parser.add_argument(
        "--out-dir",
        default="",
        help="Output directory (default data/ops/cfb-season-engine-<ts>)",
    )
    args = parser.parse_args()

    from src.services.cfb_season_engine import (  # noqa: E402
        DEFAULT_SEASON_ENGINE_VERSION,
        build_packaged_universe,
        engine_status_payload,
        project_game_preview,
        project_game_to_dict,
        season_sim_to_dict,
        simulate_full_season,
    )

    if args.status_only:
        print(json.dumps(engine_status_payload(season=args.season, demo=True), indent=2))
        return

    universe = build_packaged_universe(season=args.season)
    print(
        f"Universe mode=packaged season={universe.season} "
        f"games={len(universe.schedule)} teams={len(universe.teams)} "
        f"version={DEFAULT_SEASON_ENGINE_VERSION}"
    )
    for k, v in universe.notes.items():
        print(f"  note[{k}]: {v}")

    artifacts: Dict[str, Any] = {
        "engine_version": DEFAULT_SEASON_ENGINE_VERSION,
        "universe_notes": universe.notes,
    }

    if not args.skip_sim:
        print(f"Running {args.n_sims} season paths...")
        season_result = simulate_full_season(
            universe,
            n_sims=args.n_sims,
            seed=args.seed,
            progress_every=max(1, args.n_sims // 5),
        )
        artifacts["season_sim"] = season_sim_to_dict(season_result)
        print(
            f"Season sim done: games/path={season_result.games_per_season} "
            f"mean_wins_sum={season_result.diagnostics.get('mean_wins_sum')} "
            f"teams_with_wins={season_result.diagnostics.get('teams_with_positive_mean_wins')}"
        )
        top = artifacts["season_sim"]["top_teams_by_wins"][:8]
        for row in top:
            print(
                f"  #{row.get('rank', '?')} {row['team']}: "
                f"wins_mean={row['mean']} p50={row.get('p50')}"
            )

    home, away = _parse_matchup(args.sample_game)
    print(f"Projecting sample game {away}@{home} week={args.week}...")
    proj = project_game_preview(
        universe,
        home_team=home,
        away_team=away,
        week=args.week,
        season=args.season,
        neutral_site=args.neutral,
    )
    artifacts["game_projection"] = project_game_to_dict(proj)
    print(
        f"  home_wp={proj.home_win_prob:.3f} "
        f"score={proj.expected_away_score:.1f}@{proj.expected_home_score:.1f} "
        f"total={proj.expected_total:.1f} spread_home={proj.spread_home:+.1f}"
    )
    print(
        f"  early_season active={proj.early_season_uncertainty.get('active')} "
        f"margin_sd={proj.margin_sd:.2f}"
    )
    if proj.drivers:
        hs = proj.drivers.get("primary_signals", {})
        print(
            f"  drivers home roster={hs.get('home_roster_strength')} "
            f"qb_idx={hs.get('home_qb_situation_index')} "
            f"| away roster={hs.get('away_roster_strength')} "
            f"qb_idx={hs.get('away_qb_situation_index')}"
        )

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = Path(args.out_dir) if args.out_dir else ROOT / "data" / "ops" / f"cfb-season-engine-{ts}"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "run.json"
    out_path.write_text(json.dumps(artifacts, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
