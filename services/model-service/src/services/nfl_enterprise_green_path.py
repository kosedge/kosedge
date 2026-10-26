"""t4359u local NFL fair-line path — fail-closed, overlays off, no schedule.

Uses the production engine (LOCKED_SCORING + nfl-handicap-core-v3.1 +
simulate_nfl_game). This is not a second model. Missing required inputs
block the run. Unknown HFA, unknown injury-as-zero, and silent 1.0 / 7.0
fills are refused.

Scheduling stays off. No Beat, no cron, no Railway, no publication.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

from src.services.nfl_epa_authority import overlays_must_stay_off
from src.services.nfl_handicapping_framework import NFL_HANDICAPPING_FRAMEWORK_VERSION
from src.services.nfl_regression_diagnose import (
    LOCKED_SCORING,
    PACKAGED_EPA_PRIORS_2026,
    load_packaged_epa_priors,
)
from src.services.nfl_simulator import NflGameInputs, simulate_nfl_game

SPEC_ID = "nfl-model-spec-t4359u-v1"
SPEC_VERSION = "1.0.0"
SPEC_ADDENDUM = "t4366u-stage12"
SPEC_DOC = Path(__file__).resolve().parents[4] / "docs" / "nfl" / "NFL_MODEL_SPEC_t4359u_v1.md"
DEFAULT_MODEL_VERSION = "nfl-v1.5-matchup-sim"
DEFAULT_SEED = 4359
DEFAULT_SIMULATIONS = 4000

REQUIRED_KEYS = (
    "game_id",
    "home_team",
    "away_team",
    "season",
    "week",
    "site_class",
    "kickoff_utc",
    "rest_days_home",
    "rest_days_away",
)

FORBIDDEN_SILENT = {
    "offense_index_home": 1.0,
    "offense_index_away": 1.0,
    "defense_index_home": 1.0,
    "defense_index_away": 1.0,
    "rest_days_home": 7.0,
    "rest_days_away": 7.0,
    "injury_impact": 0.0,
}

SITE_HOME = "HOME"
SITE_NEUTRAL = "NEUTRAL"
SITE_UNKNOWN = "UNKNOWN"

REASON_MISSING = "MISSING_REQUIRED_INPUT"
REASON_PLACEHOLDER = "PLACEHOLDER_FORBIDDEN"
REASON_UNKNOWN_HFA = "UNKNOWN_HFA_REFUSED"
REASON_T7_NEUTRAL = "T7_BLOCKED_NEUTRAL_SITE"
REASON_SILENT_DEFAULT = "SILENT_DEFAULT_REFUSED"
REASON_UNKNOWN_INJURY_ZERO = "UNKNOWN_INJURY_AS_ZERO_REFUSED"
REASON_STRENGTH_MISSING = "STRENGTH_MISSING"
REASON_SCHEDULE = "SCHEDULE_REFUSED"
REASON_OVERLAY = "OVERLAY_UNLOCK_REFUSED"

ISO_TZ_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(Z|[+-]\d{2}:\d{2})$"
)


class FailClosed(ValueError):
    """Required input or policy gate failed. Do not catch-and-fill."""

    def __init__(self, reason: str, detail: str = "") -> None:
        self.reason = reason
        self.detail = detail
        super().__init__(f"{reason}: {detail}" if detail else reason)


def spec_sha256(path: Optional[Path] = None) -> str:
    target = path or SPEC_DOC
    if not target.is_file():
        raise FailClosed(REASON_MISSING, f"spec file missing: {target}")
    return hashlib.sha256(target.read_bytes()).hexdigest()


def canonical_dumps(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def fingerprint(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_dumps(payload).encode("utf-8")).hexdigest()


def weekly_pipeline_schedule_enabled() -> bool:
    raw = os.getenv("NFL_WEEKLY_PIPELINE_SCHEDULE_ENABLED", "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def assert_schedule_disabled() -> None:
    if weekly_pipeline_schedule_enabled():
        raise FailClosed(
            REASON_SCHEDULE,
            "NFL_WEEKLY_PIPELINE_SCHEDULE_ENABLED is on; t4359u local path refuses Beat/cron",
        )


def _as_str(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _require_str(card: Mapping[str, Any], key: str) -> str:
    raw = _as_str(card.get(key))
    if not raw:
        raise FailClosed(REASON_MISSING, key)
    upper = raw.upper()
    if "PLACEHOLDER" in upper or upper in {"TODO", "TBD", "NULL", "NONE"}:
        raise FailClosed(REASON_PLACEHOLDER, key)
    return raw


def _require_int(card: Mapping[str, Any], key: str, *, lo: int, hi: int) -> int:
    raw = card.get(key)
    if raw is None or raw == "":
        raise FailClosed(REASON_MISSING, key)
    try:
        out = int(raw)
    except (TypeError, ValueError) as exc:
        raise FailClosed(REASON_MISSING, f"{key}={raw!r}") from exc
    if out < lo or out > hi:
        raise FailClosed(REASON_MISSING, f"{key}={out} out of [{lo},{hi}]")
    return out


def _require_float(
    card: Mapping[str, Any],
    key: str,
    *,
    allow_explicit_forbidden: bool = False,
) -> float:
    raw = card.get(key)
    if raw is None or raw == "":
        raise FailClosed(REASON_MISSING, key)
    try:
        out = float(raw)
    except (TypeError, ValueError) as exc:
        raise FailClosed(REASON_MISSING, f"{key}={raw!r}") from exc
    if out != out or out in {float("inf"), float("-inf")}:
        raise FailClosed(REASON_MISSING, f"{key} non-finite")
    forbidden = FORBIDDEN_SILENT.get(key)
    source = _as_str(card.get(f"{key}_source")).lower()
    if (
        forbidden is not None
        and out == forbidden
        and source != "explicit_named_value"
        and not allow_explicit_forbidden
    ):
        raise FailClosed(
            REASON_SILENT_DEFAULT,
            f"{key}={out} looks like a silent fill; set {key}_source=explicit_named_value",
        )
    return out


def _site_class(card: Mapping[str, Any]) -> str:
    site = _require_str(card, "site_class").upper()
    if site == SITE_HOME:
        return SITE_HOME
    if site == SITE_NEUTRAL:
        raise FailClosed(
            REASON_T7_NEUTRAL,
            "T7 is Ryan-blocked; this path does not invent option A or B",
        )
    raise FailClosed(REASON_UNKNOWN_HFA, f"site_class={site}")


def _refuse_unknown_injury_zero(card: Mapping[str, Any]) -> None:
    for key in (
        "injury_impact",
        "injury_nowcast_impact_home",
        "injury_nowcast_impact_away",
        "home_injury_impact",
        "away_injury_impact",
    ):
        if key not in card:
            continue
        raw = card.get(key)
        source = _as_str(card.get(f"{key}_source")).lower()
        if raw in (0, 0.0, "0", "0.0") and source != "explicit_named_value":
            raise FailClosed(
                REASON_UNKNOWN_INJURY_ZERO,
                f"{key}={raw!r} is not a sourced healthy-zero; overlays stay off",
            )
    if bool(card.get("unlock_overlays")) or bool(card.get("apply_injury_overlay")):
        raise FailClosed(REASON_OVERLAY, "overlays stay OFF on t4359u")


def _strength_pair(
    card: Mapping[str, Any],
    *,
    side: str,
    priors: Mapping[str, Mapping[str, float]],
) -> Dict[str, Any]:
    off_key = f"offense_index_{side}"
    def_key = f"defense_index_{side}"
    team = _require_str(card, f"{side}_team").upper()
    if team == "LA":
        team = "LAR"
    has_off = card.get(off_key) not in (None, "")
    has_def = card.get(def_key) not in (None, "")
    if has_off and has_def:
        off = _require_float(card, off_key)
        deff = _require_float(card, def_key)
        if off == 1.0 and _as_str(card.get(f"{off_key}_source")).lower() != "explicit_named_value":
            raise FailClosed(REASON_SILENT_DEFAULT, off_key)
        if deff == 1.0 and _as_str(card.get(f"{def_key}_source")).lower() != "explicit_named_value":
            raise FailClosed(REASON_SILENT_DEFAULT, def_key)
        return {
            "team": team,
            "offense_index": off,
            "defense_index": deff,
            "strength_source": "explicit",
        }
    prior = priors.get(team)
    if not prior:
        raise FailClosed(REASON_STRENGTH_MISSING, f"{side} {team} has no explicit index and no packaged EPA")
    off = prior.get("offense_index")
    deff = prior.get("defense_index")
    if off is None or deff is None:
        raise FailClosed(REASON_STRENGTH_MISSING, f"{side} {team} packaged EPA incomplete")
    return {
        "team": team,
        "offense_index": float(off),
        "defense_index": float(deff),
        "strength_source": "packaged_epa_prior",
        "prior_as_of": prior.get("as_of"),
        "prior_source": prior.get("source"),
    }


def validate_game_card(
    card: Mapping[str, Any],
    *,
    priors: Optional[Mapping[str, Mapping[str, float]]] = None,
) -> Dict[str, Any]:
    if not isinstance(card, Mapping):
        raise FailClosed(REASON_MISSING, "card is not an object")
    assert_schedule_disabled()
    if not overlays_must_stay_off(force_overlays_off=True, unlock_overlays=False):
        raise FailClosed(REASON_OVERLAY, "overlays_must_stay_off returned false")
    _refuse_unknown_injury_zero(card)
    game_id = _require_str(card, "game_id")
    home = _require_str(card, "home_team").upper()
    away = _require_str(card, "away_team").upper()
    if home == away:
        raise FailClosed(REASON_MISSING, "home_team == away_team")
    season = _require_int(card, "season", lo=2013, hi=2026)
    week = _require_int(card, "week", lo=1, hi=18)
    site = _site_class(card)
    kickoff = _require_str(card, "kickoff_utc")
    if not ISO_TZ_RE.match(kickoff):
        raise FailClosed(REASON_MISSING, f"kickoff_utc not timezone-aware ISO: {kickoff}")
    rest_home = _require_float(card, "rest_days_home")
    rest_away = _require_float(card, "rest_days_away")
    loaded = priors if priors is not None else load_packaged_epa_priors()
    home_str = _strength_pair(card, side="home", priors=loaded)
    away_str = _strength_pair(card, side="away", priors=loaded)
    seed = card.get("seed", DEFAULT_SEED)
    try:
        seed_i = int(seed)
    except (TypeError, ValueError) as exc:
        raise FailClosed(REASON_MISSING, f"seed={seed!r}") from exc
    sims = card.get("simulations", DEFAULT_SIMULATIONS)
    try:
        sims_i = int(sims)
    except (TypeError, ValueError) as exc:
        raise FailClosed(REASON_MISSING, f"simulations={sims!r}") from exc
    if sims_i < 300:
        raise FailClosed(REASON_MISSING, "simulations < 300")
    return {
        "game_id": game_id,
        "home_team": home,
        "away_team": away,
        "season": season,
        "week": week,
        "site_class": site,
        "kickoff_utc": kickoff,
        "rest_days_home": rest_home,
        "rest_days_away": rest_away,
        "home": home_str,
        "away": away_str,
        "seed": seed_i,
        "simulations": sims_i,
        "model_version": _as_str(card.get("model_version")) or DEFAULT_MODEL_VERSION,
    }


def _overlay_off_config() -> Dict[str, Any]:
    return {
        "priors": {
            "base_total_points": LOCKED_SCORING["base_total_points"],
            "home_field_points": LOCKED_SCORING["home_field_points"],
        },
        "factors": {
            "home_field_advantage": {
                "margin_points": LOCKED_SCORING["home_field_points"],
            },
            "base_efficiency": {
                "margin_weight": LOCKED_SCORING["base_efficiency_margin_weight"],
                "total_weight": LOCKED_SCORING["base_efficiency_total_weight"],
                "max_margin_points": LOCKED_SCORING["base_efficiency_max_margin_points"],
                "max_total_points": LOCKED_SCORING["base_efficiency_max_total_points"],
            },
            # Overlays OFF: leftover or-1.0 / or-0.0 in the framework cannot move the line.
            "injuries_depth": {
                "margin_weight": 0.0,
                "total_weight": 0.0,
                "max_margin_points": 0.0,
                "max_total_points": 0.0,
            },
            "personnel_efficiency": {"enabled": False},
            "info_velocity": {"enabled": False},
            "coach_aggression": {"enabled": False},
        },
    }


def _blocked(reason: str, detail: str, card: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    return {
        "status": "BLOCKED",
        "reason_codes": [reason],
        "detail": detail,
        "markets": None,
        "spec_id": SPEC_ID,
        "spec_version": SPEC_VERSION,
        "overlays_off": True,
        "injury_status": "OVERLAY_OFF_UNAVAILABLE",
        "schedule_enabled": False,
        "publication": "NFL_NO_GO",
        "game_id": (card or {}).get("game_id"),
    }


def run_local_fair_line(
    card: Mapping[str, Any],
    *,
    priors: Optional[Mapping[str, Mapping[str, float]]] = None,
    spec_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Produce fair spread / total / ML or BLOCK. Never invent."""
    try:
        gated = validate_game_card(card, priors=priors)
        sha = spec_sha256(spec_path)
    except FailClosed as exc:
        return _blocked(exc.reason, exc.detail, card)

    inputs = NflGameInputs(
        game_id=gated["game_id"],
        home_team=gated["home_team"],
        away_team=gated["away_team"],
        offense_index_home=gated["home"]["offense_index"],
        offense_index_away=gated["away"]["offense_index"],
        defense_index_home=gated["home"]["defense_index"],
        defense_index_away=gated["away"]["defense_index"],
        rest_days_home=gated["rest_days_home"],
        rest_days_away=gated["rest_days_away"],
        matchup_season=gated["season"],
        matchup_week=gated["week"],
        matchup_game_id=gated["game_id"],
        matchup_home_team=gated["home_team"],
        matchup_away_team=gated["away_team"],
        # Injury: omit. Overlays off. Do not pass 0.0 / 1.0 as healthy.
        weather_available=False,
        travel_available=False,
    )

    env_restore = {
        "NFL_TOTALS_INJURY_WEIGHT": os.environ.get("NFL_TOTALS_INJURY_WEIGHT"),
        "NFL_TOTALS_INJURY_STDEV_WEIGHT": os.environ.get("NFL_TOTALS_INJURY_STDEV_WEIGHT"),
    }
    os.environ["NFL_TOTALS_INJURY_WEIGHT"] = "0"
    os.environ["NFL_TOTALS_INJURY_STDEV_WEIGHT"] = "0"
    try:
        raw = simulate_nfl_game(
            inputs,
            simulations=gated["simulations"],
            seed=gated["seed"],
            model_version=gated["model_version"],
            totals_calibration=None,
            apply_linear_totals_calibration=False,
            config_overrides=_overlay_off_config(),
            market_spread_home=None,
            market_total=None,
        )
    finally:
        for key, value in env_restore.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    markets = raw.get("markets") or {}
    stamp = {
        "status": "READY",
        "reason_codes": [],
        "spec_id": SPEC_ID,
        "spec_version": SPEC_VERSION,
        "spec_sha256": sha,
        "framework_version": NFL_HANDICAPPING_FRAMEWORK_VERSION,
        "locked_scoring": dict(LOCKED_SCORING),
        "model_version": gated["model_version"],
        "game_id": gated["game_id"],
        "home_team": gated["home_team"],
        "away_team": gated["away_team"],
        "season": gated["season"],
        "week": gated["week"],
        "site_class": gated["site_class"],
        "kickoff_utc": gated["kickoff_utc"],
        "hfa_status": "LOCKED_HOME_1_05",
        "hfa_points": LOCKED_SCORING["home_field_points"],
        "overlays_off": True,
        "injury_status": "OVERLAY_OFF_UNAVAILABLE",
        "injury_applied": False,
        "unknown_injury_treated_as_zero": False,
        "schedule_enabled": False,
        "publication": "NFL_NO_GO",
        "coming_soon": True,
        "market_blend": False,
        "totals_calibration": False,
        "seed": gated["seed"],
        "simulations": gated["simulations"],
        "strength": {"home": gated["home"], "away": gated["away"]},
        "rest_days_home": gated["rest_days_home"],
        "rest_days_away": gated["rest_days_away"],
        "fair_spread_home": markets.get("spread_home"),
        "fair_total": markets.get("total_mean"),
        "home_win_prob": markets.get("home_win_prob"),
        "away_win_prob": markets.get("away_win_prob"),
        "fair_home_ml": markets.get("fair_home_ml"),
        "fair_away_ml": markets.get("fair_away_ml"),
        "mean_home_points": (raw.get("diagnostics") or {}).get("mean_home_points"),
        "mean_away_points": (raw.get("diagnostics") or {}).get("mean_away_points"),
        "t7_status": "RYAN_BLOCKED_NEUTRAL_REFUSED",
        "add141_q9_status": "RYAN_BLOCKED",
        "holdout_2024_25": "SEALED",
        "step3": "FROZEN",
        "step4": "BLOCKED",
        "nr1": "CLOSED_MISSING",
    }
    fp_body = deepcopy(stamp)
    stamp["fingerprint"] = fingerprint(fp_body)
    return stamp


def demo_home_card() -> Dict[str, Any]:
    """Deterministic HOME card. Strength from packaged EPA. Rest tagged explicit."""
    return {
        "game_id": "t4359u-DEMO-KC@BUF",
        "home_team": "BUF",
        "away_team": "KC",
        "season": 2026,
        "week": 6,
        "site_class": "HOME",
        "kickoff_utc": "2026-10-18T17:00:00Z",
        "rest_days_home": 7.0,
        "rest_days_away": 7.0,
        "rest_days_home_source": "explicit_named_value",
        "rest_days_away_source": "explicit_named_value",
        "seed": DEFAULT_SEED,
        "simulations": 2000,
        "model_version": DEFAULT_MODEL_VERSION,
    }


def attach_slate_defaults(
    card: Mapping[str, Any],
    slate: Mapping[str, Any],
) -> Dict[str, Any]:
    """Copy season/week from the slate only when the card omits the key.

    An explicit null week stays missing (fail-closed). This does not change
    the frozen overview null-week SQL assertion.
    """
    out = dict(card)
    for key in ("season", "week"):
        if key in out:
            continue
        if slate.get(key) in (None, ""):
            continue
        out[key] = slate[key]
    for key in ("seed", "simulations", "model_version"):
        if key not in out and slate.get(key) not in (None, ""):
            out[key] = slate[key]
    return out


def run_local_slate(
    cards: Sequence[Mapping[str, Any]],
    *,
    priors: Optional[Mapping[str, Mapping[str, float]]] = None,
    spec_path: Optional[Path] = None,
) -> Dict[str, Any]:
    rows = [run_local_fair_line(card, priors=priors, spec_path=spec_path) for card in cards]
    ready = [r for r in rows if r.get("status") == "READY"]
    blocked = [r for r in rows if r.get("status") != "READY"]
    by_reason: Dict[str, int] = {}
    for row in blocked:
        for reason in row.get("reason_codes") or []:
            by_reason[str(reason)] = by_reason.get(str(reason), 0) + 1
    summary = {
        "spec_id": SPEC_ID,
        "spec_version": SPEC_VERSION,
        "spec_addendum": SPEC_ADDENDUM,
        "n_cards": len(rows),
        "n_ready": len(ready),
        "n_blocked": len(blocked),
        "blocked_by_reason": by_reason,
        "overlays_off": True,
        "schedule_enabled": False,
        "publication": "NFL_NO_GO",
        "t7_status": "FROZEN_PENDING_RYAN_AFTER_IMV_PACKET",
        "rows": rows,
    }
    summary["fingerprint"] = fingerprint(
        {
            k: summary[k]
            for k in (
                "spec_id",
                "spec_version",
                "n_cards",
                "n_ready",
                "n_blocked",
                "blocked_by_reason",
                "rows",
            )
        }
    )
    return summary


def run_local_week(
    slate: Mapping[str, Any],
    *,
    priors: Optional[Mapping[str, Mapping[str, float]]] = None,
    spec_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Manual weekly pipeline. Scheduling stays off. T7 expectation unchanged."""
    if not isinstance(slate, Mapping):
        raise FailClosed(REASON_MISSING, "week slate is not an object")
    assert_schedule_disabled()
    cards = slate.get("cards")
    if not isinstance(cards, list) or not cards:
        raise FailClosed(REASON_MISSING, "week slate cards")
    materialized = [attach_slate_defaults(card, slate) for card in cards]
    summary = run_local_slate(materialized, priors=priors, spec_path=spec_path)
    summary["season"] = slate.get("season")
    summary["week"] = slate.get("week")
    summary["pipeline"] = "local_weekly_manual"
    summary["schedule_enabled"] = False
    return summary


def week6_boundary_slate() -> Dict[str, Any]:
    """HOME + fail-closed boundary cards. Neutral stays T7-blocked (frozen)."""
    home = demo_home_card()
    short = {
        "game_id": "t4366u-BOUNDARY-GB@DET",
        "home_team": "DET",
        "away_team": "GB",
        "season": 2026,
        "week": 6,
        "site_class": "HOME",
        "kickoff_utc": "2026-10-18T20:25:00Z",
        "rest_days_home": 4.0,
        "rest_days_away": 10.0,
        "seed": DEFAULT_SEED,
        "simulations": 2000,
        "model_version": DEFAULT_MODEL_VERSION,
    }
    neutral = {
        "game_id": "t4366u-T7-NEUTRAL-XXX",
        "home_team": "PHI",
        "away_team": "DAL",
        "season": 2026,
        "week": 6,
        "site_class": "NEUTRAL",
        "kickoff_utc": "2026-10-18T13:30:00Z",
        "rest_days_home": 6.0,
        "rest_days_away": 6.0,
        "seed": DEFAULT_SEED,
        "simulations": 2000,
    }
    missing_week = {
        "game_id": "t4366u-NULL-WEEK-NO@GO",
        "home_team": "PHI",
        "away_team": "DAL",
        "season": 2026,
        "week": None,
        "site_class": "HOME",
        "kickoff_utc": "2026-10-18T17:00:00Z",
        "rest_days_home": 6.0,
        "rest_days_away": 6.0,
        "seed": DEFAULT_SEED,
        "simulations": 2000,
    }
    missing_strength = {
        "game_id": "t4366u-NO-EPA-ZZ@BUF",
        "home_team": "BUF",
        "away_team": "ZZZ",
        "season": 2026,
        "week": 6,
        "site_class": "HOME",
        "kickoff_utc": "2026-10-18T17:00:00Z",
        "rest_days_home": 6.0,
        "rest_days_away": 6.0,
        "seed": DEFAULT_SEED,
        "simulations": 2000,
    }
    return {
        "season": 2026,
        "week": 6,
        "schedule_enabled": False,
        "publication": "NFL_NO_GO",
        "t7_status": "FROZEN_PENDING_RYAN_AFTER_IMV_PACKET",
        "cards": [home, short, neutral, missing_week, missing_strength],
    }


def load_cards(path: Path) -> List[Dict[str, Any]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, list):
        return [dict(item) for item in raw]
    if isinstance(raw, dict) and isinstance(raw.get("cards"), list):
        return [dict(item) for item in raw["cards"]]
    if isinstance(raw, dict):
        return [dict(raw)]
    raise FailClosed(REASON_MISSING, f"unrecognized card file: {path}")


def packaged_epa_path() -> Path:
    return PACKAGED_EPA_PRIORS_2026


def packaged_epa_sha256() -> str:
    return hashlib.sha256(PACKAGED_EPA_PRIORS_2026.read_bytes()).hexdigest()
