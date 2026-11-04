"""Season-stratified pooled game-weighted week bootstrap. CERT=0.

Golden: week means [-9] (n=1) and [+1] (n=9) → pooled 0, not unweighted -4.
Two resampled blocks → means -9, 0, 0, 1.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping, Sequence

from src.services.nfl_r7_record_date_retro_c1.pins import BOOTSTRAP_B, BOOTSTRAP_GEN, BOOTSTRAP_SEED
from src.services.nfl_r7_record_date_retro_c1.refuse import RetroRefuse

GOLDEN_WEEK_A = {"signed": -9.0, "n_games": 1}
GOLDEN_WEEK_B = {"signed": 1.0, "n_games": 9}
GOLDEN_POOLED = 0.0
GOLDEN_UNWEIGHTED = -4.0
GOLDEN_TWO_BLOCK_MEANS = (-9.0, 0.0, 0.0, 1.0)


def unweighted_week_mean(weeks: Sequence[Mapping[str, Any]]) -> float:
    if not weeks:
        raise RetroRefuse("no weeks")
    return sum(float(row["signed"]) for row in weeks) / float(len(weeks))


def pooled_game_weighted(weeks: Sequence[Mapping[str, Any]]) -> float:
    num = 0.0
    den = 0
    for row in weeks:
        n = int(row["n_games"])
        if n < 1:
            raise RetroRefuse("week n_games < 1")
        num += float(row["signed"]) * n
        den += n
    if den < 1:
        raise RetroRefuse("pooled denominator < 1")
    return num / float(den)


def two_block_means(week_a: Mapping[str, Any], week_b: Mapping[str, Any]) -> tuple[float, float, float, float]:
    aa = pooled_game_weighted([week_a, week_a])
    ab = pooled_game_weighted([week_a, week_b])
    ba = pooled_game_weighted([week_b, week_a])
    bb = pooled_game_weighted([week_b, week_b])
    return (aa, ab, ba, bb)


def assert_golden_two_block() -> dict[str, Any]:
    weeks = (GOLDEN_WEEK_A, GOLDEN_WEEK_B)
    unweighted = unweighted_week_mean(weeks)
    pooled = pooled_game_weighted(weeks)
    means = two_block_means(GOLDEN_WEEK_A, GOLDEN_WEEK_B)
    if abs(unweighted - GOLDEN_UNWEIGHTED) > 1e-12:
        raise RetroRefuse(f"golden unweighted {unweighted} != {GOLDEN_UNWEIGHTED}")
    if abs(pooled - GOLDEN_POOLED) > 1e-12:
        raise RetroRefuse(f"golden pooled {pooled} != 0 (got unweighted-like?)")
    if means != GOLDEN_TWO_BLOCK_MEANS:
        raise RetroRefuse(f"golden two-block means {means} != {GOLDEN_TWO_BLOCK_MEANS}")
    return {
        "unweighted": unweighted,
        "pooled": pooled,
        "two_block_means": list(means),
        "ok": True,
    }


def week_blocks_from_rows(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[int, int], list[float]] = {}
    for row in rows:
        key = (int(row["season"]), int(row["week"]))
        grouped.setdefault(key, []).append(float(row["signed_c_minus_y"]))
    blocks = []
    for (season, week), signed in sorted(grouped.items()):
        blocks.append(
            {
                "season": season,
                "week": week,
                "n_games": len(signed),
                "signed": sum(signed) / float(len(signed)),
            }
        )
    return blocks


def season_stratified_pooled_bootstrap(
    rows: Sequence[Mapping[str, Any]],
    *,
    B: int = BOOTSTRAP_B,
    seed: int = BOOTSTRAP_SEED,
) -> dict[str, Any]:
    """Resample week-blocks within season; pool game-weighted. Real computation."""
    import numpy as np

    blocks = week_blocks_from_rows(rows)
    if not blocks:
        raise RetroRefuse("bootstrap has no week blocks")
    by_season: dict[int, list[dict[str, Any]]] = {}
    for block in blocks:
        by_season.setdefault(int(block["season"]), []).append(block)
    rng = np.random.Generator(np.random.PCG64(int(seed)))
    draws: list[float] = []
    for _ in range(int(B)):
        resampled: list[dict[str, Any]] = []
        for season_blocks in by_season.values():
            idx = rng.integers(0, len(season_blocks), size=len(season_blocks))
            resampled.extend(season_blocks[int(i)] for i in idx)
        draws.append(pooled_game_weighted(resampled))
    arr = np.asarray(draws, dtype=float)
    return {
        "B": int(B),
        "seed": int(seed),
        "gen": BOOTSTRAP_GEN,
        "n_weeks": len(blocks),
        "mean": float(arr.mean()),
        "p05": float(np.quantile(arr, 0.05)),
        "p95": float(np.quantile(arr, 0.95)),
        "observed_pooled": pooled_game_weighted(blocks),
        "observed_unweighted": unweighted_week_mean(blocks),
        "run": True,
        "scientific_claim": False,
    }
