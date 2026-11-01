"""Prove the 70 2017 targets were excluded from fitting a_q2 / b_q2."""

from __future__ import annotations

from typing import Any, Iterable, Mapping, Sequence

from q2pb.constants import DEV_SEASONS, DEV_WEEKS, HISTORY_ONLY_SEASONS

SEALED_FIT_SHA = "70db070dad3fcdb4d4ff165ba09b7840c173c232a71c8fcd670ba9c3c0bc5571"
SEALED_N_FIT = 960
TARGET_SEASON = 2017


class CoverageRefuse(RuntimeError):
    """Incomplete coverage or unproven fit exclusion — no synthetic fallback."""


def prove_fit_exclusion(
    targets: Sequence[Mapping[str, Any]],
    frozen: Mapping[str, Any],
    *,
    history_game_ids_dev: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Fail-closed proof that a_q2/b_q2 (70db070d) did not see these games.

    Evidence (all required):
    1. Frozen fit object sha == 70db070d… and n_fit == 960.
    2. Frozen season_end_ratings keys are DEV seasons only (≤ 2016).
    3. Keep constants: DEV_SEASONS = 2013–16; HISTORY_ONLY = (2017,).
    4. Every target is season 2017 (HISTORY_ONLY; never fit / never EVAL).
    5. Optional: no target game_id appears in the DEV window id set.
    """
    blockers: list[str] = []
    fit_sha = str(frozen.get("fit_object_sha256") or "")
    if fit_sha != SEALED_FIT_SHA:
        blockers.append(f"fit_object_sha256 {fit_sha[:8]} != 70db070d")
    try:
        n_fit = int(frozen.get("n_fit"))
    except (TypeError, ValueError):
        n_fit = -1
    if n_fit != SEALED_N_FIT:
        blockers.append(f"n_fit {n_fit} != sealed 960")

    raw_priors = frozen.get("season_end_ratings") or {}
    prior_seasons = sorted(int(k) for k in raw_priors)
    if any(s >= TARGET_SEASON for s in prior_seasons):
        blockers.append(f"season_end_ratings includes {prior_seasons} (≥2017)")
    if tuple(prior_seasons) != tuple(DEV_SEASONS):
        blockers.append(f"season_end_ratings seasons {prior_seasons} != DEV {DEV_SEASONS}")

    if HISTORY_ONLY_SEASONS != (TARGET_SEASON,):
        blockers.append(f"HISTORY_ONLY_SEASONS {HISTORY_ONLY_SEASONS} != (2017,)")
    if DEV_SEASONS != (2013, 2014, 2015, 2016):
        blockers.append(f"DEV_SEASONS {DEV_SEASONS} != 2013–16")

    seasons = {int(t["season"]) for t in targets}
    if seasons != {TARGET_SEASON}:
        blockers.append(f"targets seasons {sorted(seasons)} != {{2017}}")

    leaked: list[str] = []
    if history_game_ids_dev is not None:
        dev_ids = set(history_game_ids_dev)
        leaked = [str(t["game_id"]) for t in targets if t["game_id"] in dev_ids]
        if leaked:
            blockers.append(f"{len(leaked)} target game_ids appear in DEV window")

    if blockers:
        raise CoverageRefuse("fit exclusion unproven: " + "; ".join(blockers))

    return {
        "ok": True,
        "fit_sha": fit_sha,
        "n_fit": n_fit,
        "dev_seasons": list(DEV_SEASONS),
        "dev_weeks": list(DEV_WEEKS),
        "history_only_seasons": list(HISTORY_ONLY_SEASONS),
        "season_end_ratings_seasons": prior_seasons,
        "n_targets": len(targets),
        "target_season": TARGET_SEASON,
        "n_leaked_into_dev_ids": 0,
        "note": (
            "2017 is HISTORY_ONLY in the keep packet: as-of carry into 2018; "
            "never fit / never EVAL-scored. a_q2/b_q2 are DEV 2013–16 REG W2–17 OLS "
            f"(n_fit={SEALED_N_FIT}) on fit object 70db070d."
        ),
        "label": "RETRO_FIT / DEV_RESEARCH",
    }
