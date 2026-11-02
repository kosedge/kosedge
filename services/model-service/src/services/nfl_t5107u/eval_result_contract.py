"""t5151u numerical output contract — strengthen #693 beyond presence.

Reuses #693 ``eval_result_contract`` keys and #698/#693 metric helpers.
Presence is not enough: recorded numerics must be finite, internally
consistent, and recomputable from the SAME saved per-game rows.

Never mutates recorded values to obtain PASS.
Does not change performance thresholds or scientific criteria.
Does not independently rerun bootstrap intervals (metadata/point check only).
Does not run real EVAL. CERT=0. DRAFT≠merge.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from typing import Any, Mapping, Sequence

from .evaluator import BOOT_B, BOOT_SEED, mean_stat, paired_bias, paired_mae, paired_rmse
from .last_played_cohort import EXPECTED_REG, EXPECTED_REG_TOTAL
from .metric_cohorts import WILDCARD_2020_W18
from .recon_contract import CONTRACT_27, _finite

SCHEMA = "nfl-t5151u-eval-result-contract-v2"
SCHEMA_V1 = "nfl-t5129u-eval-result-contract-v1"
TICKET = "t5151u"
PACKAGE = "B_NUMERICAL_OUTPUT_CONTRACT"
CERT_CANDIDATE = 0
OWNER_CLEAR_SHA8 = "d6aa1ef5"
COS_ORDER_B_SHA8 = "d821fe61"
COS_ACCEPT_SCOPED_SHA8 = "96908853"
OWNER_AMEND_SHA8 = "cd253f7a"
COS_ORDER_RETURN_SHA8 = "42b6e832"
ALEX_RETURN_SHA8 = "7057e5a9"
ALEX_RETURN_ACCEPTED_SHA8 = "ee23cc57"
PACKAGE_A_TIP = "42ff285cc1be2459512af4761651ba6dfe17dc75"
PACKAGE_A_STAMP = "f7ec09ee2ffcce7b130c9b858304bbe8006a4428"
R4_496_ACCEPTED_TIP = "bc1b62fc13a1c16ba1e39ccce39fb60180dc565e"
ALEX_PASS_RO = "274cf246"
PARTIAL_PLUMBING_TIP = "ac35ed55a8aa1d11ecf742b9280e5483ebe95bfc"
PARTIAL_PLUMBING_STAMP = "bad2049446168f009b54b89f45d522fc803a4d7f"
DEV437_RESULT_PATH = (
    "data/ops/nfl-forecast-builder-t5107u/DEV_RESEARCH_t5125u_R2B2_437.json"
)
DEV437_RESULT_SHA256 = (
    "66c3bde18fd6b1a4766f1001403deb68b9f625ccd00372f280f187ef95a54e50"
)
DEV437_RECORD_SHA256 = (
    "0550ef9b498a2240919d8cf570ccb7c94b67f6815ba3625789901f8390143637"
)
MARKET72_RESULT_PATH = (
    "data/ops/nfl-forecast-builder-t5107u/DEV_RESEARCH_t5137u_MATCHED72.json"
)
MARKET72_RESULT_SHA256 = (
    "88d63eb7f6b09e967fcf60122f525c2873072aaada93bb0dab3d8c3ff17fd9ea"
)
MARKET72_RECORD_SHA256 = (
    "72a1f1f9ad1befa95b0cdb10588935da1e39fb857b06ee4f9a5778b1af1c3437"
)
MARKET72_SOURCE_TIP = "316345fae6631fe2d357e34de0417f7a57916e3f"

PROFILE_FEATURE_RECON_REG496 = "FEATURE_RECON_REG496"
PROFILE_DEV_IF437 = "DEV_IF437"
PROFILE_DEV_MARKET72 = "DEV_MARKET72"
PROFILES = (
    PROFILE_FEATURE_RECON_REG496,
    PROFILE_DEV_IF437,
    PROFILE_DEV_MARKET72,
)

REG496_N = EXPECTED_REG_TOTAL
REG496_BY_SEASON = {str(k): v for k, v in EXPECTED_REG.items()}
DEV_IF437_N = 437
DEV_IF437_BY_SEASON = {"2020": 210, "2021": 227}
DEV_MARKET72_N = 72
DEV_MARKET72_BY_SEASON = {"2020": 35, "2021": 37}
REG_W18_2021_N = 16

REL_TOL_SCALE = 1e-9
INTERVAL_CONTRACT = {
    "B": BOOT_B,
    "seed": BOOT_SEED,
    "level": 0.95,
    "statistic": "MEAN signed paired absolute-loss difference",
    "rerun_intervals": False,
}

MARKET_UNAVAILABLE_STATUSES = frozenset(
    {"UNAVAILABLE", "NOT_READY", "MARKET_UNAVAILABLE", "IF_ONLY"}
)

EVAL_RESULT_CONTRACT_KEYS = (
    "n",
    "n_by_season",
    "mae_challenger",
    "mae_if",
    "mae_market",
    "rmse_challenger",
    "rmse_if",
    "rmse_market",
    "bias_challenger",
    "bias_if",
    "bias_market",
    "delta_mae_vs_if",
    "delta_mae_vs_market",
    "mean_signed_diff_vs_if",
    "mean_signed_diff_vs_market",
    "per_season",
    "bootstrap_game",
    "bootstrap_season_week",
    "bootstrap_game_vs_market",
    "bootstrap_season_week_vs_market",
)

PER_SEASON_CONTRACT_KEYS = (
    "n",
    "mae_challenger",
    "mae_if",
    "mae_market",
    "rmse_challenger",
    "rmse_if",
    "rmse_market",
    "bias_challenger",
    "bias_if",
    "bias_market",
    "mean_signed_diff_vs_if",
    "mean_signed_diff_vs_market",
)

BOOTSTRAP_KEYS = (
    "bootstrap_game",
    "bootstrap_season_week",
    "bootstrap_game_vs_market",
    "bootstrap_season_week_vs_market",
)

BOOTSTRAP_LABELS = {
    "bootstrap_game": {"unit": "game", "control": "if"},
    "bootstrap_season_week": {"unit": "season_week", "control": "if"},
    "bootstrap_game_vs_market": {"unit": "game", "control": "market"},
    "bootstrap_season_week_vs_market": {"unit": "season_week", "control": "market"},
}

IF_ONLY_REQUIRED = (
    "n",
    "n_by_season",
    "mae_challenger",
    "mae_if",
    "rmse_challenger",
    "rmse_if",
    "bias_challenger",
    "bias_if",
    "delta_mae_vs_if",
    "mean_signed_diff_vs_if",
    "per_season",
    "bootstrap_game",
    "bootstrap_season_week",
    "market_unavailable",
    "market_status",
)

INVENTED_RECON_METRIC_KEYS = (
    "mae",
    "mae_challenger",
    "mae_if",
    "mae_market",
    "rmse",
    "rmse_challenger",
    "rmse_if",
    "rmse_market",
    "bias",
    "bias_challenger",
    "bias_if",
    "bias_market",
    "delta_mae",
    "delta_mae_vs_if",
    "delta_mae_vs_market",
    "mean_signed_diff_vs_if",
    "mean_signed_diff_vs_market",
    "actual_margin",
    "actual_total",
    "home_score",
    "away_score",
    "error",
    "abs_error",
    "m_if",
    "m_challenger",
    "m_market",
    "market",
    "quote",
    "spread",
    "total",
    "bootstrap_game",
    "bootstrap_season_week",
)

RECON_IDENTITY_LINEAGE_KEYS = (
    "t1_home",
    "t1_away",
    "consumed_game_ids_home",
    "consumed_game_ids_away",
    "selected_rating_week_home",
    "selected_rating_week_away",
    "source_path",
    "source_sha256",
    "derivation_lineage",
)

RECON_IDENTITY_REQUIRED = (
    "game_id",
    "season",
    "week",
    "home",
    "away",
    "t1_home",
    "t1_away",
    "consumed_game_ids_home",
    "consumed_game_ids_away",
    "selected_rating_week_home",
    "selected_rating_week_away",
    "derived",
    "missing",
    "publication_timestamp_status",
    "observation_timestamp_status",
    "production_causal_claim",
    "labels",
)


class EvalResultContractRefuse(ValueError):
    """Numerical output contract failed. Not a retune. Not EXEC. Not EVAL."""


def _present(value: Any) -> bool:
    return value is not None


def require_finite(value: Any, name: str) -> float:
    if value is None:
        raise EvalResultContractRefuse(f"{name} is null — refuse")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise EvalResultContractRefuse(f"{name} is not numeric — refuse")
    number = float(value)
    if math.isnan(number):
        raise EvalResultContractRefuse(f"{name} is NaN — refuse")
    if not math.isfinite(number):
        raise EvalResultContractRefuse(f"{name} is not finite — refuse")
    return number


def recorded_agrees(recorded: Any, achieved: float, name: str) -> None:
    """Compare recorded vs recomputed. Never rewrite recorded to pass."""
    got = require_finite(recorded, name)
    scale = max(1.0, abs(float(achieved)))
    if abs(got - float(achieved)) > REL_TOL_SCALE * scale:
        raise EvalResultContractRefuse(
            f"{name} inconsistent with saved rows: recorded={got} achieved={achieved}"
        )


def _n_by_season_from_ids(game_ids: Sequence[str]) -> dict[str, int]:
    counts = Counter(str(gid).split("_", 1)[0] for gid in game_ids)
    return dict(sorted(counts.items()))


def _as_ids(values: Sequence[Any] | None) -> list[str]:
    return [str(v) for v in (values or [])]


def _float_or_none(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number) or not math.isfinite(number):
        return None
    return number


def _row_error(row: Mapping[str, Any], arm: str) -> float:
    err_key = f"err_{arm}"
    if err_key in row and row[err_key] is not None:
        err = require_finite(row[err_key], f"games[].{err_key}")
        actual = row.get("actual_margin")
        pred = row.get(f"m_{arm}")
        if actual is not None and pred is not None:
            derived = require_finite(pred, f"games[].m_{arm}") - require_finite(
                actual, "games[].actual_margin"
            )
            recorded_agrees(err, derived, f"games[].{err_key}")
        return err
    actual = row.get("actual_margin")
    pred = row.get(f"m_{arm}")
    if actual is None or pred is None:
        raise EvalResultContractRefuse(f"games[] missing {err_key} and m_{arm}/actual_margin")
    return require_finite(pred, f"games[].m_{arm}") - require_finite(
        actual, "games[].actual_margin"
    )


def _row_abs_loss(row: Mapping[str, Any], arm: str) -> float:
    loss_key = f"L_{arm}"
    err = _row_error(row, arm)
    achieved = abs(err)
    if loss_key in row and row[loss_key] is not None:
        recorded_agrees(row[loss_key], achieved, f"games[].{loss_key}")
        return require_finite(row[loss_key], f"games[].{loss_key}")
    return achieved


def _row_signed_diff(row: Mapping[str, Any], control: str) -> float:
    key = f"signed_diff_vs_{control}"
    achieved = _row_abs_loss(row, "challenger") - _row_abs_loss(row, control)
    if key in row and row[key] is not None:
        recorded_agrees(row[key], achieved, f"games[].{key}")
        return require_finite(row[key], f"games[].{key}")
    return achieved


def saved_game_rows(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    games = payload.get("games")
    if not isinstance(games, Sequence) or not games:
        raise EvalResultContractRefuse("saved per-game rows required for numerical consistency")
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for idx, row in enumerate(games):
        if not isinstance(row, Mapping):
            raise EvalResultContractRefuse(f"games[{idx}] is not a mapping")
        gid = str(row.get("game_id") or "")
        if not gid:
            raise EvalResultContractRefuse(f"games[{idx}] missing game_id")
        if gid in seen:
            raise EvalResultContractRefuse(f"duplicate saved game_id {gid}")
        seen.add(gid)
        season = row.get("season")
        if season is None:
            try:
                season = int(gid.split("_", 1)[0])
            except (TypeError, ValueError) as exc:
                raise EvalResultContractRefuse(f"games[{gid}] missing season") from exc
        week = row.get("week")
        if week is None:
            parts = gid.split("_")
            week = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else None
        if week is None:
            raise EvalResultContractRefuse(f"games[{gid}] missing week")
        item = dict(row)
        item["game_id"] = gid
        item["season"] = int(season)
        item["week"] = int(week)
        item["season_week"] = str(row.get("season_week") or f"{int(season)}-{int(week):02d}")
        out.append(item)
    return out


def recompute_from_saved_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    require_market: bool,
) -> dict[str, Any]:
    """Recompute achieved statistics from saved rows. Does not rewrite payload."""
    if not rows:
        raise EvalResultContractRefuse("cannot recompute from empty saved rows")
    err_c = [_row_error(row, "challenger") for row in rows]
    err_if = [_row_error(row, "if") for row in rows]
    diffs_if = [_row_signed_diff(row, "if") for row in rows]
    ids = [str(row["game_id"]) for row in rows]
    seasons = [int(row["season"]) for row in rows]
    n_by = dict(sorted(Counter(str(s) for s in seasons).items()))
    achieved: dict[str, Any] = {
        "n": len(rows),
        "game_ids": ids,
        "n_by_season": n_by,
        "mae_challenger": paired_mae(err_c),
        "mae_if": paired_mae(err_if),
        "rmse_challenger": paired_rmse(err_c),
        "rmse_if": paired_rmse(err_if),
        "bias_challenger": paired_bias(err_c),
        "bias_if": paired_bias(err_if),
        "delta_mae_vs_if": paired_mae(err_c) - paired_mae(err_if),
        "mean_signed_diff_vs_if": mean_stat(diffs_if),
    }
    if require_market:
        missing = [str(row["game_id"]) for row in rows if not _has_market_fields(row)]
        if missing:
            raise EvalResultContractRefuse(
                f"missing candidate-vs-market fields for {len(missing)} saved rows "
                f"(e.g. {missing[:4]})"
            )
        err_m = [_row_error(row, "market") for row in rows]
        diffs_m = [_row_signed_diff(row, "market") for row in rows]
        achieved.update(
            {
                "mae_market": paired_mae(err_m),
                "rmse_market": paired_rmse(err_m),
                "bias_market": paired_bias(err_m),
                "delta_mae_vs_market": paired_mae(err_c) - paired_mae(err_m),
                "mean_signed_diff_vs_market": mean_stat(diffs_m),
            }
        )
    return achieved


def _has_market_fields(row: Mapping[str, Any]) -> bool:
    if row.get("m_market") is not None or row.get("err_market") is not None:
        return True
    if row.get("signed_diff_vs_market") is not None:
        return True
    return False


def _check_bootstrap_metadata(
    name: str,
    body: Any,
    *,
    expected_point: float | None,
    expected_n: int | None,
) -> None:
    """Validate declared interval contract. Does not rerun bootstrap."""
    if not isinstance(body, Mapping):
        raise EvalResultContractRefuse(f"{name} missing from result")
    labels = BOOTSTRAP_LABELS[name]
    unit = body.get("unit") or body.get("cluster") or body.get("label_unit")
    control = body.get("control") or body.get("vs") or body.get("label_control")
    if unit not in (None, labels["unit"]) and str(unit) != labels["unit"]:
        raise EvalResultContractRefuse(f"{name} mislabeled unit={unit!r}")
    if control not in (None, labels["control"]) and str(control) != labels["control"]:
        raise EvalResultContractRefuse(f"{name} mislabeled control={control!r}")
    if name.endswith("_vs_market") and "market" not in name:
        raise EvalResultContractRefuse(f"{name} market interval mislabeled")
    ci = body.get("ci95")
    if not isinstance(ci, (list, tuple)) or len(ci) != 2:
        raise EvalResultContractRefuse(f"{name} requires ci95 [lo, hi]")
    lo = require_finite(ci[0], f"{name}.ci95[0]")
    hi = require_finite(ci[1], f"{name}.ci95[1]")
    if lo > hi:
        raise EvalResultContractRefuse(f"{name} ci95 not ordered: {lo} > {hi}")
    if body.get("B") != INTERVAL_CONTRACT["B"]:
        raise EvalResultContractRefuse(
            f"{name} bootstrap B is frozen at {INTERVAL_CONTRACT['B']}"
        )
    if body.get("seed") != INTERVAL_CONTRACT["seed"]:
        raise EvalResultContractRefuse(
            f"{name} bootstrap seed is frozen at {INTERVAL_CONTRACT['seed']}"
        )
    if "point" not in body:
        raise EvalResultContractRefuse(f"{name} requires point (MEAN signed paired loss diff)")
    point = require_finite(body.get("point"), f"{name}.point")
    if expected_point is not None:
        recorded_agrees(point, expected_point, f"{name}.point")
    if expected_n is not None and body.get("n") not in (None, expected_n):
        raise EvalResultContractRefuse(f"{name}.n={body.get('n')} != saved n={expected_n}")


def _check_count_agreement(
    payload: Mapping[str, Any],
    achieved: Mapping[str, Any],
    *,
    expected_n: int | None,
    expected_by_season: Mapping[str, int] | None,
    expected_ids: Sequence[str] | None,
) -> None:
    recorded_n = payload.get("n")
    if recorded_n != achieved["n"]:
        raise EvalResultContractRefuse(
            f"inconsistent counts: recorded n={recorded_n} saved_rows={achieved['n']}"
        )
    if expected_n is not None and achieved["n"] != expected_n:
        raise EvalResultContractRefuse(f"n={achieved['n']} != profile expected {expected_n}")
    n_by = payload.get("n_by_season")
    if not isinstance(n_by, Mapping) or not n_by:
        raise EvalResultContractRefuse("n_by_season required")
    achieved_by = {str(k): int(v) for k, v in achieved["n_by_season"].items()}
    recorded_by = {str(k): int(v) for k, v in n_by.items()}
    if recorded_by != achieved_by:
        raise EvalResultContractRefuse(
            f"n_by_season inconsistent with saved rows: {recorded_by} != {achieved_by}"
        )
    if sum(recorded_by.values()) != achieved["n"]:
        raise EvalResultContractRefuse("n_by_season sum != n")
    if expected_by_season is not None and recorded_by != dict(expected_by_season):
        raise EvalResultContractRefuse(
            f"n_by_season {recorded_by} != profile {dict(expected_by_season)}"
        )
    recorded_ids = _as_ids(payload.get("game_ids") or achieved["game_ids"])
    if set(recorded_ids) != set(achieved["game_ids"]):
        raise EvalResultContractRefuse("cohort IDs disagree between payload and saved rows")
    if expected_ids is not None and set(recorded_ids) != set(_as_ids(expected_ids)):
        raise EvalResultContractRefuse("cohort IDs disagree with declared profile IDs")
    cohort = payload.get("cohort_id") or payload.get("cohort_sha256")
    declared = payload.get("declared_cohort_id") or payload.get("declared_cohort_sha256")
    if cohort is not None and declared is not None and str(cohort) != str(declared):
        raise EvalResultContractRefuse("cohort IDs disagree (declared vs recorded)")


def _check_recorded_vs_achieved(
    payload: Mapping[str, Any],
    achieved: Mapping[str, Any],
    keys: Sequence[str],
) -> None:
    for key in keys:
        if key not in achieved:
            continue
        recorded_agrees(payload.get(key), float(achieved[key]), key)


def _per_season_tables(
    payload: Mapping[str, Any],
    rows: Sequence[Mapping[str, Any]],
    *,
    require_market: bool,
    expected_by_season: Mapping[str, int] | None,
) -> None:
    seasons = payload.get("per_season")
    if not isinstance(seasons, Mapping) or not seasons:
        raise EvalResultContractRefuse("per-season tables required")
    grouped: dict[str, list[Mapping[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(str(row["season"]), []).append(row)
    if set(map(str, seasons)) != set(grouped):
        raise EvalResultContractRefuse(
            f"per_season keys {sorted(map(str, seasons))} != saved seasons {sorted(grouped)}"
        )
    for season, table in seasons.items():
        if not isinstance(table, Mapping):
            raise EvalResultContractRefuse(f"per_season[{season}] is not a table")
        required = PER_SEASON_CONTRACT_KEYS if require_market else (
            "n",
            "mae_challenger",
            "mae_if",
            "rmse_challenger",
            "rmse_if",
            "bias_challenger",
            "bias_if",
            "mean_signed_diff_vs_if",
        )
        gap = [k for k in required if k not in table]
        if gap:
            raise EvalResultContractRefuse(f"per_season[{season}] missing fields: {gap}")
        achieved = recompute_from_saved_rows(grouped[str(season)], require_market=require_market)
        if table.get("n") != achieved["n"]:
            raise EvalResultContractRefuse(
                f"per_season[{season}].n={table.get('n')} != saved {achieved['n']}"
            )
        if expected_by_season is not None and achieved["n"] != int(expected_by_season[str(season)]):
            raise EvalResultContractRefuse(
                f"per_season[{season}] n={achieved['n']} != profile {expected_by_season[str(season)]}"
            )
        keys = (
            "mae_challenger",
            "mae_if",
            "rmse_challenger",
            "rmse_if",
            "bias_challenger",
            "bias_if",
            "mean_signed_diff_vs_if",
        )
        if require_market:
            keys = keys + (
                "mae_market",
                "rmse_market",
                "bias_market",
                "mean_signed_diff_vs_market",
            )
        _check_recorded_vs_achieved(table, achieved, keys)
        for key in keys:
            require_finite(table.get(key), f"per_season[{season}].{key}")


def market_is_unavailable(payload: Mapping[str, Any]) -> bool:
    if payload.get("market_unavailable") is True:
        return True
    market = payload.get("market")
    if isinstance(market, Mapping):
        status = str(market.get("status") or "").upper()
        if status in MARKET_UNAVAILABLE_STATUSES:
            return True
    status = str(payload.get("market_status") or "").upper()
    return status in MARKET_UNAVAILABLE_STATUSES


def refuse_synthetic_flag(payload: Mapping[str, Any], *, label: str) -> None:
    if payload.get("synthetic") is True:
        raise EvalResultContractRefuse(
            f"{label}: synthetic=true refused — fixtures are test-helper only"
        )


def validate_eval_result_contract(scored: Mapping[str, Any]) -> None:
    """Require vs-IF **and** vs-market. DEV437 / IF-only does not pass.

    Strengthened: presence plus finite/consistency when saved rows exist.
    """
    if not isinstance(scored, Mapping):
        raise EvalResultContractRefuse("EVAL result is not a mapping")
    if market_is_unavailable(scored) or scored.get("mae_market") is None:
        raise EvalResultContractRefuse(
            "IF-only / market unavailable cannot satisfy the EVAL market contract"
        )
    missing = [k for k in EVAL_RESULT_CONTRACT_KEYS if k not in scored]
    if missing:
        raise EvalResultContractRefuse(
            f"EVAL result contract incomplete (need IF and market): {missing}"
        )
    for key in (
        "mae_if",
        "mae_market",
        "rmse_if",
        "rmse_market",
        "bias_if",
        "bias_market",
        "mean_signed_diff_vs_if",
        "mean_signed_diff_vs_market",
        "mae_challenger",
        "rmse_challenger",
        "bias_challenger",
        "delta_mae_vs_if",
        "delta_mae_vs_market",
        "n",
    ):
        if not _present(scored.get(key)):
            raise EvalResultContractRefuse(
                f"EVAL result missing {key} — DEV437 / IF-only does not complete this contract"
            )
        require_finite(scored.get(key), key)
    seasons = scored.get("per_season")
    if not isinstance(seasons, Mapping) or not seasons:
        raise EvalResultContractRefuse("EVAL result requires per-season tables vs IF and market")
    n_by = scored.get("n_by_season")
    if not isinstance(n_by, Mapping) or not n_by:
        raise EvalResultContractRefuse("EVAL result requires n_by_season")
    for season, row in seasons.items():
        if not isinstance(row, Mapping):
            raise EvalResultContractRefuse(f"per_season[{season}] is not a table")
        gap = [k for k in PER_SEASON_CONTRACT_KEYS if k not in row or not _present(row.get(k))]
        if gap:
            raise EvalResultContractRefuse(
                f"per_season[{season}] missing IF+market fields: {gap}"
            )
        for key in PER_SEASON_CONTRACT_KEYS:
            if key == "n":
                if int(row.get("n") or 0) <= 0:
                    raise EvalResultContractRefuse(f"per_season[{season}].n invalid")
                continue
            require_finite(row.get(key), f"per_season[{season}].{key}")
    for name in BOOTSTRAP_KEYS:
        _check_bootstrap_metadata(name, scored.get(name), expected_point=None, expected_n=None)
    if scored.get("games"):
        ids = _as_ids(scored.get("game_ids") or [r.get("game_id") for r in scored.get("games") or []])
        validate_market72_consistency(scored, expected_ids=ids)


def apply_eval_result_contract(scored: dict[str, Any]) -> dict[str, Any]:
    """Validate then stamp. Does not rewrite recorded numerics."""
    validate_eval_result_contract(scored)
    scored["eval_result_contract"] = SCHEMA
    scored["eval_result_sides"] = ["if", "market"]
    scored["interval_contract"] = dict(INTERVAL_CONTRACT)
    scored["cert_candidate"] = CERT_CANDIDATE
    return scored


def refuse_incomplete_market_before_claim(
    *,
    eligible_cohorts: Mapping[str, Any] | None,
    market_points: Sequence[Mapping[str, Any]] | None,
) -> None:
    """IF-only / partial market must not claim (look burn). Pre-claim, pre-loader."""
    allow = list(((eligible_cohorts or {}).get("margin_cohort") or {}).get("game_ids") or [])
    if not allow:
        raise EvalResultContractRefuse(
            "eligible margin cohort required for market-completeness gate"
        )
    market_by = {str(p.get("game_id")): p for p in (market_points or [])}
    missing = [
        gid for gid in allow if (market_by.get(gid) or {}).get("market_margin") is None
    ]
    if missing:
        raise EvalResultContractRefuse(
            "market incomplete for eligible cohort — refuse before claim "
            f"(missing {len(missing)} of {len(allow)})"
        )


def joined_row_sha256(rows: Sequence[Mapping[str, Any]]) -> str:
    body = []
    for row in rows:
        body.append(
            {
                "game_id": str(row["game_id"]),
                "season": int(row["season"]),
                "week": int(row["week"]),
                "actual_margin": row.get("actual_margin"),
                "m_challenger": row.get("m_challenger"),
                "m_if": row.get("m_if"),
                "m_market": row.get("m_market"),
            }
        )
    return hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


def join_market72_from_if437(
    if437: Mapping[str, Any],
    market72: Mapping[str, Any],
    *,
    expected_ids: Sequence[str],
) -> dict[str, Any]:
    """Join published 437 per-game rows to published 72 market points. No new scoring."""
    refuse_synthetic_flag(if437, label="DEV_IF437")
    refuse_synthetic_flag(market72, label="DEV_MARKET72")
    want = _as_ids(expected_ids)
    if len(want) != DEV_MARKET72_N or _n_by_season_from_ids(want) != DEV_MARKET72_BY_SEASON:
        raise EvalResultContractRefuse("DEV_MARKET72 expected IDs are not 35+37")
    published_ids = _as_ids(market72.get("game_ids"))
    if set(published_ids) != set(want) or len(published_ids) != DEV_MARKET72_N:
        raise EvalResultContractRefuse("matched72 game_ids disagree with profile identity")
    points = {
        str(p.get("game_id")): p
        for p in (market72.get("market_points") or [])
        if isinstance(p, Mapping)
    }
    if set(points) != set(want) or len(points) != DEV_MARKET72_N:
        raise EvalResultContractRefuse("matched72 market_points disagree with profile identity")
    by437 = {str(r.get("game_id")): r for r in (if437.get("games") or []) if isinstance(r, Mapping)}
    missing = [gid for gid in want if gid not in by437]
    if missing:
        raise EvalResultContractRefuse(f"matched72 IDs missing from saved 437 rows: {missing[:8]}")
    joined: list[dict[str, Any]] = []
    for gid in published_ids:
        src = by437[gid]
        point = points[gid]
        actual = src.get("actual_margin")
        require_finite(actual, f"{gid}.actual_margin")
        if int(src.get("season") or 0) != int(point.get("season") or -1):
            raise EvalResultContractRefuse(f"{gid} season identity mismatch 437 vs market point")
        if int(src.get("week") or 0) != int(point.get("week") or -1):
            raise EvalResultContractRefuse(f"{gid} week identity mismatch 437 vs market point")
        m_mkt = point.get("market_margin")
        require_finite(m_mkt, f"{gid}.market_margin")
        row = dict(src)
        row["m_market"] = float(m_mkt)
        row["err_market"] = float(m_mkt) - float(actual)
        row["L_market"] = abs(row["err_market"])
        row["signed_diff_vs_market"] = _row_abs_loss(row, "challenger") - row["L_market"]
        joined.append(row)
    out = dict(market72)
    out["games"] = joined
    out["game_ids"] = published_ids
    out["n"] = DEV_MARKET72_N
    out["joined_from_437"] = True
    out["synthetic"] = False
    return out


def validate_market72_consistency(
    payload: Mapping[str, Any],
    *,
    expected_ids: Sequence[str] | None = None,
) -> dict[str, Any]:
    refuse_synthetic_flag(payload, label="DEV_MARKET72")
    if expected_ids is None:
        raise EvalResultContractRefuse("DEV_MARKET72 requires declared profile IDs")
    rows = saved_game_rows(payload)
    achieved = recompute_from_saved_rows(rows, require_market=True)
    _check_count_agreement(
        payload,
        achieved,
        expected_n=DEV_MARKET72_N,
        expected_by_season=DEV_MARKET72_BY_SEASON,
        expected_ids=expected_ids,
    )
    _check_recorded_vs_achieved(
        payload,
        achieved,
        (
            "mae_challenger",
            "mae_if",
            "mae_market",
            "rmse_challenger",
            "rmse_if",
            "rmse_market",
            "bias_challenger",
            "bias_if",
            "bias_market",
            "delta_mae_vs_if",
            "delta_mae_vs_market",
            "mean_signed_diff_vs_if",
            "mean_signed_diff_vs_market",
        ),
    )
    _per_season_tables(
        payload,
        rows,
        require_market=True,
        expected_by_season=DEV_MARKET72_BY_SEASON,
    )
    _check_bootstrap_metadata(
        "bootstrap_game",
        payload.get("bootstrap_game"),
        expected_point=float(achieved["mean_signed_diff_vs_if"]),
        expected_n=int(achieved["n"]),
    )
    _check_bootstrap_metadata(
        "bootstrap_season_week",
        payload.get("bootstrap_season_week"),
        expected_point=float(achieved["mean_signed_diff_vs_if"]),
        expected_n=int(achieved["n"]),
    )
    _check_bootstrap_metadata(
        "bootstrap_game_vs_market",
        payload.get("bootstrap_game_vs_market"),
        expected_point=float(achieved["mean_signed_diff_vs_market"]),
        expected_n=int(achieved["n"]),
    )
    _check_bootstrap_metadata(
        "bootstrap_season_week_vs_market",
        payload.get("bootstrap_season_week_vs_market"),
        expected_point=float(achieved["mean_signed_diff_vs_market"]),
        expected_n=int(achieved["n"]),
    )
    return {
        "ok": True,
        "profile": PROFILE_DEV_MARKET72,
        "n": achieved["n"],
        "n_by_season": dict(achieved["n_by_season"]),
        "joined_row_sha256": joined_row_sha256(rows),
    }


def validate_dev_if437(
    payload: Mapping[str, Any],
    *,
    expected_ids: Sequence[str] | None = None,
) -> dict[str, Any]:
    """IF-only DEV: market must be explicitly unavailable; cannot satisfy market."""
    if not isinstance(payload, Mapping):
        raise EvalResultContractRefuse("DEV_IF437 payload is not a mapping")
    refuse_synthetic_flag(payload, label="DEV_IF437")
    if expected_ids is None:
        raise EvalResultContractRefuse("DEV_IF437 requires declared profile IDs")
    if not market_is_unavailable(payload):
        raise EvalResultContractRefuse("DEV_IF437 must explicitly mark market unavailable")
    status = str(payload.get("market_status") or "")
    nested = payload.get("market") if isinstance(payload.get("market"), Mapping) else {}
    nested_status = str((nested or {}).get("status") or "")
    declared = status.upper() if status else nested_status.upper()
    if declared not in MARKET_UNAVAILABLE_STATUSES:
        raise EvalResultContractRefuse(
            f"DEV_IF437 market_status={declared!r} must be one of {sorted(MARKET_UNAVAILABLE_STATUSES)}"
        )
    cannot = payload.get("cannot_satisfy_profiles") or payload.get("cannot_satisfy_profile")
    cannot_list = [cannot] if isinstance(cannot, str) else list(cannot or [])
    if PROFILE_DEV_MARKET72 not in cannot_list and declared not in MARKET_UNAVAILABLE_STATUSES:
        raise EvalResultContractRefuse(
            "DEV_IF437 must declare it cannot satisfy DEV_MARKET72"
        )
    missing = [
        k
        for k in IF_ONLY_REQUIRED
        if k not in payload and k not in {"market_unavailable", "market_status"}
    ]
    if missing:
        raise EvalResultContractRefuse(f"DEV_IF437 missing IF-only fields: {missing}")
    for key in (
        "mae_challenger",
        "mae_if",
        "rmse_challenger",
        "rmse_if",
        "bias_challenger",
        "bias_if",
        "delta_mae_vs_if",
        "mean_signed_diff_vs_if",
        "n",
    ):
        require_finite(payload.get(key), key)
    for banned in (
        "mae_market",
        "rmse_market",
        "bias_market",
        "delta_mae_vs_market",
        "mean_signed_diff_vs_market",
        "bootstrap_game_vs_market",
        "bootstrap_season_week_vs_market",
    ):
        value = payload.get(banned)
        if _finite(value) or (isinstance(value, Mapping) and value.get("point") is not None):
            raise EvalResultContractRefuse(
                f"DEV_IF437 carries market numeric {banned} — cannot satisfy market by silence"
            )
    try:
        validate_eval_result_contract(payload)
    except EvalResultContractRefuse:
        pass
    else:
        raise EvalResultContractRefuse(
            "DEV_IF437 unexpectedly satisfied the market EVAL contract"
        )
    rows = saved_game_rows(payload)
    if any(_has_market_fields(row) for row in rows):
        raise EvalResultContractRefuse("DEV_IF437 saved rows include market fields")
    achieved = recompute_from_saved_rows(rows, require_market=False)
    _check_count_agreement(
        payload,
        achieved,
        expected_n=DEV_IF437_N,
        expected_by_season=DEV_IF437_BY_SEASON,
        expected_ids=expected_ids,
    )
    _check_recorded_vs_achieved(
        payload,
        achieved,
        (
            "mae_challenger",
            "mae_if",
            "rmse_challenger",
            "rmse_if",
            "bias_challenger",
            "bias_if",
            "delta_mae_vs_if",
            "mean_signed_diff_vs_if",
        ),
    )
    _per_season_tables(
        payload,
        rows,
        require_market=False,
        expected_by_season=DEV_IF437_BY_SEASON,
    )
    _check_bootstrap_metadata(
        "bootstrap_game",
        payload.get("bootstrap_game"),
        expected_point=float(achieved["mean_signed_diff_vs_if"]),
        expected_n=int(achieved["n"]),
    )
    _check_bootstrap_metadata(
        "bootstrap_season_week",
        payload.get("bootstrap_season_week"),
        expected_point=float(achieved["mean_signed_diff_vs_if"]),
        expected_n=int(achieved["n"]),
    )
    return {
        "ok": True,
        "profile": PROFILE_DEV_IF437,
        "n": achieved["n"],
        "n_by_season": dict(achieved["n_by_season"]),
        "joined_row_sha256": joined_row_sha256(rows),
        "market_unavailable": True,
        "cannot_satisfy_profile": PROFILE_DEV_MARKET72,
    }


def _walk_forbidden_metrics(obj: Any, *, trail: str = "") -> list[str]:
    hits: list[str] = []
    if isinstance(obj, Mapping):
        for key, value in obj.items():
            path = f"{trail}.{key}" if trail else str(key)
            if str(key) in INVENTED_RECON_METRIC_KEYS:
                hits.append(path)
            hits.extend(_walk_forbidden_metrics(value, trail=path))
    elif isinstance(obj, Sequence) and not isinstance(obj, (str, bytes)):
        if len(obj) > 64:
            return hits
        for idx, value in enumerate(obj[:8]):
            hits.extend(_walk_forbidden_metrics(value, trail=f"{trail}[{idx}]"))
    return hits


def validate_feature_recon_reg496(
    payload: Mapping[str, Any],
    *,
    expected_ids: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Reconstruction: lineage + completeness. No invented metrics."""
    if not isinstance(payload, Mapping):
        raise EvalResultContractRefuse("FEATURE_RECON_REG496 payload is not a mapping")
    refuse_synthetic_flag(payload, label=PROFILE_FEATURE_RECON_REG496)
    invented = _walk_forbidden_metrics(
        {k: v for k, v in payload.items() if k not in {"matrix"}}
    )
    if invented:
        raise EvalResultContractRefuse(
            f"FEATURE_RECON_REG496 invented metric keys: {invented[:12]}"
        )
    if payload.get("eval") not in (None, {}, False):
        raise EvalResultContractRefuse("FEATURE_RECON_REG496 must not carry eval scoring")
    if payload.get("scored_look") or payload.get("accuracy_run"):
        raise EvalResultContractRefuse("FEATURE_RECON_REG496 must not invent accuracy metrics")
    n = payload.get("n")
    if n is None:
        n = payload.get("n_complete_27")
    if n != REG496_N:
        raise EvalResultContractRefuse(f"FEATURE_RECON_REG496 n={n} != {REG496_N}")
    n_by = {str(k): int(v) for k, v in (payload.get("n_by_season") or {}).items()}
    if n_by != REG496_BY_SEASON:
        raise EvalResultContractRefuse(f"FEATURE_RECON_REG496 n_by_season {n_by} != {REG496_BY_SEASON}")
    if int(payload.get("n_complete_27") or -1) != REG496_N:
        raise EvalResultContractRefuse("FEATURE_RECON_REG496 incomplete: n_complete_27 != 496")
    if int(payload.get("n_partial") or 0) != 0 or int(payload.get("n_refused") or 0) != 0:
        raise EvalResultContractRefuse("FEATURE_RECON_REG496 completeness refused (partial/refused)")
    ids = _as_ids(payload.get("game_ids"))
    complete = _as_ids(payload.get("complete_game_ids") or ids)
    identities = list(payload.get("identities") or [])
    if len(ids) != REG496_N or len(complete) != REG496_N or len(identities) != REG496_N:
        raise EvalResultContractRefuse(
            f"FEATURE_RECON_REG496 count disagree n={len(ids)} "
            f"complete={len(complete)} identities={len(identities)}"
        )
    if set(ids) != set(complete):
        raise EvalResultContractRefuse("FEATURE_RECON_REG496 game_ids != complete_game_ids")
    if _n_by_season_from_ids(ids) != REG496_BY_SEASON:
        raise EvalResultContractRefuse("FEATURE_RECON_REG496 season sums disagree")
    leaked = [g for g in ids if g in set(WILDCARD_2020_W18)]
    if leaked:
        raise EvalResultContractRefuse(f"FEATURE_RECON_REG496 leaked 2020 Wild Card {leaked}")
    w18 = [g for g in ids if g.startswith("2021_18_")]
    if len(w18) != REG_W18_2021_N:
        raise EvalResultContractRefuse(
            f"FEATURE_RECON_REG496 2021 REG week 18 count {len(w18)} != {REG_W18_2021_N}"
        )
    if expected_ids is not None and set(ids) != set(_as_ids(expected_ids)):
        raise EvalResultContractRefuse("FEATURE_RECON_REG496 cohort IDs disagree with declared")
    identity_ids: list[str] = []
    for idx, row in enumerate(identities):
        if not isinstance(row, Mapping):
            raise EvalResultContractRefuse(f"identities[{idx}] is not a mapping")
        gap = [k for k in RECON_IDENTITY_REQUIRED if k not in row]
        if gap:
            raise EvalResultContractRefuse(f"identities[{idx}] missing lineage/completeness: {gap}")
        gid = str(row["game_id"])
        identity_ids.append(gid)
        t1_home = str(row.get("t1_home") or "")
        t1_away = str(row.get("t1_away") or "")
        if not t1_home.startswith("t1=") or not t1_away.startswith("t1="):
            raise EvalResultContractRefuse(f"{gid} missing t1= feature/source lineage")
        home_ids = [str(x) for x in (row.get("consumed_game_ids_home") or [])]
        away_ids = [str(x) for x in (row.get("consumed_game_ids_away") or [])]
        if t1_home[3:] != "|".join(home_ids):
            raise EvalResultContractRefuse(f"{gid} t1_home does not match consumed source IDs")
        if t1_away[3:] != "|".join(away_ids):
            raise EvalResultContractRefuse(f"{gid} t1_away does not match consumed source IDs")
        if not home_ids or not away_ids:
            raise EvalResultContractRefuse(f"{gid} empty consumed source-game lineage")
        derived = row.get("derived")
        missing = row.get("missing")
        if derived is None or int(derived) != len(CONTRACT_27) or missing is None or int(missing) != 0:
            raise EvalResultContractRefuse(f"{gid} incomplete 27-field reconstruction")
        if row.get("publication_timestamp_status") != "unverified":
            raise EvalResultContractRefuse(f"{gid} publication timestamp not unverified")
        labels = {str(x) for x in (row.get("labels") or [])}
        if "RECONSTRUCTED" not in labels or "RETRO_FIT" not in labels:
            raise EvalResultContractRefuse(f"{gid} missing RECONSTRUCTED/RETRO_FIT lineage labels")
        if row.get("production_causal_claim"):
            raise EvalResultContractRefuse(f"{gid} production-causal claim forbidden")
    if set(identity_ids) != set(ids):
        raise EvalResultContractRefuse("identity game_ids disagree with payload game_ids")
    matrix = payload.get("matrix")
    if isinstance(matrix, Sequence) and matrix:
        sample = [row for row in matrix if isinstance(row, Mapping)][:32]
        for row in sample:
            for key in ("source_path", "source_sha256", "derivation_lineage", "field", "game_id"):
                if not row.get(key):
                    raise EvalResultContractRefuse(f"matrix row missing {key}")
    return {
        "ok": True,
        "profile": PROFILE_FEATURE_RECON_REG496,
        "n": REG496_N,
        "n_by_season": dict(REG496_BY_SEASON),
        "invented_metrics": False,
        "w18_2021_retained": REG_W18_2021_N,
        "joined_row_sha256": joined_row_sha256(
            [
                {
                    "game_id": gid,
                    "season": int(str(gid).split("_")[0]),
                    "week": int(str(gid).split("_")[1]),
                }
                for gid in ids
            ]
        ),
    }


def validate_profile_output(
    profile: str,
    payload: Mapping[str, Any],
    *,
    expected_ids: Sequence[str] | None = None,
) -> dict[str, Any]:
    refuse_synthetic_flag(payload, label=profile)
    if expected_ids is None:
        raise EvalResultContractRefuse(f"{profile} requires declared profile IDs")
    if profile == PROFILE_FEATURE_RECON_REG496:
        return validate_feature_recon_reg496(payload, expected_ids=expected_ids)
    if profile == PROFILE_DEV_IF437:
        return validate_dev_if437(payload, expected_ids=expected_ids)
    if profile == PROFILE_DEV_MARKET72:
        if market_is_unavailable(payload):
            raise EvalResultContractRefuse("DEV_MARKET72 cannot use an IF-only / market-unavailable result")
        validate_eval_result_contract(payload)
        return validate_market72_consistency(payload, expected_ids=expected_ids)
    raise EvalResultContractRefuse(f"unknown profile {profile}")
