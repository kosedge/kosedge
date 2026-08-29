"""Universe loaders for the hierarchical season engine.

Default (``demo=False``): real 2026 regular-season schedule — prefer
``nfl_dp_schedules`` when a DB session has rows; otherwise the packaged
wall-chart JSON (272 REG games with byes).

Depth / roster — **single source of truth** for player→team identities:

1. Packaged ``nfl_depth_chart_2026_w1.json`` when present for the season
   (authoritative SoT shared with intel depth/roster surfaces)
2. ``nfl_dp_depth_chart_weekly`` only when no packaged SoT exists
3. ``nfl_dp_official_depth_charts`` only when no packaged SoT exists
4. ``demo_depth_chart`` (explicit ``demo=True`` only — never a silent fill
   when the packaged SoT is present)

The engine must never prefer stale DB weekly/official rows that disagree
with the packaged depth SoT. Roster/depth changes update the pack only.

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
from src.services.nfl_season_engine.player_regression import (
    apply_process_priors_to_roster_book,
)
from src.services.nfl_season_engine.usage_roles import annotate_roster_book

_PACKAGE_DATA_DIR = Path(__file__).resolve().parent / "data"
_PACKAGED_SCHEDULE_FILES = {
    2026: _PACKAGE_DATA_DIR / "nfl_regular_schedule_2026.json",
}
_PACKAGED_DEPTH_FILES = {
    2026: _PACKAGE_DATA_DIR / "nfl_depth_chart_2026_w1.json",
}
_PACKAGED_ROOKIE_FLAG_FILES = {
    2026: _PACKAGE_DATA_DIR / "nfl_skill_rookie_flags_2026.json",
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
STRENGTH_SOURCE_BLEND = "efficiency_backbone_blend"
STRENGTH_SOURCE_PLACEHOLDER = "placeholder_league_avg"

_SKILL_POSITIONS = ("QB", "RB", "WR", "TE")

# Approximate overall-pick → round when draft_picks round is unavailable.
# Compensatory picks make this imperfect; used only when draft_number is known
# (never invents capital for undrafted / missing rows).
_DRAFT_PICKS_PER_ROUND = 32


def normalize_team_abbr(raw: str) -> str:
    """Normalize common NFL team abbreviations (LAR → LA)."""
    token = str(raw or "").strip().upper()
    if token in ("LAR",):
        return "LA"
    if token == "AZ":
        return "ARI"
    return token


def draft_round_from_number(draft_number: Optional[int]) -> Optional[int]:
    """Map overall draft pick → round 1–7 when pick is known.

    Returns ``None`` for missing / non-positive picks (UDFA / unknown). Does
    **not** invent draft capital — only projects round slots from a real pick.
    """
    if draft_number is None:
        return None
    try:
        n = int(draft_number)
    except (TypeError, ValueError):
        return None
    if n < 1:
        return None
    return int(min(7, max(1, (n - 1) // _DRAFT_PICKS_PER_ROUND + 1)))


def load_packaged_rookie_flags(season: int) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Any]]:
    """Load packaged player_id → rookie/draft flags for ``season``.

    Returns ``(by_player_id, meta)``. Missing artifact → empty map (callers
    leave depth rows unclassified rather than guessing).
    """
    path = _PACKAGED_ROOKIE_FLAG_FILES.get(int(season))
    if path is None or not path.is_file():
        return {}, {
            "rookie_flag_source": "missing",
            "rookie_flag_path": "",
            "rookie_flag_count": 0,
        }
    payload = json.loads(path.read_text(encoding="utf-8"))
    players = payload.get("players") or {}
    out: Dict[str, Dict[str, Any]] = {}
    if isinstance(players, Mapping):
        for pid, row in players.items():
            if not pid or not isinstance(row, Mapping):
                continue
            out[str(pid)] = dict(row)
    meta = {
        "rookie_flag_source": str(payload.get("source") or "packaged_nflverse_rookie_flags"),
        "rookie_flag_path": str(path.name),
        "rookie_flag_count": len(out),
        "rookie_flag_as_of": str(payload.get("as_of") or ""),
        "flagged_rookies": int(payload.get("flagged_rookies") or 0),
        "unclassified": int(payload.get("unclassified") or 0),
    }
    return out, meta


def classify_rookie_from_roster_fields(
    *,
    season: int,
    rookie_year: Optional[int] = None,
    entry_year: Optional[int] = None,
    years_exp: Optional[int] = None,
    draft_number: Optional[int] = None,
    draft_round: Optional[int] = None,
) -> Dict[str, Any]:
    """Derive is_rookie / draft_round / status from roster signals.

    Unclassified when no experience/rookie-year signal exists — leaves
    ``is_rookie=False`` and ``draft_round=None`` (do not invent capital).
    """
    ry = rookie_year
    ey = entry_year
    ye = years_exp
    is_rookie = False
    status = "veteran"
    classification = "veteran"
    if ry is not None and int(ry) == int(season):
        is_rookie = True
        status = "rookie"
        classification = "rookie_year_match"
    elif ry is None and ye == 0:
        is_rookie = True
        status = "rookie"
        classification = "years_exp_0_unset_rookie_year"
    elif ry is None and ey is not None and int(ey) == int(season):
        is_rookie = True
        status = "rookie"
        classification = "entry_year_match_unset_rookie_year"
    elif ry is None and ye is None and ey is None:
        status = "unclassified"
        classification = "unclassified_neutral"

    round_i = draft_round
    if round_i is None:
        round_i = draft_round_from_number(draft_number)
    return {
        "is_rookie": bool(is_rookie),
        "draft_round": int(round_i) if round_i is not None else None,
        "draft_number": int(draft_number) if draft_number is not None else None,
        "rookie_status": status,
        "rookie_classification": classification,
    }


def enrich_depth_rows_with_rookie_flags(
    depth_rows: Sequence[Mapping[str, Any]],
    flags_by_player_id: Mapping[str, Mapping[str, Any]],
    *,
    season: int,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Attach is_rookie / draft_round / rookie_status onto depth rows.

    Prefer explicit fields already on the row; else join by ``player_id``.
    Missing join → unclassified (neutral; no invented draft_round).
    """
    out: List[Dict[str, Any]] = []
    stats = {
        "rookie_flagged": 0,
        "rookie_with_draft_round": 0,
        "unclassified": 0,
        "veteran": 0,
        "joined_by_player_id": 0,
    }
    for raw in depth_rows:
        row = dict(raw)
        pid = str(row.get("player_id") or "").strip()
        flag = flags_by_player_id.get(pid) if pid else None

        # Explicit row fields win when present (tests / DB pre-joined rows).
        has_explicit = row.get("is_rookie") is not None or row.get("draft_round") is not None
        if flag is not None and not has_explicit:
            stats["joined_by_player_id"] += 1
            classified = classify_rookie_from_roster_fields(
                season=season,
                rookie_year=flag.get("rookie_year"),
                entry_year=flag.get("entry_year"),
                years_exp=flag.get("years_exp"),
                draft_number=flag.get("draft_number"),
                draft_round=flag.get("draft_round"),
            )
            # Packaged flags may already set is_rookie / classification.
            if "is_rookie" in flag and flag.get("classification"):
                classified["is_rookie"] = bool(flag.get("is_rookie"))
                classified["rookie_classification"] = str(flag.get("classification"))
                classified["rookie_status"] = (
                    "rookie"
                    if classified["is_rookie"]
                    else (
                        "unclassified"
                        if str(flag.get("classification", "")).startswith("unclassified")
                        else "veteran"
                    )
                )
                if flag.get("draft_round") is not None:
                    try:
                        classified["draft_round"] = int(flag["draft_round"])
                    except (TypeError, ValueError):
                        classified["draft_round"] = None
                elif classified["is_rookie"] is False and str(
                    flag.get("classification", "")
                ).startswith("unclassified"):
                    classified["draft_round"] = None
            row.update(classified)
        elif has_explicit:
            try:
                draft_i = (
                    int(row["draft_round"]) if row.get("draft_round") is not None else None
                )
            except (TypeError, ValueError):
                draft_i = None
            if draft_i is None and row.get("draft_number") is not None:
                draft_i = draft_round_from_number(row.get("draft_number"))
            is_rook = bool(row.get("is_rookie"))
            row["is_rookie"] = is_rook
            row["draft_round"] = draft_i
            row["rookie_status"] = "rookie" if is_rook else str(
                row.get("rookie_status") or "veteran"
            )
            row["rookie_classification"] = str(
                row.get("rookie_classification")
                or ("rookie_explicit" if is_rook else "veteran_explicit")
            )
        elif pid:
            # Known identity but no roster flag → unclassified, not a guessed rookie.
            row["is_rookie"] = False
            row["draft_round"] = None
            row["rookie_status"] = "unclassified"
            row["rookie_classification"] = "unclassified_missing_roster"
        else:
            row["is_rookie"] = False
            row["draft_round"] = None
            row["rookie_status"] = "unclassified"
            row["rookie_classification"] = "unclassified_no_player_id"

        if row.get("is_rookie"):
            stats["rookie_flagged"] += 1
            if row.get("draft_round") is not None:
                stats["rookie_with_draft_round"] += 1
        elif str(row.get("rookie_status") or "") == "unclassified":
            stats["unclassified"] += 1
        else:
            stats["veteran"] += 1
        out.append(row)
    return out, stats


def _load_rookie_flags_from_db(
    session: Any,
    *,
    season: int,
) -> Dict[str, Dict[str, Any]]:
    """Best-effort ``player_id`` → roster rookie/draft fields from DB."""
    from sqlalchemy import text

    try:
        rows = session.execute(
            text(
                """
                SELECT DISTINCT ON (player_id)
                  player_id, player_name, team, position,
                  rookie_year, entry_year, draft_number
                FROM nfl_dp_rosters
                WHERE season = :season
                  AND player_id IS NOT NULL
                  AND player_id <> ''
                ORDER BY player_id, updated_at DESC NULLS LAST
                """
            ),
            {"season": int(season)},
        ).fetchall()
    except Exception:
        try:
            rows = session.execute(
                text(
                    """
                    SELECT player_id, player_name, team, position,
                           rookie_year, entry_year, draft_number
                    FROM nfl_dp_rosters
                    WHERE season = :season
                      AND player_id IS NOT NULL
                      AND player_id <> ''
                    """
                ),
                {"season": int(season)},
            ).fetchall()
        except Exception:
            return {}

    out: Dict[str, Dict[str, Any]] = {}
    for r in rows or []:
        mapping = dict(getattr(r, "_mapping", {}) or {})
        if not mapping:
            mapping = {
                "player_id": getattr(r, "player_id", None),
                "player_name": getattr(r, "player_name", None),
                "team": getattr(r, "team", None),
                "position": getattr(r, "position", None),
                "rookie_year": getattr(r, "rookie_year", None),
                "entry_year": getattr(r, "entry_year", None),
                "draft_number": getattr(r, "draft_number", None),
            }
        pid = str(mapping.get("player_id") or "").strip()
        if not pid:
            continue

        def _opt_int(key: str) -> Optional[int]:
            val = mapping.get(key)
            if val is None or val == "":
                return None
            try:
                return int(val)
            except (TypeError, ValueError):
                return None

        classified = classify_rookie_from_roster_fields(
            season=season,
            rookie_year=_opt_int("rookie_year"),
            entry_year=_opt_int("entry_year"),
            years_exp=None,
            draft_number=_opt_int("draft_number"),
            draft_round=None,
        )
        out[pid] = {
            "player_id": pid,
            "player_name": mapping.get("player_name"),
            "team": normalize_team_abbr(str(mapping.get("team") or "")),
            "position": str(mapping.get("position") or "").upper(),
            "rookie_year": _opt_int("rookie_year"),
            "entry_year": _opt_int("entry_year"),
            "draft_number": _opt_int("draft_number"),
            "draft_round": classified["draft_round"],
            "is_rookie": classified["is_rookie"],
            "classification": classified["rookie_classification"],
            "source": "nfl_dp_rosters",
        }
    return out


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
                "past_sos": dict(row.get("past_sos") or {}),
                "raw_off_epa": float(
                    (row.get("past_sos") or {}).get(
                        "raw_off_epa", row.get("off_epa_per_play", 0.0)
                    )
                    or 0.0
                ),
                "schedule_adj_off_epa": float(
                    (row.get("past_sos") or {}).get(
                        "schedule_adj_off_epa", row.get("off_epa_per_play", 0.0)
                    )
                    or 0.0
                ),
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
    player_name (+ optional player_id / injury_* fields). Raises when the
    artifact is missing or empty — callers fall through to demo depth.

    When the pack is present it is the exclusive player→team SoT. Optional
    ``ol_roles`` / ``defense_roles`` / ``injury_paths`` / ``camp_intel`` ride
    along in ``meta`` for ops + KEI (OL/defense do not enter skill usage
    allocation).
    """
    path = _PACKAGED_DEPTH_FILES.get(int(season))
    if path is None or not path.is_file():
        raise FileNotFoundError(
            f"No packaged depth chart for season={season} "
            f"(expected under {_PACKAGE_DATA_DIR})"
        )
    payload = json.loads(path.read_text(encoding="utf-8"))
    # Attach / preserve snapshot lineage metadata (Phase 1 integrity gate).
    from src.services.nfl_season_engine.data_integrity import (
        ensure_snapshot_metadata,
        pack_sha256,
        validate_depth_sot_pack,
    )
    import os as _os

    payload = ensure_snapshot_metadata(payload, pack_path=path)
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
        row: Dict[str, Any] = {
            "team": team,
            "position": pos,
            "depth_order": depth,
            "player_name": name,
            "player_id": str(r.get("player_id") or ""),
            "role_confidence": float(r.get("role_confidence") or (0.85 if depth == 1 else 0.6)),
        }
        # Optional camp / injury intel fields (ignored by share math; used by
        # intel surfaces + packaged injury_paths derivation).
        for key in (
            "depth_slot",
            "injury_status",
            "injury_window",
            "injury_note",
            "injury_sources",
            "competition_status",
            "snap_share_prior",
            "snap_share_package",
        ):
            if key in r and r.get(key) not in (None, ""):
                row[key] = r.get(key)
        rows.append(row)
    if not rows:
        raise ValueError(f"Packaged depth chart empty: {path}")
    injury_paths_raw = payload.get("injury_paths") or []
    injury_paths = [
        dict(p)
        for p in injury_paths_raw
        if isinstance(p, Mapping) and (p.get("player_name") or p.get("player_key"))
    ]
    ol_roles = [
        dict(p) for p in (payload.get("ol_roles") or []) if isinstance(p, Mapping)
    ]
    defense_roles = [
        dict(p)
        for p in (payload.get("defense_roles") or [])
        if isinstance(p, Mapping)
    ]
    sha = pack_sha256(path)
    meta = {
        "roster_source": str(payload.get("source") or ROSTER_SOURCE_PACKAGED),
        "roster_as_of": str(payload.get("as_of") or payload.get("as_of_timestamp") or ""),
        "depth_path": str(path.name),
        "depth_row_count": len(rows),
        "depth_upstream": str(payload.get("upstream") or "nflverse"),
        "depth_week": int(payload.get("week") or 1),
        "daily_intel_as_of": str(payload.get("daily_intel_as_of") or ""),
        "snapshot_id": str(payload.get("snapshot_id") or ""),
        "pack_sha256": sha,
        "depth_sha256": sha,
        "identity_scheme": str(
            payload.get("identity_scheme") or "nflverse_gsis_player_id"
        ),
        "injury_paths": injury_paths,
        "ol_roles": ol_roles,
        "defense_roles": defense_roles,
        "defense_positions": list(payload.get("defense_positions") or []),
        "camp_intel": dict(payload.get("camp_intel") or {})
        if isinstance(payload.get("camp_intel"), Mapping)
        else {},
        "ol_efficiency_hooks": dict(
            ((payload.get("camp_intel") or {}) if isinstance(payload.get("camp_intel"), Mapping) else {}).get(
                "ol_efficiency_hooks"
            )
            or {}
        ),
    }
    # Fail-closed load path for CI / daily job (opt-in). Default: attach lineage only.
    if _os.environ.get("NFL_DEPTH_INTEGRITY_FAIL_CLOSED", "").strip() in {
        "1",
        "true",
        "TRUE",
        "yes",
    }:
        report = validate_depth_sot_pack(payload, pack_path=path)
        if not report.ok:
            from src.services.nfl_season_engine.data_integrity import DataIntegrityError

            msgs = "; ".join(f"{f.check}: {f.message}" for f in report.findings)
            raise DataIntegrityError(
                f"Depth SoT integrity FAILED snapshot_id={report.snapshot_id}: {msgs}"
            )
        meta["integrity_ok"] = True
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
    is_rookie: bool = False,
    draft_round: Optional[int] = None,
    rookie_status: str = "veteran",
    snap_share_prior: Optional[float] = None,
    snap_share_package: Optional[str] = None,
    injury_status: Optional[str] = None,
    depth_slot: Optional[str] = None,
) -> Tuple[PlayerRole, bool]:
    """Build a PlayerRole from a depth-chart identity + share priors."""
    conf = (
        float(role_confidence)
        if role_confidence is not None
        else (0.7 if depth == 1 else 0.5)
    )
    status = str(rookie_status or ("rookie" if is_rookie else "veteran"))
    from src.services.nfl_snap_share_prior import resolve_snap_share_prior

    pack_share = resolve_snap_share_prior(
        {
            "position": pos,
            "depth_order": depth,
            "snap_share_prior": snap_share_prior,
            "snap_share_package": snap_share_package,
            "injury_status": injury_status,
            "depth_slot": depth_slot,
        }
    )
    role = PlayerRole(
        player_key=f"{team}-{pos}{depth}-{name}".replace(" ", ""),
        player_name=name,
        team=team,
        position=pos,
        depth_order=depth,
        snap_share=float(pack_share),
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
        is_rookie=bool(is_rookie),
        draft_round=draft_round,
        rookie_status=status,
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


def _apply_qb_rush_profile_to_role(
    role: "PlayerRole",
    *,
    player_id: str = "",
) -> "PlayerRole":
    """Lift QB1 rush_share from SoT player_id tier (general feature)."""
    from dataclasses import replace

    from src.services.nfl_season_engine.qb_rushing_profile import (
        apply_qb_rush_to_role_shares,
        resolve_qb1_profile,
    )

    if str(role.position or "").upper() != "QB" or int(role.depth_order or 99) != 1:
        return role
    profile = resolve_qb1_profile(
        player_id=player_id,
        player_name=role.player_name,
        team=role.team,
        rush_share=float(role.rush_share or 0.0) or None,
    )
    new_rush = apply_qb_rush_to_role_shares(float(role.rush_share or 0.0), profile)
    if abs(new_rush - float(role.rush_share or 0.0)) < 1e-6:
        return role
    return replace(
        role,
        rush_share=new_rush,
        source=f"{role.source}+qb_rush_{profile.tier}",
    )


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
        is_rookie_raw = r.get("is_rookie")
        if is_rookie_raw is None:
            is_rookie_raw = getattr(r, "is_rookie", False)
        draft_raw = r.get("draft_round")
        if draft_raw is None:
            draft_raw = getattr(r, "draft_round", None)
        try:
            draft_i = int(draft_raw) if draft_raw is not None else None
        except (TypeError, ValueError):
            draft_i = None
        status_raw = r.get("rookie_status")
        if status_raw is None:
            status_raw = getattr(r, "rookie_status", None)
        if not status_raw:
            status_raw = "rookie" if is_rookie_raw else "veteran"
        snap_prior_raw = r.get("snap_share_prior")
        if snap_prior_raw is None:
            snap_prior_raw = getattr(r, "snap_share_prior", None)
        snap_pkg_raw = r.get("snap_share_package")
        if snap_pkg_raw is None:
            snap_pkg_raw = getattr(r, "snap_share_package", None)
        injury_raw = r.get("injury_status")
        if injury_raw is None:
            injury_raw = getattr(r, "injury_status", None)
        slot_raw = r.get("depth_slot")
        if slot_raw is None:
            slot_raw = getattr(r, "depth_slot", None)
        role, hit = _role_from_depth_row(
            team=team,
            pos=pos,
            depth=depth,
            name=name,
            source=source,
            role_confidence=float(conf_raw) if conf_raw is not None else None,
            baseline_eff=baseline_eff,
            is_rookie=bool(is_rookie_raw),
            draft_round=draft_i,
            rookie_status=str(status_raw),
            snap_share_prior=float(snap_prior_raw) if snap_prior_raw is not None else None,
            snap_share_package=str(snap_pkg_raw) if snap_pkg_raw not in (None, "") else None,
            injury_status=str(injury_raw) if injury_raw not in (None, "") else None,
            depth_slot=str(slot_raw) if slot_raw not in (None, "") else None,
        )
        pid = str(r.get("player_id") or getattr(r, "player_id", "") or "").strip()
        if pid and not pid.startswith(f"{team}-{pos}-"):
            from dataclasses import replace as _replace

            role = _replace(role, player_id=pid)
        role = _apply_qb_rush_profile_to_role(role, player_id=pid)
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
        "snapshot_id": str(notes.get("snapshot_id") or ""),
        "pack_sha256": str(notes.get("pack_sha256") or notes.get("depth_sha256") or ""),
        "depth_sha256": str(notes.get("depth_sha256") or notes.get("pack_sha256") or ""),
        "daily_intel_as_of": str(notes.get("daily_intel_as_of") or ""),
        "identity_scheme": str(notes.get("identity_scheme") or ""),
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
# v1.16: widen pace/pass identity so demo QB1 season yards are not a flat band.
_DEMO_STRENGTH_BUMPS: Dict[str, Dict[str, float]] = {
    "KC": {"off": 0.15, "def": 0.10, "pace": 0.03, "pass": 0.045},
    "BUF": {"off": 0.14, "def": 0.09, "pace": 0.04, "pass": 0.020},
    "PHI": {"off": 0.13, "def": 0.09, "pace": 0.02, "pass": -0.035},
    "SF": {"off": 0.11, "def": 0.12, "pace": -0.03, "pass": -0.040},
    "DET": {"off": 0.13, "def": 0.07, "pace": 0.035, "pass": 0.030},
    "BAL": {"off": 0.12, "def": 0.10, "pace": 0.02, "pass": -0.050},
    "CIN": {"off": 0.10, "def": 0.03, "pace": 0.02, "pass": 0.040},
    "MIA": {"off": 0.06, "def": 0.01, "pace": 0.05, "pass": 0.050},
    "DAL": {"off": 0.05, "def": 0.05, "pace": 0.01, "pass": 0.035},
    "GB": {"off": 0.07, "def": 0.04, "pace": 0.00, "pass": 0.015},
    "HOU": {"off": 0.06, "def": 0.08, "pace": -0.02, "pass": 0.010},
    "LAC": {"off": 0.08, "def": 0.05, "pace": 0.01, "pass": 0.035},
    "MIN": {"off": 0.05, "def": 0.03, "pace": 0.02, "pass": 0.040},
    "SEA": {"off": 0.03, "def": 0.03, "pace": 0.02, "pass": 0.020},
    "TB": {"off": 0.04, "def": 0.02, "pace": 0.01, "pass": 0.035},
    "ATL": {"off": 0.02, "def": 0.00, "pace": 0.02, "pass": -0.015},
    "LA": {"off": 0.03, "def": 0.05, "pace": -0.01, "pass": 0.030},
    "PIT": {"off": 0.00, "def": 0.08, "pace": -0.04, "pass": -0.040},
    "DEN": {"off": 0.01, "def": 0.06, "pace": -0.02, "pass": -0.010},
    "NYJ": {"off": -0.04, "def": 0.06, "pace": -0.035, "pass": -0.025},
    "CLE": {"off": -0.05, "def": 0.04, "pace": -0.04, "pass": -0.040},
    "CHI": {"off": -0.02, "def": -0.01, "pace": 0.00, "pass": -0.010},
    "IND": {"off": -0.04, "def": -0.03, "pace": 0.01, "pass": 0.005},
    "JAX": {"off": -0.05, "def": -0.04, "pace": 0.02, "pass": 0.020},
    "LV": {"off": -0.06, "def": -0.04, "pace": 0.00, "pass": 0.010},
    "NO": {"off": -0.07, "def": -0.01, "pace": -0.02, "pass": 0.005},
    "NYG": {"off": -0.08, "def": -0.05, "pace": -0.01, "pass": -0.015},
    "TEN": {"off": -0.09, "def": -0.05, "pace": -0.03, "pass": -0.035},
    "CAR": {"off": -0.11, "def": -0.07, "pace": -0.01, "pass": -0.020},
    "NE": {"off": -0.09, "def": -0.03, "pace": -0.03, "pass": -0.030},
    "WAS": {"off": 0.02, "def": -0.02, "pace": 0.02, "pass": 0.020},
    "ARI": {"off": -0.01, "def": -0.04, "pace": 0.02, "pass": 0.015},
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
    draft_round = row.get("draft_round")
    try:
        draft_round_i = int(draft_round) if draft_round is not None else None
    except (TypeError, ValueError):
        draft_round_i = None
    is_rook = bool(row.get("is_rookie", False))
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
        is_rookie=is_rook,
        draft_round=draft_round_i,
        rookie_status=str(row.get("rookie_status") or ("rookie" if is_rook else "veteran")),
    )
    return apply_efficiency_priors(role, overrides=overrides or None, source_suffix="league_efficiency_v1")


def _ensure_team_rosters(
    rosters: Dict[str, List[PlayerRole]],
    *,
    allow_demo_fill: bool,
) -> List[str]:
    """Fill missing teams. When the pack is present, never invent synthetic starters."""
    holes: List[str] = []
    for team in NFL_TEAMS:
        if rosters.get(team):
            continue
        holes.append(team)
        if allow_demo_fill:
            rosters[team] = [_role_from_demo(team, r) for r in _generic_skill(team)]
        else:
            rosters[team] = []
    return holes


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

    from dataclasses import replace as _dc_replace

    from src.services.nfl_season_engine.calibration import DEFAULT_YPA as _DEFAULT_YPA

    rosters: Dict[str, List[PlayerRole]] = {}
    for team in NFL_TEAMS:
        rows = _DEMO_SKILL.get(team) or _generic_skill(team)
        roles = [_role_from_demo(team, r) for r in rows]
        # v1.16: ladder league-default QB1 YPA off team offense (collapse fix).
        oi = float(strength_inputs[team]["offense_index"])  # type: ignore[arg-type]
        ypa_mult = max(0.88, min(1.14, 1.0 + 0.55 * (oi - 1.0)))
        roles = [
            _dc_replace(r, ypa=round(_DEFAULT_YPA * ypa_mult, 3))
            if r.position == "QB"
            and int(r.depth_order or 99) <= 1
            and abs(float(r.ypa) - _DEFAULT_YPA) < 0.06
            else r
            for r in roles
        ]
        rosters[team] = roles

    schedule = _round_robin_schedule(season, NFL_TEAMS)
    rosters = annotate_roster_book(rosters)
    rosters, depth_structures = apply_depth_chart_roster_book(rosters)
    rosters = apply_process_priors_to_roster_book(rosters)
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
    """Load schedule + true-PR strength core + best-effort depth roles from DB.

    Strengths come from ``_load_team_strength_priors`` (same gradual
    prior→current blend as Edge Board). Missing teams use packaged backbone
    or an explicit ``placeholder_league_avg`` label — never demo strength
    bumps. Depth does **not** silently fall back to ``demo_depth_chart`` when
    the packaged SoT is present (empty team = hole, not a fake starter).
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
    def _strength_input_from_prior(
        team: str,
        prior: Mapping[str, Any],
        pkg: Mapping[str, Any],
        *,
        source: str,
    ) -> Dict[str, float | str | Dict[str, Any]]:
        off = float(prior.get("offense_index", pkg.get("offense_index", 1.0)) or 1.0)
        deff = float(prior.get("defense_index", pkg.get("defense_index", 1.0)) or 1.0)
        full_off = float(prior.get("full_strength_offense_index", off) or off)
        full_def = float(prior.get("full_strength_defense_index", deff) or deff)
        drivers = prior.get("drivers") if isinstance(prior.get("drivers"), dict) else {}
        return {
            "offense_index": off,
            "defense_index": deff,
            "full_strength_offense_index": full_off,
            "full_strength_defense_index": full_def,
            "injury_delta_offense": float(prior.get("injury_delta_offense", 0.0) or 0.0),
            "injury_delta_defense": float(prior.get("injury_delta_defense", 0.0) or 0.0),
            "blend_prior_weight": float(prior.get("blend_prior_weight", 1.0) or 1.0),
            "blend_current_weight": float(prior.get("blend_current_weight", 0.0) or 0.0),
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
            "variance": float(prior.get("variance", pkg.get("variance", 1.35)) or 1.35),
            "qb_premium": float(prior.get("qb_premium", 0.0) or 0.0),
            "games_played": int(prior.get("games_played", 0) or 0),
            "drivers": drivers,
            "as_of": str(
                prior.get("as_of")
                or pkg.get("as_of")
                or packaged_meta.get("strength_as_of")
                or ""
            ),
            "version": str(
                prior.get("version")
                or pkg.get("version")
                or packaged_meta.get("backbone_version")
                or ""
            ),
            "source": source,
        }

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
            packaged_fill += 1
            strength_inputs[team] = _strength_input_from_prior(
                team,
                prior,
                pkg,
                source=prior_source or STRENGTH_SOURCE_PACKAGED_EFFICIENCY,
            )
        elif prior:
            epa_count += 1
            if prior_source == STRENGTH_SOURCE_BLEND or prior_source.endswith("_blend"):
                src = STRENGTH_SOURCE_BLEND
            elif prior_source.startswith("efficiency") or prior_source.startswith(
                "packaged_efficiency"
            ):
                src = STRENGTH_SOURCE_EFFICIENCY
            else:
                src = STRENGTH_SOURCE_EPA_PRIOR
            strength_inputs[team] = _strength_input_from_prior(
                team, prior, pkg, source=src
            )
        elif team in packaged_priors:
            packaged_fill += 1
            strength_inputs[team] = _strength_input_from_prior(
                team,
                pkg,
                pkg,
                source=str(
                    pkg.get("source")
                    or packaged_meta.get("strength_source")
                    or STRENGTH_SOURCE_PACKAGED_EFFICIENCY
                ),
            )
        else:
            # Explicit labeled fallback — never silent demo fill.
            strength_inputs[team] = {
                "offense_index": 1.0,
                "defense_index": 1.0,
                "full_strength_offense_index": 1.0,
                "full_strength_defense_index": 1.0,
                "blend_prior_weight": 1.0,
                "blend_current_weight": 0.0,
                "variance": 1.35,
                "qb_premium": 0.0,
                "source": STRENGTH_SOURCE_PLACEHOLDER,
                "drivers": {
                    "fallback": "placeholder_league_avg",
                    "stubs": {
                        "qb_premium": "stub_not_applied",
                        "continuity": "stub_not_applied",
                        "injury_at_time_depth": "stub_not_applied",
                        "full_venue_model": "stub_not_applied",
                        "true_time_of_game_sos": "thin_unavailable",
                    },
                    "past_sos": {
                        "status": "thin_unavailable",
                        "future_schedule_excluded": True,
                    },
                },
            }

    baseline_eff = _load_baseline_efficiency_map(session, season=season, as_of_week=as_of_week)

    weekly_rows = session.execute(
        text(
            """
            SELECT DISTINCT ON (team, position, depth_order)
              team, player_name, position, depth_order, role_confidence, player_id
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
                      team, player_name, position, depth_order, player_id
                    FROM (
                      SELECT
                        team,
                        player_name,
                        position,
                        depth_team AS depth_order,
                        player_id,
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

    # Rookie / draft flags: prefer DB rostres; fall back to packaged nflverse join.
    # Rookie-flag ``team`` is metadata only — never reassigns player→team vs depth SoT.
    rookie_flags = _load_rookie_flags_from_db(session, season=season)
    rookie_flag_meta: Dict[str, Any] = {
        "rookie_flag_source": "nfl_dp_rosters" if rookie_flags else "missing_db",
        "rookie_flag_count": len(rookie_flags),
    }
    if not rookie_flags:
        packaged_flags, packaged_flag_meta = load_packaged_rookie_flags(season)
        rookie_flags = packaged_flags
        rookie_flag_meta = packaged_flag_meta

    rosters: Dict[str, List[PlayerRole]]
    roster_source = ROSTER_SOURCE_DEMO
    roster_as_of = f"season={season};as_of_week<={as_of_week}"
    coverage: Dict[str, Any] = {}
    baseline_hits = 0
    rookie_enrich_stats: Dict[str, Any] = {}
    roster_note = ""

    # Packaged depth is the exclusive player→team SoT when present for season.
    packaged_rows: Optional[List[Dict[str, Any]]] = None
    pkg_depth_meta: Dict[str, Any] = {}
    try:
        packaged_rows, pkg_depth_meta = load_packaged_depth_chart(season)
    except (FileNotFoundError, ValueError, OSError, json.JSONDecodeError):
        packaged_rows = None

    if packaged_rows:
        depth_rows, rookie_enrich_stats = enrich_depth_rows_with_rookie_flags(
            packaged_rows,
            rookie_flags,
            season=season,
        )
        rosters, baseline_hits, coverage = _rosters_from_depth_rows(
            depth_rows,
            source=ROSTER_SOURCE_PACKAGED,
            baseline_eff=baseline_eff,
        )
        roster_source = str(pkg_depth_meta.get("roster_source") or ROSTER_SOURCE_PACKAGED)
        roster_as_of = str(pkg_depth_meta.get("roster_as_of") or "")
        skipped = []
        if weekly_rows:
            skipped.append("nfl_dp_depth_chart_weekly")
        if official_rows:
            skipped.append("nfl_dp_official_depth_charts")
        skip_note = (
            f"; ignored stale DB depth ({', '.join(skipped)}) in favor of packaged SoT"
            if skipped
            else ""
        )
        if baseline_hits:
            roster_note = (
                f"REAL packaged depth SoT identities; efficiency from baselines "
                f"({baseline_hits} hits) else league priors{skip_note}"
            )
        else:
            roster_note = (
                "REAL packaged depth SoT identities; PLACEHOLDER league efficiency priors "
                f"(nfl_player_projection_baselines unavailable or empty for as_of_week)"
                f"{skip_note}"
            )
    elif weekly_rows:
        depth_rows, rookie_enrich_stats = enrich_depth_rows_with_rookie_flags(
            [dict(r._mapping) for r in weekly_rows],  # type: ignore[attr-defined]
            rookie_flags,
            season=season,
        )
        rosters, baseline_hits, coverage = _rosters_from_depth_rows(
            depth_rows,
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
        depth_rows, rookie_enrich_stats = enrich_depth_rows_with_rookie_flags(
            [dict(r._mapping) for r in official_rows],  # type: ignore[attr-defined]
            rookie_flags,
            season=season,
        )
        rosters, baseline_hits, coverage = _rosters_from_depth_rows(
            depth_rows,
            source="official_depth_charts",
            baseline_eff=baseline_eff,
        )
        roster_source = ROSTER_SOURCE_OFFICIAL
        roster_as_of = f"season={season};official_as_of_week<={as_of_week}"
        roster_note = (
            "REAL nflverse official depth identities "
            "(no packaged SoT; bridged from nfl_dp_official_depth_charts)"
        )
    else:
        rosters = {}
        for team in NFL_TEAMS:
            rows = _DEMO_SKILL.get(team) or _generic_skill(team)
            rosters[team] = [_role_from_demo(team, r) for r in rows]
        roster_source = ROSTER_SOURCE_DEMO
        roster_as_of = "2025_offseason_approx"
        roster_note = "PLACEHOLDER demo rosters (all real depth sources empty)"
        coverage = depth_coverage_from_rosters(rosters)

    depth_holes = _ensure_team_rosters(
        rosters, allow_demo_fill=packaged_rows is None
    )
    demo_fill = (
        "applied_last_resort" if packaged_rows is None else "blocked_pack_present"
    )

    rosters = annotate_roster_book(rosters)
    rosters, _depth_structures = apply_depth_chart_roster_book(rosters)
    rosters = apply_process_priors_to_roster_book(rosters)
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

    if rookie_enrich_stats:
        roster_note = (
            f"{roster_note}; rookies_flagged="
            f"{rookie_enrich_stats.get('rookie_flagged', 0)}"
            f"/{rookie_flag_meta.get('rookie_flag_source', 'n/a')}"
        )

    final_schedule = schedule[:272] if len(schedule) >= 272 else schedule
    packaged_injury_paths = (
        list(pkg_depth_meta.get("injury_paths") or []) if packaged_rows else []
    )
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
            "rookie_flags": {**rookie_flag_meta, **rookie_enrich_stats},
            "daily_intel_as_of": str(pkg_depth_meta.get("daily_intel_as_of") or ""),
            "snapshot_id": str(pkg_depth_meta.get("snapshot_id") or ""),
            "pack_sha256": str(pkg_depth_meta.get("pack_sha256") or ""),
            "depth_sha256": str(pkg_depth_meta.get("depth_sha256") or ""),
            "identity_scheme": str(pkg_depth_meta.get("identity_scheme") or ""),
            "ol_roles_count": len(pkg_depth_meta.get("ol_roles") or []),
            "ol_efficiency_hooks": pkg_depth_meta.get("ol_efficiency_hooks") or {},
            "demo_depth_fill": demo_fill,
            "depth_team_holes": depth_holes,
            **coverage,
            **{f"cal_{k}": v for k, v in calibration_notes().items()},
        },
        packaged_injury_paths=packaged_injury_paths,
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
        off = float(prior["offense_index"])
        deff = float(prior["defense_index"])
        strength_inputs[team] = {
            "offense_index": off,
            "defense_index": deff,
            "full_strength_offense_index": off,
            "full_strength_defense_index": deff,
            "injury_delta_offense": 0.0,
            "injury_delta_defense": 0.0,
            "blend_prior_weight": 1.0,
            "blend_current_weight": 0.0,
            "pace_factor": float(prior.get("pace_factor", 1.0)),
            "pass_rate_bias": float(prior.get("pass_rate_bias", 0.0)),
            "st_index": float(prior.get("st_index", 1.0) or 1.0),
            "explosiveness": float(prior.get("explosiveness", 0.0) or 0.0),
            "variance": float(prior.get("variance", 1.35) or 1.35),
            "qb_premium": 0.0,  # stub
            "games_played": 0,
            "drivers": {
                "blend": {"w_prior": 1.0, "w_current": 0.0},
                "injury_availability_delta": {
                    "offense": 0.0,
                    "defense": 0.0,
                    "status": "structure_ready_zero",
                },
                "uncertainty": {
                    "variance": float(prior.get("variance", 1.35) or 1.35),
                    "games_played": 0,
                    "sample_note": "wide_early",
                },
                "stubs": {
                    "qb_premium": "stub_not_applied",
                    "continuity": "stub_not_applied",
                    "injury_at_time_depth": "stub_not_applied",
                    "full_venue_model": str(
                        (prior.get("past_sos") or {}).get("full_venue_model")
                        or (
                            "partial_hfa_only"
                            if prior.get("past_sos")
                            else "stub_not_applied"
                        )
                    ),
                    "true_time_of_game_sos": str(
                        (prior.get("past_sos") or {}).get("status")
                        or "thin_unavailable"
                    ),
                },
                "past_sos": dict(
                    prior.get("past_sos")
                    or {
                        "status": "thin_unavailable",
                        "future_schedule_excluded": True,
                    }
                ),
            },
            "as_of": str(prior.get("as_of") or epa_meta.get("strength_as_of") or ""),
            "version": str(prior.get("version") or epa_meta.get("backbone_version") or ""),
            "source": strength_source,
        }
    strengths = initialize_strengths(strength_inputs)
    prior_season = int(epa_meta.get("prior_season") or (int(season) - 1))
    strength_note = (
        f"REAL {strength_source} for 32/32 teams "
        f"(prior_season={prior_season} efficiency backbone; "
        f"true-PR 100% prior at 0 REG games; "
        f"as_of={epa_meta.get('strength_as_of') or '?'})"
    )

    roster_source = ROSTER_SOURCE_DEMO
    roster_as_of = "2025_offseason_approx"
    roster_note = (
        "Offline demo skill cores (packaged depth missing); "
        "prefer nfl_dp_depth_chart_weekly when DB is up."
    )
    rosters = demo.rosters
    coverage: Dict[str, Any] = {}
    rookie_flag_meta: Dict[str, Any] = {}
    rookie_enrich_stats: Dict[str, Any] = {}
    depth_holes: List[str] = []
    demo_fill = "applied_last_resort"
    try:
        packaged_rows, pkg_depth_meta = load_packaged_depth_chart(season)
        rookie_flags, rookie_flag_meta = load_packaged_rookie_flags(season)
        depth_rows, rookie_enrich_stats = enrich_depth_rows_with_rookie_flags(
            packaged_rows,
            rookie_flags,
            season=season,
        )
        rosters, _hits, coverage = _rosters_from_depth_rows(
            depth_rows,
            source=ROSTER_SOURCE_PACKAGED,
            baseline_eff=None,
        )
        depth_holes = _ensure_team_rosters(rosters, allow_demo_fill=False)
        demo_fill = "blocked_pack_present"
        rosters = annotate_roster_book(rosters)
        rosters, _depth_structures = apply_depth_chart_roster_book(rosters)
        # v1.16: ladder league-default QB1 YPA off team offense before process priors.
        from dataclasses import replace as _dc_replace
        from src.services.nfl_season_engine.calibration import DEFAULT_YPA as _DEFAULT_YPA

        for team in NFL_TEAMS:
            oi = float(strength_inputs[team]["offense_index"])  # type: ignore[arg-type]
            ypa_mult = max(0.88, min(1.14, 1.0 + 0.55 * (oi - 1.0)))
            roles = list(rosters.get(team) or [])
            rosters[team] = [
                _dc_replace(r, ypa=round(_DEFAULT_YPA * ypa_mult, 3))
                if r.position == "QB"
                and int(r.depth_order or 99) <= 1
                and abs(float(r.ypa) - _DEFAULT_YPA) < 0.06
                else r
                for r in roles
            ]
        rosters = apply_process_priors_to_roster_book(rosters)
        roster_source = str(pkg_depth_meta.get("roster_source") or ROSTER_SOURCE_PACKAGED)
        roster_as_of = str(pkg_depth_meta.get("roster_as_of") or "")
        roster_note = (
            f"REAL packaged depth SoT ({coverage.get('depth_named_skill_teams', 0)}/32 "
            f"named skill teams); rookies_flagged="
            f"{rookie_enrich_stats.get('rookie_flagged', 0)}; "
            "packaged SoT is exclusive player-to-team source (no DB depth override)."
        )
        packaged_injury_paths = list(pkg_depth_meta.get("injury_paths") or [])
        ol_roles_n = len(pkg_depth_meta.get("ol_roles") or [])
        if pkg_depth_meta.get("daily_intel_as_of"):
            roster_note += (
                f" daily_intel_as_of={pkg_depth_meta.get('daily_intel_as_of')}"
                f"; ol_roles={ol_roles_n}"
                f"; packaged_injury_paths={len(packaged_injury_paths)}"
            )
        # Phase 2: transparent OL protection → modest offense_index (not EPA magic).
        from src.services.nfl_season_engine.ol_protection import (
            apply_ol_protection_to_strength,
            build_ol_protection_book,
        )
        from dataclasses import replace as _dc_replace

        ol_book = build_ol_protection_book(
            list(pkg_depth_meta.get("ol_roles") or []),
            teams=NFL_TEAMS,
        )
        patched: Dict[str, Any] = {}
        for team, state in strengths.items():
            feat = ol_book.get(team)
            if feat is None or feat.fidelity != "applied":
                patched[team] = state
                continue
            new_off = apply_ol_protection_to_strength(float(state.offense_index), feat)
            drivers = dict(getattr(state, "drivers", None) or {})
            stubs = dict(drivers.get("stubs") or {})
            stubs["injury_at_time_depth"] = "ol_protection_v1_applied"
            drivers["stubs"] = stubs
            drivers["ol_protection"] = feat.to_dict()
            patched[team] = _dc_replace(
                state,
                offense_index=new_off,
                injury_delta_offense=round(
                    float(state.injury_delta_offense) + float(feat.offense_index_delta),
                    6,
                ),
                drivers=drivers,
            )
        strengths = patched
        strength_note += "; ol_protection_v1 from SoT ol_roles"
    except (FileNotFoundError, ValueError, OSError, json.JSONDecodeError):
        coverage = depth_coverage_from_rosters(rosters)
        packaged_injury_paths = []
        pkg_depth_meta = {}

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
        "rookie_flags": {**rookie_flag_meta, **rookie_enrich_stats},
        "daily_intel_as_of": str(pkg_depth_meta.get("daily_intel_as_of") or ""),
        "snapshot_id": str(pkg_depth_meta.get("snapshot_id") or ""),
        "pack_sha256": str(pkg_depth_meta.get("pack_sha256") or ""),
        "depth_sha256": str(pkg_depth_meta.get("depth_sha256") or ""),
        "identity_scheme": str(pkg_depth_meta.get("identity_scheme") or ""),
        "ol_roles_count": len(pkg_depth_meta.get("ol_roles") or []),
        "ol_roles": list(pkg_depth_meta.get("ol_roles") or []),
        "demo_depth_fill": demo_fill,
        "depth_team_holes": depth_holes,
        "ol_efficiency_hooks": {
            **dict(pkg_depth_meta.get("ol_efficiency_hooks") or {}),
            "status": "ol_protection_v1_feature",
            "formula": (
                "protection=1−edge_out*0.055−C_out*0.040−G_out*0.025"
                "−competition*0.012; ypa/offense deltas documented in ol_protection.py"
            ),
        },
        **coverage,
        **{f"cal_{k}": v for k, v in calibration_notes().items()},
    }
    return EngineUniverse(
        season=season,
        schedule=schedule,
        strengths=strengths,
        rosters=rosters,
        notes=notes,
        packaged_injury_paths=list(packaged_injury_paths),
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
