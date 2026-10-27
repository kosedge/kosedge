"""Week slate: current-input fail-closed, plus t4564u research emit with flags."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.services.nfl_model_forecast_emit.completeness import (
    assert_week_inputs_complete,
    audit_week_inputs,
    week_games_from_canonical,
)
from src.services.nfl_model_forecast_emit.dest import (
    make_run_id,
    research_runs_root,
    run_dir_for,
)
from src.services.nfl_model_forecast_emit.emit import (
    ForecastIncompleteError,
    canonicalize,
    emit_model_forecast,
    format_utc,
    parse_utc,
    resolve_code_tip_sha,
)
from src.services.nfl_model_forecast_emit.engine_adapter import (
    inputs_from_engine_projection,
)
from src.services.nfl_model_forecast_emit.schema import (
    CERT_CANDIDATE,
    FILE_MODE_READONLY,
    LABEL,
    SOP_4A017F22,
)
from src.services.nfl_season_engine import (
    DEFAULT_SEASON_ENGINE_VERSION,
    build_packaged_real_universe,
    project_game_player_boxes,
)
from src.services.nfl_season_engine.sim_depth import HONEST_PRECISION_MIN_N, prob_to_american


def run_week_slate(
    *,
    season: int = 2026,
    week: int = 8,
    dest_dir: Optional[Path] = None,
    now_utc: Any = None,
    n_replicates: Optional[int] = None,
) -> Dict[str, Any]:
    """Current-input slate. Fail-closed when the W8 audit is incomplete."""
    del dest_dir, n_replicates
    report = audit_week_inputs(season=season, week=week, now_utc=now_utc)
    if not report["ok"]:
        raise ForecastIncompleteError(
            "t4559u current-input slate blocked: "
            + ", ".join(report["failing_components"]),
            gap="G8",
            reason="slate_inputs_incomplete",
        )
    raise ForecastIncompleteError(
        "current-input slate projection is reserved until inputs_complete",
        gap="G8",
        reason="slate_projection_not_armed",
    )


def audit_or_raise(**kwargs: Any) -> Dict[str, Any]:
    return assert_week_inputs_complete(**kwargs)


def _engine_team(token: str) -> str:
    return "LA" if token == "LAR" else token


def _missing_from_audit(report: Dict[str, Any], *, n_replicates: int) -> List[Dict[str, str]]:
    flags: List[Dict[str, str]] = []
    for check in report.get("checks") or []:
        if check.get("ok"):
            continue
        flags.append(
            {
                "name": str(check.get("name") or ""),
                "reason": str(check.get("blocker") or ""),
            }
        )
    if int(n_replicates) < int(HONEST_PRECISION_MIN_N):
        flags.append(
            {
                "name": "n_replicates_below_honest_precision",
                "reason": (
                    f"n_replicates={n_replicates} < HONEST_PRECISION_MIN_N="
                    f"{HONEST_PRECISION_MIN_N} (research depth, CERT=0)"
                ),
            }
        )
    return flags


def _latest_input_as_of(report: Dict[str, Any]) -> str:
    latest = None
    for check in report.get("checks") or []:
        ev = check.get("evidence") or {}
        for key in ("as_of_timestamp", "as_of", "daily_intel_as_of"):
            raw = ev.get(key)
            if not raw:
                continue
            dt = parse_utc(raw if "T" in str(raw) else f"{raw}T00:00:00Z")
            if dt and (latest is None or dt > latest):
                latest = dt
    if latest is None:
        latest = parse_utc("2026-08-29T00:00:00Z")
    return format_utc(latest)


def emit_research_week_slate(
    *,
    season: int = 2026,
    week: int = 8,
    n_replicates: int = 40,
    seed: int = 7,
    now_utc: Any = None,
    dest_root: Optional[Path] = None,
    code_tip_sha: Optional[str] = None,
) -> Dict[str, Any]:
    """Packaged-engine G1–G8 emit with explicit missing_inputs. CERT=0."""
    now = parse_utc(now_utc) or datetime.now(timezone.utc).replace(microsecond=0)
    forecast_ts = format_utc(now)
    tip = resolve_code_tip_sha(code_tip_sha)
    report = audit_week_inputs(season=season, week=week, now_utc=forecast_ts)
    games = week_games_from_canonical(season, week)
    if not games:
        raise ForecastIncompleteError(
            f"no canonical games for {season} W{week}",
            gap="G1",
            reason="slate_empty",
        )
    missing = _missing_from_audit(report, n_replicates=n_replicates)
    latest_s = _latest_input_as_of(report)

    universe = build_packaged_real_universe(season)
    notes = dict(universe.notes or {})
    extra_fp: Dict[str, str] = {}
    if notes.get("pack_sha256"):
        extra_fp["pack_sha256"] = str(notes["pack_sha256"])
    if notes.get("depth_sha256"):
        extra_fp["depth_sha256"] = str(notes["depth_sha256"])

    run_id = make_run_id(
        season=season,
        week=week,
        forecast_ts_utc=forecast_ts,
        code_tip_sha=tip,
    )
    dest = run_dir_for(run_id, root=dest_root or research_runs_root())
    dest.mkdir(parents=True, exist_ok=True)

    artifacts: List[Dict[str, Any]] = []
    for game in games:
        home = str(game["home_team"])
        away = str(game["away_team"])
        proj = project_game_player_boxes(
            universe,
            home_team=_engine_team(home),
            away_team=_engine_team(away),
            week=week,
            n_replicates=int(n_replicates),
            seed=int(seed),
        )
        payload = {
            "game_id": proj.game_id,
            "home_team": proj.home_team,
            "away_team": proj.away_team,
            "season": proj.season,
            "week": proj.week,
            "engine_version": proj.engine_version or DEFAULT_SEASON_ENGINE_VERSION,
            "n_replicates": proj.n_replicates,
            "mode": notes.get("mode") or "packaged_real",
            "notes": dict(proj.notes or {}) | notes,
            "game_script_summary": dict(proj.game_script_summary or {}),
        }
        inputs = inputs_from_engine_projection(
            payload,
            kickoff_utc=game["kickoff_utc"],
            latest_input_as_of=latest_s,
            code_tip_sha=tip,
            extra_fingerprints=extra_fp or None,
        )
        inputs["game_id"] = game["game_id"]
        inputs["home_team"] = home
        inputs["away_team"] = away
        inputs["missing_inputs"] = missing
        inputs["forecast_ts_utc"] = forecast_ts
        ml = inputs["markets"].get("moneyline")
        if isinstance(ml, dict) and "home_ml" not in ml:
            hp = float(ml["prediction"])
            ml["home_ml"] = prob_to_american(hp)
            ml["away_ml"] = prob_to_american(max(0.0, min(1.0, 1.0 - hp)))
        dest_path = dest / f"{game['game_id']}.json"
        art = emit_model_forecast(inputs, dest_path=dest_path)
        sidecar = dest_path.with_name(dest_path.name + ".record_sha256")
        artifacts.append(
            {
                "game_id": art["game_id"],
                "path": str(dest_path),
                "record_sha256": sidecar.read_text(encoding="utf-8").strip(),
                "spread": (art.get("markets") or {}).get("spread", {}).get("prediction"),
                "total": (art.get("markets") or {}).get("total", {}).get("prediction"),
                "home_win_prob": (art.get("markets") or {}).get("moneyline", {}).get(
                    "prediction"
                ),
            }
        )

    manifest = {
        "schema_version": "nfl-model-forecast-research-run-v1",
        "label": LABEL,
        "cert_candidate": CERT_CANDIDATE,
        "sop": SOP_4A017F22,
        "run_id": run_id,
        "forecast_ts_utc": forecast_ts,
        "season": season,
        "week": week,
        "n_replicates": int(n_replicates),
        "seed": int(seed),
        "code_tip_sha": tip,
        "engine_version": DEFAULT_SEASON_ENGINE_VERSION,
        "inputs_complete": False,
        "missing_inputs": missing,
        "peer_agent": "bc-e1ed23ad-d814-5e4b-be93-0c97072a5bcd",
        "note": (
            "t4564u research emit. Packaged engine numbers with explicit "
            "missing-input flags. Not a current-W8 CLEAR. F2/#641 untouched."
        ),
        "artifacts": artifacts,
        "dest": str(dest),
    }
    man_path = dest / "MANIFEST.json"
    man_path.write_text(canonicalize(manifest) + "\n", encoding="utf-8")
    os.chmod(man_path, FILE_MODE_READONLY)

    completeness_path = dest / "INPUT_COMPLETENESS.json"
    completeness_path.write_text(canonicalize(report) + "\n", encoding="utf-8")
    os.chmod(completeness_path, FILE_MODE_READONLY)

    return {
        "run_id": run_id,
        "dest": str(dest),
        "n": len(artifacts),
        "missing_inputs": [m["name"] for m in missing],
        "artifacts": artifacts,
        "cert_candidate": CERT_CANDIDATE,
        "sop": SOP_4A017F22,
        "forecast_ts_utc": forecast_ts,
    }
