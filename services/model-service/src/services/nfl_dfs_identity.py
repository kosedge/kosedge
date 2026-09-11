"""NFL DFS V1 — canonical identities and fail-closed joins.

Football production stays on the player-production spine. DFS only prices and
scores that truth for a site/slate. Wrong-week, wrong-player, wrong-site,
stale-salary, missing-slate, and team-changed joins FAIL CLOSED.

Never silently substitute season averages.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Iterable, Literal, Optional

from src.services.nfl_canonical_teams import canonicalize_team
from src.services.nfl_player_production import PRODUCTION_VERSION

DFS_SITES = ("DK", "FD")
DfsSite = Literal["DK", "FD"]
SCORING_BY_SITE: Dict[str, str] = {"DK": "dk_classic", "FD": "fd_classic"}
DFS_SKILL_POSITIONS = ("QB", "RB", "WR", "TE")
DFS_IDENTITY_VERSION = "nfl-dfs-identity-v1"

JoinReason = Literal[
    "ok",
    "site_mismatch",
    "scoring_site_mismatch",
    "season_mismatch",
    "week_mismatch",
    "slate_mismatch",
    "missing_slate",
    "missing_player_identity",
    "player_mismatch",
    "wrong_player",
    "opponent_mismatch",
    "game_mismatch",
    "team_changed",
    "stale_salary",
    "missing_salary",
    "missing_projection",
    "duplicate_player_identity",
    "position_not_supported",
]


def canonical_dfs_site(raw: Any) -> Optional[str]:
    token = str(raw or "").strip().upper()
    if token in {"DK", "DRAFTKINGS", "DRAFT_KINGS"}:
        return "DK"
    if token in {"FD", "FANDUEL", "FAN_DUEL"}:
        return "FD"
    return None


def canonical_dfs_position(raw: Any) -> Optional[str]:
    token = str(raw or "").strip().upper()
    if not token:
        return None
    # DK roster cells can be "WR/FLEX" — take the primary skill slot.
    primary = token.split("/")[0].strip()
    if primary in DFS_SKILL_POSITIONS:
        return primary
    if primary in {"FB", "HB"}:
        return "RB"
    return None


def canonical_team_code(raw: Any) -> Optional[str]:
    return canonicalize_team(str(raw or "").strip() or None)


@dataclass(frozen=True)
class DfsSlateIdentity:
    season: int
    week: int
    site: str
    slate_id: str
    contest_style: str = "classic"

    def key(self) -> tuple[int, int, str, str]:
        return (self.season, self.week, self.site, self.slate_id)


@dataclass(frozen=True)
class DfsPlayerIdentity:
    player_uid: Optional[str]
    source_player_id: Optional[str]
    player_name: str
    team: str
    position: str


@dataclass(frozen=True)
class DfsSalaryObservation:
    site: str
    season: int
    week: int
    slate_id: str
    source_player_id: str
    player_uid: Optional[str]
    player_name: str
    team: str
    opponent: str
    position: str
    salary: int
    game_id: Optional[str]
    game_label: Optional[str]
    game_time: Optional[str]
    source: str
    source_version: str
    captured_at: str
    is_current: bool
    identity_status: str = "unresolved"


@dataclass(frozen=True)
class DfsProjectionTarget:
    season: int
    week: int
    player_uid: Optional[str]
    player_name: str
    team: str
    opponent: Optional[str]
    position: str
    game_id: Optional[str]
    production_version: str = PRODUCTION_VERSION
    scoring_system: str = "dk_classic"


@dataclass(frozen=True)
class DfsJoinVerdict:
    ok: bool
    reason: JoinReason
    fail_closed: bool

    @property
    def allow_value(self) -> bool:
        return self.ok and not self.fail_closed


def certify_dfs_join(
    *,
    requested: DfsSlateIdentity,
    salary: Optional[DfsSalaryObservation],
    projection: Optional[DfsProjectionTarget],
) -> DfsJoinVerdict:
    """Legal DFS row only when slate/site/week/player/game identities match."""

    if salary is None:
        return DfsJoinVerdict(False, "missing_salary", True)
    if projection is None:
        return DfsJoinVerdict(False, "missing_projection", True)

    req_site = canonical_dfs_site(requested.site)
    sal_site = canonical_dfs_site(salary.site)
    if req_site is None or sal_site is None or req_site != sal_site:
        return DfsJoinVerdict(False, "site_mismatch", True)
    expected_scoring = SCORING_BY_SITE[req_site]
    if str(projection.scoring_system or "").strip().lower() != expected_scoring:
        return DfsJoinVerdict(False, "scoring_site_mismatch", True)
    if int(salary.season) != int(requested.season) or int(projection.season) != int(requested.season):
        return DfsJoinVerdict(False, "season_mismatch", True)
    if int(salary.week) != int(requested.week) or int(projection.week) != int(requested.week):
        return DfsJoinVerdict(False, "week_mismatch", True)
    if str(salary.slate_id) != str(requested.slate_id) or not str(requested.slate_id).strip():
        return DfsJoinVerdict(False, "slate_mismatch" if requested.slate_id else "missing_slate", True)
    if not salary.is_current:
        return DfsJoinVerdict(False, "stale_salary", True)
    if int(salary.salary) <= 0:
        return DfsJoinVerdict(False, "missing_salary", True)

    if salary.identity_status == "conflict":
        return DfsJoinVerdict(False, "duplicate_player_identity", True)
    if not salary.player_uid or not projection.player_uid:
        return DfsJoinVerdict(False, "missing_player_identity", True)
    if str(salary.player_uid) != str(projection.player_uid):
        return DfsJoinVerdict(False, "wrong_player", True)

    sal_pos = canonical_dfs_position(salary.position)
    proj_pos = canonical_dfs_position(projection.position)
    if sal_pos is None or proj_pos is None or sal_pos not in DFS_SKILL_POSITIONS:
        return DfsJoinVerdict(False, "position_not_supported", True)

    sal_team = canonical_team_code(salary.team)
    proj_team = canonical_team_code(projection.team)
    if not sal_team or not proj_team or sal_team != proj_team:
        return DfsJoinVerdict(False, "team_changed", True)

    sal_opp = canonical_team_code(salary.opponent)
    proj_opp = canonical_team_code(projection.opponent) if projection.opponent else None
    if not sal_opp:
        return DfsJoinVerdict(False, "opponent_mismatch", True)
    if proj_opp and sal_opp != proj_opp:
        return DfsJoinVerdict(False, "opponent_mismatch", True)

    if salary.game_id and projection.game_id and str(salary.game_id) != str(projection.game_id):
        return DfsJoinVerdict(False, "game_mismatch", True)

    return DfsJoinVerdict(True, "ok", False)


def detect_duplicate_player_uids(
    salaries: Iterable[DfsSalaryObservation],
) -> set[str]:
    """Same player_uid twice on one current site/slate → both fail closed."""
    counts: Dict[str, int] = {}
    for row in salaries:
        if not row.is_current or not row.player_uid:
            continue
        key = f"{row.site}|{row.slate_id}|{row.player_uid}"
        counts[key] = counts.get(key, 0) + 1
    return {key.split("|", 2)[2] for key, n in counts.items() if n > 1}


def present_salary_for_site(
    salary: DfsSalaryObservation,
    site: str,
) -> DfsJoinVerdict:
    """DK observations cannot be presented as FD (and vice versa)."""
    want = canonical_dfs_site(site)
    have = canonical_dfs_site(salary.site)
    if want is None or have is None or want != have:
        return DfsJoinVerdict(False, "site_mismatch", True)
    if not salary.is_current:
        return DfsJoinVerdict(False, "stale_salary", True)
    return DfsJoinVerdict(True, "ok", False)


def identity_payload(obj: Any) -> Dict[str, Any]:
    if hasattr(obj, "__dataclass_fields__"):
        return asdict(obj)
    return dict(obj)
