"""Local sealed-tree contract check (IMV C-6 / C-7 / C-8).

Not a runner. Not a gate. Status is never a certification or PREP_VALIDATED
token. Validates as-of proofs, L-1/L-2/L-3 contracts, and expanding-window
plans on a local tree only.

Does not simulate games, fit models on real seasons, fetch odds, or open a
database.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Optional

from src.services.nfl_eval_prep.asof import (
    ASOF_IS_SELF_DECLARED,
    forbidden_feature_columns_present,
    proofs_from_feature_row,
    validate_asof_proofs,
)
from src.services.nfl_eval_prep.leaks import (
    apply_strict_week_join,
    flag_l3_defaults,
    leak_fix_diff,
    require_week_cap,
)
from src.services.nfl_eval_prep.local_path import LocalInputPath, LocalPathError, load_local_input_path
from src.services.nfl_eval_prep.splits import (
    CONTAMINATED_EVAL_SEASONS,
    SplitError,
    assert_not_plumbing_week,
    assert_season_in_rebuild_universe,
    assert_train_only,
    build_expanding_window_folds,
)


FEATURE_NAMES = (
    "home_off_epa_5g",
    "away_off_epa_5g",
    "home_def_epa_allowed_5g",
    "away_def_epa_allowed_5g",
    "home_kav_net_5g",
    "away_kav_net_5g",
    "rest_days_home",
    "rest_days_away",
    "home_injury_impact",
    "away_injury_impact",
)

# C-8: non-gate status. Do not treat as PREP_VALIDATED or a CLEAR.
LOCAL_TREE_CHECKED = "LOCAL_TREE_CHECKED"


class LocalTreeCheckError(ValueError):
    """Local tree contract check refused the request."""


@dataclass
class LocalTreeCheckResult:
    status: str
    games_seen: int
    games_kept: int
    excluded: list[dict[str, Any]] = field(default_factory=list)
    l3_flags: list[dict[str, Any]] = field(default_factory=list)
    folds: list[dict[str, Any]] = field(default_factory=list)
    leak_diff: dict[str, Any] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "gate": False,
            "asof_self_declared": ASOF_IS_SELF_DECLARED,
            "games_seen": self.games_seen,
            "games_kept": self.games_kept,
            "excluded": self.excluded,
            "l3_flags": self.l3_flags,
            "folds": self.folds,
            "leak_diff": self.leak_diff,
            "notes": self.notes,
            "simulated": False,
            "graded": False,
            "certified": False,
        }


def _refuse_live_env() -> None:
    if os.environ.get("DATABASE_URL"):
        raise LocalTreeCheckError("local tree check refuses DATABASE_URL (local path only)")
    if os.environ.get("ODDS_API_KEY") or os.environ.get("THE_ODDS_API_KEY"):
        raise LocalTreeCheckError("local tree check refuses odds-api credentials")


def _schedule_index(
    bundle: LocalInputPath,
    *,
    ryan_filed_pre2013: Optional[frozenset[int]] = None,
) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in bundle.schedule_rows:
        gid = str(row.get("game_id") or "")
        if not gid:
            raise LocalTreeCheckError("schedule row missing game_id")
        season = int(row.get("season") or 0)
        week = int(row.get("week") or 0)
        assert_season_in_rebuild_universe(
            season, ryan_filed_pre2013=ryan_filed_pre2013
        )
        if season in CONTAMINATED_EVAL_SEASONS:
            raise LocalTreeCheckError(
                f"local tree check refuses contaminated eval season {season} (game {gid})"
            )
        assert_not_plumbing_week(season=season, week=week or None)
        if season >= 2024:
            raise LocalTreeCheckError(
                f"local tree check refuses season {season}; eval seasons are not runnable"
            )
        out[gid] = row
    return out


def check_local_tree(
    root: str,
    *,
    build_folds: bool = True,
    min_train_seasons: int = 1,
    ryan_filed_pre2013: Optional[frozenset[int]] = None,
) -> LocalTreeCheckResult:
    """Check a local sealed tree. Does not score, fit, or certify."""
    _refuse_live_env()
    try:
        bundle = load_local_input_path(root)
    except LocalPathError as exc:
        raise LocalTreeCheckError(str(exc)) from exc

    try:
        schedule = _schedule_index(
            bundle, ryan_filed_pre2013=ryan_filed_pre2013
        )
    except SplitError as exc:
        raise LocalTreeCheckError(str(exc)) from exc
    excluded: list[dict[str, Any]] = []
    l3_flags: list[dict[str, Any]] = []
    kept_seasons: set[int] = set()
    kept_n = 0

    for row in bundle.feature_rows:
        gid = str(row.get("game_id") or "")
        banned = forbidden_feature_columns_present(row)
        if banned:
            excluded.append(
                {
                    "game_id": gid,
                    "reason": "close_or_score_column_refused_as_feature",
                    "columns": list(banned),
                }
            )
            continue
        if "as_of" in row and not any(f"{name}_as_of" in row for name in FEATURE_NAMES):
            excluded.append(
                {
                    "game_id": gid,
                    "reason": "whole_row_as_of_refused",
                }
            )
            continue
        game = schedule.get(gid)
        if game is None:
            excluded.append({"game_id": gid, "reason": "schedule_miss"})
            continue
        season = int(game["season"])
        week = int(game["week"])
        kickoff = str(game.get("kickoff_utc") or "")
        feature_week = row.get("feature_week")
        if feature_week is None:
            feature_week = row.get("as_of_week")
        if not apply_strict_week_join(game_week=week, feature_week=feature_week):
            excluded.append(
                {
                    "game_id": gid,
                    "reason": "L-1_same_week_or_missing_feature_week",
                    "feature_week": feature_week,
                    "game_week": week,
                }
            )
            continue
        try:
            require_week_cap(int(feature_week), game_week=week)
        except ValueError as exc:
            excluded.append({"game_id": gid, "reason": str(exc)})
            continue
        proofs = proofs_from_feature_row(
            row,
            feature_names=FEATURE_NAMES,
            kickoff_utc=kickoff,
            source_key="source",
        )
        if not proofs:
            excluded.append(
                {
                    "game_id": gid,
                    "reason": "no_named_feature_as_of_proofs",
                }
            )
            continue
        checked = validate_asof_proofs(proofs)
        if checked.excluded:
            excluded.append(
                {
                    "game_id": gid,
                    "reason": "as_of_proof_failed",
                    "violations": [v.to_dict() for v in checked.excluded],
                }
            )
            continue
        for flag in flag_l3_defaults(row, game_id=gid):
            l3_flags.append(flag.to_dict())
        kept_seasons.add(season)
        kept_n += 1

    folds: list[dict[str, Any]] = []
    if build_folds and len(kept_seasons) >= 2:
        try:
            folds = [
                f.to_dict()
                for f in build_expanding_window_folds(
                    sorted(kept_seasons),
                    min_train_seasons=min_train_seasons,
                )
            ]
            for fold in folds:
                assert_train_only(fold["train_seasons"], fold["eval_season"])
        except SplitError as exc:
            raise LocalTreeCheckError(str(exc)) from exc

    return LocalTreeCheckResult(
        status=LOCAL_TREE_CHECKED,
        games_seen=len(bundle.feature_rows),
        games_kept=kept_n,
        excluded=excluded,
        l3_flags=l3_flags,
        folds=folds,
        leak_diff=leak_fix_diff(),
        notes=[
            "LOCAL_TREE_CHECKED is not a gate and is not PREP_VALIDATED.",
            "As-of timestamps are self-declared; this check does not verify "
            "them against an external clock or source capture time.",
            "Close and score columns are refused as features.",
            "Whole-row as-of fallback is refused.",
            "Named archived source (archive:<name>) is required.",
            "Pre-2013 seasons are refused unless a Ryan-filed season list includes them.",
            "No simulation ran.",
            "No grading ran.",
            "No eval season (2024/2025) was opened.",
            "2026 W4–W6 plumbing weeks are refused.",
            "Performer numbers stay REPORTED (LC-5).",
        ],
    )
