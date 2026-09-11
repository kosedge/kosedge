"""Assemble a certified NFL DFS research board.

Salary + weekly production + site scoring. Failed identity joins never
produce value or a recommendation. Season averages are never substituted.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from src.services.nfl_dfs_game_env import DfsGameEnv, DfsGameMarketQuote, join_game_environment
from src.services.nfl_dfs_identity import (
    DFS_IDENTITY_VERSION,
    DFS_SKILL_POSITIONS,
    DfsJoinVerdict,
    DfsProjectionTarget,
    DfsSalaryObservation,
    DfsSlateIdentity,
    canonical_dfs_position,
    canonical_dfs_site,
    certify_dfs_join,
    detect_duplicate_player_uids,
    present_salary_for_site,
)
from src.services.nfl_dfs_ownership import unavailable_ownership
from src.services.nfl_dfs_scoring import score_production_for_site
from src.services.nfl_dfs_value import salary_relative_positional_value
from src.services.nfl_player_production import (
    PRODUCTION_VERSION,
    PlayerGameProduction,
    production_from_baseline_row,
)

BOARD_VERSION = "nfl-dfs-board-v1"


@dataclass
class DfsBoardRow:
    site: str
    slate_id: str
    season: int
    week: int
    player_uid: str
    player_name: str
    position: str
    team: str
    opponent: str
    salary: int
    projection: float
    median: Optional[float]
    floor: Optional[float]
    ceiling: Optional[float]
    value: Optional[float]
    salary_rel_delta: Optional[float]
    salary_rel_per_1k: Optional[float]
    rank_position: Optional[int]
    rank_overall_value: Optional[int]
    scoring_system: str
    production_version: str
    salary_source: str
    salary_source_version: str
    salary_captured_at: str
    projection_run: str
    ownership_status: str
    leverage: Optional[float]
    game_env: Dict[str, Any]
    join_reason: str = "ok"


@dataclass
class DfsRejected:
    reason: str
    player_name: Optional[str] = None
    source_player_id: Optional[str] = None
    player_uid: Optional[str] = None


@dataclass
class DfsBoard:
    site: str
    season: int
    week: int
    slate_id: Optional[str]
    slate_name: Optional[str]
    status: str
    live: bool
    rows: List[DfsBoardRow] = field(default_factory=list)
    rejected: List[DfsRejected] = field(default_factory=list)
    slates: List[Dict[str, Any]] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)
    diagnostics: Dict[str, Any] = field(default_factory=dict)

    def as_public(self) -> Dict[str, Any]:
        return {
            "site": self.site,
            "season": self.season,
            "week": self.week,
            "slate_id": self.slate_id,
            "slate_name": self.slate_name,
            "status": self.status,
            "live": False,  # Product VERIFY required before treating DFS as live.
            "board_version": BOARD_VERSION,
            "identity_version": DFS_IDENTITY_VERSION,
            "production_version": PRODUCTION_VERSION,
            "rows": [asdict(row) for row in self.rows],
            "rejected": [asdict(item) for item in self.rejected],
            "slates": self.slates,
            "summary": self.summary,
            "diagnostics": self.diagnostics,
            "ownership": {
                "status": "unavailable",
                "reason": "no_defensible_source",
            },
        }


@dataclass
class DfsProjectionInput:
    player_uid: str
    player_name: str
    team: str
    opponent: Optional[str]
    position: str
    game_id: Optional[str]
    production: PlayerGameProduction
    baseline_row: Dict[str, Any]


def _empty_board(
    *,
    site: str,
    season: int,
    week: int,
    status: str,
    slate_id: Optional[str] = None,
    slates: Optional[List[Dict[str, Any]]] = None,
    rejected: Optional[List[DfsRejected]] = None,
    extra_diag: Optional[Dict[str, Any]] = None,
) -> DfsBoard:
    return DfsBoard(
        site=site,
        season=season,
        week=week,
        slate_id=slate_id,
        slate_name=None,
        status=status,
        live=False,
        rejected=rejected or [],
        slates=slates or [],
        diagnostics={
            "fail_closed": True,
            "season_average_substituted": False,
            **(extra_diag or {}),
        },
    )


def assemble_dfs_board(
    *,
    requested: DfsSlateIdentity,
    salaries: Sequence[DfsSalaryObservation],
    projections: Sequence[DfsProjectionInput],
    available_slates: Optional[Sequence[DfsSlateIdentity]] = None,
    game_quotes: Optional[Dict[str, tuple[Optional[DfsGameMarketQuote], Optional[DfsGameMarketQuote]]]] = None,
    position: Optional[str] = None,
) -> DfsBoard:
    site = canonical_dfs_site(requested.site)
    if site is None:
        return _empty_board(
            site=str(requested.site),
            season=requested.season,
            week=requested.week,
            status="invalid_site",
        )

    pos_filter = canonical_dfs_position(position) if position else None
    if position and pos_filter is None:
        return _empty_board(
            site=site,
            season=requested.season,
            week=requested.week,
            status="position_not_supported",
            extra_diag={"requested_position": position},
        )

    if not str(requested.slate_id).strip():
        current = [
            s
            for s in (available_slates or [])
            if canonical_dfs_site(s.site) == site
            and int(s.season) == int(requested.season)
            and int(s.week) == int(requested.week)
        ]
        if len(current) == 0:
            return _empty_board(
                site=site,
                season=requested.season,
                week=requested.week,
                status="no_slate",
                slates=[],
            )
        if len(current) > 1:
            return _empty_board(
                site=site,
                season=requested.season,
                week=requested.week,
                status="ambiguous_slate",
                slates=[asdict(s) for s in current],
            )
        requested = current[0]

    slate_id = requested.slate_id
    duplicate_uids = detect_duplicate_player_uids(
        row for row in salaries if row.slate_id == slate_id and canonical_dfs_site(row.site) == site
    )
    proj_by_uid = {p.player_uid: p for p in projections if p.player_uid}

    certified: List[DfsBoardRow] = []
    rejected: List[DfsRejected] = []
    seen_uid: set[str] = set()

    for salary in salaries:
        site_verdict = present_salary_for_site(salary, site)
        if not site_verdict.ok:
            rejected.append(
                DfsRejected(
                    reason=site_verdict.reason,
                    player_name=salary.player_name,
                    source_player_id=salary.source_player_id,
                    player_uid=salary.player_uid,
                )
            )
            continue
        if salary.player_uid and salary.player_uid in duplicate_uids:
            rejected.append(
                DfsRejected(
                    reason="duplicate_player_identity",
                    player_name=salary.player_name,
                    source_player_id=salary.source_player_id,
                    player_uid=salary.player_uid,
                )
            )
            continue
        projection_input = proj_by_uid.get(str(salary.player_uid)) if salary.player_uid else None
        projection_target = (
            DfsProjectionTarget(
                season=requested.season,
                week=requested.week,
                player_uid=projection_input.player_uid,
                player_name=projection_input.player_name,
                team=projection_input.team,
                opponent=projection_input.opponent,
                position=projection_input.position,
                game_id=projection_input.game_id,
                production_version=PRODUCTION_VERSION,
                scoring_system="dk_classic" if site == "DK" else "fd_classic",
            )
            if projection_input
            else None
        )
        verdict: DfsJoinVerdict = certify_dfs_join(
            requested=requested,
            salary=salary,
            projection=projection_target,
        )
        if not verdict.allow_value:
            rejected.append(
                DfsRejected(
                    reason=verdict.reason,
                    player_name=salary.player_name,
                    source_player_id=salary.source_player_id,
                    player_uid=salary.player_uid,
                )
            )
            continue
        if pos_filter and canonical_dfs_position(salary.position) != pos_filter:
            continue
        assert projection_input is not None
        scored = score_production_for_site(
            projection_input.production,
            site=site,
            baseline_row=projection_input.baseline_row,
        )
        quotes = (game_quotes or {}).get(f"{salary.team}|{salary.opponent}")
        env = (
            join_game_environment(
                season=requested.season,
                week=requested.week,
                team=salary.team,
                opponent=salary.opponent,
                total_quote=quotes[0] if quotes else None,
                spread_quote=quotes[1] if quotes else None,
            )
            if quotes
            else DfsGameEnv(False, "missing_game_quotes")
        )
        ownership = unavailable_ownership(
            site=site,
            season=requested.season,
            week=requested.week,
            slate_id=slate_id,
            player_uid=str(salary.player_uid),
        )
        if salary.player_uid in seen_uid:
            rejected.append(
                DfsRejected(
                    reason="duplicate_player_identity",
                    player_name=salary.player_name,
                    source_player_id=salary.source_player_id,
                    player_uid=salary.player_uid,
                )
            )
            certified = [row for row in certified if row.player_uid != salary.player_uid]
            continue
        seen_uid.add(str(salary.player_uid))
        certified.append(
            DfsBoardRow(
                site=site,
                slate_id=slate_id,
                season=requested.season,
                week=requested.week,
                player_uid=str(salary.player_uid),
                player_name=salary.player_name,
                position=canonical_dfs_position(salary.position) or salary.position,
                team=salary.team,
                opponent=salary.opponent,
                salary=int(salary.salary),
                projection=scored.projection,
                median=scored.median,
                floor=scored.floor,
                ceiling=scored.ceiling,
                value=None,
                salary_rel_delta=None,
                salary_rel_per_1k=None,
                rank_position=None,
                rank_overall_value=None,
                scoring_system=scored.scoring_system,
                production_version=PRODUCTION_VERSION,
                salary_source=salary.source,
                salary_source_version=salary.source_version,
                salary_captured_at=salary.captured_at,
                projection_run=projection_input.production.version,
                ownership_status=ownership.status,
                leverage=None,
                game_env=env.as_public(),
            )
        )

    by_pos: Dict[str, List[DfsBoardRow]] = defaultdict(list)
    for row in certified:
        by_pos[row.position].append(row)
    for pos, group in by_pos.items():
        peers = [(r.salary, r.projection) for r in group]
        for row in group:
            valued = salary_relative_positional_value(
                projection=row.projection,
                salary=row.salary,
                peer_salaries_and_projections=peers,
            )
            row.value = valued.points_per_1k
            row.salary_rel_delta = valued.salary_rel_delta
            row.salary_rel_per_1k = valued.salary_rel_per_1k
        ordered_proj = sorted(group, key=lambda r: r.projection, reverse=True)
        for idx, row in enumerate(ordered_proj, start=1):
            row.rank_position = idx

    valued_rows = [r for r in certified if r.value is not None]
    for idx, row in enumerate(sorted(valued_rows, key=lambda r: r.value or 0, reverse=True), start=1):
        row.rank_overall_value = idx

    certified.sort(key=lambda r: r.projection, reverse=True)
    summary = _board_summary(certified)
    return DfsBoard(
        site=site,
        season=requested.season,
        week=requested.week,
        slate_id=slate_id,
        slate_name=None,
        status="ok" if certified else "empty",
        live=False,
        rows=certified,
        rejected=rejected,
        slates=[asdict(s) for s in (available_slates or [])],
        summary=summary,
        diagnostics={
            "fail_closed": True,
            "season_average_substituted": False,
            "salary_count": len(salaries),
            "projection_count": len(projections),
            "certified_count": len(certified),
            "rejected_count": len(rejected),
            "ownership_published": False,
            "k_dst_supported": False,
            "optimizer": False,
        },
    )


def _board_summary(rows: Sequence[DfsBoardRow]) -> Dict[str, Any]:
    if not rows:
        return {"top_projection": None, "best_value": None, "highest_ceiling": None}

    def _pub(row: DfsBoardRow) -> Dict[str, Any]:
        return {
            "player_uid": row.player_uid,
            "player_name": row.player_name,
            "position": row.position,
            "team": row.team,
            "opponent": row.opponent,
            "salary": row.salary,
            "projection": row.projection,
            "floor": row.floor,
            "ceiling": row.ceiling,
            "value": row.value,
        }

    top_proj = max(rows, key=lambda r: r.projection)
    valued = [r for r in rows if r.value is not None]
    best_value = max(valued, key=lambda r: r.value or 0) if valued else None
    ceiled = [r for r in rows if r.ceiling is not None]
    highest_ceiling = max(ceiled, key=lambda r: r.ceiling or 0) if ceiled else None
    return {
        "top_projection": _pub(top_proj),
        "best_value": _pub(best_value) if best_value else None,
        "highest_ceiling": _pub(highest_ceiling) if highest_ceiling else None,
    }


def projection_input_from_baseline(row: Any) -> Optional[DfsProjectionInput]:
    player_uid = getattr(row, "player_uid", None)
    if hasattr(row, "get"):
        player_uid = row.get("player_uid") or player_uid
        mapping = dict(row)
    else:
        mapping = {k: getattr(row, k) for k in dir(row) if not k.startswith("_")}
        # Prefer SQLAlchemy mapping when present.
        if hasattr(row, "_mapping"):
            mapping = dict(row._mapping)
    if not player_uid:
        return None
    position = canonical_dfs_position(mapping.get("position"))
    if position not in DFS_SKILL_POSITIONS:
        return None
    return DfsProjectionInput(
        player_uid=str(player_uid),
        player_name=str(mapping.get("player_name") or ""),
        team=str(mapping.get("team") or ""),
        opponent=mapping.get("opponent"),
        position=position,
        game_id=str(mapping.get("game_id")) if mapping.get("game_id") is not None else None,
        production=production_from_baseline_row(mapping),
        baseline_row=mapping,
    )
