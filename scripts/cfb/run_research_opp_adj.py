#!/usr/bin/env python3
"""Research-only CFB opponent-adjusted O/D EPA (on top of #559).

Reproducible entrypoint. Does not touch production SP+, NFL, or KEI.

  PYTHONPATH=services/model-service python scripts/cfb/run_research_opp_adj.py \\
      --as-of 20260915 --write-ops

No CFBD. No Mac HD required. Historical restore lands under
data/cfb/research/pbp_hist/as_of_YYYYMMDD/ (gitignored).
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


def _write(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _sha256(path: Path, *, chunk: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            block = fh.read(chunk)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def _artifact_checksums(paths: list[Path]) -> dict:
    out = {}
    for path in paths:
        if not path.exists():
            continue
        out[path.name] = {
            "path": str(path),
            "sha256": _sha256(path),
            "bytes": path.stat().st_size,
        }
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--as-of", default="20260915")
    parser.add_argument("--as-of-week", type=int, default=3)
    parser.add_argument("--skip-hist", action="store_true")
    parser.add_argument("--skip-2026", action="store_true")
    parser.add_argument("--skip-validate", action="store_true")
    parser.add_argument("--allow-fetch", action="store_true", default=True)
    parser.add_argument("--no-fetch", action="store_true")
    parser.add_argument("--write-ops", action="store_true")
    parser.add_argument("--seasons", default="2014-2025")
    args = parser.parse_args(argv)

    allow_fetch = bool(args.allow_fetch) and not args.no_fetch
    as_of = "".join(ch for ch in args.as_of if ch.isdigit())[:8]

    from src.services.cfb_warehouse.current_season_2026 import (
        assert_not_historical_write,
        research_dest_dir,
        schedule_game_rows,
        load_schedule_frame,
        restore_2026_pbp,
        restore_2026_schedule,
        pbp_game_ids,
    )
    from src.services.cfb_warehouse.delayed_game_verify import (
        DELAYED_GAME_ID,
        audit_pbp_vs_official_final,
        verify_delayed_game,
        should_exclude_snapshot_game,
    )
    from src.services.cfb_warehouse.paths import REPO_ROOT, hd_pbp_hist_research_target
    from src.services.cfb_warehouse.research_hist_features import (
        HIST_SEASONS,
        restore_and_build,
        rows_to_team_game_epa,
        load_restored_epa_games,
    )
    from src.services.cfb_warehouse.research_opp_adj import (
        AdjParams,
        ESTIMATOR_ID,
        PIPELINE_VERSION,
        aggregate_team_game_epa,
    )
    from src.services.cfb_warehouse.research_opp_adj_validate import (
        HOLDOUT_SEASON,
        apply_to_season,
        build_season_finals,
        run_validation_suite,
    )
    from src.services.cfb_warehouse.team_game_w1_2026 import (
        load_pbp_records,
        run_research_pipeline,
    )

    ops = REPO_ROOT / "data" / "ops" / f"cfb-research-opp-adj-epa-{as_of}"
    ops.mkdir(parents=True, exist_ok=True)
    assert_not_historical_write(ops)

    print("== 1. Delayed-game close (401868140) ==", flush=True)
    verdict = verify_delayed_game(fetch=True)
    _write(ops / "delayed_game_verification.json", verdict)
    print(
        f"decision={verdict['decision_on_559_snapshot']} "
        f"old={verdict['old_status']} {verdict['old_score']} "
        f"official={verdict['official_status']} {verdict['official_score']}",
        flush=True,
    )

    hist_dest = None
    hist_inv = None
    if not args.skip_hist:
        print("== 2. Historical restore + raw features ==", flush=True)
        start, end = (int(x) for x in args.seasons.split("-"))
        seasons = tuple(s for s in HIST_SEASONS if start <= s <= end)
        hist = restore_and_build(
            as_of=as_of, seasons=seasons, allow_fetch=allow_fetch, write_artifacts=True
        )
        hist_dest = Path(hist["dest"])
        hist_inv = hist["inventory"]
        _write(ops / "hist_inventory.json", hist_inv)
        print(
            f"hist dest={hist_dest} games={hist_inv['totals']['games']} "
            f"play_delta={hist_inv['totals']['play_delta_vs_aug13']} "
            f"hd_mirror={hd_pbp_hist_research_target(as_of)}",
            flush=True,
        )

    report = None
    selected = None
    if not args.skip_validate:
        print("== 3/4/5. Pregame cutoff validation (holdout untouched) ==", flush=True)
        if hist_dest is None:
            from src.services.cfb_warehouse.paths import pbp_hist_research_dir

            hist_dest = pbp_hist_research_dir(as_of)
        epa_rows = load_restored_epa_games(hist_dest)
        games = rows_to_team_game_epa(epa_rows)
        if not games:
            raise SystemExit(f"no historical EPA team-games at {hist_dest}")
        report = run_validation_suite(games, dest=ops)
        selected = AdjParams(**report["selection"]["selected"])
        rec = report["recommendation"]["recommendation"]
        print(
            f"selected={report['selection']['selected']} "
            f"holdout_mae={report['holdout']['mean_mae']} "
            f"unadj={report['holdout']['mean_mae_unadj']} "
            f"blend={report['holdout']['mean_mae_blend']} "
            f"recommendation={rec}",
            flush=True,
        )

    apply_2026 = None
    closed_559 = None
    if hist_dest is None:
        from src.services.cfb_warehouse.paths import pbp_hist_research_dir

        hist_dest = pbp_hist_research_dir(as_of)
    if not args.skip_2026:
        print("== 6. Frozen method → 2026 (research) ==", flush=True)
        dest_2026 = research_dest_dir(as_of)
        dest_2026.mkdir(parents=True, exist_ok=True)
        pbp_path = restore_2026_pbp(dest_dir=dest_2026, force=False)
        sched_path = restore_2026_schedule(dest_dir=dest_2026, force=False)
        closed_559 = run_research_pipeline(
            as_of=as_of,
            as_of_week=int(args.as_of_week),
            dest_dir=dest_2026,
            allow_fetch=False,
            pbp_path=pbp_path,
            schedule_path=sched_path,
            write_artifacts=True,
            commit_ops=False,
        )
        plays_all = load_pbp_records(pbp_path)
        pbp_audit = audit_pbp_vs_official_final(plays_all)
        _write(ops / "delayed_game_pbp_audit.json", pbp_audit)
        verdict = verify_delayed_game(fetch=False, live_summary=verdict.get("live_fetch"), plays=plays_all)
        verdict["pbp_sha256"] = closed_559["manifest"].get("pbp_sha256")
        _write(ops / "delayed_game_verification.json", verdict)
        # Belt: drop 401868140 unless PBP is complete through official 49-7.
        manifest = closed_559["manifest"]
        sched_by_id = {
            str(r.get("game_id")): r
            for r in schedule_game_rows(load_schedule_frame(sched_path))
        }
        pbp_ok = bool(pbp_audit.get("complete_through_final"))
        dropped = [
            gid
            for gid in list(manifest.get("eligible_game_ids") or [])
            if should_exclude_snapshot_game(
                gid,
                status=(sched_by_id.get(str(gid)) or {}).get("status_raw"),
                home_score=(sched_by_id.get(str(gid)) or {}).get("home_score"),
                away_score=(sched_by_id.get(str(gid)) or {}).get("away_score"),
                pbp_complete=pbp_ok if str(gid) == DELAYED_GAME_ID else None,
            )
        ]
        if dropped:
            manifest["eligible_game_ids"] = [
                g for g in manifest["eligible_game_ids"] if g not in dropped
            ]
            manifest["eligible_count"] = len(manifest["eligible_game_ids"])
            manifest["delayed_game_exclusions"] = dropped
        _write(ops / "closed_559_validation.json", closed_559["validation"])
        _write(
            ops / "closed_559_eligibility_summary.json",
            {
                "eligible_count": manifest.get("eligible_count"),
                "reason_counts": manifest.get("reason_counts"),
                "delayed_game_id": DELAYED_GAME_ID,
                "delayed_included": DELAYED_GAME_ID in set(manifest.get("eligible_game_ids") or []),
                "pbp_complete_through_final": pbp_ok,
                "pbp_max_period": pbp_audit.get("max_period"),
                "pbp_last_score": {
                    "home": pbp_audit.get("max_home_score"),
                    "away": pbp_audit.get("max_away_score"),
                },
                "fail_closed": True,
            },
        )

        eligible_ids = set(manifest.get("eligible_game_ids") or [])
        plays = [
            p
            for p in plays_all
            if str(p.get("game_id")) in eligible_ids
            and not should_exclude_snapshot_game(
                p.get("game_id"),
                status=(sched_by_id.get(str(p.get("game_id"))) or {}).get("status_raw"),
                home_score=(sched_by_id.get(str(p.get("game_id"))) or {}).get("home_score"),
                away_score=(sched_by_id.get(str(p.get("game_id"))) or {}).get("away_score"),
                pbp_complete=pbp_ok if str(p.get("game_id")) == DELAYED_GAME_ID else None,
            )
        ]
        games_2026 = aggregate_team_game_epa(plays)
        params = selected or AdjParams()
        prior_fit = None
        if hist_dest is not None:
            hist_games = rows_to_team_game_epa(load_restored_epa_games(hist_dest))
            finals = build_season_finals(hist_games, [2024, 2025], params)
            prior_fit = finals.get(2025) or finals.get(2024)
        apply_2026 = apply_to_season(
            games_2026,
            season=2026,
            as_of_week=int(args.as_of_week),
            params=params,
            prior_fit=prior_fit,
        )
        apply_2026["eligible_2026_games"] = len({g.game_id for g in games_2026})
        apply_2026["delayed_game_excluded_if_incomplete"] = True
        apply_2026["estimator_id"] = ESTIMATOR_ID
        _write(ops / "cfb_2026_adj_epa.json", apply_2026)
        print(
            f"2026 teams={apply_2026['n_teams']} "
            f"obs={apply_2026['n_obs']} mu={apply_2026['mu']:.4f} "
            f"hfa={apply_2026['hfa']:.4f}",
            flush=True,
        )

    checksum_paths = [
        ops / "validation_report.json",
        ops / "cfb_2026_adj_epa.json",
        ops / "closed_559_eligibility_summary.json",
        ops / "delayed_game_pbp_audit.json",
    ]
    if hist_dest is not None:
        checksum_paths.append(Path(hist_dest) / "team_game_epa_eligible.parquet")
    checksums = _artifact_checksums(checksum_paths)
    _write(ops / "artifact_checksums.json", checksums)

    summary = {
        "pipeline_version": PIPELINE_VERSION,
        "estimator_id": ESTIMATOR_ID,
        "pre_fix_holdout_mae_not_frozen": True,
        "as_of": as_of,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "research_only": True,
        "not_ke_ratings": True,
        "production_sp_plus_unchanged": True,
        "production_nfl_unchanged": True,
        "production_kei_unchanged": True,
        "cfbd_used": False,
        "delayed_game": {
            "game_id": verdict["game_id"],
            "decision": verdict["decision_on_559_snapshot"],
            "reason": verdict["reason"],
        },
        "recommendation": None if report is None else report.get("recommendation"),
        "holdout_season": HOLDOUT_SEASON,
        "closed_559_eligible_games": None
        if closed_559 is None
        else (closed_559.get("manifest") or {}).get("eligible_count"),
        "apply_2026_teams": None if apply_2026 is None else apply_2026.get("n_teams"),
        "apply_2026_obs": None if apply_2026 is None else apply_2026.get("n_obs"),
        "artifact_checksums": checksums,
        "ops": str(ops),
    }
    _write(ops / "summary.json", summary)
    checksums["summary.json"] = {
        "path": str(ops / "summary.json"),
        "sha256": _sha256(ops / "summary.json"),
        "bytes": (ops / "summary.json").stat().st_size,
    }
    _write(ops / "artifact_checksums.json", checksums)
    if args.write_ops:
        print(f"ops written → {ops}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
