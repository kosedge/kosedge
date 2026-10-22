"""S-1 expanding-window walk-forward by season. Train-only fitting (LC-3).

Fold k trains on seasons <= Y_k-1 and evaluates season Y_k. Within-season
week-forward refits are NOT registered here and are refused.

2024–2025 are CONTAMINATED (78f5ee7e) and cannot be eval folds.
2026 W4–W6 are RETROSPECTIVE plumbing only and are never in either set.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable, Optional, Sequence


CONTAMINATED_EVAL_SEASONS = frozenset({2024, 2025})
FROZEN_PLUMBING_WEEKS_2026 = frozenset({4, 5, 6})
DIAGNOSTIC_SEASONS_DEFAULT = tuple(range(2013, 2024))  # 2013–2023 inclusive


class SplitError(ValueError):
    """Illegal split, eval season, or train/eval overlap."""


@dataclass(frozen=True)
class ExpandingWindowFold:
    fold_id: str
    train_seasons: tuple[int, ...]
    eval_season: int
    role: str = "G3_DIAGNOSTIC"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def assert_not_plumbing_week(*, season: int, week: Optional[int] = None) -> None:
    if int(season) == 2026 and week is not None and int(week) in FROZEN_PLUMBING_WEEKS_2026:
        raise SplitError(
            "2026 W4–W6 are frozen plumbing (78f5ee7e C-5) and are never in a predictive set"
        )


def assert_train_only(
    train_seasons: Sequence[int],
    eval_season: int,
    *,
    week: Optional[int] = None,
) -> None:
    """LC-3: no eval-season information in train. No contaminated eval."""
    if not train_seasons:
        raise SplitError("train_seasons is empty")
    ev = int(eval_season)
    assert_not_plumbing_week(season=ev, week=week)
    if ev in CONTAMINATED_EVAL_SEASONS:
        raise SplitError(
            f"season {ev} is CONTAMINATED and cannot be an evaluation fold (78f5ee7e)"
        )
    if ev >= 2026:
        raise SplitError(
            f"season {ev} is not a registered G3 diagnostic eval season in this prep harness"
        )
    trains = tuple(int(s) for s in train_seasons)
    if ev in trains:
        raise SplitError(f"eval season {ev} appears in train_seasons={trains}")
    if max(trains) >= ev:
        raise SplitError(
            f"train-only violation: max(train_seasons)={max(trains)} is not < eval_season={ev}"
        )
    if any(s > ev for s in trains):
        raise SplitError("future season in train")


def build_expanding_window_folds(
    seasons: Sequence[int] = DIAGNOSTIC_SEASONS_DEFAULT,
    *,
    min_train_seasons: int = 1,
    allow_contaminated_eval: bool = False,
) -> list[ExpandingWindowFold]:
    """S-1. ``allow_contaminated_eval`` is locked False; the flag exists to fail closed."""
    if allow_contaminated_eval:
        raise SplitError("contaminated eval folds are forbidden in this harness")
    ordered = tuple(sorted({int(s) for s in seasons}))
    if not ordered:
        raise SplitError("no seasons")
    blocked = [s for s in ordered if s in CONTAMINATED_EVAL_SEASONS or s >= 2026]
    if blocked:
        raise SplitError(f"blocked seasons in split universe: {blocked}")
    folds: list[ExpandingWindowFold] = []
    for idx in range(min_train_seasons, len(ordered)):
        train = ordered[:idx]
        ev = ordered[idx]
        assert_train_only(train, ev)
        folds.append(
            ExpandingWindowFold(
                fold_id=f"expanding-{train[0]}-{train[-1]}-eval-{ev}",
                train_seasons=train,
                eval_season=ev,
                role="G3_DIAGNOSTIC",
            )
        )
    return folds


def assert_no_eval_season_in_fit_rows(
    rows: Iterable[dict[str, Any]],
    *,
    eval_season: int,
    season_key: str = "season",
) -> None:
    leaked = [row for row in rows if int(row.get(season_key) or 0) == int(eval_season)]
    if leaked:
        raise SplitError(
            f"LC-3: {len(leaked)} fit rows carry eval_season={eval_season}"
        )
