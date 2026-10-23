"""NFL injury NULL contract, ledger, residual applicator, and sealed export.

Design v2 (713ae876) §7.1 items 1–5 + D-1 erratum (any injury path).
Overlays stay off. No live apply. No fit. Shadow adjusted values are
export-only.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

INJURY_KEYS = ("home_injury_impact", "away_injury_impact", "diff_injury_impact")
FLAG_MISSING_KOSEDGE_INJURY_NOWCAST = "FLAG_MISSING_KOSEDGE_INJURY_NOWCAST"
FLAG_RAW_INJURIES_2026_REFUSED = "FLAG_RAW_INJURIES_2026_REFUSED"
FLAG_INJURY_PARTIAL_OFF = "FLAG_INJURY_PARTIAL_OFF"
FLAG_INJURY_PARTIAL_DEF = "FLAG_INJURY_PARTIAL_DEF"
FLAG_INJURY_PARTIAL_OL = "FLAG_INJURY_PARTIAL_OL"
SOURCE_HEALTHY_COMPLETE = "nowcast_healthy_complete"
MISSING_DISCLOSURE = "no injury adjustment applied"
LEDGER_VERSION = "injury-residual-v2"
APPLICATION_SITE = "post_baseline_residual"

REFUSED_RAW_INJURY_NAMES = frozenset(
    {
        "injuries_2026",
        "nflverse_injuries",
        "raw_injury_report",
    }
)

RESIDUAL_COMPONENT_KEYS = (
    "off_home",
    "def_home",
    "ol_home",
    "off_away",
    "def_away",
    "ol_away",
)

PARTIAL_FLAG_BY_UNIT = {
    "off": FLAG_INJURY_PARTIAL_OFF,
    "def": FLAG_INJURY_PARTIAL_DEF,
    "ol": FLAG_INJURY_PARTIAL_OL,
}

GAME_LINE_INJURY_GUARDS = {
    "index_scale_applied": False,
    "injuries_depth_applied": False,
    "totals_injury_signal_applied": False,
    "kei_injury_applied": False,
    "continuity_as_second_line": False,
}

NFL_TOTALS_ENV_KEYS = (
    "NFL_TOTALS_PASS_RATE_WEIGHT",
    "NFL_TOTALS_EPA_INTERACTION_WEIGHT",
    "NFL_TOTALS_SUCCESS_DELTA_WEIGHT",
    "NFL_TOTALS_INJURY_WEIGHT",
    "NFL_TOTALS_MAX_ADJUSTMENT_POINTS",
    "NFL_TOTALS_INJURY_STDEV_WEIGHT",
    "NFL_TOTALS_MAX_STDEV_ADJUSTMENT",
    "NFL_TOTALS_CALIBRATION_MIN_TOTAL",
    "NFL_TOTALS_CALIBRATION_MAX_TOTAL",
    "NFL_TOTALS_CALIBRATION_SLOPE_DEFAULT",
    "NFL_TOTALS_CALIBRATION_INTERCEPT_DEFAULT",
    "NFL_TOTALS_CALIBRATION_MIN_SAMPLE",
    "NFL_TOTALS_CALIBRATION_INTERCEPT_ABS_MAX",
    "NFL_TOTALS_CALIBRATION_LOOKBACK_DAYS",
    "NFL_TOTALS_CALIBRATION_MIN_SLATE",
    "NFL_TOTALS_CALIBRATION_HALF_LIFE_DAYS",
    "NFL_TOTALS_CALIBRATION_PRIOR_REFERENCE",
    "NFL_TOTALS_LEVEL_SHIFT_SHRINK",
    "NFL_TOTALS_LEVEL_SHIFT_SHRINK_DEFAULT_WITH_PRIOR_DELTA",
    "NFL_TOTALS_CALIBRATION_SLOPE_MIN",
    "NFL_TOTALS_CALIBRATION_SLOPE_MAX",
)


def nullable_float(value: Any) -> Optional[float]:
    """Parse a number or return None. Never substitutes 0.0."""
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(out) or math.isinf(out):
        return None
    return out


def impact_triple(
    home: Any,
    away: Any,
) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    """home, away, diff. Diff is NULL if either side is NULL (C-7)."""
    home_v = nullable_float(home)
    away_v = nullable_float(away)
    if home_v is None or away_v is None:
        return home_v, away_v, None
    return home_v, away_v, home_v - away_v


def empty_nowcast_payload(*, flags: Optional[Sequence[str]] = None) -> Dict[str, Any]:
    """Fail-closed empty aggregate. Not a Q1 sourced-0.0 row."""
    return {
        "injury_count": 0,
        "freshness_hours": None,
        "freshness_multiplier": None,
        "confidence": None,
        "offense_multiplier": None,
        "defense_multiplier": None,
        "impact_score": None,
        "top_drivers": [],
        "flags": list(flags or [FLAG_MISSING_KOSEDGE_INJURY_NOWCAST]),
        "source": None,
    }


def nowcast_is_missing(nowcast: Optional[Mapping[str, Any]]) -> bool:
    if not isinstance(nowcast, Mapping):
        return True
    return (
        nowcast.get("impact_score") is None
        and nowcast.get("offense_multiplier") is None
        and nowcast.get("defense_multiplier") is None
    )


def injury_fields_complete(values: Iterable[Any]) -> bool:
    return all(nullable_float(v) is not None for v in values)


def refuse_raw_injury_source(name: Any) -> bool:
    raw = str(name or "").strip().lower()
    stem = raw.rsplit("/", 1)[-1]
    stem = stem.split(".", 1)[0]
    return stem in REFUSED_RAW_INJURY_NAMES or raw in REFUSED_RAW_INJURY_NAMES


def game_line_guards(*, applied: bool = False) -> Dict[str, bool]:
    guards = dict(GAME_LINE_INJURY_GUARDS)
    if applied and any(guards.values()):
        raise RuntimeError("BLOCK: true game-line injury guard with applied=true")
    return guards


def assert_guards_or_block(guards: Mapping[str, Any], *, applied: bool) -> None:
    if not applied:
        return
    true_guards = [k for k, v in GAME_LINE_INJURY_GUARDS.items() if bool(guards.get(k))]
    if true_guards:
        raise RuntimeError(f"BLOCK: true game-line injury guard with applied=true: {true_guards}")


def resolve_nfl_totals_env(env: Optional[Mapping[str, str]] = None) -> Dict[str, Any]:
    """C-9: each NFL_TOTALS_* is unset or a finite number. Non-finite → STOP."""
    source = env if env is not None else os.environ
    resolved: Dict[str, Any] = {}
    for key in NFL_TOTALS_ENV_KEYS:
        if key not in source:
            resolved[key] = None
            continue
        raw = source.get(key)
        if raw is None or str(raw).strip() == "":
            raise ValueError(f"STOP: {key} is empty (C-9)")
        value = nullable_float(raw)
        if value is None:
            raise ValueError(f"STOP: {key} is not a finite number (C-9)")
        resolved[key] = value
    extra = sorted(k for k in source if k.startswith("NFL_TOTALS_") and k not in resolved)
    for key in extra:
        raw = source.get(key)
        if raw is None or str(raw).strip() == "":
            raise ValueError(f"STOP: {key} is empty (C-9)")
        value = nullable_float(raw)
        if value is None:
            raise ValueError(f"STOP: {key} is not a finite number (C-9)")
        resolved[key] = value
    return resolved


def config_hash(
    *,
    extra: Optional[Mapping[str, Any]] = None,
    env: Optional[Mapping[str, str]] = None,
) -> str:
    payload = {
        "nfl_totals": resolve_nfl_totals_env(env),
        "ledger_version": LEDGER_VERSION,
        "application_site": APPLICATION_SITE,
        "extra": dict(extra or {}),
    }
    blob = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def payload_sha256(payload: Any) -> str:
    blob = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def snapshot_baseline_markets(markets: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    keys = (
        "home_win_prob",
        "away_win_prob",
        "total_mean",
        "spread_home",
        "fair_home_ml",
        "fair_away_ml",
        "predicted_margin",
        "predicted_total",
    )
    src = markets if isinstance(markets, Mapping) else {}
    return {key: src.get(key) for key in keys if key in src}


def _unit_from_component(key: str) -> str:
    if key.startswith("off_"):
        return "off"
    if key.startswith("def_"):
        return "def"
    if key.startswith("ol_"):
        return "ol"
    return key


def apply_injury_residual_once(
    *,
    baseline_markets: Mapping[str, Any],
    components: Optional[Mapping[str, Any]] = None,
    baseline_stdev: Optional[float] = None,
    applied: bool = False,
) -> Dict[str, Any]:
    """Post-baseline residual. Live remat calls this with applied=False.

    Shadow adjusted markets are returned only when every OFF/DEF/OL component
    is non-NULL (Q4) *and* the caller asked for an export shadow (not publish).
    """
    comps = dict(components or {})
    missing_units: List[str] = []
    flags: List[str] = []
    for key in RESIDUAL_COMPONENT_KEYS:
        if nullable_float(comps.get(key)) is None:
            comps[key] = None
            unit = _unit_from_component(key)
            if unit not in missing_units:
                missing_units.append(unit)
                flags.append(PARTIAL_FLAG_BY_UNIT[unit])
    complete = not missing_units
    if not complete:
        flags.append(FLAG_MISSING_KOSEDGE_INJURY_NOWCAST)
        deltas = {
            "margin": None,
            "total": None,
            "home_pts": None,
            "away_pts": None,
        }
        adjusted = None
        line_applied = False
    else:
        off_home = float(comps["off_home"])
        def_home = float(comps["def_home"])
        ol_home = float(comps["ol_home"])
        off_away = float(comps["off_away"])
        def_away = float(comps["def_away"])
        ol_away = float(comps["ol_away"])
        def_home_leak = -def_home
        def_away_leak = -def_away
        home_pts = off_home + ol_home + def_away_leak
        away_pts = off_away + ol_away + def_home_leak
        d_margin = home_pts - away_pts
        d_total = home_pts + away_pts
        deltas = {
            "margin": d_margin,
            "total": d_total,
            "home_pts": home_pts,
            "away_pts": away_pts,
        }
        # Shadow math only. Never a published apply from this module.
        base_margin = nullable_float(baseline_markets.get("predicted_margin"))
        if base_margin is None:
            spread = nullable_float(baseline_markets.get("spread_home"))
            base_margin = None if spread is None else -spread
        base_total = nullable_float(
            baseline_markets.get("predicted_total", baseline_markets.get("total_mean"))
        )
        if base_margin is None or base_total is None:
            adjusted = None
        else:
            adj_margin = base_margin + d_margin
            adj_total = base_total + d_total
            sigma = nullable_float(baseline_stdev)
            if sigma is None or sigma <= 0:
                sigma = 13.5
            # Φ(margin / (√2 · σ)) — Q5 pinned identity.
            from math import erf, sqrt

            z = adj_margin / (sqrt(2.0) * sigma)
            p_home = 0.5 * (1.0 + erf(z / sqrt(2.0)))
            # Wait: Φ(x) = 0.5(1+erf(x/√2)). The design pins Φ(margin/(√2·σ)).
            # So argument to Φ is margin/(√2·σ). Φ(z) with z = margin/(√2·σ)
            # is 0.5(1+erf(z/√2)).
            adjusted = {
                "predicted_margin": adj_margin,
                "predicted_total": adj_total,
                "spread_home": -adj_margin,
                "total_mean": adj_total,
                "home_win_prob": p_home,
                "away_win_prob": 1.0 - p_home,
            }
        line_applied = False

    return {
        "applied": bool(line_applied and applied and complete),
        "complete": complete,
        "components": {key: comps.get(key) for key in RESIDUAL_COMPONENT_KEYS},
        "delta": deltas,
        "adjusted_markets": None if not complete else adjusted,
        "flags": flags,
        "missing_units": missing_units,
    }


def build_injury_accounting_ledger(
    *,
    baseline_markets: Optional[Mapping[str, Any]] = None,
    home_nowcast: Optional[Mapping[str, Any]] = None,
    away_nowcast: Optional[Mapping[str, Any]] = None,
    components: Optional[Mapping[str, Any]] = None,
    flags: Optional[Sequence[str]] = None,
    as_of: Optional[Mapping[str, Any]] = None,
    source: Optional[Mapping[str, Any]] = None,
    code_sha: Optional[str] = None,
    config_hash_value: Optional[str] = None,
    sigma_baseline: Optional[float] = None,
    replacement_players: Optional[Sequence[Mapping[str, Any]]] = None,
    coverage: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Ledger on every remat. applied=false. adjusted_markets null on remat."""
    home = home_nowcast if isinstance(home_nowcast, Mapping) else {}
    away = away_nowcast if isinstance(away_nowcast, Mapping) else {}
    home_imp, away_imp, diff_imp = impact_triple(home.get("impact_score"), away.get("impact_score"))
    collected_flags = list(flags or [])
    if nowcast_is_missing(home) or nowcast_is_missing(away) or home_imp is None or away_imp is None:
        if FLAG_MISSING_KOSEDGE_INJURY_NOWCAST not in collected_flags:
            collected_flags.append(FLAG_MISSING_KOSEDGE_INJURY_NOWCAST)
    for side in (home, away):
        for flag in side.get("flags") or []:
            if flag not in collected_flags:
                collected_flags.append(flag)

    residual = apply_injury_residual_once(
        baseline_markets=snapshot_baseline_markets(baseline_markets),
        components=components,
        baseline_stdev=sigma_baseline,
        applied=False,
    )
    for flag in residual.get("flags") or []:
        if flag not in collected_flags:
            collected_flags.append(flag)

    sigma_b = nullable_float(sigma_baseline)
    sigma_r = sigma_b  # residual must not shrink σ (C-10); unused until fit
    guards = game_line_guards(applied=False)
    return {
        "version": LEDGER_VERSION,
        "applied": False,
        "application_site": APPLICATION_SITE,
        "baseline_markets": snapshot_baseline_markets(baseline_markets),
        "adjusted_markets": None,
        "delta": residual.get("delta"),
        "components": {
            **{key: (components or {}).get(key) for key in RESIDUAL_COMPONENT_KEYS},
            "continuity": (components or {}).get("continuity"),
        },
        "keys": {
            "home_injury_impact": home_imp,
            "away_injury_impact": away_imp,
            "diff_injury_impact": diff_imp,
        },
        "guards": guards,
        "as_of": dict(as_of or {}),
        "source": {
            "table": "nfl_dp_injuries",
            "nowcast_fn": "fetch_nfl_injury_nowcast",
            "code_sha": code_sha,
            "config_hash": config_hash_value,
            **dict(source or {}),
        },
        "replacement": {
            "table_version": None,
            "players": list(replacement_players or []),
        },
        "coverage": dict(coverage or {}),
        "uncertainty": {
            "sigma_baseline": sigma_b,
            "sigma_residual": sigma_r,
            "v2_play_noplay_p10_p90": None,
        },
        "flags": collected_flags,
        "disclosure": MISSING_DISCLOSURE,
    }


def write_sealed_injury_export(
    path: str,
    *,
    games: Sequence[Mapping[str, Any]],
    players: Sequence[Mapping[str, Any]],
    code_sha: str,
    config_hash_value: str,
    nowcast_payload_sha: Optional[str] = None,
    fit_object_sha: Optional[str] = None,
    fit_years: Optional[Sequence[int]] = None,
    source_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Sealed export (C-5). No warehouse session. Never maps raw injury files."""
    if refuse_raw_injury_source(source_name) or refuse_raw_injury_source(path):
        raise ValueError(
            f"{FLAG_RAW_INJURIES_2026_REFUSED}: refused raw injury source {source_name or path}"
        )
    for game in games:
        src = (game.get("source") if isinstance(game, Mapping) else None) or source_name
        if refuse_raw_injury_source(src):
            raise ValueError(f"{FLAG_RAW_INJURIES_2026_REFUSED}: refused raw injury source {src}")
    years = [int(y) for y in (fit_years or [])]
    if set(years) & {2024, 2025, 2026}:
        raise ValueError("fit years must be disjoint from {2024, 2025, 2026}")
    document = {
        "kind": "sealed_injury_export",
        "version": LEDGER_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "code_sha": code_sha,
        "config_hash": config_hash_value,
        "nowcast_payload_sha": nowcast_payload_sha,
        "fit_object_sha": fit_object_sha,
        "fit_years": years,
        "games": list(games),
        "players": list(players),
        "published": False,
    }
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    blob = json.dumps(document, sort_keys=True, default=str, indent=2)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(blob)
        handle.write("\n")
    digest = hashlib.sha256(blob.encode("utf-8")).hexdigest()
    with open(f"{path}.sha256", "w", encoding="utf-8") as handle:
        handle.write(f"{digest}  {os.path.basename(path)}\n")
    return {"path": path, "sha256": digest, "n_games": len(games), "n_players": len(players)}


def stamp_projection_injury_accounting(
    projection: Dict[str, Any],
    ledger: Mapping[str, Any],
) -> Dict[str, Any]:
    """Attach ledger to remat diagnostics. Does not mutate published markets."""
    diagnostics = projection.get("diagnostics")
    if not isinstance(diagnostics, dict):
        diagnostics = {}
    else:
        diagnostics = dict(diagnostics)
    diagnostics["injury_accounting"] = dict(ledger)
    injury_nowcast = diagnostics.get("injury_nowcast")
    if not isinstance(injury_nowcast, dict):
        injury_nowcast = {}
    else:
        injury_nowcast = dict(injury_nowcast)
    injury_nowcast["applied"] = False
    injury_nowcast["disclosure"] = MISSING_DISCLOSURE
    diagnostics["injury_nowcast"] = injury_nowcast
    projection["diagnostics"] = diagnostics
    projection["baseline_markets"] = ledger.get("baseline_markets") or snapshot_baseline_markets(
        projection.get("markets") if isinstance(projection.get("markets"), dict) else {}
    )
    return projection
