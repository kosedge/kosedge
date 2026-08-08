"""Universe loaders for the hierarchical season engine.

Default (``demo=False``): real 2026 regular-season schedule — prefer
``nfl_dp_schedules`` when a DB session has rows; otherwise the packaged
wall-chart JSON (272 REG games with byes).

Depth / roster fallback (fantasy-usable identities):

1. ``nfl_dp_depth_chart_weekly`` (preferred when populated)
2. ``nfl_dp_official_depth_charts`` (nflverse official snapshots)
3. Packaged ``nfl_depth_chart_2026_w1.json`` (checked-in nflverse slice)
4. ``demo_depth_chart`` (last resort / explicit ``demo=True``)

Strength priors (real mode) — efficiency backbone → existing O/D slot:

1. DB ``nfl_dp_team_rolling_features_weekly`` via ``_load_team_strength_priors``
   (mapped through ``efficiency_backbone`` when success/pace available)
2. Packaged ``nfl_team_efficiency_backbone_<season>.json`` (preferred) or
   legacy ``nfl_team_epa_priors_<season>.json``
3. League-average placeholder — never ``_DEMO_STRENGTH_BUMPS`` in real mode

``demo=True``: explicit opt-in round-robin + sparse demo skill cores + demo
strength bumps for offline unit tests. Never silently stay on demo
schedule/depth/strengths when a real artifact is available.

North star: ``data/ops/nfl-model-vision.md``.

Efficiency rates are always passed through ``calibration.apply_efficiency_priors``
(or baseline-derived overrides) so Layer 4 is never left on uncalibrated
dataclass defaults alone.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from src.services.nfl_season_engine.calibration import (
    CALIBRATION_TAG,
    ELITE_INT_RATE,
    apply_efficiency_priors,
    calibration_notes,
    efficiency_from_baseline_row,
)
from src.services.nfl_season_engine.team_strength import initialize_strengths
from src.services.nfl_season_engine.types import (
    EngineUniverse,
    PlayerRole,
    ScheduledGame,
)
from src.services.nfl_season_engine.depth_chart import apply_depth_chart_roster_book
from src.services.nfl_season_engine.usage_roles import annotate_roster_book

_PACKAGE_DATA_DIR = Path(__file__).resolve().parent / "data"
_PACKAGED_SCHEDULE_FILES = {
    2026: _PACKAGE_DATA_DIR / "nfl_regular_schedule_2026.json",
}
_PACKAGED_DEPTH_FILES = {
    2026: _PACKAGE_DATA_DIR / "nfl_depth_chart_2026_w1.json",
}
_PACKAGED_EPA_PRIOR_FILES = {
    2026: _PACKAGE_DATA_DIR / "nfl_team_epa_priors_2026.json",
}
_PACKAGED_EFFICIENCY_BACKBONE_FILES = {
    2026: _PACKAGE_DATA_DIR / "nfl_team_efficiency_backbone_2026.json",
}

NFL_TEAMS: List[str] = [
    "ARI", "ATL", "BAL", "BUF", "CAR", "CHI", "CIN", "CLE",
    "DAL", "DEN", "DET", "GB", "HOU", "IND", "JAX", "KC",
    "LA", "LAC", "LV", "MIA", "MIN", "NE", "NO", "NYG",
    "NYJ", "PHI", "PIT", "SEA", "SF", "TB", "TEN", "WAS",
]

SCHEDULE_SOURCE_DEMO = "demo_round_robin"
SCHEDULE_SOURCE_DB = "nfl_dp_schedules"
SCHEDULE_SOURCE_PACKAGED = "packaged_wall_chart_2026"

ROSTER_SOURCE_DEMO = "demo_depth_chart"
ROSTER_SOURCE_WEEKLY = "nfl_dp_depth_chart_weekly"
ROSTER_SOURCE_OFFICIAL = "nfl_dp_official_depth_charts"
ROSTER_SOURCE_PACKAGED = "packaged_nflverse_depth_2026"

STRENGTH_SOURCE_DEMO = "demo_epa_style_prior"
STRENGTH_SOURCE_EPA_PRIOR = "epa_prior"
STRENGTH_SOURCE_PACKAGED_EPA = "packaged_epa_prior"
STRENGTH_SOURCE_EFFICIENCY = "efficiency_backbone"
STRENGTH_SOURCE_PACKAGED_EFFICIENCY = "packaged_efficiency_backbone"
STRENGTH_SOURCE_PLACEHOLDER = "placeholder_league_avg"

_SKILL_POSITIONS = ("QB", "RB", "WR", "TE")


def normalize_team_abbr(raw: str) -> str:
    """Normalize common NFL team abbreviations (LAR → LA)."""
    token = str(raw or "").strip().upper()
    if token == "LAR":
        return "LA"
    return token


def load_packaged_regular_schedule(season: int) -> Tuple[List[ScheduledGame], Dict[str, Any]]:
    """Load the packaged real REG schedule artifact for ``season``.

    Returns ``(games, meta)``. Raises ``FileNotFoundError`` / ``ValueError``
    when the artifact is missing or malformed — callers should not silently
    invent a demo slate.
    """
    path = _PACKAGED_SCHEDULE_FILES.get(int(season))
    if path is None or not path.is_file():
        raise FileNotFoundError(
            f"No packaged regular-season schedule for season={season} "
            f"(expected under {_PACKAGE_DATA_DIR})"
        )
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("games") or []
    games: List[ScheduledGame] = []
    for r in rows:
        home = normalize_team_abbr(r["home_team"])
        away = normalize_team_abbr(r["away_team"])
        week = int(r["week"])
        gid = str(r.get("game_id") or f"{season}-W{week:02d}-{away}@{home}")
        games.append(
            ScheduledGame(
                season=int(r.get("season") or season),
                week=week,
                game_id=gid,
                home_team=home,
                away_team=away,
            )
        )
    if not games:
        raise ValueError(f"Packaged schedule empty: {path}")
    meta = {
        "schedule_source": str(payload.get("source") or SCHEDULE_SOURCE_PACKAGED),
        "schedule_as_of": str(payload.get("as_of") or ""),
        "schedule_game_count": len(games),
        "schedule_path": str(path.name),
        "bye_teams_by_week": payload.get("bye_teams_by_week") or {},
    }
    return games, meta


def load_packaged_efficiency_backbone(
    season: int,
) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Any]]:
    """Load packaged efficiency-backbone strength payloads for ``season``.

    Preferred cold-start artifact (Sprint 2). Each team row already carries
    O/D indices mapped through ``efficiency_backbone.package_to_strength_indices``
    plus pace / ST / variance metadata.
    """
    from src.services.nfl_season_engine.efficiency_backbone import (
        EFFICIENCY_BACKBONE_VERSION,
        packages_from_team_rows,
        strength_payload_from_package,
    )

    path = _PACKAGED_EFFICIENCY_BACKBONE_FILES.get(int(season))
    if path is None or not path.is_file():
        raise FileNotFoundError(
            f"No packaged efficiency backbone for season={season} "
            f"(expected under {_PACKAGE_DATA_DIR})"
        )
    payload = json.loads(path.read_text(encoding="utf-8"))
    teams_raw = payload.get("teams") or {}
    # Prefer precomputed strength fields when present; else rebuild packages.
    out: Dict[str, Dict[str, Any]] = {}
    if teams_raw and all(
        isinstance(v, Mapping) and "offense_index" in v for v in teams_raw.values()
    ):
        for raw_team, row in teams_raw.items():
            team = normalize_team_abbr(str(raw_team))
            if team not in NFL_TEAMS or not isinstance(row, Mapping):
                continue
            out[team] = {
                "offense_index": float(row["offense_index"]),
                "defense_index": float(row["defense_index"]),
                "pace_factor": float(row.get("pace_factor", 1.0) or 1.0),
                "pass_rate_bias": float(row.get("pass_rate_bias", 0.0) or 0.0),
                "st_index": float(row.get("st_index", 1.0) or 1.0),
                "explosiveness": float(row.get("explosiveness", 0.0) or 0.0),
                "variance": float(row.get("variance", 1.0) or 1.0),
                "qb_premium": float(row.get("qb_premium", 0.0) or 0.0),
                "as_of": str(payload.get("as_of") or row.get("as_of") or ""),
                "version": str(
                    row.get("version")
                    or payload.get("version")
                    or EFFICIENCY_BACKBONE_VERSION
                ),
                "off_epa_per_play": float(row.get("off_epa_per_play", 0.0) or 0.0),
                "def_epa_allowed_per_play": float(
                    row.get("def_epa_allowed_per_play", 0.0) or 0.0
                ),
                "games_played": int(row.get("games_played") or row.get("n_weeks") or 0),
                "_season": float(payload.get("prior_season") or (int(season) - 1)),
                "source": STRENGTH_SOURCE_PACKAGED_EFFICIENCY,
            }
    else:
        rows = [{"team": t, **dict(r)} for t, r in teams_raw.items() if isinstance(r, Mapping)]
        packages = packages_from_team_rows(
            rows,
            as_of=str(payload.get("as_of") or ""),
            source=STRENGTH_SOURCE_PACKAGED_EFFICIENCY,
            prior_season=int(payload.get("prior_season") or (int(season) - 1)),
        )
        for team, pkg in packages.items():
            if team not in NFL_TEAMS:
                continue
            out[team] = strength_payload_from_package(
                pkg, source=STRENGTH_SOURCE_PACKAGED_EFFICIENCY
            )
            out[team]["_season"] = float(
                payload.get("prior_season") or (int(season) - 1)
            )

    missing = [t for t in NFL_TEAMS if t not in out]
    if missing:
        raise ValueError(
            f"Packaged efficiency backbone incomplete for season={season}; missing {missing}"
        )
    meta = {
        "strength_source": STRENGTH_SOURCE_PACKAGED_EFFICIENCY,
        "strength_as_of": str(payload.get("as_of") or ""),
        "prior_season": int(payload.get("prior_season") or (int(season) - 1)),
        "strength_path": str(path.name),
        "strength_method": str(
            payload.get("method") or "efficiency_backbone_v1_packaged"
        ),
        "backbone_version": str(payload.get("version") or EFFICIENCY_BACKBONE_VERSION),
        "team_count": len(out),
    }
    return out, meta


def load_packaged_epa_priors(season: int) -> Tuple[Dict[str, Dict[str, float]], Dict[str, Any]]:
    """Load packaged strength indices for ``season`` (offline / cold-start).

    Prefers the Sprint 2 efficiency-backbone artifact; falls back to legacy
    EPA-prior JSON. Units always match live Edge Board / ``simulate_nfl_game``.
    """
    try:
        return load_packaged_efficiency_backbone(season)
    except (FileNotFoundError, ValueError, OSError, json.JSONDecodeError):
        pass

    path = _PACKAGED_EPA_PRIOR_FILES.get(int(season))
    if path is None or not path.is_file():
        raise FileNotFoundError(
            f"No packaged EPA priors / efficiency backbone for season={season} "
            f"(expected under {_PACKAGE_DATA_DIR})"
        )
    payload = json.loads(path.read_text(encoding="utf-8"))
    teams_raw = payload.get("teams") or {}
    out: Dict[str, Dict[str, float]] = {}
    for raw_team, row in teams_raw.items():
        team = normalize_team_abbr(str(raw_team))
        if team not in NFL_TEAMS or not isinstance(row, Mapping):
            continue
        try:
            offense_index = float(row["offense_index"])
            defense_index = float(row["defense_index"])
        except (KeyError, TypeError, ValueError):
            continue
        out[team] = {
            "offense_index": offense_index,
            "defense_index": defense_index,
            "pace_factor": float(row.get("pace_factor", 1.0) or 1.0),
            "pass_rate_bias": float(row.get("pass_rate_bias", 0.0) or 0.0),
            "st_index": float(row.get("st_index", 1.0) or 1.0),
            "explosiveness": float(row.get("explosiveness", 0.0) or 0.0),
            "variance": float(row.get("variance", 1.0) or 1.0),
            "qb_premium": float(row.get("qb_premium", 0.0) or 0.0),
            "off_epa_per_play": float(row.get("off_epa_per_play", 0.0) or 0.0),
            "def_epa_allowed_per_play": float(
                row.get("def_epa_allowed_per_play", 0.0) or 0.0
            ),
            "_season": float(payload.get("prior_season") or (int(season) - 1)),
        }
    missing = [t for t in NFL_TEAMS if t not in out]
    if missing:
        raise ValueError(
            f"Packaged EPA priors incomplete for season={season}; missing {missing}"
        )
    meta = {
        "strength_source": str(payload.get("source") or STRENGTH_SOURCE_PACKAGED_EPA),
        "strength_as_of": str(payload.get("as_of") or ""),
        "prior_season": int(payload.get("prior_season") or (int(season) - 1)),
        "strength_path": str(path.name),
        "strength_method": str(payload.get("method") or ""),
        "team_count": len(out),
    }
    return out, meta


def load_packaged_depth_chart(season: int) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Load packaged nflverse skill-depth snapshot for ``season``.

    Returns ``(rows, meta)`` where each row has team/position/depth_order/
    player_name (+ optional player_id). Raises when the artifact is missing
    or empty — callers fall through to demo depth.
    """
    path = _PACKAGED_DEPTH_FILES.get(int(season))
    if path is None or not path.is_file():
        raise FileNotFoundError(
            f"No packaged depth chart for season={season} "
            f"(expected under {_PACKAGE_DATA_DIR})"
        )
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows_raw = payload.get("rows") or []
    rows: List[Dict[str, Any]] = []
    for r in rows_raw:
        team = normalize_team_abbr(str(r.get("team") or ""))
        pos = str(r.get("position") or "").strip().upper()
        try:
            depth = int(r.get("depth_order") or 0)
        except (TypeError, ValueError):
            continue
        name = str(r.get("player_name") or "").strip()
        if team not in NFL_TEAMS or pos not in _SKILL_POSITIONS or depth < 1 or not name:
            continue
        if depth > 3:
            continue
        rows.append(
            {
                "team": team,
                "position": pos,
                "depth_order": depth,
                "player_name": name,
                "player_id": str(r.get("player_id") or ""),
                "role_confidence": float(r.get("role_confidence") or (0.85 if depth == 1 else 0.6)),
            }
        )
    if not rows:
        raise ValueError(f"Packaged depth chart empty: {path}")
    meta = {
        "roster_source": str(payload.get("source") or ROSTER_SOURCE_PACKAGED),
        "roster_as_of": str(payload.get("as_of") or payload.get("as_of_timestamp") or ""),
        "depth_path": str(path.name),
        "depth_row_count": len(rows),
        "depth_upstream": str(payload.get("upstream") or "nflverse"),
        "depth_week": int(payload.get("week") or 1),
    }
    return rows, meta


def _role_from_depth_row(
    *,
    team: str,
    pos: str,
    depth: int,
    name: str,
    source: str,
    role_confidence: Optional[float] = None,
    baseline_eff: Optional[Mapping[str, Dict[str, float]]] = None,
) -> Tuple[PlayerRole, bool]:
    """Build a PlayerRole from a depth-chart identity + share priors."""
    conf = (
        float(role_confidence)
        if role_confidence is not None
        else (0.7 if depth == 1 else 0.5)
    )
    role = PlayerRole(
        player_key=f"{team}-{pos}{depth}-{name}".replace(" ", ""),
        player_name=name,
        team=team,
        position=pos,
        depth_order=depth,
        snap_share=(
            {1: 0.9, 2: 0.45, 3: 0.2}.get(depth, 0.1)
            if pos == "QB"
            else {1: 0.65, 2: 0.38, 3: 0.18}.get(depth, 0.1)
        ),
        target_share=(
            {1: 0.22, 2: 0.14, 3: 0.08}.get(depth, 0.05)
            if pos in ("WR", "TE")
            else ({1: 0.10, 2: 0.05}.get(depth, 0.03) if pos == "RB" else 0.0)
        ),
        rush_share=(
            {1: 0.52, 2: 0.26, 3: 0.12}.get(depth, 0.05)
            if pos == "RB"
            else ({1: 0.07}.get(depth, 0.02) if pos == "QB" else 0.0)
        ),
        route_share={1: 0.85, 2: 0.65, 3: 0.4}.get(depth, 0.2) if pos in ("WR", "TE") else 0.2,
        red_zone_share=(
            {1: 0.22, 2: 0.12, 3: 0.07}.get(depth, 0.04)
            if pos in ("WR", "TE", "RB")
            else 0.05
        ),
        role_confidence=conf,
        source=source,
    )
    hit = False
    key = f"{team}|{pos}|{name}".upper()
    overrides = (baseline_eff or {}).get(key)
    if overrides:
        hit = True
        role = apply_efficiency_priors(role, overrides=overrides, source_suffix="baseline_efficiency")
    else:
        role = apply_efficiency_priors(role, source_suffix="league_efficiency_v1")
    return role, hit


def _rosters_from_depth_rows(
    depth_rows: Sequence[Mapping[str, Any]],
    *,
    source: str,
    baseline_eff: Optional[Mapping[str, Dict[str, float]]] = None,
) -> Tuple[Dict[str, List[PlayerRole]], int, Dict[str, Any]]:
    """Map depth rows → per-team skill roles + coverage stats."""
    rosters: Dict[str, List[PlayerRole]] = {t: [] for t in NFL_TEAMS}
    baseline_hits = 0
    seen: set[Tuple[str, str, int]] = set()
    for r in depth_rows:
        team = normalize_team_abbr(str(r.get("team") or getattr(r, "team", "") or ""))
        if team not in rosters:
            continue
        pos = str(r.get("position") or getattr(r, "position", "") or "").strip().upper()
        try:
            depth = int(r.get("depth_order") or getattr(r, "depth_order", 1) or 1)
        except (TypeError, ValueError):
            continue
        if pos not in _SKILL_POSITIONS or depth < 1 or depth > 3:
            continue
        key = (team, pos, depth)
        if key in seen:
            continue
        seen.add(key)
        name = str(
            r.get("player_name") or getattr(r, "player_name", None) or f"{team} {pos}{depth}"
        ).strip()
        conf_raw = r.get("role_confidence")
        if conf_raw is None:
            conf_raw = getattr(r, "role_confidence", None)
        role, hit = _role_from_depth_row(
            team=team,
            pos=pos,
            depth=depth,
            name=name,
            source=source,
            role_confidence=float(conf_raw) if conf_raw is not None else None,
            baseline_eff=baseline_eff,
        )
        if hit:
            baseline_hits += 1
        rosters[team].append(role)

    named_skill_teams = 0
    teams_with_qb1_rb1_wr1_te1 = 0
    for team in NFL_TEAMS:
        roles = rosters[team]
        if not roles:
            continue
        generic_prefix = f"{team} "
        if any(not role.player_name.startswith(generic_prefix) for role in roles):
            named_skill_teams += 1
        starters = {
            (role.position, role.depth_order)
            for role in roles
            if role.depth_order == 1 and role.position in _SKILL_POSITIONS
        }
        if all((p, 1) in starters for p in _SKILL_POSITIONS):
            teams_with_qb1_rb1_wr1_te1 += 1

    coverage = {
        "depth_team_count": sum(1 for t in NFL_TEAMS if rosters[t]),
        "depth_named_skill_teams": named_skill_teams,
        "depth_full_skill_starter_teams": teams_with_qb1_rb1_wr1_te1,
        "depth_player_rows": sum(len(rosters[t]) for t in NFL_TEAMS),
    }
    return rosters, baseline_hits, coverage


def depth_coverage_from_rosters(rosters: Mapping[str, Sequence[PlayerRole]]) -> Dict[str, Any]:
    """Compute depth coverage counters for status / notes."""
    named_skill_teams = 0
    teams_with_qb1_rb1_wr1_te1 = 0
    team_count = 0
    player_rows = 0
    for team in NFL_TEAMS:
        roles = list(rosters.get(team) or [])
        if not roles:
            continue
        team_count += 1
        player_rows += len(roles)
        generic_prefix = f"{team} "
        if any(not role.player_name.startswith(generic_prefix) for role in roles):
            named_skill_teams += 1
        starters = {
            (role.position, role.depth_order)
            for role in roles
            if role.depth_order == 1 and role.position in _SKILL_POSITIONS
        }
        if all((p, 1) in starters for p in _SKILL_POSITIONS):
            teams_with_qb1_rb1_wr1_te1 += 1
    return {
        "depth_team_count": team_count,
        "depth_named_skill_teams": named_skill_teams,
        "depth_full_skill_starter_teams": teams_with_qb1_rb1_wr1_te1,
        "depth_player_rows": player_rows,
    }


def universe_schedule_meta(universe: EngineUniverse) -> Dict[str, Any]:
    """Extract mode / schedule_source / depth coverage from universe notes."""
    notes = universe.notes or {}
    source = str(notes.get("schedule_source") or "")
    mode = str(notes.get("mode") or ("demo" if source == SCHEDULE_SOURCE_DEMO else "real"))
    roster_source = str(notes.get("roster_source") or "")
    roster_as_of = str(notes.get("roster_as_of") or "")
    coverage = {
        "depth_team_count": notes.get("depth_team_count"),
        "depth_named_skill_teams": notes.get("depth_named_skill_teams"),
        "depth_full_skill_starter_teams": notes.get("depth_full_skill_starter_teams"),
        "depth_player_rows": notes.get("depth_player_rows"),
    }
    # Prefer notes; else derive from live roster book.
    if coverage["depth_team_count"] in (None, ""):
        coverage = depth_coverage_from_rosters(universe.rosters or {})
    return {
        "mode": mode,
        "schedule_source": source or (
            SCHEDULE_SOURCE_DEMO if mode == "demo" else SCHEDULE_SOURCE_PACKAGED
        ),
        "schedule_game_count": len(universe.schedule),
        "schedule_as_of": notes.get("schedule_as_of") or "",
        "roster_source": roster_source,
        "roster_as_of": roster_as_of,
        # Aliases requested by ops/status consumers.
        "depth_source": roster_source,
        "depth_as_of": roster_as_of,
        "depth_team_count": int(coverage.get("depth_team_count") or 0),
        "depth_named_skill_teams": int(coverage.get("depth_named_skill_teams") or 0),
        "depth_full_skill_starter_teams": int(
            coverage.get("depth_full_skill_starter_teams") or 0
        ),
        "depth_player_rows": int(coverage.get("depth_player_rows") or 0),
        "schedule_note": notes.get("schedule") or "",
        "roster_note": notes.get("rosters") or "",
        "strength_source": str(notes.get("strength_source") or ""),
        "strength_as_of": str(notes.get("strength_as_of") or ""),
        "strength_note": notes.get("strengths") or "",
    }

# Approximate 2025/26 style skill cores for demo / offline runs.
# Shares are absolute fractions of team volume (residual "other" absorbs rest).
_DEMO_SKILL: Dict[str, List[Dict[str, Any]]] = {
    "KC": [
        {"name": "P.Mahomes", "pos": "QB", "depth": 1, "snap": 0.98, "rush": 0.07, "tgt": 0.0, "ypa": 7.35, "int_rate": ELITE_INT_RATE},
        {"name": "I.Pacheco", "pos": "RB", "depth": 1, "snap": 0.58, "rush": 0.52, "tgt": 0.09, "ypc": 4.25},
        {"name": "R.Rice", "pos": "WR", "depth": 1, "snap": 0.82, "rush": 0.0, "tgt": 0.22, "ypr": 11.6},
        {"name": "X.Worthy", "pos": "WR", "depth": 2, "snap": 0.70, "rush": 0.02, "tgt": 0.14, "ypr": 13.2},
        {"name": "J.Watson", "pos": "WR", "depth": 3, "snap": 0.48, "rush": 0.0, "tgt": 0.08, "ypr": 12.5},
        {"name": "T.Kelce", "pos": "TE", "depth": 1, "snap": 0.72, "rush": 0.0, "tgt": 0.16, "ypr": 10.9},
        {"name": "N.Gray", "pos": "TE", "depth": 2, "snap": 0.38, "rush": 0.0, "tgt": 0.06, "ypr": 9.8},
    ],
    "BUF": [
        {"name": "J.Allen", "pos": "QB", "depth": 1, "snap": 0.98, "rush": 0.16, "tgt": 0.0, "ypa": 7.25, "int_rate": ELITE_INT_RATE, "ypc": 5.4},
        {"name": "J.Cook", "pos": "RB", "depth": 1, "snap": 0.60, "rush": 0.52, "tgt": 0.10, "ypc": 4.55},
        {"name": "T.Johnson", "pos": "RB", "depth": 2, "snap": 0.28, "rush": 0.22, "tgt": 0.04, "ypc": 4.10},
        {"name": "K.Shakir", "pos": "WR", "depth": 1, "snap": 0.80, "rush": 0.0, "tgt": 0.19, "ypr": 11.0},
        {"name": "K.Coleman", "pos": "WR", "depth": 2, "snap": 0.65, "rush": 0.0, "tgt": 0.13, "ypr": 12.0},
        {"name": "K.Palmer", "pos": "WR", "depth": 3, "snap": 0.45, "rush": 0.0, "tgt": 0.08, "ypr": 11.5},
        {"name": "D.Kincaid", "pos": "TE", "depth": 1, "snap": 0.68, "rush": 0.0, "tgt": 0.14, "ypr": 10.5},
    ],
    "PHI": [
        {"name": "J.Hurts", "pos": "QB", "depth": 1, "snap": 0.97, "rush": 0.18, "tgt": 0.0, "ypa": 7.05, "ypc": 5.2, "int_rate": 0.016},
        {"name": "S.Barkley", "pos": "RB", "depth": 1, "snap": 0.70, "rush": 0.58, "tgt": 0.10, "ypc": 4.65},
        {"name": "W.Shipley", "pos": "RB", "depth": 2, "snap": 0.22, "rush": 0.16, "tgt": 0.03, "ypc": 4.05},
        {"name": "A.Brown", "pos": "WR", "depth": 1, "snap": 0.88, "rush": 0.0, "tgt": 0.24, "ypr": 12.8},
        {"name": "D.Smith", "pos": "WR", "depth": 2, "snap": 0.80, "rush": 0.0, "tgt": 0.18, "ypr": 12.2},
        {"name": "J.Dotson", "pos": "WR", "depth": 3, "snap": 0.48, "rush": 0.0, "tgt": 0.08, "ypr": 11.2},
        {"name": "D.Goedert", "pos": "TE", "depth": 1, "snap": 0.70, "rush": 0.0, "tgt": 0.12, "ypr": 10.8},
    ],
    "SF": [
        {"name": "B.Purdy", "pos": "QB", "depth": 1, "snap": 0.96, "rush": 0.05, "tgt": 0.0, "ypa": 7.45, "int_rate": 0.016},
        {"name": "C.McCaffrey", "pos": "RB", "depth": 1, "snap": 0.72, "rush": 0.50, "tgt": 0.16, "ypc": 4.45},
        {"name": "J.Mason", "pos": "RB", "depth": 2, "snap": 0.30, "rush": 0.22, "tgt": 0.04, "ypc": 4.20},
        {"name": "D.Samuel", "pos": "WR", "depth": 1, "snap": 0.78, "rush": 0.04, "tgt": 0.18, "ypr": 11.8},
        {"name": "B.Aiyuk", "pos": "WR", "depth": 2, "snap": 0.80, "rush": 0.0, "tgt": 0.17, "ypr": 13.0},
        {"name": "R.Pearsall", "pos": "WR", "depth": 3, "snap": 0.50, "rush": 0.0, "tgt": 0.09, "ypr": 11.5},
        {"name": "G.Kittle", "pos": "TE", "depth": 1, "snap": 0.80, "rush": 0.0, "tgt": 0.14, "ypr": 12.4},
    ],
    "DET": [
        {"name": "J.Goff", "pos": "QB", "depth": 1, "snap": 0.98, "rush": 0.02, "tgt": 0.0, "ypa": 7.40, "int_rate": 0.016},
        {"name": "J.Gibbs", "pos": "RB", "depth": 1, "snap": 0.58, "rush": 0.45, "tgt": 0.12, "ypc": 4.85},
        {"name": "D.Montgomery", "pos": "RB", "depth": 2, "snap": 0.38, "rush": 0.32, "tgt": 0.05, "ypc": 4.15},
        {"name": "A.St. Brown", "pos": "WR", "depth": 1, "snap": 0.88, "rush": 0.0, "tgt": 0.24, "ypr": 11.3},
        {"name": "J.Williams", "pos": "WR", "depth": 2, "snap": 0.75, "rush": 0.0, "tgt": 0.15, "ypr": 12.8},
        {"name": "K.Raymond", "pos": "WR", "depth": 3, "snap": 0.48, "rush": 0.0, "tgt": 0.08, "ypr": 10.8},
        {"name": "S.LaPorta", "pos": "TE", "depth": 1, "snap": 0.78, "rush": 0.0, "tgt": 0.14, "ypr": 11.0},
        {"name": "B.Wright", "pos": "TE", "depth": 2, "snap": 0.35, "rush": 0.0, "tgt": 0.05, "ypr": 9.5},
    ],
}

# Demo EPA-style talent bumps (offense / defense index deltas vs 1.0).
# Spread sized so projected win means ~5–12 (recent NFL projection band),
# with contenders clearly above replacement — not hash noise.
_DEMO_STRENGTH_BUMPS: Dict[str, Dict[str, float]] = {
    "KC": {"off": 0.15, "def": 0.10, "pace": 0.00, "pass": 0.02},
    "BUF": {"off": 0.14, "def": 0.09, "pace": 0.02, "pass": -0.01},
    "PHI": {"off": 0.13, "def": 0.09, "pace": 0.01, "pass": -0.02},
    "SF": {"off": 0.11, "def": 0.12, "pace": -0.01, "pass": 0.00},
    "DET": {"off": 0.13, "def": 0.07, "pace": 0.02, "pass": 0.01},
    "BAL": {"off": 0.12, "def": 0.10, "pace": 0.01, "pass": -0.03},
    "CIN": {"off": 0.10, "def": 0.03, "pace": 0.01, "pass": 0.02},
    "MIA": {"off": 0.06, "def": 0.01, "pace": 0.03, "pass": 0.03},
    "DAL": {"off": 0.05, "def": 0.05, "pace": 0.00, "pass": 0.01},
    "GB": {"off": 0.07, "def": 0.04, "pace": 0.00, "pass": 0.00},
    "HOU": {"off": 0.06, "def": 0.08, "pace": -0.01, "pass": 0.00},
    "LAC": {"off": 0.08, "def": 0.05, "pace": 0.00, "pass": 0.01},
    "MIN": {"off": 0.05, "def": 0.03, "pace": 0.01, "pass": 0.02},
    "SEA": {"off": 0.03, "def": 0.03, "pace": 0.01, "pass": 0.01},
    "TB": {"off": 0.04, "def": 0.02, "pace": 0.00, "pass": 0.02},
    "ATL": {"off": 0.02, "def": 0.00, "pace": 0.01, "pass": 0.00},
    "LA": {"off": 0.03, "def": 0.05, "pace": -0.01, "pass": 0.01},
    "PIT": {"off": 0.00, "def": 0.08, "pace": -0.02, "pass": -0.02},
    "DEN": {"off": 0.01, "def": 0.06, "pace": -0.01, "pass": 0.00},
    "NYJ": {"off": -0.04, "def": 0.06, "pace": -0.02, "pass": -0.01},
    "CLE": {"off": -0.05, "def": 0.04, "pace": -0.02, "pass": -0.02},
    "CHI": {"off": -0.02, "def": -0.01, "pace": 0.00, "pass": 0.00},
    "IND": {"off": -0.04, "def": -0.03, "pace": 0.00, "pass": 0.00},
    "JAX": {"off": -0.05, "def": -0.04, "pace": 0.01, "pass": 0.01},
    "LV": {"off": -0.06, "def": -0.04, "pace": 0.00, "pass": 0.00},
    "NO": {"off": -0.07, "def": -0.01, "pace": -0.01, "pass": 0.00},
    "NYG": {"off": -0.08, "def": -0.05, "pace": 0.00, "pass": 0.00},
    "TEN": {"off": -0.09, "def": -0.05, "pace": -0.01, "pass": -0.01},
    "CAR": {"off": -0.11, "def": -0.07, "pace": 0.00, "pass": 0.00},
    "NE": {"off": -0.09, "def": -0.03, "pace": -0.01, "pass": -0.01},
    "WAS": {"off": 0.02, "def": -0.02, "pace": 0.01, "pass": 0.01},
    "ARI": {"off": -0.01, "def": -0.04, "pace": 0.01, "pass": 0.01},
}


def _generic_skill(team: str) -> List[Dict[str, Any]]:
    return [
        {"name": f"{team} QB1", "pos": "QB", "depth": 1, "snap": 0.97, "rush": 0.06, "tgt": 0.0},
        {"name": f"{team} RB1", "pos": "RB", "depth": 1, "snap": 0.58, "rush": 0.52, "tgt": 0.09},
        {"name": f"{team} RB2", "pos": "RB", "depth": 2, "snap": 0.28, "rush": 0.24, "tgt": 0.05},
        {"name": f"{team} WR1", "pos": "WR", "depth": 1, "snap": 0.85, "rush": 0.0, "tgt": 0.22},
        {"name": f"{team} WR2", "pos": "WR", "depth": 2, "snap": 0.72, "rush": 0.0, "tgt": 0.15},
        {"name": f"{team} WR3", "pos": "WR", "depth": 3, "snap": 0.50, "rush": 0.0, "tgt": 0.09},
        {"name": f"{team} TE1", "pos": "TE", "depth": 1, "snap": 0.68, "rush": 0.0, "tgt": 0.12},
    ]


def _role_from_demo(team: str, row: Mapping[str, Any]) -> PlayerRole:
    pos = str(row["pos"])
    depth = int(row.get("depth", 1))
    key = f"{team}-{pos}{depth}-{row['name']}".replace(" ", "")
    overrides = {
        k: float(row[k])
        for k in ("ypa", "ypc", "ypr", "catch_rate", "pass_td_rate", "rush_td_rate", "rec_td_rate", "int_rate")
        if k in row and row[k] is not None
    }
    role = PlayerRole(
        player_key=key,
        player_name=str(row["name"]),
        team=team,
        position=pos,
        depth_order=depth,
        snap_share=float(row.get("snap", 0.5)),
        target_share=float(row.get("tgt", 0.0)),
        rush_share=float(row.get("rush", 0.0)),
        route_share=float(row.get("tgt", 0.0)) * 1.15 if pos in ("WR", "TE", "RB") else 0.0,
        red_zone_share=float(row.get("tgt", row.get("rush", 0.1))) * 0.9,
        role_confidence=0.75 if depth == 1 else 0.55,
        source="demo_depth_chart",
    )
    return apply_efficiency_priors(role, overrides=overrides or None, source_suffix="league_efficiency_v1")


def _round_robin_schedule(season: int, teams: Sequence[str]) -> List[ScheduledGame]:
    """Build a 272-game (17×32/2) schedule via mirrored round-robin.

    PLACEHOLDER structure for offline demos. Prefer ``nfl_dp_schedules``
    when a DB session is available.
    """
    clubs = list(teams)
    if len(clubs) != 32:
        raise ValueError(f"Expected 32 teams, got {len(clubs)}")
    fixed = clubs[0]
    rotating = clubs[1:]
    games: List[ScheduledGame] = []
    gid = 0
    for week in range(1, 18):
        circle = [fixed] + rotating
        for i in range(16):
            home = circle[i]
            away = circle[-(i + 1)]
            if home == away:
                continue
            if week % 2 == 0:
                home, away = away, home
            gid += 1
            games.append(
                ScheduledGame(
                    season=season,
                    week=week,
                    game_id=f"{season}-W{week:02d}-{away}@{home}-{gid}",
                    home_team=home,
                    away_team=away,
                )
            )
        rotating = rotating[1:] + rotating[:1]
    if len(games) > 272:
        games = games[:272]
    while len(games) < 272:
        a, b = clubs[len(games) % 32], clubs[(len(games) + 7) % 32]
        if a == b:
            b = clubs[(len(games) + 3) % 32]
        games.append(
            ScheduledGame(
                season=season,
                week=17,
                game_id=f"{season}-pad-{len(games)}",
                home_team=a,
                away_team=b,
            )
        )
    return games


def build_demo_universe(season: int = 2026) -> EngineUniverse:
    """Self-contained universe for offline tests and sample projections."""
    strength_inputs: Dict[str, Dict[str, float | str]] = {}
    for t in NFL_TEAMS:
        bump = _DEMO_STRENGTH_BUMPS.get(t, {"off": 0.0, "def": 0.0, "pace": 0.0, "pass": 0.0})
        # Tiny deterministic jitter so non-bumped teams are not identical.
        jitter = ((hash(t) % 7) - 3) * 0.008
        strength_inputs[t] = {
            "offense_index": 1.0 + float(bump.get("off", 0.0)) + jitter,
            "defense_index": 1.0 + float(bump.get("def", 0.0)) - 0.5 * jitter,
            "pace_factor": 1.0 + float(bump.get("pace", 0.0)),
            "pass_rate_bias": float(bump.get("pass", 0.0)),
            "source": STRENGTH_SOURCE_DEMO,
        }

    rosters: Dict[str, List[PlayerRole]] = {}
    for team in NFL_TEAMS:
        rows = _DEMO_SKILL.get(team) or _generic_skill(team)
        rosters[team] = [_role_from_demo(team, r) for r in rows]

    schedule = _round_robin_schedule(season, NFL_TEAMS)
    rosters = annotate_roster_book(rosters)
    rosters, depth_structures = apply_depth_chart_roster_book(rosters)
    committee_teams = sorted(
        t for t, s in depth_structures.items() if s.rb_structure == "committee"
    )
    murky_wr_teams = sorted(
        t for t, s in depth_structures.items() if s.wr_hierarchy == "murky"
    )
    coverage = depth_coverage_from_rosters(rosters)
    notes = {
        "mode": "demo",
        "schedule_source": SCHEDULE_SOURCE_DEMO,
        "schedule_as_of": "",
        "roster_source": ROSTER_SOURCE_DEMO,
        "roster_as_of": "2025_offseason_approx",
        "depth_source": ROSTER_SOURCE_DEMO,
        "depth_as_of": "2025_offseason_approx",
        "schedule": (
            "PLACEHOLDER round-robin (272 games, no byes). Explicit demo=true only; "
            "default prefers real 2026 schedule."
        ),
        "strengths": "Calibrated demo EPA-style priors with contender-tier bumps (KC/BUF/PHI/SF/DET/BAL...).",
        "rosters": (
            "Mixed: named demo skill cores for 5 teams; generic depth for others. "
            "Absolute usage shares + usage_role taxonomy (QB1/RB1/WR1…) + depth-chart structure."
        ),
        "depth_chart": (
            f"committee_rb={','.join(committee_teams) or 'none'}; "
            f"murky_wr={','.join(murky_wr_teams) or 'none'}"
        ),
        "calibration": CALIBRATION_TAG,
        **coverage,
        **{f"cal_{k}": v for k, v in calibration_notes().items()},
    }
    return EngineUniverse(
        season=season,
        schedule=schedule,
        strengths=initialize_strengths(strength_inputs),
        rosters=rosters,
        notes=notes,
    )


def _load_baseline_efficiency_map(
    session: Any,
    *,
    season: int,
    as_of_week: int,
) -> Dict[str, Dict[str, float]]:
    """Best-effort map of player_name|team|pos → efficiency overrides from baselines.

    Returns empty dict when the table is missing or empty — callers fall back
    to league priors (documented, not invented player grades).
    """
    from sqlalchemy import text

    try:
        rows = session.execute(
            text(
                """
                SELECT DISTINCT ON (team, player_name, position)
                  team, player_name, position,
                  attempts_mean, pass_yards_mean, rush_yards_mean,
                  carries_mean, targets_mean, receptions_mean,
                  receiving_yards_mean, pass_tds_mean, rush_tds_mean,
                  rec_tds_mean, interceptions_mean
                FROM nfl_player_projection_baselines
                WHERE season = :season
                  AND week <= :week
                ORDER BY team, player_name, position, week DESC
                """
            ),
            {"season": int(season), "week": int(as_of_week)},
        ).fetchall()
    except Exception:
        # Column names vary across migrations — try a narrower select.
        try:
            rows = session.execute(
                text(
                    """
                    SELECT DISTINCT ON (team, player_name, position)
                      team, player_name, position,
                      pass_yards_mean, rush_yards_mean,
                      receptions_mean, receiving_yards_mean
                    FROM nfl_player_projection_baselines
                    WHERE season = :season
                      AND week <= :week
                    ORDER BY team, player_name, position, week DESC
                    """
                ),
                {"season": int(season), "week": int(as_of_week)},
            ).fetchall()
        except Exception:
            return {}

    out: Dict[str, Dict[str, float]] = {}
    for r in rows or []:
        team = str(r.team)
        if team == "LAR":
            team = "LA"
        pos = str(getattr(r, "position", "") or "")
        name = str(r.player_name or "")
        key = f"{team}|{pos}|{name}".upper()
        payload = {c: getattr(r, c, None) for c in r._mapping.keys()}  # type: ignore[attr-defined]
        out[key] = efficiency_from_baseline_row(payload, pos)
    return out


def load_universe_from_db(
    session: Any,
    *,
    season: int,
    as_of_week: int = 1,
) -> EngineUniverse:
    """Load schedule + EPA strength priors + best-effort depth roles from DB.

    Falls back to demo roles/strengths for any team missing data so the
    engine remains runnable. Does not modify Edge Board tables.
    """
    from sqlalchemy import text

    from src.tasks import _load_team_strength_priors

    schedule_rows = session.execute(
        text(
            """
            SELECT season, week, home_team, away_team, game_id
            FROM nfl_dp_schedules
            WHERE season = :season
              AND week BETWEEN 1 AND 18
            ORDER BY week, home_team, away_team
            """
        ),
        {"season": int(season)},
    ).fetchall()

    schedule: List[ScheduledGame] = []
    schedule_source = SCHEDULE_SOURCE_PACKAGED
    schedule_as_of = ""
    if schedule_rows:
        for r in schedule_rows:
            home = normalize_team_abbr(r.home_team)
            away = normalize_team_abbr(r.away_team)
            gid = str(getattr(r, "game_id", None) or f"{season}-W{int(r.week):02d}-{away}@{home}")
            schedule.append(
                ScheduledGame(
                    season=int(r.season),
                    week=int(r.week),
                    game_id=gid,
                    home_team=home,
                    away_team=away,
                )
            )
        schedule_source = SCHEDULE_SOURCE_DB
        schedule_note = f"REAL nfl_dp_schedules ({len(schedule)} games)"
    else:
        # Do NOT silently invent round-robin when DB schedule is empty.
        schedule, pkg_meta = load_packaged_regular_schedule(season)
        schedule_source = str(pkg_meta.get("schedule_source") or SCHEDULE_SOURCE_PACKAGED)
        schedule_as_of = str(pkg_meta.get("schedule_as_of") or "")
        schedule_note = (
            f"REAL packaged schedule ({len(schedule)} games); "
            "nfl_dp_schedules empty for season"
        )

    priors = _load_team_strength_priors(session, season_year=int(season), as_of_week=int(as_of_week))
    strength_inputs: Dict[str, Dict[str, float | str]] = {}
    epa_count = 0
    packaged_fill = 0
    packaged_priors: Dict[str, Dict[str, float]] = {}
    packaged_meta: Dict[str, Any] = {}
    # Always load packaged backbone for metadata fill (pace/ST) + missing teams.
    try:
        packaged_priors, packaged_meta = load_packaged_epa_priors(season)
    except (FileNotFoundError, ValueError, OSError, json.JSONDecodeError):
        packaged_priors, packaged_meta = {}, {}
    for team in NFL_TEAMS:
        prior = priors.get(team) or {}
        pkg = packaged_priors.get(team) or {}
        prior_source = str(prior.get("_source") or "")
        if prior and prior_source in (
            STRENGTH_SOURCE_PACKAGED_EPA,
            STRENGTH_SOURCE_PACKAGED_EFFICIENCY,
            "packaged_epa_prior",
            "packaged_efficiency_backbone",
        ):
            # DB helper already filled from packaged cold-start.
            packaged_fill += 1
            strength_inputs[team] = {
                "offense_index": float(prior.get("offense_index", 1.0)),
                "defense_index": float(prior.get("defense_index", 1.0)),
                "pace_factor": float(
                    prior.get("pace_factor", pkg.get("pace_factor", 1.0)) or 1.0
                ),
                "pass_rate_bias": float(
                    prior.get("pass_rate_bias", pkg.get("pass_rate_bias", 0.0)) or 0.0
                ),
                "st_index": float(prior.get("st_index", pkg.get("st_index", 1.0)) or 1.0),
                "explosiveness": float(
                    prior.get("explosiveness", pkg.get("explosiveness", 0.0)) or 0.0
                ),
                "variance": float(prior.get("variance", pkg.get("variance", 1.0)) or 1.0),
                "qb_premium": float(
                    prior.get("qb_premium", pkg.get("qb_premium", 0.0)) or 0.0
                ),
                "as_of": str(prior.get("as_of") or packaged_meta.get("strength_as_of") or ""),
                "version": str(
                    prior.get("version")
                    or packaged_meta.get("backbone_version")
                    or ""
                ),
                "source": prior_source or STRENGTH_SOURCE_PACKAGED_EFFICIENCY,
            }
        elif prior:
            epa_count += 1
            strength_inputs[team] = {
                "offense_index": float(prior.get("offense_index", 1.0)),
                "defense_index": float(prior.get("defense_index", 1.0)),
                "pace_factor": float(prior.get("pace_factor", pkg.get("pace_factor", 1.0)) or 1.0),
                "pass_rate_bias": float(
                    prior.get("pass_rate_bias", pkg.get("pass_rate_bias", 0.0)) or 0.0
                ),
                "st_index": float(prior.get("st_index", pkg.get("st_index", 1.0)) or 1.0),
                "explosiveness": float(
                    prior.get("explosiveness", pkg.get("explosiveness", 0.0)) or 0.0
                ),
                "variance": float(prior.get("variance", pkg.get("variance", 1.0)) or 1.0),
                "qb_premium": float(
                    prior.get("qb_premium", pkg.get("qb_premium", 0.0)) or 0.0
                ),
                "as_of": str(prior.get("as_of") or ""),
                "version": str(prior.get("version") or ""),
                "source": STRENGTH_SOURCE_EFFICIENCY
                if prior_source.startswith("efficiency")
                else STRENGTH_SOURCE_EPA_PRIOR,
            }
        elif team in packaged_priors:
            packaged_fill += 1
            strength_inputs[team] = {
                "offense_index": float(pkg.get("offense_index", 1.0)),
                "defense_index": float(pkg.get("defense_index", 1.0)),
                "pace_factor": float(pkg.get("pace_factor", 1.0)),
                "pass_rate_bias": float(pkg.get("pass_rate_bias", 0.0)),
                "st_index": float(pkg.get("st_index", 1.0) or 1.0),
                "explosiveness": float(pkg.get("explosiveness", 0.0) or 0.0),
                "variance": float(pkg.get("variance", 1.0) or 1.0),
                "qb_premium": float(pkg.get("qb_premium", 0.0) or 0.0),
                "as_of": str(pkg.get("as_of") or packaged_meta.get("strength_as_of") or ""),
                "version": str(
                    pkg.get("version") or packaged_meta.get("backbone_version") or ""
                ),
                "source": str(
                    pkg.get("source")
                    or packaged_meta.get("strength_source")
                    or STRENGTH_SOURCE_PACKAGED_EFFICIENCY
                ),
            }
        else:
            strength_inputs[team] = {
                "offense_index": 1.0,
                "defense_index": 1.0,
                "source": STRENGTH_SOURCE_PLACEHOLDER,
            }

    baseline_eff = _load_baseline_efficiency_map(session, season=season, as_of_week=as_of_week)

    weekly_rows = session.execute(
        text(
            """
            SELECT DISTINCT ON (team, position, depth_order)
              team, player_name, position, depth_order, role_confidence
            FROM nfl_dp_depth_chart_weekly
            WHERE season = :season
              AND week <= :week
              AND position IN ('QB', 'RB', 'WR', 'TE')
            ORDER BY team, position, depth_order, week DESC
            """
        ),
        {"season": int(season), "week": int(as_of_week)},
    ).fetchall()

    official_rows: List[Any] = []
    if not weekly_rows:
        try:
            official_rows = session.execute(
                text(
                    """
                    SELECT DISTINCT ON (team, position, depth_order)
                      team, player_name, position, depth_order
                    FROM (
                      SELECT
                        team,
                        player_name,
                        position,
                        depth_team AS depth_order,
                        week
                      FROM nfl_dp_official_depth_charts
                      WHERE season = :season
                        AND week <= :week
                        AND position IN ('QB', 'RB', 'WR', 'TE')
                        AND depth_team BETWEEN 1 AND 3
                    ) official
                    ORDER BY team, position, depth_order, week DESC
                    """
                ),
                {"season": int(season), "week": int(as_of_week)},
            ).fetchall()
        except Exception:
            official_rows = []

    rosters: Dict[str, List[PlayerRole]]
    roster_source = ROSTER_SOURCE_DEMO
    roster_as_of = f"season={season};as_of_week<={as_of_week}"
    coverage: Dict[str, Any] = {}
    baseline_hits = 0

    if weekly_rows:
        rosters, baseline_hits, coverage = _rosters_from_depth_rows(
            [dict(r._mapping) for r in weekly_rows],  # type: ignore[attr-defined]
            source="depth_chart_weekly",
            baseline_eff=baseline_eff,
        )
        roster_source = ROSTER_SOURCE_WEEKLY
        if baseline_hits:
            roster_note = (
                f"REAL depth chart identities; efficiency from baselines "
                f"({baseline_hits} hits) else league priors"
            )
        else:
            roster_note = (
                "REAL depth chart identities; PLACEHOLDER league efficiency priors "
                "(nfl_player_projection_baselines unavailable or empty for as_of_week)"
            )
    elif official_rows:
        rosters, baseline_hits, coverage = _rosters_from_depth_rows(
            [dict(r._mapping) for r in official_rows],  # type: ignore[attr-defined]
            source="official_depth_charts",
            baseline_eff=baseline_eff,
        )
        roster_source = ROSTER_SOURCE_OFFICIAL
        roster_as_of = f"season={season};official_as_of_week<={as_of_week}"
        roster_note = (
            "REAL nflverse official depth identities "
            "(weekly inferred table empty; bridged from nfl_dp_official_depth_charts)"
        )
    else:
        try:
            packaged_rows, pkg_depth_meta = load_packaged_depth_chart(season)
            rosters, baseline_hits, coverage = _rosters_from_depth_rows(
                packaged_rows,
                source=ROSTER_SOURCE_PACKAGED,
                baseline_eff=baseline_eff,
            )
            roster_source = str(pkg_depth_meta.get("roster_source") or ROSTER_SOURCE_PACKAGED)
            roster_as_of = str(pkg_depth_meta.get("roster_as_of") or "")
            roster_note = (
                "REAL packaged nflverse depth snapshot "
                "(DB weekly + official empty for season)"
            )
        except (FileNotFoundError, ValueError, OSError, json.JSONDecodeError):
            rosters = {}
            for team in NFL_TEAMS:
                rows = _DEMO_SKILL.get(team) or _generic_skill(team)
                rosters[team] = [_role_from_demo(team, r) for r in rows]
            roster_source = ROSTER_SOURCE_DEMO
            roster_as_of = "2025_offseason_approx"
            roster_note = "PLACEHOLDER demo rosters (all real depth sources empty)"
            coverage = depth_coverage_from_rosters(rosters)

    for team in NFL_TEAMS:
        if not rosters.get(team):
            rosters[team] = [_role_from_demo(team, r) for r in _generic_skill(team)]

    rosters = annotate_roster_book(rosters)
    rosters, _depth_structures = apply_depth_chart_roster_book(rosters)
    if not coverage:
        coverage = depth_coverage_from_rosters(rosters)
    if epa_count and packaged_fill:
        strength_note = (
            f"REAL efficiency_backbone/epa_prior for {epa_count}/32 teams; "
            f"packaged_efficiency_backbone fill for {packaged_fill}/32"
        )
    elif epa_count:
        strength_note = f"REAL efficiency_backbone for {epa_count}/32 teams"
    elif packaged_fill:
        prior_season = packaged_meta.get("prior_season") or (int(season) - 1)
        strength_note = (
            f"REAL packaged_efficiency_backbone for {packaged_fill}/32 teams "
            f"(prior_season={prior_season}; rolling features empty)"
        )
    else:
        strength_note = "PLACEHOLDER league-average strengths (efficiency backbone empty)"

    final_schedule = schedule[:272] if len(schedule) >= 272 else schedule
    return EngineUniverse(
        season=season,
        schedule=final_schedule,
        strengths=initialize_strengths(strength_inputs),
        rosters=rosters,
        notes={
            "mode": "real",
            "schedule_source": schedule_source,
            "schedule_as_of": schedule_as_of,
            "roster_source": roster_source,
            "roster_as_of": roster_as_of,
            "depth_source": roster_source,
            "depth_as_of": roster_as_of,
            "schedule": schedule_note,
            "strengths": strength_note,
            "rosters": f"{roster_note}; usage_role taxonomy annotated",
            "calibration": CALIBRATION_TAG,
            **coverage,
            **{f"cal_{k}": v for k, v in calibration_notes().items()},
        },
    )


def build_packaged_real_universe(season: int = 2026) -> EngineUniverse:
    """Real packaged schedule + depth + efficiency backbone (no DB required).

    Used when DB is unreachable or empty so the engine still projects against
    the actual 2026 slate (with byes), real skill identities, and prior-season
    efficiency strength hierarchy instead of inventing round-robin / demo bumps.
    """
    schedule, pkg_meta = load_packaged_regular_schedule(season)
    demo = build_demo_universe(season=season)

    # Strengths: packaged efficiency backbone (never demo bumps for "real" mode).
    epa_priors, epa_meta = load_packaged_epa_priors(season)
    strength_source = str(
        epa_meta.get("strength_source") or STRENGTH_SOURCE_PACKAGED_EFFICIENCY
    )
    strength_inputs: Dict[str, Dict[str, float | str]] = {}
    for team in NFL_TEAMS:
        prior = epa_priors[team]
        strength_inputs[team] = {
            "offense_index": float(prior["offense_index"]),
            "defense_index": float(prior["defense_index"]),
            "pace_factor": float(prior.get("pace_factor", 1.0)),
            "pass_rate_bias": float(prior.get("pass_rate_bias", 0.0)),
            "st_index": float(prior.get("st_index", 1.0) or 1.0),
            "explosiveness": float(prior.get("explosiveness", 0.0) or 0.0),
            "variance": float(prior.get("variance", 1.0) or 1.0),
            "qb_premium": float(prior.get("qb_premium", 0.0) or 0.0),
            "as_of": str(prior.get("as_of") or epa_meta.get("strength_as_of") or ""),
            "version": str(prior.get("version") or epa_meta.get("backbone_version") or ""),
            "source": strength_source,
        }
    strengths = initialize_strengths(strength_inputs)
    prior_season = int(epa_meta.get("prior_season") or (int(season) - 1))
    strength_note = (
        f"REAL {strength_source} for 32/32 teams "
        f"(prior_season={prior_season} efficiency backbone v1 → "
        f"strength indices; as_of={epa_meta.get('strength_as_of') or '?'})"
    )

    roster_source = ROSTER_SOURCE_DEMO
    roster_as_of = "2025_offseason_approx"
    roster_note = (
        "Offline demo skill cores (packaged depth missing); "
        "prefer nfl_dp_depth_chart_weekly when DB is up."
    )
    rosters = demo.rosters
    coverage: Dict[str, Any] = {}
    try:
        packaged_rows, pkg_depth_meta = load_packaged_depth_chart(season)
        rosters, _hits, coverage = _rosters_from_depth_rows(
            packaged_rows,
            source=ROSTER_SOURCE_PACKAGED,
            baseline_eff=None,
        )
        for team in NFL_TEAMS:
            if not rosters.get(team):
                rosters[team] = [_role_from_demo(team, r) for r in _generic_skill(team)]
        rosters = annotate_roster_book(rosters)
        rosters, _depth_structures = apply_depth_chart_roster_book(rosters)
        roster_source = str(pkg_depth_meta.get("roster_source") or ROSTER_SOURCE_PACKAGED)
        roster_as_of = str(pkg_depth_meta.get("roster_as_of") or "")
        roster_note = (
            f"REAL packaged nflverse depth ({coverage.get('depth_named_skill_teams', 0)}/32 "
            "named skill teams); DB weekly preferred when populated."
        )
    except (FileNotFoundError, ValueError, OSError, json.JSONDecodeError):
        coverage = depth_coverage_from_rosters(rosters)

    notes = {
        "mode": "real",
        "schedule_source": str(pkg_meta.get("schedule_source") or SCHEDULE_SOURCE_PACKAGED),
        "schedule_as_of": str(pkg_meta.get("schedule_as_of") or ""),
        "roster_source": roster_source,
        "roster_as_of": roster_as_of,
        "depth_source": roster_source,
        "depth_as_of": roster_as_of,
        "strength_source": strength_source,
        "strength_as_of": str(epa_meta.get("strength_as_of") or ""),
        "backbone_version": str(epa_meta.get("backbone_version") or ""),
        "schedule": (
            f"REAL packaged 2026 REG schedule ({len(schedule)} games, byes). "
            "DB unavailable — using packaged offline artifacts."
        ),
        "strengths": strength_note,
        "rosters": roster_note,
        "calibration": CALIBRATION_TAG,
        **coverage,
        **{f"cal_{k}": v for k, v in calibration_notes().items()},
    }
    return EngineUniverse(
        season=season,
        schedule=schedule,
        strengths=strengths,
        rosters=rosters,
        notes=notes,
    )


def resolve_season_universe(
    *,
    season: int = 2026,
    as_of_week: int = 1,
    demo: bool = False,
    session: Any = None,
) -> Tuple[EngineUniverse, Dict[str, Any]]:
    """Resolve the engine universe for HTTP/CLI callers.

    * ``demo=True`` → explicit round-robin demo (tests).
    * else try DB session when provided; on failure / empty → packaged real.
    * Never silently returns demo schedule unless ``demo=True``.
    """
    if demo:
        universe = build_demo_universe(season=season)
        return universe, universe_schedule_meta(universe)

    if session is not None:
        try:
            universe = load_universe_from_db(
                session, season=season, as_of_week=as_of_week
            )
            meta = universe_schedule_meta(universe)
            # Guard: if somehow still on demo schedule, upgrade to packaged.
            if meta.get("schedule_source") == SCHEDULE_SOURCE_DEMO:
                universe = build_packaged_real_universe(season=season)
                meta = universe_schedule_meta(universe)
            return universe, meta
        except Exception:
            pass

    universe = build_packaged_real_universe(season=season)
    return universe, universe_schedule_meta(universe)
