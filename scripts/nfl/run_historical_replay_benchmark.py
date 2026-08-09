#!/usr/bin/env python3
"""Phase 3 historical replay + baseline scorecard CLI.

Example
-------
  DATABASE_URL=postgresql+psycopg://ryankos:postgres@127.0.0.1:5432/kosedge \\
    python scripts/nfl/run_historical_replay_benchmark.py \\
      --seasons 2019-2025 --n-sims 40 --package-depth
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


def _scrub(obj: Any) -> Any:
    if isinstance(obj, float) and not math.isfinite(obj):
        return None
    if isinstance(obj, dict):
        return {k: _scrub(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_scrub(v) for v in obj]
    return obj

ROOT = Path(__file__).resolve().parents[2]
MS = ROOT / "services" / "model-service"
sys.path.insert(0, str(MS))


def _sqlalchemy_database_url(raw: str) -> str:
    url = (raw or "").strip().strip('"').strip("'")
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://") :]
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://") :]
    return url


def _parse_seasons(raw: str) -> List[int]:
    seasons: List[int] = []
    for part in str(raw).split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part and part.count("-") == 1:
            a, b = part.split("-")
            seasons.extend(range(int(a), int(b) + 1))
        else:
            seasons.append(int(part))
    return seasons


def _md_table(headers: List[str], rows: List[List[Any]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(c) for c in row) + " |")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seasons", default="2019-2025")
    parser.add_argument("--n-sims", type=int, default=40)
    parser.add_argument("--seed", type=int, default=20260809)
    parser.add_argument(
        "--package-depth",
        action="store_true",
        help="Download/package nflverse depth packs before replay",
    )
    parser.add_argument(
        "--vegas-json",
        type=Path,
        default=ROOT / "data" / "ops" / "nfl-preseason-vegas-win-totals.json",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=ROOT / "data" / "ops" / "nfl-phase3-historical-replay-20260809",
    )
    parser.add_argument(
        "--ops-md",
        type=Path,
        default=ROOT / "data" / "ops" / "nfl-phase3-historical-replay-benchmark-20260809.md",
    )
    args = parser.parse_args(argv)

    from src.services.nfl_season_engine.calibration import ENGINE_VERSION
    from src.services.nfl_season_engine.historical_replay import (
        DEFAULT_HIST_DEPTH_DIR,
        REPLAY_PROTOCOL_VERSION,
        load_vegas_win_totals,
        pool_scorecards,
        run_season_replay,
        verdict_from_pooled,
        write_historical_depth_pack,
    )

    seasons = _parse_seasons(args.seasons)
    if args.package_depth:
        cache = ROOT / "data" / "ops" / "nfl-phase3-depth-cache"
        for season in seasons:
            path = write_historical_depth_pack(
                season, cache_dir=cache, out_dir=DEFAULT_HIST_DEPTH_DIR
            )
            print(f"packaged depth {season} -> {path}")

    db = os.getenv("DATABASE_URL") or (
        "postgresql+psycopg://ryankos:postgres@127.0.0.1:5432/kosedge"
    )
    os.environ["DATABASE_URL"] = _sqlalchemy_database_url(db)

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(os.environ["DATABASE_URL"])
    Session = sessionmaker(bind=engine)
    session = Session()

    vegas_by_season, vegas_note = load_vegas_win_totals(args.vegas_json)
    cards = []
    data_gaps: List[str] = [vegas_note]
    try:
        for season in seasons:
            print(f"=== replaying {season} n_sims={args.n_sims} ===", flush=True)
            card = run_season_replay(
                session,
                season=season,
                n_sims=args.n_sims,
                seed=args.seed,
                depth_pack_dir=DEFAULT_HIST_DEPTH_DIR,
                vegas_totals=vegas_by_season.get(season),
            )
            cards.append(card)
            data_gaps.extend(card.gaps)
            tw = card.model_team.get("wins") or {}
            print(
                f"  model wins MAE={tw.get('mae'):.3f} bias={tw.get('bias'):.3f} "
                f"ρ={tw.get('rank_corr'):.3f} snapshot={card.snapshot_id}",
                flush=True,
            )
    finally:
        session.close()

    pooled = pool_scorecards(cards)
    verdict = verdict_from_pooled(pooled)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    stamp = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "engine_version": ENGINE_VERSION,
        "protocol_version": REPLAY_PROTOCOL_VERSION,
        "n_sims": args.n_sims,
        "seed": args.seed,
        "seasons": seasons,
        "replicate_count": args.n_sims,
    }
    (args.out_dir / "run_stamp.json").write_text(
        json.dumps(stamp, indent=2) + "\n", encoding="utf-8"
    )
    (args.out_dir / "scorecards.json").write_text(
        json.dumps(_scrub([c.to_dict() for c in cards]), indent=2) + "\n",
        encoding="utf-8",
    )
    (args.out_dir / "pooled.json").write_text(
        json.dumps(_scrub(pooled), indent=2) + "\n", encoding="utf-8"
    )
    (args.out_dir / "verdict.json").write_text(
        json.dumps(_scrub(verdict), indent=2) + "\n", encoding="utf-8"
    )
    unique_gaps = sorted(set(data_gaps))
    (args.out_dir / "data_gaps.json").write_text(
        json.dumps(unique_gaps, indent=2) + "\n", encoding="utf-8"
    )

    # Markdown ops report
    def fmt(node: Dict[str, Any] | None) -> str:
        if not node or not isinstance(node, dict):
            return "n/a"
        mae = node.get("mae")
        bias = node.get("bias")
        rho = node.get("rank_corr")
        if mae is None:
            return "n/a"
        try:
            return f"{float(mae):.3f} / {float(bias):.3f} / {float(rho):.3f}"
        except (TypeError, ValueError):
            return "n/a"

    team_rows = []
    for c in cards:
        b = c.baselines
        team_rows.append(
            [
                c.season,
                fmt(c.model_team.get("wins")),
                fmt((b.get("prior_year_regression") or {}).get("wins")),
                fmt((b.get("epa_power") or {}).get("wins")),
                fmt((b.get("vegas") or {}).get("wins")),
                c.snapshot_id[-16:] if c.snapshot_id else "",
            ]
        )
    pooled_rows = [
        ["model wins", fmt(pooled.get("model_team_wins"))],
        ["prior-year+regression wins", fmt(pooled.get("prior_year_wins"))],
        ["epa_power wins", fmt(pooled.get("epa_power_wins"))],
        ["vegas wins", fmt(pooled.get("vegas_wins"))],
        ["model PF", fmt(pooled.get("model_team_pf"))],
        ["model PA", fmt(pooled.get("model_team_pa"))],
        ["model team pass yards", fmt(pooled.get("model_pass_yards"))],
        ["model team rush yards", fmt(pooled.get("model_rush_yards"))],
        ["model player pass yards", fmt(pooled.get("model_player_pass_yards"))],
        ["model player rush yards", fmt(pooled.get("model_player_rush_yards"))],
        ["model player rec yards", fmt(pooled.get("model_player_rec_yards"))],
    ]

    md = f"""# NFL Phase 3 — Historical Replay & Benchmark Gate (2026-08-09)

**Engine stamp:** `{ENGINE_VERSION}`  
**Protocol:** `{REPLAY_PROTOCOL_VERSION}`  
**Seasons scored:** {", ".join(str(s) for s in seasons)}  
**Replicates / season:** `{args.n_sims}` (seed base `{args.seed}`)  
**PR target:** `deploy-vercel`

## Cutoff rules (no look-ahead)

| Season band | Depth cutoff | Strength prior |
|-------------|--------------|----------------|
| ≤2024 | nflverse `week=1` + `game_type=REG` | Y−1 play-weighted EPA (`nfl_dp_team_situational_weekly`, source=nflverse) |
| ≥2025 | latest nflverse `dt` on/before Labor Day Monday of season year | same Y−1 EPA |

**Forbidden inputs:** season-Y regular-season results, season-Y rolling features (week-1 rolling embeds Y games), end-of-year ranks, calibrating knobs on Y then scoring Y.

## Team wins scorecard (MAE / bias / Spearman ρ)

{_md_table(["Season", "Model", "Prior-year+reg", "EPA power", "Vegas", "snapshot"], team_rows)}

## Pooled (equal team-weight via n)

{_md_table(["Metric", "MAE / bias / ρ"], pooled_rows)}

## Where we add value vs where we do not

**Earned (pre-registered MAE wins or produced honest scorecards):**
{chr(10).join(f"- {x}" for x in verdict.get("earned") or ["(none)"])}

**Not earned:**
{chr(10).join(f"- {x}" for x in verdict.get("not_earned") or ["(none)"])}

| Gate | Status |
|------|--------|
| Phase 4 infrastructure unblocked | **{"YES" if verdict.get("phase4_infrastructure_unblocked") else "NO"}** |
| Phase 4 model-value claim unblocked | **{"YES" if verdict.get("phase4_model_claim_unblocked") else "NO"}** |

{verdict.get("note") or ""}

## Watchlist rule

Fixed per era: top 5 prior-year volume at each of QB / RB / WR / TE (pass yards / rush+rec / rec yards). Not cherry-picked after errors.

## Data gaps

{chr(10).join(f"- {g}" for g in unique_gaps) if unique_gaps else "- (none logged)"}

## Fantasy consensus

Skipped cleanly — no historical consensus ADP/projection archive in-repo for 2019–2025.

## Artifacts

- `{args.out_dir}/run_stamp.json`
- `{args.out_dir}/scorecards.json`
- `{args.out_dir}/pooled.json`
- `{args.out_dir}/verdict.json`
- Depth packs: `services/model-service/src/services/nfl_season_engine/data/historical/`

## How to re-run

```bash
DATABASE_URL=postgresql+psycopg://ryankos:postgres@127.0.0.1:5432/kosedge \\
  python scripts/nfl/run_historical_replay_benchmark.py \\
    --seasons 2019-2025 --n-sims 40 --package-depth
```

## Explicit non-goals (this pass)

- No Phase 4 full calibration suite beyond reporting replay metrics
- No Decision Engine unlock from coherence alone
- No freezing 2026 baseline
- No team-specific sculpture to improve historical scores
"""
    args.ops_md.write_text(md, encoding="utf-8")
    print(f"Wrote ops report {args.ops_md}")
    print(json.dumps(verdict, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
