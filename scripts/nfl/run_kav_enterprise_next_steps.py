#!/usr/bin/env python3
"""KAV enterprise next steps (local, DB-first).

1. Snapshot before supervised metrics + board grading baseline
2. Retrain supervised schema v3 (KAV FEATURE_KEYS) via run_nfl_supervised_retrain
3. Re-sim 2025 boards with KAV-wired market sim path (bounded sim count)
4. Re-grade open/close vs model; write before/after ops report under data/ops/nfl-kav-*

No Odds API pulls. Densify only if grading coverage is broken (not in this script).

Usage:
  DATABASE_URL=postgresql+psycopg://ryankos:postgres@127.0.0.1:5432/kosedge \\
    /Users/ryankos/kosedge/.venv/bin/python scripts/nfl/run_kav_enterprise_next_steps.py

Env knobs:
  NFL_KAV_RESIM_SEASON=2025
  NFL_KAV_RESIM_SIMS=1000
  NFL_KAV_RESIM_MIN_DATE=2025-09-01
  NFL_KAV_SKIP_RESIM=0
  NFL_KAV_SKIP_RETRAIN=0
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))
os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg://ryankos:postgres@127.0.0.1:5432/kosedge"
)

from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from src.services.nfl_supervised_retrain import (  # noqa: E402
    FEATURE_KEYS,
    MODEL_SCHEMA_VERSION,
)
from src.tasks import (  # noqa: E402
    DEFAULT_NFL_MODEL_VERSION,
    run_nfl_market_simulations,
    run_nfl_supervised_retrain,
)

OUT_DIR = ROOT / "data" / "ops"
TS = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
CHECKPOINT = OUT_DIR / f"nfl-kav-enterprise-next-{TS}.json"
REPORT_MD = OUT_DIR / "nfl-kav-enterprise-next-report.md"
REPORT_JSON = OUT_DIR / "nfl-kav-enterprise-next-report.json"
GRADING_BEFORE = OUT_DIR / "nfl-kav-grading-before.json"
GRADING_AFTER = OUT_DIR / "nfl-kav-grading-after.json"
SUPERVISED_OUT = OUT_DIR / "nfl-kav-supervised-retrain-v3.json"


def _engine():
    url = os.environ["DATABASE_URL"]
    if url.startswith("postgresql://") and "+psycopg" not in url:
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    return create_engine(url)


def _snapshot_active_fit(conn) -> Dict[str, Any]:
    row = conn.execute(
        text(
            """
            SELECT model_version, train_rows, test_rows, created_at,
                   metrics, payload->>'schema_version' AS schema_version,
                   jsonb_array_length(COALESCE(payload->'feature_keys','[]'::jsonb)) AS n_features,
                   (payload->'feature_keys') ? 'diff_kav_net_5g' AS has_kav_feature
            FROM nfl_supervised_model_fits
            WHERE is_active = true
            ORDER BY created_at DESC
            LIMIT 1
            """
        )
    ).mappings().first()
    if not row:
        return {}
    metrics = row["metrics"] if isinstance(row["metrics"], dict) else {}
    return {
        "model_version": row["model_version"],
        "train_rows": row["train_rows"],
        "test_rows": row["test_rows"],
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        "schema_version": int(row["schema_version"] or 0) or None,
        "n_features": int(row["n_features"] or 0),
        "has_kav_feature": bool(row["has_kav_feature"]),
        "metrics": {
            "train_brier": metrics.get("train_brier"),
            "test_brier": metrics.get("test_brier"),
            "train_margin_mae": metrics.get("train_margin_mae"),
            "test_margin_mae": metrics.get("test_margin_mae"),
            "train_total_mae": metrics.get("train_total_mae"),
            "test_total_mae": metrics.get("test_total_mae"),
        },
    }


def _db_inventory(conn) -> Dict[str, Any]:
    def scalar(sql: str) -> int:
        return int(conn.execute(text(sql)).scalar() or 0)

    return {
        "nfl_dp_schedules": scalar("SELECT count(*) FROM nfl_dp_schedules"),
        "nfl_dp_team_kav_weekly": scalar("SELECT count(*) FROM nfl_dp_team_kav_weekly"),
        "nfl_dp_team_kav_game": scalar("SELECT count(*) FROM nfl_dp_team_kav_game"),
        "matchup_with_kav": scalar(
            "SELECT count(*) FROM nfl_dp_matchup_features_weekly WHERE home_kav_net_5g IS NOT NULL"
        ),
        "matchup_total": scalar("SELECT count(*) FROM nfl_dp_matchup_features_weekly"),
        "odds_snapshots": scalar("SELECT count(*) FROM odds_snapshots"),
        "nfl_market_projections": scalar("SELECT count(*) FROM nfl_market_projections"),
        "games_nfl": scalar(
            """
            SELECT count(*) FROM games g
            JOIN seasons s ON s.id = g.season_id
            JOIN leagues l ON l.id = s.league_id
            WHERE l.code = 'nfl'
            """
        ),
    }


def _copy_existing_grading_baseline() -> Optional[str]:
    src = OUT_DIR / "nfl-odds-open-close-grading.json"
    if not src.exists():
        return None
    shutil.copy2(src, GRADING_BEFORE)
    return str(GRADING_BEFORE)


def _delete_season_projections(conn, *, season: int, min_date: str, model_version: str) -> int:
    result = conn.execute(
        text(
            """
            DELETE FROM nfl_market_projections p
            USING games g, seasons s, leagues l
            WHERE p.game_id = g.id
              AND g.season_id = s.id
              AND s.league_id = l.id
              AND l.code = 'nfl'
              AND s.season_year = :season
              AND g.game_date >= CAST(:min_date AS date)
              AND p.model_version = :model_version
            """
        ),
        {"season": season, "min_date": min_date, "model_version": model_version},
    )
    conn.commit()
    return int(result.rowcount or 0)


def _season_dates(conn, *, season: int, min_date: str) -> List[str]:
    rows = conn.execute(
        text(
            """
            SELECT DISTINCT g.game_date::text
            FROM games g
            JOIN seasons s ON s.id = g.season_id
            JOIN leagues l ON l.id = s.league_id
            WHERE l.code = 'nfl'
              AND s.season_year = :season
              AND g.game_date >= CAST(:min_date AS date)
            ORDER BY 1
            """
        ),
        {"season": season, "min_date": min_date},
    ).fetchall()
    return [str(r[0]) for r in rows]


def _write_report(payload: Dict[str, Any]) -> None:
    before_fit = payload.get("supervised_before") or {}
    after_fit = payload.get("supervised_after") or {}
    before_g = payload.get("grading_before") or {}
    after_g = payload.get("grading_after") or {}
    bm = (before_g.get("model") or {}) if isinstance(before_g, dict) else {}
    am = (after_g.get("model") or {}) if isinstance(after_g, dict) else {}
    sim = payload.get("resim") or {}

    def delta(a, b):
        if a is None or b is None:
            return None
        return round(float(b) - float(a), 4)

    lines = [
        "# NFL KAV Enterprise Next Steps Report",
        "",
        f"Generated: {payload.get('generated_at')}",
        f"Branch commit context: local `nfl-kav-sharpen`",
        f"DATABASE: `{os.environ.get('DATABASE_URL', '').split('@')[-1]}`",
        "",
        "## 1. Supervised retrain (schema v3 / KAV features)",
        "",
        f"- Path: `services/model-service/src/services/nfl_supervised_retrain.py` "
        f"(`FEATURE_KEYS`, `MODEL_SCHEMA_VERSION={MODEL_SCHEMA_VERSION}`)",
        f"- Task: `src.tasks.run_nfl_supervised_retrain` "
        f"(invoked by `scripts/nfl/run_kav_enterprise_next_steps.py`)",
        f"- Artifact: `{SUPERVISED_OUT.relative_to(ROOT)}`",
        f"- Feature count expected: **{len(FEATURE_KEYS)}** (includes `diff_kav_net_5g`)",
        "",
        "| | Before | After |",
        "| --- | --- | --- |",
        f"| Schema | {before_fit.get('schema_version')} | {after_fit.get('schema_version')} |",
        f"| Features | {before_fit.get('n_features')} (kav={before_fit.get('has_kav_feature')}) "
        f"| {after_fit.get('n_features')} (kav={after_fit.get('has_kav_feature')}) |",
        f"| Train / test rows | {before_fit.get('train_rows')} / {before_fit.get('test_rows')} "
        f"| {after_fit.get('train_rows')} / {after_fit.get('test_rows')} |",
        f"| Test Brier | {(before_fit.get('metrics') or {}).get('test_brier')} "
        f"| {(after_fit.get('metrics') or {}).get('test_brier')} |",
        f"| Test margin MAE | {(before_fit.get('metrics') or {}).get('test_margin_mae')} "
        f"| {(after_fit.get('metrics') or {}).get('test_margin_mae')} |",
        f"| Test total MAE | {(before_fit.get('metrics') or {}).get('test_total_mae')} "
        f"| {(after_fit.get('metrics') or {}).get('test_total_mae')} |",
        "",
        "## 2. Board re-sim (KAV-wired market path)",
        "",
        f"- Path: `src.tasks.run_nfl_market_simulations` "
        f"(matchup pack → `NflGameInputs` KAV fields → handicapping `kav_efficiency`)",
        f"- Season: {sim.get('season')} from {sim.get('min_date')}",
        f"- Simulations/game: {sim.get('simulations')}",
        f"- Days / games processed: {sim.get('days')} / {sim.get('games_processed')}",
        f"- Projections inserted: {sim.get('projections_inserted')}",
        f"- Prior projections deleted (same model_version window): {sim.get('deleted_prior_projections')}",
        f"- Wall time (resim): {sim.get('elapsed_sec')}s",
        "",
        "## 3. Odds grading before → after (DB-first)",
        "",
        f"- Before artifact: `{GRADING_BEFORE.name}` "
        f"(copied from prior `nfl-odds-open-close-grading.json` when present)",
        f"- After artifact: `{GRADING_AFTER.name}`",
        "",
        "| Metric | Before | After | Δ |",
        "| --- | --- | --- | --- |",
        f"| Spread MAE | {bm.get('spread_mae')} | {am.get('spread_mae')} | "
        f"{delta(bm.get('spread_mae'), am.get('spread_mae'))} |",
        f"| Total MAE | {bm.get('total_mae')} | {am.get('total_mae')} | "
        f"{delta(bm.get('total_mae'), am.get('total_mae'))} |",
        f"| ML Brier | {bm.get('ml_brier')} | {am.get('ml_brier')} | "
        f"{delta(bm.get('ml_brier'), am.get('ml_brier'))} |",
        f"| ATS hit | {bm.get('ats_hit_rate')} | {am.get('ats_hit_rate')} | "
        f"{delta(bm.get('ats_hit_rate'), am.get('ats_hit_rate'))} |",
        f"| CLV spread avg / +rate | {bm.get('clv_spread_avg')} / {bm.get('clv_spread_positive_rate')} "
        f"| {am.get('clv_spread_avg')} / {am.get('clv_spread_positive_rate')} | — |",
        f"| CLV total avg / +rate | {bm.get('clv_total_avg')} / {bm.get('clv_total_positive_rate')} "
        f"| {am.get('clv_total_avg')} / {am.get('clv_total_positive_rate')} | — |",
        "",
        "## 4. Inventory (DB-first; no odds pull)",
        "",
        "```json",
        json.dumps(payload.get("inventory") or {}, indent=2),
        "```",
        "",
        "## 5. Prod / PR checklist",
        "",
        "1. Open compare URL (no `gh` in this environment):",
        "   `https://github.com/kosedge/kosedge/compare/main...nfl-kav-sharpen`",
        "   (adjust org/repo if different).",
        "2. Promote local `kosedge` restore → prod warehouse (or re-ingest) with migration 041 + KAV tables.",
        "3. Run supervised retrain + 2025 re-sim against prod with the same script knobs.",
        "4. Only densify owned open/close gaps via Odds API if grading `owned_open_close_games` collapses;",
        "   2024–25 were already dense in the prior sprint report.",
        "",
        f"Checkpoint JSON: `{CHECKPOINT.relative_to(ROOT)}`",
        "",
    ]
    REPORT_MD.write_text("\n".join(lines) + "\n")
    REPORT_JSON.write_text(json.dumps(payload, indent=2, default=str) + "\n")


def main() -> int:
    season = int(os.getenv("NFL_KAV_RESIM_SEASON", "2025"))
    simulations = int(os.getenv("NFL_KAV_RESIM_SIMS", "1000"))
    min_date = os.getenv("NFL_KAV_RESIM_MIN_DATE", f"{season}-09-01")
    skip_resim = os.getenv("NFL_KAV_SKIP_RESIM", "0") == "1"
    skip_retrain = os.getenv("NFL_KAV_SKIP_RETRAIN", "0") == "1"
    model_version = DEFAULT_NFL_MODEL_VERSION

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    engine = _engine()
    Session = sessionmaker(bind=engine)
    payload: Dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model_version": model_version,
        "feature_count_expected": len(FEATURE_KEYS),
        "schema_version_expected": MODEL_SCHEMA_VERSION,
        "steps": [],
    }

    with engine.connect() as conn:
        payload["inventory"] = _db_inventory(conn)
        payload["supervised_before"] = _snapshot_active_fit(conn)

    baseline = _copy_existing_grading_baseline()
    payload["grading_before_path"] = baseline
    if baseline and GRADING_BEFORE.exists():
        payload["grading_before"] = json.loads(GRADING_BEFORE.read_text())

    # --- Retrain ---
    if not skip_retrain:
        t0 = time.time()
        print("==> supervised retrain schema v3", flush=True)
        retrain = run_nfl_supervised_retrain.run(
            model_version=model_version,
            start_season=2013,
            end_season=2025,
        )
        retrain["elapsed_sec"] = round(time.time() - t0, 1)
        SUPERVISED_OUT.write_text(json.dumps(retrain, indent=2, default=str) + "\n")
        payload["supervised_retrain"] = retrain
        payload["steps"].append("retrain")
        print(json.dumps({"retrain_metrics": retrain.get("metrics")}, indent=2), flush=True)
    else:
        print("==> skip retrain", flush=True)

    with engine.connect() as conn:
        payload["supervised_after"] = _snapshot_active_fit(conn)

    # --- Re-sim ---
    resim_summary: Dict[str, Any] = {
        "season": season,
        "min_date": min_date,
        "simulations": simulations,
        "skipped": skip_resim,
    }
    if not skip_resim:
        session = Session()
        try:
            deleted = _delete_season_projections(
                session,
                season=season,
                min_date=min_date,
                model_version=model_version,
            )
            dates = _season_dates(session, season=season, min_date=min_date)
        finally:
            session.close()

        print(
            f"==> resim season={season} days={len(dates)} sims={simulations} deleted={deleted}",
            flush=True,
        )
        t0 = time.time()
        total_games = 0
        total_inserted = 0
        day_results = []
        for i, day in enumerate(dates, 1):
            result = run_nfl_market_simulations(
                game_date=day,
                simulations=simulations,
                model_version=model_version,
                include_completed_games=True,
                projection_created_at_mode="kickoff_minus_buffer",
                kickoff_buffer_minutes=30,
            )
            total_games += int(result.get("games_processed") or 0)
            total_inserted += int(result.get("projections_inserted") or 0)
            day_results.append({"game_date": day, **result})
            print(f"[{i}/{len(dates)}] {day}: {result}", flush=True)

        resim_summary.update(
            {
                "deleted_prior_projections": deleted,
                "days": len(dates),
                "games_processed": total_games,
                "projections_inserted": total_inserted,
                "elapsed_sec": round(time.time() - t0, 1),
                "results": day_results,
            }
        )
        payload["steps"].append("resim")
    payload["resim"] = resim_summary

    # --- Grade after ---
    print("==> grading after", flush=True)
    # Avoid circular import name collision with packaging
    import importlib.util

    grading_path = ROOT / "scripts" / "nfl" / "odds_open_close_grading.py"
    spec = importlib.util.spec_from_file_location("odds_open_close_grading_kav", grading_path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.OUT_JSON = GRADING_AFTER
    mod.OUT_MD = GRADING_AFTER.with_suffix(".md")
    mod.main()
    payload["grading_after"] = json.loads(GRADING_AFTER.read_text())
    payload["steps"].append("grade_after")

    CHECKPOINT.write_text(json.dumps(payload, indent=2, default=str) + "\n")
    _write_report(payload)
    print(f"wrote {REPORT_MD}", flush=True)
    print(f"wrote {REPORT_JSON}", flush=True)
    print(f"wrote {CHECKPOINT}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
