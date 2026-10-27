"""Map full-engine / handicap projection payloads onto emit inputs.

Does not call Odds. Does not invent close. Missing engine fields fail-closed
at emit time (G8).
"""

from __future__ import annotations

from typing import Any, Dict, Mapping, Optional

from src.services.nfl_model_forecast_emit.emit import (
    ForecastIncompleteError,
    sha256_hex,
)
from src.services.nfl_model_forecast_emit.schema import (
    MODEL_IDENTITY_SEASON_ENGINE,
    SPREAD_ORIENTATION,
    SPREAD_SIGN_CONVENTION,
)
from src.services.nfl_model_handicap import (
    extract_model_markets_from_projection,
    snapshot_markets,
)


def _opt_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if out == out else None


def markets_from_engine_projection(
    projection: Mapping[str, Any],
) -> Dict[str, Dict[str, Any]]:
    """Prefer stamped model_markets; else game-script means; else markets."""
    source = f"{MODEL_IDENTITY_SEASON_ENGINE}:model_markets"
    model = extract_model_markets_from_projection(projection)
    if model is None:
        markets = projection.get("markets")
        if isinstance(markets, dict) and markets:
            model = snapshot_markets(markets)
            source = f"{MODEL_IDENTITY_SEASON_ENGINE}:markets"
    if model is None:
        summary = projection.get("game_script_summary")
        if isinstance(summary, Mapping):
            eh = _opt_float(summary.get("expected_home_score_mean"))
            ea = _opt_float(summary.get("expected_away_score_mean"))
            total = _opt_float(summary.get("expected_total_mean"))
            home_wp = _opt_float(summary.get("home_win_prob_mean"))
            model = {}
            if eh is not None and ea is not None:
                model["spread_home"] = round(-(eh - ea), 2)
            if total is not None:
                model["total_mean"] = total
            if home_wp is not None:
                model["home_win_prob"] = home_wp
                model["away_win_prob"] = round(1.0 - home_wp, 4)
            source = f"{MODEL_IDENTITY_SEASON_ENGINE}:game_script_summary"
    if not model:
        raise ForecastIncompleteError(
            "engine projection has no model markets / game-script means",
            gap="G8",
            reason="engine_markets_missing",
        )

    out: Dict[str, Dict[str, Any]] = {}
    spread = _opt_float(model.get("spread_home"))
    if spread is not None:
        out["spread"] = {
            "prediction": spread,
            "ref_line": spread,
            "ref_line_source": f"{source}.spread_home",
            "orientation": SPREAD_ORIENTATION,
            "sign_convention": SPREAD_SIGN_CONVENTION,
        }
    total = _opt_float(model.get("total_mean"))
    if total is not None:
        out["total"] = {
            "prediction": total,
            "ref_line": total,
            "ref_line_source": f"{source}.total_mean",
            "orientation": "game",
        }
    home_wp = _opt_float(model.get("home_win_prob"))
    if home_wp is not None:
        ml: Dict[str, Any] = {
            "prediction": home_wp,
            "ref_line": home_wp,
            "ref_line_source": f"{source}.home_win_prob",
            "orientation": "home",
        }
        away_wp = _opt_float(model.get("away_win_prob"))
        if away_wp is not None:
            ml["away_win_prob"] = away_wp
        home_ml = _opt_float(model.get("fair_home_ml"))
        away_ml = _opt_float(model.get("fair_away_ml"))
        if home_ml is not None:
            ml["home_ml"] = home_ml
        if away_ml is not None:
            ml["away_ml"] = away_ml
        out["moneyline"] = ml
    if not out:
        raise ForecastIncompleteError(
            "engine projection produced no complete markets",
            gap="G8",
            reason="engine_markets_empty",
        )
    return out


def fingerprints_from_engine_projection(
    projection: Mapping[str, Any],
) -> Dict[str, str]:
    """Content hashes only — never secrets."""
    notes = projection.get("notes")
    lineage = projection.get("run_lineage") or projection.get("lineage") or {}
    if not isinstance(notes, Mapping):
        notes = {}
    if not isinstance(lineage, Mapping):
        lineage = {}
    candidates = {
        "pack_sha256": notes.get("pack_sha256") or lineage.get("pack_sha256"),
        "depth_sha256": notes.get("depth_sha256") or lineage.get("depth_sha256"),
        "snapshot_id": notes.get("snapshot_id") or lineage.get("snapshot_id"),
        "engine_version": projection.get("engine_version") or notes.get("engine_version"),
        "schedule_source": notes.get("schedule_source") or projection.get("schedule_source"),
    }
    out: Dict[str, str] = {}
    for key, value in candidates.items():
        text = str(value or "").strip()
        if not text:
            continue
        if re_sha256(text):
            out[key] = text.lower().removeprefix("sha256:")
        else:
            out[key] = sha256_hex(text.encode("utf-8"))
    if not out:
        raise ForecastIncompleteError(
            "engine projection has no provenance fingerprints",
            gap="G2",
            reason="engine_provenance_missing",
        )
    return out


def re_sha256(value: str) -> bool:
    text = value.strip().lower()
    if text.startswith("sha256:"):
        text = text[7:]
    return len(text) == 64 and all(c in "0123456789abcdef" for c in text)


def inputs_from_engine_projection(
    projection: Mapping[str, Any],
    *,
    kickoff_utc: Any,
    latest_input_as_of: Any,
    code_tip_sha: Any = None,
    extra_fingerprints: Optional[Mapping[str, str]] = None,
) -> Dict[str, Any]:
    """Build emit() inputs from a season-engine / handicap projection."""
    game_id = str(projection.get("game_id") or "").strip().upper()
    home = str(projection.get("home_team") or "").strip().upper()
    away = str(projection.get("away_team") or "").strip().upper()
    version = str(
        projection.get("engine_version")
        or (projection.get("model") or {}).get("version")
        or ""
    ).strip()
    fingerprints = fingerprints_from_engine_projection(projection)
    if extra_fingerprints:
        fingerprints.update(dict(extra_fingerprints))
    n = projection.get("n_replicates")
    config: Dict[str, Any] = {
        "schema_version": "nfl-model-forecast-artifact-v1",
        "model_identity": MODEL_IDENTITY_SEASON_ENGINE,
        "model_version": version,
        "n_replicates": n,
        "mode": projection.get("mode") or (projection.get("notes") or {}).get("mode"),
    }
    return {
        "game_id": game_id,
        "home_team": home,
        "away_team": away,
        "kickoff_utc": kickoff_utc,
        "latest_input_as_of": latest_input_as_of,
        "code_tip_sha": code_tip_sha,
        "model": {"identity": MODEL_IDENTITY_SEASON_ENGINE, "version": version},
        "markets": markets_from_engine_projection(projection),
        "input_provenance": {
            "fingerprints": fingerprints,
            "engine_mode": projection.get("mode"),
            "n_replicates": n,
        },
        "config": config,
    }
