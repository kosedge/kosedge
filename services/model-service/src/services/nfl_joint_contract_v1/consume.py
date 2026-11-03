"""Consume SUPPLIED adapter output. Recompute that record — not the default oracle. CERT=0."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Optional

from src.services.nfl_joint_contract_v1.constants import (
    CERT,
    CONTRACT_HASH,
    CONTRACT_ID,
    DATA_LABEL,
    ELIGIBILITY,
    KNOWN_SETTLEMENT_PROFILE,
    ORACLE_HOME_SPREAD,
    ORACLE_PAIRS,
    ORACLE_TOTAL,
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


def _close(value: Any, expected: float, name: str) -> None:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise JointContractRefuse(
            f"{name} is not numeric",
            refuse_class=RefuseClass.NONFINITE,
        ) from exc
    if abs(number - expected) > _TOL:
        raise JointContractRefuse(
            f"{name} supplied {value} != recomputed {expected}",
            refuse_class=RefuseClass.HASH_MUTATED,
        )


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
        home = raw.get("home") if raw.get("home") is not None else raw.get("home_score")
        away = raw.get("away") if raw.get("away") is not None else raw.get("away_score")
        pairs.append(
            (
                _int_score(home, f"outcomes[{idx}].home"),
                _int_score(away, f"outcomes[{idx}].away"),
            )
        )
        weights.append(raw.get("weight"))
    return pairs, list(weights)


def recompute_supplied_law(record: Mapping[str, Any]) -> dict[str, Any]:
    """Recompute partitions from the supplied record only."""
    pairs, weights = _pairs_weights_from_outcomes(record.get("outcomes"))
    if tuple(pairs) != ORACLE_PAIRS:
        raise JointContractRefuse(
            f"supplied pairs {pairs} are not the one sealed paired law {list(ORACLE_PAIRS)}",
            refuse_class=RefuseClass.IDENTITY,
        )
    declared_parts = record.get("partitions")
    if not isinstance(declared_parts, Mapping):
        raise JointContractRefuse("partitions missing", refuse_class=RefuseClass.INCOMPLETE)
    spread_line = declared_parts.get("spread", {}).get("line", ORACLE_HOME_SPREAD) if isinstance(declared_parts.get("spread"), Mapping) else ORACLE_HOME_SPREAD
    total_line = declared_parts.get("total", {}).get("line", ORACLE_TOTAL) if isinstance(declared_parts.get("total"), Mapping) else ORACLE_TOTAL
    law = law_from_pairs(pairs, weights)
    computed = partitions_from_law(pairs=pairs, weights=weights, home_spread=spread_line, total_line=total_line)
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
    for key in ("home_win", "away_win", "tie"):
        _finite_prob(ml.get(key), f"partitions.ml.{key}")
        _close(ml.get(key), computed["ml"][key], f"partitions.ml.{key}")
    if abs(float(ml["home_win"]) + float(ml["away_win"]) + float(ml["tie"]) - 1.0) > _TOL:
        raise JointContractRefuse("supplied ML partition does not sum to 1", refuse_class=RefuseClass.PARTITION)

    means = declared.get("means")
    if not isinstance(means, Mapping):
        raise JointContractRefuse("partitions.means missing", refuse_class=RefuseClass.INCOMPLETE)
    _close(means.get("margin"), computed["means"]["margin"], "partitions.means.margin")
    _close(means.get("total"), computed["means"]["total"], "partitions.means.total")

    spread = declared.get("spread")
    if not isinstance(spread, Mapping):
        raise JointContractRefuse("partitions.spread missing", refuse_class=RefuseClass.INCOMPLETE)
    for key in ("cover", "push", "loss"):
        _finite_prob(spread.get(key), f"partitions.spread.{key}")
        _close(spread.get(key), computed["spread"][key], f"partitions.spread.{key}")

    total = declared.get("total")
    if not isinstance(total, Mapping):
        raise JointContractRefuse("partitions.total missing", refuse_class=RefuseClass.INCOMPLETE)
    for key in ("over", "push", "under"):
        _finite_prob(total.get(key), f"partitions.total.{key}")
        _close(total.get(key), computed["total"][key], f"partitions.total.{key}")


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
