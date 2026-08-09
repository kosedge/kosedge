#!/usr/bin/env python3
"""Heavy NFL season-engine research sims for launch numbers (offline CLI).

Does **not** hit Railway HTTP (capped at 500) or mutate live fantasy/survivor
request paths. Writes versioned artifacts under data/ops/ and optionally
mirrors to /Volumes/KosEdgeData/clean/nfl/research/.

Examples
--------
# Practical launch bundle: 50k team W/L + 1k full player paths
.venv/bin/python -u scripts/nfl/run_launch_research_sims.py \\
  --n-team-sims 50000 --n-player-sims 1000

# Push team W/L to 100k when overnight is OK
.venv/bin/python -u scripts/nfl/run_launch_research_sims.py \\
  --n-team-sims 100000 --n-player-sims 1000 --workers 8
"""

from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import statistics
import sys
import time
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))

HD_RESEARCH = Path("/Volumes/KosEdgeData/clean/nfl/research")


def _sqlalchemy_database_url(raw: str) -> str:
    url = (raw or "").strip().strip('"').strip("'")
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://") :]
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://") :]
    return url


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")


def _dist_stats(values: Sequence[float]) -> Dict[str, float]:
    clean = [float(v) for v in values if math.isfinite(float(v))]
    if not clean:
        return {"mean": 0.0, "std": 0.0, "p10": 0.0, "p50": 0.0, "p90": 0.0}
    ordered = sorted(clean)
    n = len(ordered)
    return {
        "mean": round(statistics.fmean(clean), 4),
        "std": round(statistics.pstdev(clean) if n > 1 else 0.0, 4),
        "p10": round(ordered[max(0, int(round((n - 1) * 0.10)))], 4),
        "p50": round(ordered[max(0, int(round((n - 1) * 0.50)))], 4),
        "p90": round(ordered[max(0, int(round((n - 1) * 0.90)))], 4),
    }


def _hist_0_17(samples: Sequence[int]) -> Dict[str, int]:
    hist = {str(i): 0 for i in range(18)}
    for w in samples:
        wi = int(w)
        if 0 <= wi <= 17:
            hist[str(wi)] += 1
    return hist


def _chunk_sizes(total: int, workers: int) -> List[int]:
    workers = max(1, min(int(workers), int(total)))
    base, rem = divmod(int(total), workers)
    return [base + (1 if i < rem else 0) for i in range(workers) if base + (1 if i < rem else 0) > 0]


def _team_wl_worker(payload: Tuple[Any, int, int]) -> Dict[str, Any]:
    """Run ``n`` team W/L season paths; return win samples + week win counts."""
    universe, n, seed = payload
    import random

    from src.services.nfl_season_engine.survivor import simulate_team_wl_path

    rng = random.Random(int(seed))
    teams = list(universe.teams)
    win_samples: Dict[str, List[int]] = {t: [] for t in teams}
    week_wins: Dict[str, Dict[int, int]] = {t: defaultdict(int) for t in teams}
    games_scheduled: Dict[str, Dict[int, int]] = {t: defaultdict(int) for t in teams}
    for game in universe.schedule:
        games_scheduled[game.home_team][game.week] = 1
        games_scheduled[game.away_team][game.week] = 1

    for _ in range(int(n)):
        # None → use packaged depth SoT injury_paths when present (daily intel).
        week_winners = simulate_team_wl_path(universe, rng=rng, injury_paths=None)
        season_wins: Dict[str, int] = {t: 0 for t in teams}
        for week, winners in week_winners.items():
            for team in winners:
                if team in season_wins:
                    season_wins[team] += 1
                    week_wins[team][int(week)] += 1
        for team, w in season_wins.items():
            win_samples[team].append(int(w))

    return {
        "n": int(n),
        "win_samples": win_samples,
        "week_wins": {t: dict(weeks) for t, weeks in week_wins.items()},
        "games_scheduled": {t: dict(weeks) for t, weeks in games_scheduled.items()},
    }


def _merge_team_wl(chunks: List[Dict[str, Any]], teams: Sequence[str]) -> Dict[str, Any]:
    win_samples: Dict[str, List[int]] = {t: [] for t in teams}
    week_wins: Dict[str, Dict[int, int]] = {t: defaultdict(int) for t in teams}
    games_scheduled: Dict[str, Dict[int, int]] = {}
    total_n = 0
    for ch in chunks:
        total_n += int(ch["n"])
        if not games_scheduled:
            games_scheduled = {
                t: {int(w): int(c) for w, c in (weeks or {}).items()}
                for t, weeks in (ch.get("games_scheduled") or {}).items()
            }
        for team in teams:
            win_samples[team].extend(int(x) for x in ch["win_samples"].get(team, []))
            for week, c in (ch["week_wins"].get(team) or {}).items():
                week_wins[team][int(week)] += int(c)

    team_rows = []
    for team in teams:
        samples = win_samples[team]
        dist = _dist_stats([float(x) for x in samples])
        team_rows.append(
            {
                "team": team,
                "n_sims": len(samples),
                **dist,
                "win_histogram": _hist_0_17(samples),
            }
        )
    team_rows.sort(key=lambda r: -float(r["mean"]))

    week_rates: Dict[str, Dict[str, float]] = {}
    for team in teams:
        rates: Dict[str, float] = {}
        for week, played in (games_scheduled.get(team) or {}).items():
            if not played:
                continue
            wins = week_wins[team].get(int(week), 0)
            rates[str(int(week))] = round(wins / max(1, total_n), 6)
        week_rates[team] = rates

    week_win_counts = {
        t: {int(w): int(c) for w, c in weeks.items()} for t, weeks in week_wins.items()
    }
    return {
        "n_sims": total_n,
        "team_win_distributions": team_rows,
        "team_week_win_rates": week_rates,
        "week_win_counts": week_win_counts,
        "games_scheduled": games_scheduled,
        "mean_wins_sum": round(sum(float(r["mean"]) for r in team_rows), 4),
    }


def _survivor_from_week_matrix(
    universe,
    *,
    week: int,
    n_sims: int,
    week_win_counts: Dict[str, Dict[int, int]],
    games_scheduled: Dict[str, Dict[int, int]],
    engine_version: str,
) -> Dict[str, Any]:
    """Rank W1 survivor picks from an already-computed week win matrix."""
    from src.services.nfl_season_engine.survivor import (
        FORMULA_NOTES,
        PREMIUM_SPOT_CAP,
        PREMIUM_WP,
        SAVE_PENALTY,
        SAVE_WEIGHT_AVG,
        SAVE_WEIGHT_MAX,
        SAVE_WEIGHT_PREMIUM,
        EDGE_BONUS,
        schedule_index,
        score_team_survivor,
    )

    by_week = schedule_index(universe.schedule)
    max_week = max((g.week for g in universe.schedule), default=week)
    week_games = by_week.get(week, {})
    all_rows: List[Dict[str, Any]] = []
    bye_teams: List[str] = []
    for team in universe.teams:
        row = score_team_survivor(
            team=team,
            week=week,
            n_sims=n_sims,
            win_counts=week_win_counts,
            games_scheduled=games_scheduled,
            max_week=max_week,
            already_used=[],
            game=week_games.get(team),
        )
        if not row["plays_this_week"]:
            bye_teams.append(team)
        all_rows.append(row)

    ranked = [r for r in all_rows if r["remaining"] and r["plays_this_week"]]
    ranked.sort(
        key=lambda r: (
            -float(r["pick_now_score"]),
            -float(r["win_rate"]),
            str(r["team"]),
        )
    )
    notes = dict(universe.notes)
    notes["survivor_mode"] = (
        f"derived from {n_sims} team_wl research paths (no second sim pass)"
    )
    notes["already_used"] = "(none)"
    notes["bye_handling"] = FORMULA_NOTES["bye_handling"]
    return {
        "season": universe.season,
        "week": week,
        "n_sims": n_sims,
        "engine_version": engine_version,
        "already_used": [],
        "ranked_picks": ranked[:32],
        "all_teams_week": all_rows,
        "formula": dict(FORMULA_NOTES),
        "notes": notes,
        "diagnostics": {
            "seed": None,
            "teams": len(universe.teams),
            "max_week": max_week,
            "scoring_knobs": {
                "premium_wp": PREMIUM_WP,
                "save_penalty": SAVE_PENALTY,
                "edge_bonus": EDGE_BONUS,
                "save_weights": {
                    "future_avg_wp": SAVE_WEIGHT_AVG,
                    "future_max_wp": SAVE_WEIGHT_MAX,
                    "premium_frac": SAVE_WEIGHT_PREMIUM,
                },
                "premium_spot_cap": PREMIUM_SPOT_CAP,
            },
            "bye_teams_this_week": sorted(bye_teams),
            "bye_count": len(bye_teams),
            "derived_from_team_wl_matrix": True,
        },
    }


def _resolve_universe(season: int, as_of_week: int, force_packaged: bool):
    from src.services.nfl_season_engine.loaders import (
        build_packaged_real_universe,
        resolve_season_universe,
        universe_schedule_meta,
    )

    if force_packaged:
        universe = build_packaged_real_universe(season=season)
        return universe, universe_schedule_meta(universe), "packaged"

    session = None
    try:
        db_url = os.getenv("DATABASE_URL", "").strip()
        # Docker hostname "postgres" is not resolvable on bare-metal Mac runs.
        if db_url and "://postgres:" not in db_url.replace("postgresql+psycopg", "postgresql"):
            host_ok = True
        else:
            # Prefer explicit localhost when .env points at docker DNS.
            localhost = os.getenv(
                "LAUNCH_RESEARCH_DATABASE_URL",
                "postgresql+psycopg://ryankos:postgres@127.0.0.1:5432/kosedge",
            )
            os.environ["DATABASE_URL"] = _sqlalchemy_database_url(localhost)
            db_url = os.environ["DATABASE_URL"]
            host_ok = True

        if host_ok and db_url:
            from sqlalchemy import create_engine
            from sqlalchemy.orm import sessionmaker

            os.environ["DATABASE_URL"] = _sqlalchemy_database_url(db_url)
            engine = create_engine(
                os.environ["DATABASE_URL"],
                pool_pre_ping=True,
                connect_args={"connect_timeout": 3},
            )
            Session = sessionmaker(bind=engine)
            session = Session()
            universe, meta = resolve_season_universe(
                season=season, as_of_week=as_of_week, demo=False, session=session
            )
            return universe, meta, str(meta.get("schedule_source") or "db")
    except Exception as exc:  # pragma: no cover - ops fallback
        print(f"DB universe resolve failed ({exc}); using packaged real universe", flush=True)
    finally:
        if session is not None:
            try:
                session.close()
            except Exception:
                pass

    universe = build_packaged_real_universe(season=season)
    return universe, universe_schedule_meta(universe), "packaged"


def main() -> None:
    parser = argparse.ArgumentParser(description="NFL launch research heavy sims")
    parser.add_argument("--season", type=int, default=2026)
    parser.add_argument("--as-of-week", type=int, default=1)
    parser.add_argument("--n-team-sims", type=int, default=50000, help="Team W/L paths (50k–100k)")
    parser.add_argument(
        "--n-player-sims",
        type=int,
        default=1000,
        help="Full hierarchical paths with player boxes (expensive; default 1000)",
    )
    parser.add_argument("--survivor-week", type=int, default=1)
    parser.add_argument("--seed", type=int, default=20260807)
    parser.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 4) - 1))
    parser.add_argument("--force-packaged", action="store_true")
    parser.add_argument("--skip-player", action="store_true")
    parser.add_argument("--skip-survivor", action="store_true")
    parser.add_argument("--out-dir", default="")
    parser.add_argument("--no-hd-mirror", action="store_true")
    args = parser.parse_args()

    from src.services.nfl_season_engine.calibration import ENGINE_VERSION
    from src.services.nfl_season_engine import simulate_full_season

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    label = (
        f"nfl-season-engine-launch-{ENGINE_VERSION}-"
        f"Nteam{args.n_team_sims}-Nplayer{0 if args.skip_player else args.n_player_sims}-{ts}"
    )
    out_dir = Path(args.out_dir) if args.out_dir else ROOT / "data" / "ops" / label
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"engine_version={ENGINE_VERSION}", flush=True)
    print(f"out_dir={out_dir}", flush=True)
    print(f"workers={args.workers}", flush=True)

    t_universe = time.time()
    universe, meta, mode = _resolve_universe(args.season, args.as_of_week, args.force_packaged)
    print(
        f"Universe mode={mode} schedule={meta.get('schedule_source')} "
        f"roster={meta.get('roster_source') or meta.get('depth_source')} "
        f"games={len(universe.schedule)} named_skill={universe.notes.get('depth_named_skill_teams')} "
        f"({time.time() - t_universe:.1f}s)",
        flush=True,
    )
    if str(meta.get("schedule_source") or "").startswith("demo"):
        raise SystemExit("Refusing demo schedule for launch research — use packaged/DB real slate")

    # ---- Team W/L heavy paths (win distributions + survivor matrix) ----
    team_chunks = _chunk_sizes(args.n_team_sims, args.workers)
    team_payloads = [
        (universe, n, args.seed + 1000 * (i + 1))
        for i, n in enumerate(team_chunks)
    ]
    print(f"Running team W/L sims n={args.n_team_sims} chunks={team_chunks}...", flush=True)
    t0 = time.time()
    team_results: List[Dict[str, Any]] = []
    if len(team_payloads) == 1:
        team_results = [_team_wl_worker(team_payloads[0])]
    else:
        with ProcessPoolExecutor(max_workers=len(team_payloads)) as pool:
            futs = [pool.submit(_team_wl_worker, p) for p in team_payloads]
            done = 0
            for fut in as_completed(futs):
                team_results.append(fut.result())
                done += 1
                finished_n = sum(int(r["n"]) for r in team_results)
                print(f"  team-wl chunks {done}/{len(futs)} (~{finished_n}/{args.n_team_sims})", flush=True)
    team_bundle = _merge_team_wl(team_results, list(universe.teams))
    team_elapsed = time.time() - t0
    print(
        f"Team W/L done in {team_elapsed:.1f}s mean_wins_sum={team_bundle['mean_wins_sum']}",
        flush=True,
    )
    _write_json(out_dir / "team_win_distributions.json", team_bundle["team_win_distributions"])
    _write_json(out_dir / "team_week_win_rates.json", team_bundle["team_week_win_rates"])

    # ---- Full player season paths (capped; expensive; single process for clean percentiles) ----
    player_bundle: Optional[Dict[str, Any]] = None
    player_elapsed = 0.0
    if not args.skip_player and args.n_player_sims > 0:
        print(
            f"Running full player season sims n={args.n_player_sims} (single process)...",
            flush=True,
        )
        t0 = time.time()
        result = simulate_full_season(
            universe,
            n_sims=int(args.n_player_sims),
            seed=args.seed + 5000,
            progress_every=max(1, int(args.n_player_sims) // 10),
            include_diagnostics=True,
        )
        player_elapsed = time.time() - t0
        team_player_rows = [
            {"team": team, **stats}
            for team, stats in sorted(
                result.team_wins.items(), key=lambda kv: -kv[1]["mean"]
            )
        ]
        player_bundle = {
            "n_sims": result.n_sims,
            "games_per_season": result.games_per_season,
            "engine_version": result.engine_version,
            "merge_note": "Single-process path-coherent player season totals.",
            "team_wins_from_player_paths": team_player_rows,
            "player_season_totals": result.player_season_totals,
            "notes": result.notes,
            "diagnostics": result.diagnostics,
        }
        _write_json(out_dir / "player_season_totals.json", player_bundle["player_season_totals"])
        _write_json(
            out_dir / "team_wins_from_player_paths.json",
            player_bundle["team_wins_from_player_paths"],
        )
        print(
            f"Player sims done in {player_elapsed:.1f}s players={len(player_bundle['player_season_totals'])}",
            flush=True,
        )

    # ---- Survivor week eval derived from the heavy team W/L matrix (no second pass) ----
    survivor_payload = None
    survivor_elapsed = 0.0
    if not args.skip_survivor:
        print(
            f"Deriving survivor eval week={args.survivor_week} from "
            f"{team_bundle['n_sims']} team W/L paths...",
            flush=True,
        )
        t0 = time.time()
        survivor_payload = _survivor_from_week_matrix(
            universe,
            week=args.survivor_week,
            n_sims=int(team_bundle["n_sims"]),
            week_win_counts=team_bundle["week_win_counts"],
            games_scheduled=team_bundle["games_scheduled"],
            engine_version=ENGINE_VERSION,
        )
        survivor_elapsed = time.time() - t0
        survivor_payload["mode"] = mode
        survivor_payload["generated_at_utc"] = datetime.now(timezone.utc).isoformat()
        survivor_payload["note"] = (
            "PRESEASON W1 survivor research slate (no already_used). "
            f"Rankings derived from the full {args.n_team_sims}-path team W/L matrix."
        )
        _write_json(out_dir / "survivor_week1_evaluate.json", survivor_payload)
        print(f"Survivor derive done in {survivor_elapsed:.1f}s", flush=True)

    generated = datetime.now(timezone.utc).isoformat()
    summary = {
        "label": "launch_current_nfl_season_engine_research",
        "preseason": True,
        "honest_label": (
            "PRESEASON research numbers from hierarchical season engine "
            f"{ENGINE_VERSION}. Team win distributions from {args.n_team_sims} "
            "Layers 1–2 team W/L paths. Player season totals from fewer full "
            "path-coherent sims (Layers 1–4). Not live request-path outputs."
        ),
        "generated_at_utc": generated,
        "engine_version": ENGINE_VERSION,
        "season": args.season,
        "as_of_week": args.as_of_week,
        "universe_mode": mode,
        "schedule_meta": meta,
        "universe_notes": {
            k: universe.notes.get(k)
            for k in (
                "schedule_source",
                "roster_source",
                "depth_source",
                "strength_source",
                "strength_as_of",
                "strengths",
                "depth_named_skill_teams",
                "depth_player_rows",
                "calibration",
                "mode",
            )
            if k in universe.notes
        },
        "n_team_sims": args.n_team_sims,
        "n_player_sims": 0 if args.skip_player else args.n_player_sims,
        "survivor_week": args.survivor_week,
        "survivor_n_sims": None if survivor_payload is None else survivor_payload.get("n_sims"),
        "seed": args.seed,
        "workers": args.workers,
        "timing_seconds": {
            "team_wl": round(team_elapsed, 2),
            "player_full": round(player_elapsed, 2),
            "survivor": round(survivor_elapsed, 2),
        },
        "sanity": {
            "team_mean_wins_sum": team_bundle["mean_wins_sum"],
            "team_mean_wins_sum_ok": abs(team_bundle["mean_wins_sum"] - 272.0) < 0.5,
        },
        "files": sorted(p.name for p in out_dir.iterdir() if p.is_file()),
        "related_market_mc_100k": {
            "path": "data/ops/nfl-preseason-sim-2026-20260729T160818Z",
            "model_version": "nfl-v1.5-matchup-sim",
            "n_sims": 100000,
            "role": "Hub futures / Bernoulli market-MC board (separate from season engine)",
        },
        "does_not_touch": [
            "Railway HTTP /season-engine/simulate (still capped ≤500)",
            "Edge board / fantasy live request paths",
            "Bulk odds loads into Railway",
        ],
    }
    _write_json(out_dir / "run_summary.json", summary)

    # Short ops note (repo + optional HD)
    note_lines = [
        f"# NFL launch research sims — {ts}",
        "",
        f"- **Engine:** `{ENGINE_VERSION}`",
        f"- **Preseason:** yes (honest launch research label)",
        f"- **Team W/L sims:** {args.n_team_sims:,} (Layers 1–2; win distributions + week matrix)",
        f"- **Full player sims:** {0 if args.skip_player else args.n_player_sims:,} (Layers 1–4 path-coherent)",
        f"- **Survivor artifact:** week {args.survivor_week} eval"
        + (f" at n={survivor_payload.get('n_sims')}" if survivor_payload else " (skipped)"),
        f"- **Universe:** {mode} / schedule={meta.get('schedule_source')} / "
        f"roster={meta.get('roster_source') or meta.get('depth_source')}",
        f"- **Output dir:** `{out_dir}`",
        f"- **Timing:** team {team_elapsed/60:.1f}m · player {player_elapsed/60:.1f}m · "
        f"survivor {survivor_elapsed/60:.1f}m",
        f"- **Sanity:** mean_wins_sum={team_bundle['mean_wins_sum']} (expect ~272)",
        "",
        "## Launch-current numbers",
        "",
        "These season-engine artifacts are the **launch-current research** board for:",
        "- season win distributions (`team_win_distributions.json`)",
        "- week win-rate matrix for survivor path research (`team_week_win_rates.json`)",
        "- player season projections (`player_season_totals.json`) when player sims ran",
        "- W1 survivor ranking sample (`survivor_week1_evaluate.json`)",
        "",
        "Separate hub futures board (market Bernoulli MC, 100k): "
        "`data/ops/nfl-preseason-sim-2026-20260729T160818Z` (`nfl-v1.5-matchup-sim`).",
        "",
        "## Caps / honesty",
        "",
        f"- Full hierarchical player paths are ~10s/path; launch research capped player N at "
        f"**{0 if args.skip_player else args.n_player_sims}** (not 50k).",
        f"- Team W/L paths reached **{args.n_team_sims}** (target band 50k–100k).",
        "- Interactive UI / Railway HTTP remain capped (≤500) so desks stay responsive.",
        "",
    ]
    note_path = out_dir / "LAUNCH_RESEARCH_NOTE.md"
    note_path.write_text("\n".join(note_lines), encoding="utf-8")
    # Stable pointer in data/ops
    pointer = ROOT / "data" / "ops" / "nfl-launch-research-sims-current.md"
    pointer.write_text(
        "\n".join(
            [
                "# NFL launch research sims — current pointer",
                "",
                f"- **Bundle:** `{out_dir.relative_to(ROOT) if out_dir.is_relative_to(ROOT) else out_dir}`",
                f"- **Engine:** `{ENGINE_VERSION}`",
                f"- **Team W/L N:** {args.n_team_sims}",
                f"- **Player full N:** {0 if args.skip_player else args.n_player_sims}",
                f"- **Generated:** {generated}",
                f"- **Detail note:** `{note_path.relative_to(ROOT) if note_path.is_relative_to(ROOT) else note_path}`",
                "",
            ]
        ),
        encoding="utf-8",
    )

    hd_path = None
    if not args.no_hd_mirror and HD_RESEARCH.parent.exists():
        try:
            HD_RESEARCH.mkdir(parents=True, exist_ok=True)
            hd_path = HD_RESEARCH / out_dir.name
            if hd_path.exists():
                shutil.rmtree(hd_path)
            shutil.copytree(out_dir, hd_path)
            # Mirror pointer onto HD docs-ish location
            (HD_RESEARCH / "CURRENT.md").write_text(
                pointer.read_text(encoding="utf-8")
                + f"\n- **HD mirror:** `{hd_path}`\n",
                encoding="utf-8",
            )
            print(f"Mirrored to HD: {hd_path}", flush=True)
        except OSError as exc:
            print(f"HD mirror skipped ({exc})", flush=True)

    summary["hd_mirror"] = str(hd_path) if hd_path else None
    summary["ops_pointer"] = str(pointer.relative_to(ROOT))
    summary["ops_note"] = str(note_path.relative_to(ROOT)) if note_path.is_relative_to(ROOT) else str(note_path)
    _write_json(out_dir / "run_summary.json", summary)

    print("Top teams by expected wins (team W/L):", flush=True)
    for row in team_bundle["team_win_distributions"][:10]:
        print(
            f"  {row['team']:3} mean={row['mean']:.3f} p10={row['p10']:.1f} "
            f"p50={row['p50']:.1f} p90={row['p90']:.1f}",
            flush=True,
        )
    print(f"DONE bundle={out_dir}", flush=True)
    print(f"POINTER={pointer}", flush=True)


if __name__ == "__main__":
    main()
