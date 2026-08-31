#!/usr/bin/env python3
"""Chapter 1 Phase 1A — replay live v0.15 project_game / KEI vs warehouse closes.

Uses historical_proxy universes (prior-year cfb_ratings + league-avg identity)
so we score the *current* margin→WP→KEI mappers without refitting.

Does NOT fit a bucket map. Measurement only.

Usage:
  python3 scripts/cfb/cfb_ch1_replay_v015_vs_close.py --seasons 2024,2025 --json \\
    > data/ops/cfb-ch1-replay-2024-2025.json
  python3 scripts/cfb/cfb_ch1_replay_v015_vs_close.py --seasons 2020,2021,2022,2023,2024,2025 --json \\
    > data/ops/cfb-ch1-replay-2020-2025.json
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))

from src.services.cfb_season_engine import priors as P  # noqa: E402
from src.services.cfb_season_engine.cfb_kei import apply_cfb_kei  # noqa: E402
from src.services.cfb_season_engine.historical_calibration import (  # noqa: E402
    build_historical_proxy_universe,
    ratings_to_efficiency_map,
)
from src.services.cfb_season_engine.team_projection import (  # noqa: E402
    project_game,
    project_game_to_dict,
)
from src.services.cfb_warehouse.paths import raw_dir  # noqa: E402

# Reuse discovery path resolution
sys.path.insert(0, str(ROOT / "scripts" / "cfb"))
from cfb_ch1_wp_bucket_discovery import (  # noqa: E402
    BUCKETS,
    SERVICE_CLEAN,
    MONOREPO_CLEAN,
    _finite,
    _read_parquet,
    _resolve_clean,
    bucket_abs,
    tier_for,
)


def _mean(xs: Sequence[float]) -> Optional[float]:
    return sum(xs) / len(xs) if xs else None


def _mae(xs: Sequence[float]) -> Optional[float]:
    return _mean([abs(x) for x in xs])


def _summarize(residuals: Sequence[float]) -> Dict[str, Any]:
    return {
        "n": len(residuals),
        "mean_residual": round(_mean(residuals), 4) if residuals else None,
        "mae": round(_mae(residuals), 4) if residuals else None,
        "median_ae": (
            round(sorted(abs(x) for x in residuals)[len(residuals) // 2], 4)
            if residuals
            else None
        ),
    }


def load_joined(clean: Path, seasons: Sequence[int]) -> List[Dict[str, Any]]:
    games = _read_parquet(clean / "games.parquet")
    closes = {
        str(r.get("game_id")): r for r in _read_parquet(clean / "closing_lines.parquet")
    }
    out: List[Dict[str, Any]] = []
    for g in games:
        season = int(g.get("season") or 0)
        if season not in seasons:
            continue
        close_row = closes.get(str(g.get("game_id")) or "") or {}
        close = _finite(close_row.get("close_spread_home"))
        if close is None:
            continue
        home = str(g.get("home_team_id") or "")
        away = str(g.get("away_team_id") or "")
        if not home or not away or home.startswith("espn:") or away.startswith("espn:"):
            continue
        fcs = bool(g.get("fcs_home") or g.get("fcs_away") or g.get("fcs_opponent"))
        out.append(
            {
                "game_id": str(g.get("game_id")),
                "season": season,
                "week": int(g.get("week") or 0),
                "home_team_id": home,
                "away_team_id": away,
                "neutral": bool(g.get("neutral")),
                "fcs": fcs,
                "close_spread_home": float(close),
                "close_source": close_row.get("source"),
                "line_fidelity": close_row.get("line_fidelity"),
                "home_score": g.get("home_score"),
                "away_score": g.get("away_score"),
                "tier": tier_for(home, away, fcs),
            }
        )
    return out


def replay(
    seasons: Sequence[int],
    *,
    prefer_hd: bool,
    limit: int = 0,
) -> Dict[str, Any]:
    clean = _resolve_clean(prefer_hd=prefer_hd)
    if not (clean / "games.parquet").is_file():
        return {
            "ok": False,
            "error": "warehouse_parquet_missing",
            "clean_dir": str(clean),
        }

    joined = load_joined(clean, seasons)
    if limit > 0:
        joined = joined[:limit]

    cache = raw_dir(prefer_hd=False) / "sdv"
    cache.mkdir(parents=True, exist_ok=True)

    universes: Dict[int, Any] = {}
    for season in sorted({int(r["season"]) for r in joined}):
        eff = ratings_to_efficiency_map(season - 1, cache_dir=cache)
        universes[season] = build_historical_proxy_universe(season, eff)

    model_by_bucket: Dict[str, List[float]] = defaultdict(list)
    kei_by_bucket: Dict[str, List[float]] = defaultdict(list)
    model_by_season_bucket: Dict[str, Dict[str, List[float]]] = defaultdict(
        lambda: defaultdict(list)
    )
    kei_by_season_bucket: Dict[str, Dict[str, List[float]]] = defaultdict(
        lambda: defaultdict(list)
    )
    skipped = Counter()
    rows_out: List[Dict[str, Any]] = []

    for g in joined:
        universe = universes.get(g["season"])
        if universe is None:
            skipped["no_universe"] += 1
            continue
        home = g["home_team_id"]
        away = g["away_team_id"]
        if home not in universe.teams or away not in universe.teams:
            skipped["team_not_in_universe"] += 1
            continue
        try:
            proj = project_game(
                universe,
                home_team=home,
                away_team=away,
                week=max(int(g["week"]), 1),
                season=g["season"],
                neutral_site=bool(g["neutral"]),
                engine_version=P.ENGINE_VERSION,
            )
        except Exception:  # noqa: BLE001
            skipped["project_game_error"] += 1
            continue

        payload = project_game_to_dict(proj)
        model_spread = float(proj.spread_home)
        raw_margin = float(proj.expected_home_score) - float(proj.expected_away_score)
        kei = apply_cfb_kei(
            payload,
            market_spread_home=float(g["close_spread_home"]),
            fbs_vs_fbs=not bool(g["fcs"]),
            fcs_home=bool(g["fcs"]),
            fcs_away=bool(g["fcs"]),
        )
        kei_spread = kei.get("kei_spread_home")
        if kei_spread is None or not math.isfinite(float(kei_spread)):
            skipped["kei_missing"] += 1
            continue

        close = float(g["close_spread_home"])
        # Bucket on |close| for residual table (market band); also record |raw_margin|
        b_close = bucket_abs(abs(close))
        b_margin = bucket_abs(abs(raw_margin))
        model_res = model_spread - close
        kei_res = float(kei_spread) - close

        model_by_bucket[b_close].append(model_res)
        kei_by_bucket[b_close].append(kei_res)
        model_by_season_bucket[str(g["season"])][b_close].append(model_res)
        kei_by_season_bucket[str(g["season"])][b_close].append(kei_res)

        rows_out.append(
            {
                "game_id": g["game_id"],
                "season": g["season"],
                "week": g["week"],
                "home": home,
                "away": away,
                "tier": g["tier"],
                "fcs": g["fcs"],
                "close_spread_home": close,
                "raw_margin_home": round(raw_margin, 4),
                "model_spread_home": round(model_spread, 4),
                "kei_spread_home": round(float(kei_spread), 4),
                "bucket_close": b_close,
                "bucket_raw_margin": b_margin,
                "residual_model_minus_close": round(model_res, 4),
                "residual_kei_minus_close": round(kei_res, 4),
                "model_home_wp": round(float(proj.home_win_prob), 4),
                "kei_home_wp": kei.get("kei_home_win_prob"),
            }
        )

    def pack_buckets(src: Dict[str, List[float]]) -> Dict[str, Any]:
        return {name: _summarize(src.get(name, [])) for name, _, _ in BUCKETS}

    return {
        "ok": True,
        "engine_version": P.ENGINE_VERSION,
        "reconstruction": "historical_proxy_prior_year_efficiency_league_avg_identity",
        "clean_dir": str(clean),
        "seasons": list(seasons),
        "n_joined_with_close": len(joined),
        "n_scored": len(rows_out),
        "skipped": dict(skipped),
        "bucket_edges_abs_close": {name: [lo, hi] for name, lo, hi in BUCKETS},
        "model_vs_close_by_bucket": pack_buckets(model_by_bucket),
        "kei_vs_close_by_bucket": pack_buckets(kei_by_bucket),
        "model_vs_close_by_season_bucket": {
            s: pack_buckets(model_by_season_bucket[s])
            for s in sorted(model_by_season_bucket.keys())
        },
        "kei_vs_close_by_season_bucket": {
            s: pack_buckets(kei_by_season_bucket[s])
            for s in sorted(kei_by_season_bucket.keys())
        },
        "fit": False,
        "note": (
            "Residuals = spread_home − close_home. Negative ⇒ model/KEI longer "
            "favorite than close; positive ⇒ shorter than close (cupcake-direction)."
        ),
        # Keep sample small in JSON for git; full rows optional via --include-rows
        "sample_rows": rows_out[:25],
        "_rows": rows_out,
    }


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seasons", default="2024,2025")
    ap.add_argument("--repo-fallback", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument(
        "--include-rows",
        action="store_true",
        help="Embed all scored rows in JSON (large).",
    )
    args = ap.parse_args(argv)
    seasons = [int(s.strip()) for s in args.seasons.split(",") if s.strip()]
    out = replay(seasons, prefer_hd=not args.repo_fallback, limit=args.limit)
    rows = out.pop("_rows", None)
    if args.include_rows and rows is not None:
        out["rows"] = rows
    if args.json:
        print(json.dumps(out, indent=2, default=str))
    else:
        if not out.get("ok"):
            print(out, file=sys.stderr)
            return 2
        print(f"engine={out['engine_version']} n_scored={out['n_scored']}")
        print("kei_vs_close_by_bucket:")
        print(json.dumps(out["kei_vs_close_by_bucket"], indent=2))
    return 0 if out.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
