"""Runner v2 (803ceb4e prep bytes). Local path only. No eval seasons.

This runner validates as-of proofs, applies L-1/L-2/L-3 contracts, and
builds an expanding-window plan. It does not simulate games, fit models
on real seasons, fetch odds, or open a database.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

from src.services.nfl_eval_prep.asof import (
    AsOfProof,
    validate_asof_proofs,
    proofs_from_feature_row,
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


class RunnerV2Error(ValueError):
    """Runner v2 refused the request."""


@dataclass
class RunnerV2Result:
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
        raise RunnerV2Error("runner v2 refuses DATABASE_URL (local path only)")
    if os.environ.get("ODDS_API_KEY") or os.environ.get("THE_ODDS_API_KEY"):
        raise RunnerV2Error("runner v2 refuses odds-api credentials")


def _schedule_index(bundle: LocalInputPath) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in bundle.schedule_rows:
        gid = str(row.get("game_id") or "")
        if not gid:
            raise RunnerV2Error("schedule row missing game_id")
        season = int(row.get("season") or 0)
        week = int(row.get("week") or 0)
        if season in CONTAMINATED_EVAL_SEASONS:
            raise RunnerV2Error(
                f"runner v2 refuses contaminated eval season {season} (game {gid})"
            )
        assert_not_plumbing_week(season=season, week=week or None)
        if season >= 2024:
            raise RunnerV2Error(
                f"runner v2 refuses season {season}; eval seasons are not runnable"
            )
        out[gid] = row
    return out


def run_local_rebuild(
    root: str,
    *,
    build_folds: bool = True,
    min_train_seasons: int = 1,
) -> RunnerV2Result:
    """Validate a local sealed tree. Does not score or fit on eval seasons."""
    _refuse_live_env()
    try:
        bundle = load_local_input_path(root)
    except LocalPathError as exc:
        raise RunnerV2Error(str(exc)) from exc

    try:
        schedule = _schedule_index(bundle)
    except SplitError as exc:
        raise RunnerV2Error(str(exc)) from exc
    excluded: list[dict[str, Any]] = []
    l3_flags: list[dict[str, Any]] = []
    kept_seasons: set[int] = set()
    kept_n = 0

    for row in bundle.feature_rows:
        gid = str(row.get("game_id") or "")
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
            as_of_key="as_of",
            source_key="source",
        )
        if not proofs:
            proofs = [
                AsOfProof(
                    game_id=gid,
                    feature_name="row",
                    as_of=str(row.get("as_of") or ""),
                    kickoff_utc=kickoff,
                    source=str(row.get("source") or ""),
                )
            ]
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
            raise RunnerV2Error(str(exc)) from exc

    return RunnerV2Result(
        status="PREP_VALIDATED",
        games_seen=len(bundle.feature_rows),
        games_kept=kept_n,
        excluded=excluded,
        l3_flags=l3_flags,
        folds=folds,
        leak_diff=leak_fix_diff(),
        notes=[
            "No simulation ran.",
            "No grading ran.",
            "No eval season (2024/2025) was opened.",
            "2026 W4–W6 plumbing weeks are refused.",
            "Performer numbers stay REPORTED (LC-5).",
        ],
    )
