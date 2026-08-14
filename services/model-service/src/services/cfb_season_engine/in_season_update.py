"""In-season updating foundation — shrinkaged rating moves from real results.

This is a **foundation**, not a fully automated live pipeline. Final scores
(via tracking ``record_result`` or the dedicated ingest endpoint) produce
inspectable per-team efficiency deltas that project-game can apply on top of
preseason SP+ priors.

Safety
------
- Per-game residual is clamped (weird blowouts cannot nuke a rating).
- Updates shrink toward the preseason prior via decaying learning rate.
- Games 0–2 are prior-heavy (no Week-1 cliff). Games 3–8 ramp toward
  observed efficiency. One noisy week must not replace the prior.
- Injury / QB inactive: full-strength vs current path when a live feed
  exists (stub until a feed is wired).
- Preseason baseline is always preserved and inspectable.
- Ops SoT: data/ops/cfb-phase1-projections-power-20260814.md
"""

from __future__ import annotations

import json
import logging
import os
import threading
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple

from src.services.cfb_season_engine import priors as P
from src.services.cfb_season_engine.types import EfficiencyProfile

log = logging.getLogger("kosedge.cfb.in_season_update")

# ---------------------------------------------------------------------------
# Knobs (documented; measured later against live results)
# ---------------------------------------------------------------------------
# Points of residual margin → points of off/def efficiency (0–100 scale).
RESIDUAL_TO_EFF = 0.35
# Max |Δeff| applied from a single game (after week weight).
MAX_GAME_MOVE = 3.5
# Hard clamp on residual margin (pts) before scaling.
MAX_RESIDUAL = 28.0
# Learning rate shrinks with games: alpha = ALPHA0 / (1 + n_games)^ALPHA_POW
# Prior-heavy: one game cannot replace the preseason prior (games/N style).
ALPHA0 = 0.32
ALPHA_POW = 0.70
# Blend of residual onto offense of winner / defense of loser split.
OFF_SHARE = 0.55  # of home residual goes to home offense; rest to away defense (signed)
# Max absolute cumulative delta from preseason.
MAX_CUMULATIVE_DELTA = 12.0
# Uncertainty reduction per observed game (applied in early_season diagnostics).
CONFIDENCE_PER_GAME = 0.08
MAX_CONFIDENCE = 0.85

_LOCK = threading.RLock()
_STATE: Optional["InSeasonState"] = None


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(x)))


def week_weight(week: int) -> float:
    """Prior-heavy early; blend ramp midseason. No Week-1 cliff.

    Games 0–2: small weight (continuity / QB prior still dominate).
    Games 3–8: ramp toward observed efficiency.
    Late season: still shrink — do not fully replace the prior.
    """
    w = int(week or 0)
    if w <= 0:
        return 0.16
    if w == 1:
        return 0.20
    if w == 2:
        return 0.28
    if w == 3:
        return 0.40
    if w == 4:
        return 0.50
    if w <= 8:
        return 0.62
    if w <= 12:
        return 0.58
    return 0.50


def learning_rate(n_games: int) -> float:
    return float(ALPHA0) / ((1.0 + max(0, int(n_games))) ** float(ALPHA_POW))


def state_paths() -> List[Path]:
    """Writable candidates for the in-season state snapshot."""
    env = os.environ.get("CFB_INSEASON_STATE_PATH", "").strip()
    paths: List[Path] = []
    if env:
        paths.append(Path(env))
    paths.extend(
        [
            Path("/app/data/ops/cfb_inseason_state/state.json"),
            Path("/tmp/cfb_inseason_state/state.json"),
            Path(__file__).resolve().parents[4]
            / "data"
            / "ops"
            / "cfb_inseason_state"
            / "state.json",
        ]
    )
    # Dedup
    out: List[Path] = []
    seen = set()
    for p in paths:
        key = str(p)
        if key not in seen:
            seen.add(key)
            out.append(p)
    return out


@dataclass
class TeamInSeasonState:
    team: str
    # Preseason baselines (efficiency 0–100 scale).
    preseason_off_eff: float
    preseason_def_eff: float
    # Cumulative deltas applied on top of preseason.
    delta_off_eff: float = 0.0
    delta_def_eff: float = 0.0
    n_games: int = 0
    confidence: float = 0.0
    last_updated: str = ""
    last_game_id: str = ""
    history: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def current_off_eff(self) -> float:
        return _clamp(self.preseason_off_eff + self.delta_off_eff, 0.0, 100.0)

    @property
    def current_def_eff(self) -> float:
        return _clamp(self.preseason_def_eff + self.delta_def_eff, 0.0, 100.0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "team": self.team,
            "preseason_off_eff": round(self.preseason_off_eff, 3),
            "preseason_def_eff": round(self.preseason_def_eff, 3),
            "delta_off_eff": round(self.delta_off_eff, 3),
            "delta_def_eff": round(self.delta_def_eff, 3),
            "current_off_eff": round(self.current_off_eff, 3),
            "current_def_eff": round(self.current_def_eff, 3),
            "n_games": self.n_games,
            "confidence": round(self.confidence, 4),
            "last_updated": self.last_updated,
            "last_game_id": self.last_game_id,
            "history": list(self.history[-12:]),
        }


@dataclass
class InSeasonState:
    season: int = 2026
    engine_version: str = ""
    updated_at: str = ""
    teams: Dict[str, TeamInSeasonState] = field(default_factory=dict)
    events: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "season": self.season,
            "engine_version": self.engine_version or P.ENGINE_VERSION,
            "updated_at": self.updated_at,
            "n_teams_touched": len(self.teams),
            "n_events": len(self.events),
            "teams": {k: v.to_dict() for k, v in sorted(self.teams.items())},
            "recent_events": list(self.events[-25:]),
            "rules": documentation()["rules"],
            "fidelity": "foundation_approximate",
        }


def documentation() -> Dict[str, Any]:
    return {
        "module": "src.services.cfb_season_engine.in_season_update",
        "engine_version": P.ENGINE_VERSION,
        "ops": "data/ops/cfb-inseason-update-20260805.md",
        "fidelity": "foundation_approximate",
        "rules": {
            "residual": "actual_margin_home - model_margin_home (home_score-away_score - model_spread_home*-1 convention: actual_home_minus_away - expected_home_minus_away)",
            "week_weight": "W0–1 prior-heavy (0.16–0.20); W3–8 ramp to 0.62; no Week-1 cliff",
            "learning_rate": f"alpha = {ALPHA0} / (1+n_games)^{ALPHA_POW}",
            "max_game_move": MAX_GAME_MOVE,
            "max_residual": MAX_RESIDUAL,
            "max_cumulative_delta": MAX_CUMULATIVE_DELTA,
            "shrinkage": "toward preseason prior via decaying alpha; cumulative clamp",
            "application": "deltas added to packaged SP+ off_eff/def_eff inside build_efficiency_profile",
        },
        "endpoints": {
            "ingest": "POST /cfb/season-engine/in-season/ingest-result",
            "state": "GET /cfb/season-engine/in-season/state",
            "team": "GET /cfb/season-engine/in-season/team/{team}",
            "reset": "POST /cfb/season-engine/in-season/reset",
            "from_tracking": "POST /cfb/season-engine/projections/{id}/result?apply_inseason=true",
        },
    }


def _ensure_team(
    state: InSeasonState,
    team: str,
    *,
    preseason_off: float,
    preseason_def: float,
) -> TeamInSeasonState:
    team = str(team).upper()
    row = state.teams.get(team)
    if row is None:
        row = TeamInSeasonState(
            team=team,
            preseason_off_eff=float(preseason_off),
            preseason_def_eff=float(preseason_def),
        )
        state.teams[team] = row
    return row


def _preseason_eff(team: str) -> Tuple[float, float]:
    from src.services.cfb_season_engine.efficiency import build_efficiency_profile

    # Read packaged baseline without applying in-season deltas (apply=False).
    prof = build_efficiency_profile(team, apply_inseason=False)
    return float(prof.off_eff), float(prof.def_eff)


def load_state(*, force_reload: bool = False) -> InSeasonState:
    global _STATE
    with _LOCK:
        if _STATE is not None and not force_reload:
            return _STATE
        for path in state_paths():
            if path.exists():
                try:
                    raw = json.loads(path.read_text(encoding="utf-8"))
                    st = _from_raw(raw)
                    _STATE = st
                    return st
                except Exception as exc:
                    log.warning("failed to load in-season state from %s: %s", path, exc)
        _STATE = InSeasonState(engine_version=P.ENGINE_VERSION, updated_at=_utc_now())
        return _STATE


def _from_raw(raw: Mapping[str, Any]) -> InSeasonState:
    teams: Dict[str, TeamInSeasonState] = {}
    for code, row in (raw.get("teams") or {}).items():
        teams[str(code).upper()] = TeamInSeasonState(
            team=str(code).upper(),
            preseason_off_eff=float(row.get("preseason_off_eff", 50.0)),
            preseason_def_eff=float(row.get("preseason_def_eff", 50.0)),
            delta_off_eff=float(row.get("delta_off_eff", 0.0)),
            delta_def_eff=float(row.get("delta_def_eff", 0.0)),
            n_games=int(row.get("n_games", 0) or 0),
            confidence=float(row.get("confidence", 0.0) or 0.0),
            last_updated=str(row.get("last_updated") or ""),
            last_game_id=str(row.get("last_game_id") or ""),
            history=list(row.get("history") or []),
        )
    return InSeasonState(
        season=int(raw.get("season") or 2026),
        engine_version=str(raw.get("engine_version") or P.ENGINE_VERSION),
        updated_at=str(raw.get("updated_at") or ""),
        teams=teams,
        events=list(raw.get("recent_events") or raw.get("events") or []),
    )


def save_state(state: Optional[InSeasonState] = None) -> Optional[Path]:
    state = state or load_state()
    state.updated_at = _utc_now()
    state.engine_version = P.ENGINE_VERSION
    payload = state.to_dict()
    # Persist fuller event list
    payload["events"] = list(state.events[-200:])
    blob = json.dumps(payload, indent=2, sort_keys=True)
    for path in state_paths():
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(blob + "\n", encoding="utf-8")
            return path
        except Exception as exc:
            log.debug("in-season state write failed for %s: %s", path, exc)
    return None


def reset_state(*, season: int = 2026) -> InSeasonState:
    global _STATE
    with _LOCK:
        _STATE = InSeasonState(
            season=int(season),
            engine_version=P.ENGINE_VERSION,
            updated_at=_utc_now(),
        )
        save_state(_STATE)
        return _STATE


def get_team_delta(team: str) -> Dict[str, float]:
    """Return efficiency deltas for a team (zeros if untouched)."""
    st = load_state()
    row = st.teams.get(str(team).upper())
    if row is None:
        return {"delta_off_eff": 0.0, "delta_def_eff": 0.0, "n_games": 0, "confidence": 0.0}
    return {
        "delta_off_eff": float(row.delta_off_eff),
        "delta_def_eff": float(row.delta_def_eff),
        "n_games": int(row.n_games),
        "confidence": float(row.confidence),
    }


def apply_efficiency_deltas(profile: EfficiencyProfile) -> EfficiencyProfile:
    """Return a copy of profile with in-season deltas applied (inspectable)."""
    d = get_team_delta(profile.team)
    if not d["n_games"] and abs(d["delta_off_eff"]) < 1e-9 and abs(d["delta_def_eff"]) < 1e-9:
        return profile
    off = _clamp(profile.off_eff + d["delta_off_eff"], 0.0, 100.0)
    de = _clamp(profile.def_eff + d["delta_def_eff"], 0.0, 100.0)
    note = (
        f"{profile.notes} | in_season: Δoff={d['delta_off_eff']:+.2f} "
        f"Δdef={d['delta_def_eff']:+.2f} n={d['n_games']} conf={d['confidence']:.2f}"
    )
    return EfficiencyProfile(
        team=profile.team,
        off_eff=off,
        def_eff=de,
        success_off=_clamp(profile.success_off + 0.6 * d["delta_off_eff"], 0.0, 100.0),
        success_def=_clamp(profile.success_def + 0.6 * d["delta_def_eff"], 0.0, 100.0),
        explosiveness=profile.explosiveness,
        sp_plus=profile.sp_plus,
        sp_offense=profile.sp_offense,
        sp_defense=profile.sp_defense,
        sp_rank=profile.sp_rank,
        prior_year=profile.prior_year,
        carry_to_season=profile.carry_to_season,
        source=f"{profile.source}+in_season",
        fidelity=profile.fidelity,
        notes=note,
    )


def _apply_team_move(
    row: TeamInSeasonState,
    *,
    d_off: float,
    d_def: float,
    week: int,
    game_id: str,
    residual: float,
) -> Dict[str, Any]:
    alpha = learning_rate(row.n_games)
    ww = week_weight(week)
    scale = alpha * ww
    move_off = _clamp(d_off * scale, -MAX_GAME_MOVE, MAX_GAME_MOVE)
    move_def = _clamp(d_def * scale, -MAX_GAME_MOVE, MAX_GAME_MOVE)
    # Shrinkage toward prior: after move, pull cumulative delta slightly back.
    shrink = 0.08 * (1.0 - ww)  # stronger late-season pull to prior
    new_delta_off = _clamp(
        (row.delta_off_eff + move_off) * (1.0 - shrink),
        -MAX_CUMULATIVE_DELTA,
        MAX_CUMULATIVE_DELTA,
    )
    new_delta_def = _clamp(
        (row.delta_def_eff + move_def) * (1.0 - shrink),
        -MAX_CUMULATIVE_DELTA,
        MAX_CUMULATIVE_DELTA,
    )
    before = {
        "delta_off_eff": row.delta_off_eff,
        "delta_def_eff": row.delta_def_eff,
        "current_off_eff": row.current_off_eff,
        "current_def_eff": row.current_def_eff,
    }
    row.delta_off_eff = new_delta_off
    row.delta_def_eff = new_delta_def
    row.n_games += 1
    row.confidence = _clamp(
        row.confidence + CONFIDENCE_PER_GAME * ww, 0.0, MAX_CONFIDENCE
    )
    row.last_updated = _utc_now()
    row.last_game_id = game_id
    step = {
        "at": row.last_updated,
        "game_id": game_id,
        "week": week,
        "residual_home": round(residual, 3),
        "week_weight": ww,
        "alpha": round(alpha, 4),
        "move_off": round(move_off, 3),
        "move_def": round(move_def, 3),
        "before": {k: round(v, 3) for k, v in before.items()},
        "after": {
            "delta_off_eff": round(row.delta_off_eff, 3),
            "delta_def_eff": round(row.delta_def_eff, 3),
            "current_off_eff": round(row.current_off_eff, 3),
            "current_def_eff": round(row.current_def_eff, 3),
            "confidence": round(row.confidence, 4),
            "n_games": row.n_games,
        },
    }
    row.history.append(step)
    row.history = row.history[-20:]
    return step


def ingest_result(
    *,
    home_team: str,
    away_team: str,
    home_score: int,
    away_score: int,
    week: int = 1,
    season: int = 2026,
    model_spread_home: Optional[float] = None,
    expected_home_score: Optional[float] = None,
    expected_away_score: Optional[float] = None,
    game_id: str = "",
    projection_id: str = "",
    source: str = "manual",
) -> Dict[str, Any]:
    """Apply one completed game to in-season state.

    ``model_spread_home`` is the model's home-relative spread (negative = home favored),
    matching project-game ``spread_home``.
    """
    home = str(home_team).upper()
    away = str(away_team).upper()
    actual_margin = float(home_score) - float(away_score)
    if model_spread_home is not None:
        # spread_home ≈ away - home expected → expected home margin = -spread_home
        expected_margin = -float(model_spread_home)
    elif expected_home_score is not None and expected_away_score is not None:
        expected_margin = float(expected_home_score) - float(expected_away_score)
    else:
        expected_margin = 0.0
    residual = _clamp(actual_margin - expected_margin, -MAX_RESIDUAL, MAX_RESIDUAL)

    # Positive residual: home outperformed model → boost home off + away def (home scored more / allowed less relative)
    # Split: home offense gets +OFF_SHARE * residual; away defense gets -OFF_SHARE * residual
    #          away offense gets - (1-OFF_SHARE) * residual; home defense gets + (1-OFF_SHARE) * residual
    home_d_off = RESIDUAL_TO_EFF * OFF_SHARE * residual
    away_d_def = -RESIDUAL_TO_EFF * OFF_SHARE * residual
    away_d_off = -RESIDUAL_TO_EFF * (1.0 - OFF_SHARE) * residual
    home_d_def = RESIDUAL_TO_EFF * (1.0 - OFF_SHARE) * residual

    gid = game_id or projection_id or f"{season}-W{int(week):02d}-{away}@{home}"

    with _LOCK:
        state = load_state()
        state.season = int(season)
        h_off0, h_def0 = _preseason_eff(home)
        a_off0, a_def0 = _preseason_eff(away)
        home_row = _ensure_team(state, home, preseason_off=h_off0, preseason_def=h_def0)
        away_row = _ensure_team(state, away, preseason_off=a_off0, preseason_def=a_def0)

        # Idempotency: skip if same game_id already applied to both
        if home_row.last_game_id == gid and away_row.last_game_id == gid:
            return {
                "ok": True,
                "skipped": True,
                "reason": "game_id already applied",
                "game_id": gid,
                "home": home_row.to_dict(),
                "away": away_row.to_dict(),
            }

        home_step = _apply_team_move(
            home_row,
            d_off=home_d_off,
            d_def=home_d_def,
            week=week,
            game_id=gid,
            residual=residual,
        )
        away_step = _apply_team_move(
            away_row,
            d_off=away_d_off,
            d_def=away_d_def,
            week=week,
            game_id=gid,
            residual=-residual,
        )
        event = {
            "at": _utc_now(),
            "game_id": gid,
            "projection_id": projection_id,
            "season": season,
            "week": week,
            "home_team": home,
            "away_team": away,
            "home_score": int(home_score),
            "away_score": int(away_score),
            "actual_margin_home": actual_margin,
            "expected_margin_home": expected_margin,
            "residual_home": residual,
            "week_weight": week_weight(week),
            "source": source,
            "home_step": home_step,
            "away_step": away_step,
        }
        state.events.append(event)
        state.events = state.events[-200:]
        path = save_state(state)

    return {
        "ok": True,
        "skipped": False,
        "game_id": gid,
        "residual_home": residual,
        "expected_margin_home": expected_margin,
        "actual_margin_home": actual_margin,
        "week_weight": week_weight(week),
        "home": home_row.to_dict(),
        "away": away_row.to_dict(),
        "state_path": str(path) if path else None,
        "rules": documentation()["rules"],
        "engine_version": P.ENGINE_VERSION,
    }


def state_summary(*, team: Optional[str] = None) -> Dict[str, Any]:
    st = load_state()
    if team:
        code = str(team).upper()
        row = st.teams.get(code)
        if row is None:
            off0, def0 = _preseason_eff(code)
            return {
                "ok": True,
                "team": code,
                "untouched": True,
                "preseason_off_eff": off0,
                "preseason_def_eff": def0,
                "delta_off_eff": 0.0,
                "delta_def_eff": 0.0,
                "current_off_eff": off0,
                "current_def_eff": def0,
                "n_games": 0,
                "engine_version": P.ENGINE_VERSION,
                "documentation": documentation(),
            }
        return {"ok": True, "untouched": False, **row.to_dict(), "documentation": documentation()}
    payload = st.to_dict()
    payload["ok"] = True
    payload["documentation"] = documentation()
    return payload
