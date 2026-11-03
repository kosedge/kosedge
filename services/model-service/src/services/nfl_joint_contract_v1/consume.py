"""Consume SUPPLIED adapter output. Recompute that record — not the default oracle. CERT=0."""

from __future__ import annotations

import copy
import math
from pathlib import Path
from typing import Any, Callable, Mapping, Optional

from src.services.nfl_joint_contract_v1.constants import (
    CERT,
    CONTRACT_HASH,
    CONTRACT_ID,
    DATA_LABEL,
    ELIGIBILITY,
    KNOWN_SETTLEMENT_PROFILE,
    ORACLE_PAIRS,
    ORACLE_WEIGHTS,
    SYNTH_IDENTITY,
    TASK_ID,
)
from src.services.nfl_joint_contract_v1.freeze import require_freeze_intact
from src.services.nfl_joint_contract_v1.oracle import (
    _finite_prob,
    _int_score,
    law_from_pairs,
    partitions_from_law,
)
from src.services.nfl_joint_contract_v1.refuse import JointContractRefuse, RefuseClass
from src.services.nfl_joint_contract_v1.settlement import identity_settlement, require_known_settlement
from src.services.nfl_joint_contract_v1.spy import (
    FORBIDDEN_CALL_ATTEMPTS,
    ForbiddenSurfaceSpy,
    OutcomeReadSpy,
    assert_zero_forbidden_on_refusal,
)

ALLOWED_CONSUMERS = frozenset({"fixture", "joint_literal"})
DENIED_CONSUMERS = frozenset(
    {
        "fair_lines_api",
        "cache",
        "production",
        "subscriber",
        "direct_api",
    }
)
_TOL = 1e-12


def _require_finite_number(value: Any, name: str) -> float:
    """Strict non-bool numeric AND finite. No string/NaN float-cast fallthrough."""
    if value is None:
        raise JointContractRefuse(f"{name} is null", refuse_class=RefuseClass.TYPE)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise JointContractRefuse(
            f"{name} is not a non-bool numeric (got {type(value).__name__})",
            refuse_class=RefuseClass.TYPE,
        )
    number = float(value)
    if math.isnan(number) or not math.isfinite(number):
        raise JointContractRefuse(
            f"{name} must be finite",
            refuse_class=RefuseClass.NONFINITE,
        )
    return number


def _require_int(value: Any, name: str) -> int:
    if value is None:
        raise JointContractRefuse(f"{name} is null", refuse_class=RefuseClass.TYPE)
    if isinstance(value, bool) or type(value) is not int:
        raise JointContractRefuse(
            f"{name} must be a non-bool int (got {type(value).__name__})",
            refuse_class=RefuseClass.TYPE,
        )
    return value


def _close(value: Any, expected: float, name: str, *, refuse_class: str = RefuseClass.HASH_MUTATED) -> float:
    number = _require_finite_number(value, name)
    if abs(number - expected) > _TOL:
        raise JointContractRefuse(
            f"{name} supplied {value} != recomputed {expected}",
            refuse_class=refuse_class,
        )
    return number


def _bind_score_field(raw: Mapping[str, Any], primary: str, alias: str, idx: int) -> int:
    """Require primary score. Conflicting or alias-only fallthrough refuses."""
    has_primary = primary in raw and raw.get(primary) is not None
    has_alias = alias in raw and raw.get(alias) is not None
    if not has_primary:
        if has_alias:
            raise JointContractRefuse(
                f"outcomes[{idx}].{primary} missing; alias {alias} is not an unchecked fallthrough",
                refuse_class=RefuseClass.TYPE,
            )
        raise JointContractRefuse(
            f"outcomes[{idx}].{primary} missing",
            refuse_class=RefuseClass.INCOMPLETE,
        )
    primary_v = _int_score(raw.get(primary), f"outcomes[{idx}].{primary}")
    if has_alias:
        alias_v = _int_score(raw.get(alias), f"outcomes[{idx}].{alias}")
        if alias_v != primary_v:
            raise JointContractRefuse(
                f"outcomes[{idx}].{alias}={alias_v} conflicts with {primary}={primary_v}",
                refuse_class=RefuseClass.HASH_MUTATED,
            )
    return primary_v


def _pairs_weights_from_outcomes(outcomes: Any) -> tuple[list[tuple[int, int]], list[float]]:
    if not isinstance(outcomes, list) or not outcomes:
        raise JointContractRefuse("outcomes missing", refuse_class=RefuseClass.INCOMPLETE)
    pairs: list[tuple[int, int]] = []
    weights: list[Any] = []
    for idx, raw in enumerate(outcomes):
        if not isinstance(raw, Mapping):
            raise JointContractRefuse(
                f"outcomes[{idx}] must be an object",
                refuse_class=RefuseClass.TYPE,
            )
        pairs.append(
            (
                _bind_score_field(raw, "home", "home_score", idx),
                _bind_score_field(raw, "away", "away_score", idx),
            )
        )
        weights.append(raw.get("weight"))
    return pairs, list(weights)


def recompute_supplied_law(record: Mapping[str, Any]) -> dict[str, Any]:
    """Recompute partitions from the supplied outcomes against the one sealed law."""
    pairs, weights = _pairs_weights_from_outcomes(record.get("outcomes"))
    if tuple(pairs) != ORACLE_PAIRS:
        raise JointContractRefuse(
            f"supplied pairs {pairs} are not the one sealed paired law {list(ORACLE_PAIRS)}",
            refuse_class=RefuseClass.IDENTITY,
        )
    declared_parts = record.get("partitions")
    if not isinstance(declared_parts, Mapping):
        raise JointContractRefuse("partitions missing", refuse_class=RefuseClass.INCOMPLETE)
    law = law_from_pairs(pairs, weights)
    computed = partitions_from_law(pairs=pairs, weights=weights)
    if tuple(law["weights"]) != ORACLE_WEIGHTS:
        raise JointContractRefuse(
            "supplied weights are not the sealed equal-weight law (no silent renormalize)",
            refuse_class=RefuseClass.PARTITION,
        )
    return computed


def _bind_partitions(declared: Mapping[str, Any], computed: Mapping[str, Any]) -> None:
    ml = declared.get("ml")
    if not isinstance(ml, Mapping):
        raise JointContractRefuse("partitions.ml missing", refuse_class=RefuseClass.INCOMPLETE)
    home_win = _finite_prob(ml.get("home_win"), "partitions.ml.home_win")
    away_win = _finite_prob(ml.get("away_win"), "partitions.ml.away_win")
    tie = _finite_prob(ml.get("tie"), "partitions.ml.tie")
    _close(home_win, computed["ml"]["home_win"], "partitions.ml.home_win")
    _close(away_win, computed["ml"]["away_win"], "partitions.ml.away_win")
    _close(tie, computed["ml"]["tie"], "partitions.ml.tie")
    if abs(home_win + away_win + tie - 1.0) > _TOL:
        raise JointContractRefuse("supplied ML partition does not sum to 1", refuse_class=RefuseClass.PARTITION)

    means = declared.get("means")
    if not isinstance(means, Mapping):
        raise JointContractRefuse("partitions.means missing", refuse_class=RefuseClass.INCOMPLETE)
    if "margin" not in means:
        raise JointContractRefuse("partitions.means.margin missing", refuse_class=RefuseClass.INCOMPLETE)
    if "total" not in means:
        raise JointContractRefuse("partitions.means.total missing", refuse_class=RefuseClass.INCOMPLETE)
    _close(means.get("margin"), computed["means"]["margin"], "partitions.means.margin")
    _close(means.get("total"), computed["means"]["total"], "partitions.means.total")

    spread = declared.get("spread")
    if not isinstance(spread, Mapping):
        raise JointContractRefuse("partitions.spread missing", refuse_class=RefuseClass.INCOMPLETE)
    if "line" not in spread:
        raise JointContractRefuse("partitions.spread.line missing", refuse_class=RefuseClass.INCOMPLETE)
    _close(spread.get("line"), computed["spread"]["line"], "partitions.spread.line")
    for key in ("cover", "push", "loss"):
        _finite_prob(spread.get(key), f"partitions.spread.{key}")
        _close(spread.get(key), computed["spread"][key], f"partitions.spread.{key}")

    total = declared.get("total")
    if not isinstance(total, Mapping):
        raise JointContractRefuse("partitions.total missing", refuse_class=RefuseClass.INCOMPLETE)
    if "line" not in total:
        raise JointContractRefuse("partitions.total.line missing", refuse_class=RefuseClass.INCOMPLETE)
    _close(total.get("line"), computed["total"]["line"], "partitions.total.line")
    for key in ("over", "push", "under"):
        _finite_prob(total.get(key), f"partitions.total.{key}")
        _close(total.get(key), computed["total"][key], f"partitions.total.{key}")

    if "n" not in declared:
        raise JointContractRefuse("partitions.n missing", refuse_class=RefuseClass.INCOMPLETE)
    n = _require_int(declared.get("n"), "partitions.n")
    if n != computed["n"]:
        raise JointContractRefuse(
            f"partitions.n supplied {n} != recomputed {computed['n']}",
            refuse_class=RefuseClass.PARTITION,
        )
    if "weight_sum" not in declared:
        raise JointContractRefuse("partitions.weight_sum missing", refuse_class=RefuseClass.INCOMPLETE)
    _close(
        declared.get("weight_sum"),
        computed["weight_sum"],
        "partitions.weight_sum",
        refuse_class=RefuseClass.PARTITION,
    )


def _bind_outcomes(declared: Any, computed: Mapping[str, Any]) -> None:
    if not isinstance(declared, list) or not declared:
        raise JointContractRefuse("outcomes missing", refuse_class=RefuseClass.INCOMPLETE)
    expected = computed["outcomes"]
    if len(declared) != len(expected):
        raise JointContractRefuse(
            f"outcomes n={len(declared)} != recomputed {len(expected)}",
            refuse_class=RefuseClass.PARTITION,
        )
    for idx, raw in enumerate(declared):
        if not isinstance(raw, Mapping):
            raise JointContractRefuse(
                f"outcomes[{idx}] must be an object",
                refuse_class=RefuseClass.TYPE,
            )
        home = _bind_score_field(raw, "home", "home_score", idx)
        away = _bind_score_field(raw, "away", "away_score", idx)
        if home != expected[idx]["home"] or away != expected[idx]["away"]:
            raise JointContractRefuse(
                f"outcomes[{idx}] pair {(home, away)} != recomputed "
                f"{(expected[idx]['home'], expected[idx]['away'])}",
                refuse_class=RefuseClass.IDENTITY,
            )
        if "weight" not in raw:
            raise JointContractRefuse(f"outcomes[{idx}].weight missing", refuse_class=RefuseClass.INCOMPLETE)
        if "margin" not in raw:
            raise JointContractRefuse(f"outcomes[{idx}].margin missing", refuse_class=RefuseClass.INCOMPLETE)
        if "total" not in raw:
            raise JointContractRefuse(f"outcomes[{idx}].total missing", refuse_class=RefuseClass.INCOMPLETE)
        _close(raw.get("weight"), expected[idx]["weight"], f"outcomes[{idx}].weight")
        _close(raw.get("margin"), expected[idx]["margin"], f"outcomes[{idx}].margin")
        _close(raw.get("total"), expected[idx]["total"], f"outcomes[{idx}].total")
        derived_margin = home - away
        derived_total = home + away
        _close(raw.get("margin"), derived_margin, f"outcomes[{idx}].margin H-A")
        _close(raw.get("total"), derived_total, f"outcomes[{idx}].total H+A")


def _bind_settlement(declared: Mapping[str, Any], computed: Mapping[str, Any]) -> None:
    require_known_settlement(declared.get("settlement_profile"))
    if declared.get("actionable") is True:
        raise JointContractRefuse(
            "exposure/settlement actionable cannot pass this consumer",
            refuse_class=RefuseClass.ACTIONABLE,
        )
    if declared.get("fair_odds") is not None or declared.get("ev") is not None:
        raise JointContractRefuse(
            "fair_odds / EV cannot pass this consumer",
            refuse_class=RefuseClass.ACTIONABLE,
        )
    expected = identity_settlement(computed, profile=str(declared.get("settlement_profile")))
    got = declared.get("settled_p")
    if not isinstance(got, Mapping):
        raise JointContractRefuse("settlement.settled_p missing", refuse_class=RefuseClass.INCOMPLETE)
    for group, keys in (
        ("ml", ("home_win", "away_win", "tie")),
        ("spread", ("cover", "push", "loss")),
        ("total", ("over", "push", "under")),
    ):
        row = got.get(group)
        if not isinstance(row, Mapping):
            raise JointContractRefuse(f"settled_p.{group} missing", refuse_class=RefuseClass.INCOMPLETE)
        for key in keys:
            _finite_prob(row.get(key), f"settled_p.{group}.{key}")
            _close(row.get(key), expected["settled_p"][group][key], f"settled_p.{group}.{key}")


def _bind_flags(record: Mapping[str, Any]) -> None:
    if type(record.get("cert")) is not int or record.get("cert") != CERT:
        raise JointContractRefuse(f"cert must be int {CERT}", refuse_class=RefuseClass.TYPE)
    if record.get("data_label") != DATA_LABEL:
        raise JointContractRefuse(
            f"data_label={record.get('data_label')!r} refused before readers/model/network/DB",
            refuse_class=RefuseClass.REAL_MODE,
        )
    if record.get("eligibility") != ELIGIBILITY:
        raise JointContractRefuse(
            f"eligibility {record.get('eligibility')!r} is not UNQUALIFIED",
            refuse_class=RefuseClass.IDENTITY,
        )
    if record.get("channel") != "FIXTURE":
        raise JointContractRefuse(
            f"channel={record.get('channel')!r} is not FIXTURE",
            refuse_class=RefuseClass.CAPABILITY,
        )
    if record.get("production_mode") is True:
        raise JointContractRefuse(
            "production_mode cannot pass this consumer",
            refuse_class=RefuseClass.CAPABILITY,
        )
    if record.get("cacheable") is True:
        raise JointContractRefuse("cacheable cannot pass this consumer", refuse_class=RefuseClass.CAPABILITY)
    if record.get("fitted") is True:
        raise JointContractRefuse("fitted adapter is not the literal-law path", refuse_class=RefuseClass.CAPABILITY)
    if record.get("ready_for_review") is True or record.get("self_accept") is True:
        raise JointContractRefuse(
            "READY_FOR_REVIEW / self_accept cannot be self-stamped",
            refuse_class=RefuseClass.ACTIONABLE,
        )
    exposure = record.get("exposure")
    if not isinstance(exposure, Mapping):
        raise JointContractRefuse("exposure missing", refuse_class=RefuseClass.INCOMPLETE)
    for key in (
        "subscriber_consumable",
        "betting_consumable",
        "production_consumable",
        "env_bypass_honored",
        "cacheable",
        "public_output",
        "actionable",
    ):
        if exposure.get(key) is not False:
            raise JointContractRefuse(
                f"exposure.{key} must be false",
                refuse_class=RefuseClass.ACTIONABLE,
            )
    capability = record.get("capability")
    if not isinstance(capability, Mapping):
        raise JointContractRefuse("capability missing", refuse_class=RefuseClass.INCOMPLETE)
    bits = capability.get("bits")
    if not isinstance(bits, list) or bits != ["JOINT_LITERAL_LAW"]:
        raise JointContractRefuse(
            "capability.bits must be exactly [JOINT_LITERAL_LAW] — point-margin is not joint",
            refuse_class=RefuseClass.CAPABILITY,
        )
    if capability.get("requested_output") != "LITERAL_JOINT_PARTITIONS":
        raise JointContractRefuse(
            "requested_output must be LITERAL_JOINT_PARTITIONS",
            refuse_class=RefuseClass.CAPABILITY,
        )


def _bind_provenance(record: Mapping[str, Any], freeze: Mapping[str, Any]) -> None:
    prov = record.get("provenance")
    if not isinstance(prov, Mapping):
        raise JointContractRefuse("provenance missing", refuse_class=RefuseClass.INCOMPLETE)
    for key in ("oracle_hash", "schema_hash", "code_hash", "receipt_hash"):
        declared = prov.get(key)
        expected = freeze.get(key)
        if declared != expected:
            raise JointContractRefuse(
                f"provenance.{key} {declared!r} != sealed freeze {expected}",
                refuse_class=RefuseClass.HASH_MUTATED,
            )
    if prov.get("data_label") != DATA_LABEL or prov.get("fitted") is True:
        raise JointContractRefuse(
            "provenance is not synthetic authored literal-law",
            refuse_class=RefuseClass.IDENTITY,
        )


def consume_literal_law(
    record: Mapping[str, Any],
    *,
    consumer: str = "joint_literal",
    settlement_profile: Optional[str] = KNOWN_SETTLEMENT_PROFILE,
    root: Path | None = None,
    outcome_spy: OutcomeReadSpy | None = None,
    surface: ForbiddenSurfaceSpy | None = None,
) -> dict[str, Any]:
    spy = outcome_spy if outcome_spy is not None else OutcomeReadSpy()
    try:
        if not isinstance(record, Mapping):
            raise JointContractRefuse("adapter record must be an object", refuse_class=RefuseClass.TYPE)
        _bind_flags(record)
        name = (consumer or "").strip().lower()
        if name in DENIED_CONSUMERS or name not in ALLOWED_CONSUMERS:
            raise JointContractRefuse(
                f"consumer {consumer!r} is not on the synthetic literal-law path",
                refuse_class=RefuseClass.CAPABILITY,
            )
        require_known_settlement(settlement_profile)
        freeze = require_freeze_intact(root)
        if record.get("contract_id") != CONTRACT_ID or record.get("contract_hash") != CONTRACT_HASH:
            raise JointContractRefuse(
                "adapter record is not NFL_JOINT_CONTRACT_V1 / 4f2c9e2b",
                refuse_class=RefuseClass.IDENTITY,
            )
        if record.get("freeze_receipt_hash") != freeze.get("receipt_hash"):
            raise JointContractRefuse(
                "adapter freeze_receipt_hash != sealed receipt",
                refuse_class=RefuseClass.HASH_MUTATED,
            )
        ident = record.get("identity")
        if not isinstance(ident, Mapping) or dict(ident) != dict(SYNTH_IDENTITY):
            raise JointContractRefuse(
                "identity is not the sealed synthetic joint envelope",
                refuse_class=RefuseClass.IDENTITY,
            )
        _bind_provenance(record, freeze)
        computed = recompute_supplied_law(record)
        _bind_partitions(record.get("partitions") or {}, computed)
        _bind_outcomes(record.get("outcomes"), computed)
        settlement = record.get("settlement")
        if not isinstance(settlement, Mapping):
            raise JointContractRefuse("settlement missing", refuse_class=RefuseClass.INCOMPLETE)
        _bind_settlement(settlement, computed)
        out = dict(record)
        out["consumed"] = True
        out["consumer"] = name
        out["cert"] = CERT
        out["task_id"] = TASK_ID
        out["ready_for_review"] = False
        out["self_accept"] = False
        out["supplied_law_recomputed"] = True
        return out
    except Exception:
        assert_zero_forbidden_on_refusal(outcome_spy=spy, surface=surface)
        raise


def _set_path(record: dict[str, Any], path: tuple[Any, ...], value: Any) -> None:
    cur: Any = record
    for key in path[:-1]:
        cur = cur[key]
    cur[path[-1]] = value


def _fault_means_margin(value: Any) -> Callable[[dict[str, Any]], None]:
    return lambda rec: _set_path(rec, ("partitions", "means", "margin"), value)


NUMERICAL_SINGLE_FAULTS: tuple[tuple[str, Callable[[dict[str, Any]], None]], ...] = (
    ("means_margin_nan", _fault_means_margin(float("nan"))),
    ("means_margin_pos_inf", _fault_means_margin(float("inf"))),
    ("means_margin_neg_inf", _fault_means_margin(float("-inf"))),
    ("means_margin_null", _fault_means_margin(None)),
    ("means_margin_bool", _fault_means_margin(True)),
    ("means_margin_string", _fault_means_margin("1.5")),
    ("partitions_n_999", lambda rec: _set_path(rec, ("partitions", "n"), 999)),
    ("partitions_weight_sum_4", lambda rec: _set_path(rec, ("partitions", "weight_sum"), 4)),
    ("outcome0_margin_999", lambda rec: _set_path(rec, ("outcomes", 0, "margin"), 999)),
    ("conflicting_home_score", lambda rec: _set_path(rec, ("outcomes", 0, "home_score"), 999)),
)


def apply_numerical_fault(record: Mapping[str, Any], case: str) -> dict[str, Any]:
    mutators = {name: fn for name, fn in NUMERICAL_SINGLE_FAULTS}
    if case not in mutators:
        raise JointContractRefuse(f"unknown numerical fault {case}", refuse_class=RefuseClass.TYPE)
    mutated = copy.deepcopy(dict(record))
    mutators[case](mutated)
    return mutated


def run_numerical_single_faults(
    record: Mapping[str, Any],
    *,
    root: Path | None = None,
) -> dict[str, Any]:
    """Single-fault NaN/±Inf/null/bool/string/count/mass/derived at the direct consumer."""
    rows: list[dict[str, Any]] = []
    for case, _fn in NUMERICAL_SINGLE_FAULTS:
        spy = OutcomeReadSpy()
        FORBIDDEN_CALL_ATTEMPTS.clear()
        mutated = apply_numerical_fault(record, case)
        refused = False
        refuse_class = None
        reason = None
        try:
            consume_literal_law(mutated, root=root, outcome_spy=spy)
        except JointContractRefuse as exc:
            refused = True
            refuse_class = exc.refuse_class
            reason = exc.reason
        if not refused:
            raise JointContractRefuse(
                f"numerical single-fault {case} was not refused",
                refuse_class=RefuseClass.HASH_MUTATED,
            )
        if spy.reads != 0 or FORBIDDEN_CALL_ATTEMPTS:
            raise JointContractRefuse(
                f"forbidden calls on numerical refuse {case}",
                refuse_class=RefuseClass.FORBIDDEN_CALL,
            )
        rows.append(
            {
                "case": case,
                "refused": True,
                "refuse_class": refuse_class,
                "reason": reason,
                "forbidden_calls": 0,
                "evidence_label": "EXECUTED_HERE",
            }
        )
    return {
        "ran": True,
        "n": len(rows),
        "all_refused": True,
        "forbidden_calls": 0,
        "faults": rows,
        "evidence_label": "EXECUTED_HERE",
    }
