#!/usr/bin/env python3
"""Re-report #560 holdout with IBF-v1 baselines (independent of candidate μ).

Frozen knobs only. No PARAM_GRID. Same 2025 obs keys as ryan_audit_560.json.

  PYTHONPATH=services/model-service python3 scripts/cfb/run_research_opp_adj_clean_baselines.py \\
      --as-of 20260915 --write-ops
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MS = ROOT / "services" / "model-service"
if str(MS) not in sys.path:
    sys.path.insert(0, str(MS))

OPS_560 = ROOT / "data" / "ops" / "cfb-research-opp-adj-epa-20260915"
PREV_OBS_SHA = "009ce549ab9e0b0b5a94aa0bdc88b0c9d57d11e156c291634dca5e08f2532508"


def _write(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _sha_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            block = fh.read(1024 * 1024)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--as-of", default="20260915")
    parser.add_argument("--write-ops", action="store_true")
    parser.add_argument("--hist-dir", default="")
    args = parser.parse_args(argv)

    from src.services.cfb_warehouse.paths import REPO_ROOT, pbp_hist_research_dir
    from src.services.cfb_warehouse.research_hist_features import (
        HIST_SEASONS,
        load_restored_epa_games,
        load_season_frame,
        rows_to_team_game_epa,
    )
    from src.services.cfb_warehouse.research_opp_adj import aggregate_team_game_epa
    from src.services.cfb_warehouse.research_opp_adj import AdjParams
    from src.services.cfb_warehouse.research_opp_adj_validate import (
        HOLDOUT_SEASON,
        IBF_RULE,
        IBF_RULE_ID,
        build_season_finals,
        evaluate_seasons,
        independent_league_raw_mean,
    )

    as_of = "".join(ch for ch in args.as_of if ch.isdigit())[:8]
    hist = Path(args.hist_dir) if args.hist_dir else pbp_hist_research_dir(as_of)
    epa_rows = load_restored_epa_games(hist)
    if epa_rows:
        games = rows_to_team_game_epa(epa_rows)
    else:
        games = []
        for season in HIST_SEASONS:
            raw = hist / f"play_by_play_{int(season)}.parquet"
            if not raw.exists():
                continue
            df = load_season_frame(raw)
            recs = df.to_dict(orient="records")
            for rec in recs:
                gid = rec.get("game_id")
                if gid is not None:
                    rec["game_id"] = str(gid).split(".")[0]
            games.extend(aggregate_team_game_epa(recs))
            print(f"built epa games {season}: running n={len(games)}", flush=True)
    if not games:
        raise SystemExit(f"no historical EPA team-games at {hist}")

    holdout = [g for g in games if g.season == HOLDOUT_SEASON and not g.fcs_offense]
    lines = [
        f"{g.season}\t{g.week}\t{g.game_id}\t{g.offense}\t{g.defense}\t{g.home:.6f}"
        for g in sorted(holdout, key=lambda g: (g.week, g.game_id, g.offense, g.defense))
    ]
    blob = "\n".join(lines) + "\n"
    obs_sha = _sha_text(blob)

    frozen = AdjParams(lam=40.0, prior_n0=4.0, prior_decay=0.75, iters=12)
    seasons = sorted({g.season for g in games if g.season <= HOLDOUT_SEASON})
    finals = build_season_finals(games, seasons, frozen)
    ev = evaluate_seasons(games, (HOLDOUT_SEASON,), frozen, finals=finals)
    ibf = independent_league_raw_mean(games)

    prev = {}
    prev_path = OPS_560 / "frozen_method.json"
    if prev_path.exists():
        prev = json.loads(prev_path.read_text())
    prev_hold = (prev.get("holdout_2025") or {}) if prev else {}
    prev_report = {}
    report_path = OPS_560 / "validation_report.json"
    if report_path.exists():
        prev_report = json.loads(report_path.read_text()).get("holdout") or {}

    def _delta(new: float | None, old: float | None) -> float | None:
        if new is None or old is None:
            return None
        return float(new) - float(old)

    clean = {
        "pipeline_version": "cfb-research-opp-adj-epa-v1-ibf",
        "research_only": True,
        "production_promote": False,
        "as_of": as_of,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "ibf": {
            "rule_id": IBF_RULE_ID,
            "rule": IBF_RULE,
            "fallback_value": ibf,
            "uses_candidate_mu": False,
        },
        "obs_keys_sha256": obs_sha,
        "obs_keys_match_560": obs_sha == PREV_OBS_SHA,
        "n_holdout_obs": len(holdout),
        "n_unique_games": len({g.game_id for g in holdout}),
        "holdout": ev,
        "previous_coupled_mu_fallback": {
            "source": "data/ops/cfb-research-opp-adj-epa-20260915/frozen_method.json",
            "mae_adj": prev_hold.get("mae_adj"),
            "mae_unadj": prev_hold.get("mae_unadj"),
            "mae_blend": prev_hold.get("mae_blend"),
            "rel_vs_unadj": prev_hold.get("rel_vs_unadj"),
            "rel_vs_blend": prev_hold.get("rel_vs_blend"),
            "note": (
                "5 defender rows used adj-model μ when STD and prior-season "
                "raw were missing. Offense unadj/blend was bit-identical; "
                "defense ticked. See ryan_audit_560.json."
            ),
        },
        "delta_vs_previous": {
            "mae_adj": _delta(ev.get("mean_mae"), prev_hold.get("mae_adj")),
            "mae_unadj": _delta(ev.get("mean_mae_unadj"), prev_hold.get("mae_unadj")),
            "mae_blend": _delta(ev.get("mean_mae_blend"), prev_hold.get("mae_blend")),
            "claim_old_pair_mae_improvement": False,
            "note": (
                "Do not claim the old 12.4% / 8.9% pair-MAE cut if unadj/blend "
                "moved. Adj MAE should be unchanged (candidate untouched)."
            ),
            "previous_unadj_off_mae": ((prev_report.get("unadjusted_std") or {}).get("off") or {}).get("mae"),
            "previous_unadj_def_mae": ((prev_report.get("unadjusted_std") or {}).get("def") or {}).get("mae"),
        },
        "frozen_knobs": {
            "lam": 40.0,
            "n0": 4.0,
            "decay": 0.75,
            "retuned": False,
        },
    }
    adj = ev.get("mean_mae")
    raw = ev.get("mean_mae_unadj")
    blend = ev.get("mean_mae_blend")
    rel_raw = ((raw - adj) / raw) if adj is not None and raw else None
    rel_blend = ((blend - adj) / blend) if adj is not None and blend else None
    clean["clean_holdout_pair_mae"] = {
        "mae_adj": adj,
        "mae_unadj": raw,
        "mae_blend": blend,
        "rel_vs_unadj": rel_raw,
        "rel_vs_blend": rel_blend,
    }

    dest = REPO_ROOT / "data" / "ops" / f"cfb-research-eff-scoring-{as_of}"
    if args.write_ops:
        dest.mkdir(parents=True, exist_ok=True)
        (dest / "holdout_2025_obs_keys.tsv").write_text(blob, encoding="utf-8")
        _write(dest / "epa_clean_baselines.json", clean)
        checksums = {
            "epa_clean_baselines.json": {
                "sha256": _sha256(dest / "epa_clean_baselines.json"),
                "bytes": (dest / "epa_clean_baselines.json").stat().st_size,
            },
            "holdout_2025_obs_keys.tsv": {
                "sha256": _sha256(dest / "holdout_2025_obs_keys.tsv"),
                "bytes": (dest / "holdout_2025_obs_keys.tsv").stat().st_size,
            },
        }
        _write(dest / "epa_clean_checksums.json", checksums)
        print(f"ops written → {dest}", flush=True)

    print(
        f"n={len(holdout)} sha_match={clean['obs_keys_match_560']} "
        f"adj={adj} unadj={raw} blend={blend} "
        f"d_unadj={clean['delta_vs_previous']['mae_unadj']} "
        f"ibf={ibf}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
