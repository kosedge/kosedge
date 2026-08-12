"""NFL Kickoff Injury → KEI Cadence (in-season reprice windows).

Doctrine
--------
- Model research fair stays stable (no automatic midweek Model overwrite).
- Injury information updates SoT depth/availability, Active PR, and KEI
  (handicap / product line) only.
- Edge tags / play-to recompute as KEI vs Current market only.
- Cadence is mechanical: fixed ET windows + status → participation map.

Config
------
Defaults live in this module; overrides load from
``data/ops/nfl-injury-kei-cadence/config.json`` when present.
"""

from __future__ import annotations

import copy
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Literal, Mapping, Optional, Sequence, Tuple

from src.services.nfl_decision_engine import decide_side
from src.services.nfl_model_handicap import (
    annotate_projection_model_handicap,
    extract_model_markets_from_projection,
    snapshot_markets,
)

WindowId = Literal["midweek", "friday_final", "gameday_inactives", "post_game"]
Scope = Literal["affected", "full_slate", "game", "played_game"]

CONFIG_RELATIVE = Path("data/ops/nfl-injury-kei-cadence/config.json")

# ---------------------------------------------------------------------------
# Defaults (overridable via config.json)
# ---------------------------------------------------------------------------

DEFAULT_WINDOWS: Dict[str, Dict[str, Any]] = {
    "midweek": {
        "label": "Midweek report",
        "day_et": "thu",
        "hour_et": 16,
        "minute_et": 0,
        "scope": "affected",
        "action": "ingest_sot_kei",
    },
    "friday_final": {
        "label": "Friday final",
        "day_et": "fri",
        "hour_et": 16,
        "minute_et": 0,
        "scope": "full_slate",
        "action": "ingest_sot_kei",
    },
    "gameday_inactives": {
        "label": "Gameday inactives",
        "minutes_before_kickoff": 90,
        "scope": "game",
        "action": "final_kei_stamp",
        "lock_pre_kick_kei": True,
    },
    "post_game": {
        "label": "Post-game",
        "scope": "played_game",
        "action": "no_kei_change",
        "tuesday_pr_only": True,
    },
}

# Out 0% · Doubtful ~25% · Questionable ~50% · Limited minor · Full expected
DEFAULT_STATUS_PARTICIPATION: Dict[str, float] = {
    "out": 0.0,
    "doubtful": 0.25,
    "questionable": 0.5,
    "limited": 0.85,
    "probable": 0.95,
    "full": 1.0,
    "healthy": 1.0,
    "ir": 0.0,
    "pup": 0.0,
    "suspended": 0.0,
    "inactive": 0.0,
}

DEFAULT_IMPACT_POINTS: Dict[str, float] = {
    "qb1_out_spread": 3.5,
    "qb1_doubtful_spread": 2.5,
    "qb1_questionable_spread": 1.0,
    "qb1_out_total": 1.5,
    "qb1_doubtful_total": 1.0,
    "qb1_questionable_total": 0.5,
    "skill_out_spread": 0.75,
    "skill_out_total": 0.4,
    "ol_out_spread": 0.5,
    "ol_out_total": 0.25,
    "defense_out_spread": 0.6,
    "defense_out_total": 0.2,
}

DEFAULT_LOG_THRESHOLDS: Dict[str, float] = {
    "spread_pts": 0.25,
    "total_pts": 0.5,
}

QB1_FORCE_REPRICE_STATUSES = frozenset({"out", "doubtful"})

SKILL_POSITIONS = frozenset({"RB", "WR", "TE", "HB", "FB"})
OL_POSITIONS = frozenset({"LT", "LG", "C", "RG", "RT", "OL", "T", "G"})
DEF_POSITIONS = frozenset({"DE", "DT", "DL", "EDGE", "LB", "CB", "S", "DB", "NT"})


@dataclass(frozen=True)
class InjuryStatusChange:
    """One SoT status diff that may move KEI."""

    team: str
    player_id: str
    player_name: str = ""
    position: str = ""
    depth_order: int = 99
    previous_status: str = "healthy"
    new_status: str = "healthy"
    is_qb1: bool = False

    @property
    def participation_delta(self) -> float:
        return participation_from_status(self.new_status) - participation_from_status(
            self.previous_status
        )


@dataclass
class KeiDelta:
    """Signed KEI moves for one side of a game (team perspective)."""

    team: str
    spread_pts: float = 0.0  # positive = team weaker (less favored / more dog)
    total_pts: float = 0.0  # negative = lower total
    confidence_delta: float = 0.0
    alert: bool = False
    reasons: List[str] = field(default_factory=list)

    def materially_moves(
        self,
        *,
        spread_thresh: float = 0.25,
        total_thresh: float = 0.5,
    ) -> bool:
        return abs(self.spread_pts) >= spread_thresh or abs(self.total_pts) >= total_thresh


@dataclass
class WindowRunResult:
    window: WindowId
    snapshot_id: str
    noop: bool
    reason: str
    affected_teams: List[str] = field(default_factory=list)
    kei_moves: List[Dict[str, Any]] = field(default_factory=list)
    tag_moves: List[Dict[str, Any]] = field(default_factory=list)
    active_pr_refreshed: bool = False
    ops_line: str = ""
    locked_pre_kick: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


_CONFIG_CACHE: Optional[Dict[str, Any]] = None


def _repo_root() -> Path:
    # .../services/model-service/src/services/this_file.py → repo root
    return Path(__file__).resolve().parents[4]


def load_cadence_config(
    *,
    config_path: Optional[Path] = None,
    reload: bool = False,
) -> Dict[str, Any]:
    """Load JSON config with Python defaults as fallback."""
    global _CONFIG_CACHE
    if _CONFIG_CACHE is not None and not reload and config_path is None:
        return _CONFIG_CACHE

    base: Dict[str, Any] = {
        "timezone": "America/New_York",
        "windows": copy.deepcopy(DEFAULT_WINDOWS),
        "status_participation": dict(DEFAULT_STATUS_PARTICIPATION),
        "impact_points": dict(DEFAULT_IMPACT_POINTS),
        "log_thresholds": dict(DEFAULT_LOG_THRESHOLDS),
        "qb1_force_reprice_statuses": sorted(QB1_FORCE_REPRICE_STATUSES),
        "manual_sot_until_feed_live": True,
        "doctrine": {
            "updates": ["sot_depth", "active_pr", "kei_handicap", "edge_tags"],
            "does_not_modify": [
                "model_pr",
                "tuesday_shrink",
                "ryan_adj",
                "model_markets_research",
            ],
        },
    }

    path = config_path or (_repo_root() / CONFIG_RELATIVE)
    if path.is_file():
        try:
            raw = json.loads(path.read_text())
            if isinstance(raw, dict):
                for key in (
                    "windows",
                    "status_participation",
                    "impact_points",
                    "log_thresholds",
                    "doctrine",
                ):
                    if isinstance(raw.get(key), dict):
                        base[key] = {**base.get(key, {}), **raw[key]}
                if "qb1_force_reprice_statuses" in raw:
                    base["qb1_force_reprice_statuses"] = list(
                        raw["qb1_force_reprice_statuses"]
                    )
                if "manual_sot_until_feed_live" in raw:
                    base["manual_sot_until_feed_live"] = bool(
                        raw["manual_sot_until_feed_live"]
                    )
                if "timezone" in raw:
                    base["timezone"] = str(raw["timezone"])
                if "as_of" in raw:
                    base["as_of"] = raw["as_of"]
                if "notes" in raw:
                    base["notes"] = raw["notes"]
        except Exception:
            pass

    if config_path is None:
        _CONFIG_CACHE = base
    return base


def normalize_status(status: Optional[str]) -> str:
    raw = str(status or "").strip().lower()
    if not raw or raw in {"healthy", "active"}:
        return "healthy"
    if raw in DEFAULT_STATUS_PARTICIPATION:
        return raw
    if "injured reserve" in raw or raw == "ir":
        return "ir"
    if "doubtful" in raw:
        return "doubtful"
    if "questionable" in raw:
        return "questionable"
    if "limited" in raw:
        return "limited"
    if "probable" in raw:
        return "probable"
    if "full" in raw:
        return "full"
    if "out" in raw or "inactive" in raw:
        return "out"
    if "pup" in raw:
        return "pup"
    if "suspend" in raw:
        return "suspended"
    return raw


def participation_from_status(status: Optional[str]) -> float:
    """Map official report status → expected participation ∈ [0, 1]."""
    cfg = load_cadence_config()
    mapping = cfg.get("status_participation") or DEFAULT_STATUS_PARTICIPATION
    key = normalize_status(status)
    if key in mapping:
        return float(mapping[key])
    return 0.88


def window_config(window: WindowId) -> Dict[str, Any]:
    cfg = load_cadence_config()
    windows = cfg.get("windows") or DEFAULT_WINDOWS
    if window not in windows:
        raise KeyError(f"Unknown injury→KEI window: {window}")
    return dict(windows[window])


def describe_friday_1600_et() -> str:
    """Operator answer: What happens Friday at 4 ET?"""
    w = window_config("friday_final")
    return (
        f"{w.get('label', 'Friday final')} ({w.get('hour_et', 16):02d}:"
        f"{int(w.get('minute_et', 0)):02d} ET): Ingest injury report → diff SoT → "
        f"snapshot_id → Active PR refresh + full-slate KEI reprice "
        f"(line_role=handicap) → refresh Edge tags vs Current → ops line. "
        f"Model research fair / Model PR unchanged."
    )


def is_qb1_row(
    *,
    position: str,
    depth_order: int = 99,
    is_qb1: bool = False,
) -> bool:
    if is_qb1:
        return True
    return str(position or "").upper() == "QB" and int(depth_order or 99) <= 1


def diff_sot_statuses(
    previous: Sequence[Mapping[str, Any]],
    current: Sequence[Mapping[str, Any]],
) -> List[InjuryStatusChange]:
    """Diff two SoT player status lists → material status changes."""

    def _key(row: Mapping[str, Any]) -> str:
        pid = str(row.get("player_id") or "").strip()
        if pid:
            return pid
        return f"{row.get('team')}|{row.get('player_name')}|{row.get('position')}"

    prev_map = {_key(r): r for r in previous if isinstance(r, Mapping)}
    cur_map = {_key(r): r for r in current if isinstance(r, Mapping)}
    keys = set(prev_map) | set(cur_map)
    out: List[InjuryStatusChange] = []
    for key in sorted(keys):
        prev = prev_map.get(key) or {}
        cur = cur_map.get(key) or prev
        prev_status = normalize_status(prev.get("injury_status") or prev.get("status"))
        new_status = normalize_status(cur.get("injury_status") or cur.get("status"))
        if prev_status == new_status and key in prev_map and key in cur_map:
            continue
        if key not in prev_map and new_status in {"healthy", "full", "probable"}:
            continue
        team = str(cur.get("team") or prev.get("team") or "")
        position = str(cur.get("position") or prev.get("position") or "")
        depth = int(cur.get("depth_order") or prev.get("depth_order") or 99)
        qb1 = bool(cur.get("is_qb1") or prev.get("is_qb1")) or is_qb1_row(
            position=position, depth_order=depth
        )
        out.append(
            InjuryStatusChange(
                team=team,
                player_id=str(cur.get("player_id") or prev.get("player_id") or key),
                player_name=str(
                    cur.get("player_name") or prev.get("player_name") or ""
                ),
                position=position,
                depth_order=depth,
                previous_status=prev_status if key in prev_map else "healthy",
                new_status=new_status if key in cur_map else "out",
                is_qb1=qb1,
            )
        )
    return out


def _impact_for_change(change: InjuryStatusChange) -> KeiDelta:
    cfg = load_cadence_config()
    pts = cfg.get("impact_points") or DEFAULT_IMPACT_POINTS
    force = set(
        cfg.get("qb1_force_reprice_statuses") or list(QB1_FORCE_REPRICE_STATUSES)
    )

    prev_p = participation_from_status(change.previous_status)
    new_p = participation_from_status(change.new_status)
    # How much worse (positive) vs better (negative) for the team.
    lost = max(0.0, prev_p - new_p)
    gained = max(0.0, new_p - prev_p)
    severity = lost - gained

    spread = 0.0
    total = 0.0
    conf = 0.0
    alert = False
    reasons: List[str] = []
    pos = str(change.position or "").upper()
    status = change.new_status

    if change.is_qb1 or (pos == "QB" and change.depth_order <= 1):
        prev = change.previous_status
        # Pick baselines from the more severe of {prev, new} so restore
        # reverses the same Out/Doubtful magnitude that was applied.
        severe = status if severity >= 0 else prev
        if severe == "out" or severe in force or status == "out" or prev in force:
            base_spread = float(pts.get("qb1_out_spread", 3.5))
            base_total = float(pts.get("qb1_out_total", 1.5))
            if severe == "doubtful":
                base_spread = float(pts.get("qb1_doubtful_spread", 2.5))
                base_total = float(pts.get("qb1_doubtful_total", 1.0))
            elif severe == "questionable":
                base_spread = float(pts.get("qb1_questionable_spread", 1.0))
                base_total = float(pts.get("qb1_questionable_total", 0.5))
            # Participation delta scales the baseline (Out→Full = full reverse).
            spread = base_spread * severity
            total = -base_total * severity  # Out lowers total; restore raises
            conf = -0.12 if severity > 0 else 0.08
            alert = status in force and severity > 0
            reasons.append(
                f"QB1 {prev}→{status} "
                f"(participation {prev_p:.2f}→{new_p:.2f})"
            )
        elif abs(severity) > 1e-9:
            base_spread = float(pts.get("qb1_questionable_spread", 1.0))
            base_total = float(pts.get("qb1_questionable_total", 0.5))
            spread = base_spread * severity
            total = -base_total * severity
            conf = -0.05 if severity > 0 else 0.03
            reasons.append(f"QB1 {prev}→{status}")
    elif pos in SKILL_POSITIONS:
        spread = float(pts.get("skill_out_spread", 0.75)) * severity
        total = -float(pts.get("skill_out_total", 0.4)) * severity
        if abs(severity) > 1e-9:
            reasons.append(f"{pos} {change.previous_status}→{status}")
    elif pos in OL_POSITIONS:
        spread = float(pts.get("ol_out_spread", 0.5)) * severity
        total = -float(pts.get("ol_out_total", 0.25)) * severity
        if abs(severity) > 1e-9:
            reasons.append(f"OL {change.previous_status}→{status}")
    elif pos in DEF_POSITIONS:
        spread = float(pts.get("defense_out_spread", 0.6)) * severity
        total = -float(pts.get("defense_out_total", 0.2)) * severity
        if abs(severity) > 1e-9:
            reasons.append(f"DEF {change.previous_status}→{status}")
    else:
        spread = 0.35 * severity
        total = -0.15 * severity
        if abs(severity) > 1e-9:
            reasons.append(f"{pos or 'UNK'} {change.previous_status}→{status}")

    return KeiDelta(
        team=change.team,
        spread_pts=round(spread, 4),
        total_pts=round(total, 4),
        confidence_delta=round(conf, 4),
        alert=alert,
        reasons=reasons,
    )


def aggregate_team_deltas(
    changes: Sequence[InjuryStatusChange],
) -> Dict[str, KeiDelta]:
    by_team: Dict[str, KeiDelta] = {}
    for change in changes:
        piece = _impact_for_change(change)
        if abs(piece.spread_pts) < 1e-12 and abs(piece.total_pts) < 1e-12:
            continue
        cur = by_team.get(change.team)
        if cur is None:
            by_team[change.team] = piece
            continue
        cur.spread_pts = round(cur.spread_pts + piece.spread_pts, 4)
        cur.total_pts = round(cur.total_pts + piece.total_pts, 4)
        cur.confidence_delta = round(cur.confidence_delta + piece.confidence_delta, 4)
        cur.alert = cur.alert or piece.alert
        cur.reasons.extend(piece.reasons)
    return by_team


def must_force_kei_reprice(changes: Sequence[InjuryStatusChange]) -> bool:
    cfg = load_cadence_config()
    force = set(
        cfg.get("qb1_force_reprice_statuses") or list(QB1_FORCE_REPRICE_STATUSES)
    )
    for c in changes:
        if c.is_qb1 and c.new_status in force:
            return True
        if c.is_qb1 and c.previous_status in force and c.new_status not in force:
            # Restore path also forces reprice so KEI snaps back.
            return True
    return False


def make_snapshot_id(
    *,
    window: WindowId,
    season: int,
    week: int,
    when: Optional[datetime] = None,
) -> str:
    ts = when or datetime.now(timezone.utc)
    stamp = ts.strftime("%Y%m%dT%H%M%SZ")
    return f"nfl-inj-kei-{season}-w{week}-{window}-{stamp}"


def apply_kei_reprice_to_projection(
    projection: Dict[str, Any],
    *,
    home_team: str,
    away_team: str,
    team_deltas: Mapping[str, KeiDelta],
    lock_pre_kick: bool = False,
) -> Dict[str, Any]:
    """Reprice KEI handicap while freezing stamped Model markets.

    Home-spread convention: negative = home favored. When the home team gets
    weaker (positive team spread_pts), home spread moves toward / past zero
    (e.g. -7 → -3.5). Away weakness moves home spread more negative.
    """
    markets = projection.get("markets")
    if not isinstance(markets, dict):
        raise ValueError("projection.markets required for KEI reprice")

    prior_model = extract_model_markets_from_projection(projection)
    if prior_model is None:
        prior_model = snapshot_markets(markets)

    home_d = team_deltas.get(home_team) or KeiDelta(team=home_team)
    away_d = team_deltas.get(away_team) or KeiDelta(team=away_team)

    old_spread = float(markets.get("spread_home"))
    old_total = float(markets.get("total_mean"))

    # Net: home weaker → +spread; away weaker → −spread (home relatively stronger).
    net_spread = float(home_d.spread_pts) - float(away_d.spread_pts)
    net_total = float(home_d.total_pts) + float(away_d.total_pts)

    new_markets = dict(markets)
    new_markets["spread_home"] = round(old_spread + net_spread, 2)
    new_markets["total_mean"] = round(old_total + net_total, 2)
    projection["markets"] = new_markets

    annotate_projection_model_handicap(
        projection,
        prior_model_markets=prior_model,
        line_role="handicap",
    )

    diag = projection.setdefault("diagnostics", {})
    if not isinstance(diag, dict):
        diag = {}
        projection["diagnostics"] = diag
    inj = {
        "home_team": home_team,
        "away_team": away_team,
        "home_spread_pts": home_d.spread_pts,
        "away_spread_pts": away_d.spread_pts,
        "net_spread_pts": round(net_spread, 4),
        "net_total_pts": round(net_total, 4),
        "home_reasons": list(home_d.reasons),
        "away_reasons": list(away_d.reasons),
        "alert": bool(home_d.alert or away_d.alert),
        "confidence_delta": round(
            home_d.confidence_delta + away_d.confidence_delta, 4
        ),
        "lock_pre_kick_kei": bool(lock_pre_kick),
        "prior_kei_spread_home": old_spread,
        "prior_kei_total_mean": old_total,
    }
    diag["injury_kei_reprice"] = inj
    if lock_pre_kick:
        projection["pre_kick_kei_locked"] = True
        projection["pre_kick_kei_markets"] = snapshot_markets(new_markets)

    return projection


def recompute_side_tag(
    *,
    kei_spread_home: float,
    market_spread_home: float,
    week: Optional[int] = 1,
) -> Dict[str, Any]:
    """Tag = KEI vs Current only (Decision Engine / point grade)."""
    decision = decide_side(
        fair_spread_home=kei_spread_home,
        market_spread_home=market_spread_home,
        week=week,
    )
    return {
        "action_label": decision.action_label,
        "point_grade": decision.point_grade,
        "edge_magnitude": decision.edge_magnitude,
        "fair_line": kei_spread_home,
        "market_line": market_spread_home,
        "tag_source": "kei_vs_current",
    }


def refresh_active_pr_rows(
    *,
    published_model_prs: Mapping[str, float],
    injury_adjusted_active: Mapping[str, float],
    ryan_adjs: Optional[Mapping[str, float]] = None,
) -> Dict[str, Dict[str, float]]:
    """Refresh Active PR while freezing published Model PR (no Tuesday shrink).

    ``injury_adjusted_active`` is Method-B active (zero-centered) from current
    indices. Model PR stays at the Tuesday published snapshot.
    """
    ryan_adjs = ryan_adjs or {}
    out: Dict[str, Dict[str, float]] = {}
    for team, model_pr in published_model_prs.items():
        adj = float(ryan_adjs.get(team, 0.0) or 0.0)
        active = float(injury_adjusted_active.get(team, model_pr)) + adj
        out[team] = {
            "model_pr": round(float(model_pr), 3),
            "ryan_adj": round(adj, 3),
            "active_pr": round(active, 3),
            "ryan_pr": round(float(model_pr) + adj, 3),
        }
    return out


def loggable_moves(
    team_deltas: Mapping[str, KeiDelta],
) -> List[Dict[str, Any]]:
    cfg = load_cadence_config()
    thresh = cfg.get("log_thresholds") or DEFAULT_LOG_THRESHOLDS
    spread_t = float(thresh.get("spread_pts", 0.25))
    total_t = float(thresh.get("total_pts", 0.5))
    rows: List[Dict[str, Any]] = []
    for team, delta in team_deltas.items():
        if not delta.materially_moves(spread_thresh=spread_t, total_thresh=total_t):
            continue
        rows.append(
            {
                "team": team,
                "spread_pts": delta.spread_pts,
                "total_pts": delta.total_pts,
                "confidence_delta": delta.confidence_delta,
                "alert": delta.alert,
                "reasons": list(delta.reasons),
            }
        )
    return rows


def run_injury_kei_window(
    *,
    window: WindowId,
    season: int,
    week: int,
    previous_sot: Sequence[Mapping[str, Any]],
    current_sot: Sequence[Mapping[str, Any]],
    games: Sequence[Mapping[str, Any]],
    published_model_prs: Optional[Mapping[str, float]] = None,
    active_prs_before: Optional[Mapping[str, float]] = None,
    dry_run: bool = True,
) -> WindowRunResult:
    """Mechanical pipeline for one report window.

    Ingest → Diff SoT → snapshot_id → Active PR + KEI (affected or full Friday)
    → refresh tags → ops line. No-diff → heartbeat no-op.
    """
    wcfg = window_config(window)
    action = str(wcfg.get("action") or "")
    scope = str(wcfg.get("scope") or "affected")

    if action == "no_kei_change":
        snap = make_snapshot_id(window=window, season=season, week=week)
        return WindowRunResult(
            window=window,
            snapshot_id=snap,
            noop=True,
            reason="post_game_no_kei_change_tuesday_pr_only",
            ops_line=(
                f"[injury-kei] {window} season={season} week={week} "
                f"NO-OP (played game locked; Tuesday PR path only) "
                f"snapshot={snap}"
            ),
        )

    changes = diff_sot_statuses(previous_sot, current_sot)
    snap = make_snapshot_id(window=window, season=season, week=week)

    if not changes and not must_force_kei_reprice(changes):
        return WindowRunResult(
            window=window,
            snapshot_id=snap,
            noop=True,
            reason="no_sot_diff_heartbeat",
            ops_line=(
                f"[injury-kei] {window} season={season} week={week} "
                f"HEARTBEAT no-diff snapshot={snap}"
                + (" dry_run" if dry_run else "")
            ),
        )

    team_deltas = aggregate_team_deltas(changes)
    affected = sorted(team_deltas.keys())
    lock = bool(wcfg.get("lock_pre_kick_kei")) and window == "gameday_inactives"

    # Scope filter for games
    kei_moves: List[Dict[str, Any]] = []
    tag_moves: List[Dict[str, Any]] = []
    for game in games:
        home = str(game.get("home_team") or game.get("home") or "")
        away = str(game.get("away_team") or game.get("away") or "")
        if not home or not away:
            continue
        if scope == "affected" and home not in team_deltas and away not in team_deltas:
            continue
        if scope == "game":
            # Caller should pass the single kickoff game; still require touch.
            if home not in team_deltas and away not in team_deltas and not changes:
                continue

        proj = game.get("projection")
        if not isinstance(proj, dict):
            # Synthesize minimal projection from fair/kei fields for dry-run.
            kei_spread = float(game.get("kei_spread_home", game.get("spread_home", 0.0)))
            kei_total = float(game.get("kei_total_mean", game.get("total_mean", 44.0)))
            model_spread = float(game.get("model_spread_home", kei_spread))
            model_total = float(game.get("model_total_mean", kei_total))
            proj = {
                "game_id": game.get("game_id") or f"{away}@{home}",
                "markets": {
                    "spread_home": kei_spread,
                    "total_mean": kei_total,
                    "home_win_prob": game.get("home_win_prob", 0.55),
                    "away_win_prob": game.get("away_win_prob", 0.45),
                    "fair_home_ml": game.get("fair_home_ml", -120),
                    "fair_away_ml": game.get("fair_away_ml", 100),
                },
                "model_markets": {
                    "spread_home": model_spread,
                    "total_mean": model_total,
                    "home_win_prob": game.get("home_win_prob", 0.55),
                    "away_win_prob": game.get("away_win_prob", 0.45),
                    "fair_home_ml": game.get("fair_home_ml", -120),
                    "fair_away_ml": game.get("fair_away_ml", 100),
                },
            }

        market_spread = game.get("market_spread_home")
        if market_spread is None:
            market_spread = game.get("current_spread_home")

        before_kei = float(proj["markets"]["spread_home"])
        before_tag = None
        if market_spread is not None:
            before_tag = recompute_side_tag(
                kei_spread_home=before_kei,
                market_spread_home=float(market_spread),
                week=week,
            )

        model_before = extract_model_markets_from_projection(proj)
        apply_kei_reprice_to_projection(
            proj,
            home_team=home,
            away_team=away,
            team_deltas=team_deltas,
            lock_pre_kick=lock,
        )
        model_after = extract_model_markets_from_projection(proj)
        after_kei = float(proj["markets"]["spread_home"])
        after_total = float(proj["markets"]["total_mean"])

        after_tag = None
        if market_spread is not None:
            after_tag = recompute_side_tag(
                kei_spread_home=after_kei,
                market_spread_home=float(market_spread),
                week=week,
            )

        move = {
            "game_id": proj.get("game_id"),
            "home_team": home,
            "away_team": away,
            "kei_spread_before": before_kei,
            "kei_spread_after": after_kei,
            "kei_total_after": after_total,
            "model_spread_before": None
            if model_before is None
            else model_before.get("spread_home"),
            "model_spread_after": None
            if model_after is None
            else model_after.get("spread_home"),
            "model_unchanged": (
                model_before is not None
                and model_after is not None
                and model_before.get("spread_home") == model_after.get("spread_home")
                and model_before.get("total_mean") == model_after.get("total_mean")
            ),
            "line_role": proj.get("line_role"),
            "dry_run": dry_run,
            "projection": proj if dry_run else None,
        }
        kei_moves.append(move)
        if before_tag and after_tag and before_tag["action_label"] != after_tag["action_label"]:
            tag_moves.append(
                {
                    "game_id": proj.get("game_id"),
                    "before": before_tag,
                    "after": after_tag,
                }
            )
        elif before_tag and after_tag:
            # Still record point-grade shifts even if action label equal.
            if before_tag.get("point_grade") != after_tag.get("point_grade"):
                tag_moves.append(
                    {
                        "game_id": proj.get("game_id"),
                        "before": before_tag,
                        "after": after_tag,
                    }
                )

    active_refreshed = False
    if published_model_prs and active_prs_before is not None:
        # Shift Active PR by team spread impact (proxy for injury-aware Method B).
        adjusted = dict(active_prs_before)
        for team, delta in team_deltas.items():
            # Weaker team → lower Active PR (spread_pts positive).
            adjusted[team] = float(adjusted.get(team, 0.0)) - float(delta.spread_pts)
        refresh_active_pr_rows(
            published_model_prs=published_model_prs,
            injury_adjusted_active=adjusted,
        )
        active_refreshed = True

    logged = loggable_moves(team_deltas)
    force = must_force_kei_reprice(changes)
    ops = (
        f"[injury-kei] {window} season={season} week={week} "
        f"scope={scope} teams={len(affected)} games={len(kei_moves)} "
        f"log_moves={len(logged)} tag_moves={len(tag_moves)} "
        f"force_qb1={force} active_pr={active_refreshed} "
        f"snapshot={snap}"
        + (" dry_run" if dry_run else "")
        + (" LOCK_PRE_KICK" if lock else "")
    )

    return WindowRunResult(
        window=window,
        snapshot_id=snap,
        noop=False,
        reason="repriced" if kei_moves else "diff_no_matching_games",
        affected_teams=affected,
        kei_moves=[
            {k: v for k, v in m.items() if k != "projection"} for m in kei_moves
        ],
        tag_moves=tag_moves,
        active_pr_refreshed=active_refreshed,
        ops_line=ops,
        locked_pre_kick=lock,
    )


def fixture_qb1_out_then_restore(
    *,
    home_team: str = "KC",
    away_team: str = "BUF",
    week: int = 1,
) -> Dict[str, Any]:
    """Built-in readiness fixture: QB1 Out moves KEI/tag; restore snaps back."""
    base_sot = [
        {
            "team": home_team,
            "player_id": "QB1-HOME",
            "player_name": "Starter QB",
            "position": "QB",
            "depth_order": 1,
            "injury_status": "healthy",
            "is_qb1": True,
        }
    ]
    out_sot = [
        {
            **base_sot[0],
            "injury_status": "out",
        }
    ]
    game = {
        "game_id": f"{away_team}@{home_team}-w{week}",
        "home_team": home_team,
        "away_team": away_team,
        "model_spread_home": -7.0,
        "model_total_mean": 48.0,
        "kei_spread_home": -6.5,
        "kei_total_mean": 47.5,
        "market_spread_home": -3.0,
        "home_win_prob": 0.72,
        "away_win_prob": 0.28,
    }
    published = {home_team: 4.2, away_team: 3.8}
    active_before = {home_team: 4.0, away_team: 3.8}

    out_run = run_injury_kei_window(
        window="midweek",
        season=2026,
        week=week,
        previous_sot=base_sot,
        current_sot=out_sot,
        games=[game],
        published_model_prs=published,
        active_prs_before=active_before,
        dry_run=True,
    )

    # After Out, build restore game from the moved KEI while Model stays -7.
    out_move = out_run.kei_moves[0] if out_run.kei_moves else {}
    restore_game = {
        **game,
        "kei_spread_home": out_move.get("kei_spread_after", -3.0),
        "kei_total_mean": out_move.get("kei_total_after", 46.0),
        "model_spread_home": -7.0,
        "model_total_mean": 48.0,
    }
    restore_run = run_injury_kei_window(
        window="friday_final",
        season=2026,
        week=week,
        previous_sot=out_sot,
        current_sot=base_sot,
        games=[restore_game],
        published_model_prs=published,
        active_prs_before={
            home_team: float(active_before[home_team])
            - float(
                (aggregate_team_deltas(diff_sot_statuses(base_sot, out_sot))
                 .get(home_team)
                 or KeiDelta(team=home_team)
                ).spread_pts
            ),
            away_team: active_before[away_team],
        },
        dry_run=True,
    )

    return {
        "out": out_run.to_dict(),
        "restore": restore_run.to_dict(),
        "friday_answer": describe_friday_1600_et(),
        "config_path": str(CONFIG_RELATIVE),
    }
