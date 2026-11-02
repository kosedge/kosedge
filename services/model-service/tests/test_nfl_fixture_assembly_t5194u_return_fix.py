"""t5194u RETURN-FIX — finite numbers, strict consume, A→B chain.

Does not rewrite t5178u pinned evidence. Synthetic only.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from src.services.nfl_fixture_assembly.assemble import (
    FORBIDDEN_CALL_ATTEMPTS,
    assemble_fixture_only,
    consume_eligibility,
    consume_fixture_eligibility,
    note_forbidden_call,
)
from src.services.nfl_fixture_assembly.chain import chain_digest, serialize_fixture_chain
from src.services.nfl_fixture_assembly.contract import (
    CHAIN_CONTRACT_ID,
    CHAIN_SCHEMA_VERSION,
    CONTRACT_ID,
    CONTRACT_SCHEMA_VERSION,
    FIXTURE_CHANNEL,
    FixtureEligibilityResult,
    FixtureHardRefuse,
    QuoteSide,
)
from src.services.nfl_fixture_assembly.produce_chain import produce_fixture_chain
from src.services.nfl_fixture_assembly.synth import synthetic_envelope

PINNED_V0 = Path(__file__).resolve().parents[3] / "data" / "ops" / "t5178u-wfix-a"
PINNED_CHAIN = Path(__file__).resolve().parents[3] / "data" / "ops" / "t5194u-wfix-a-chain"


def _allow_payload() -> dict:
    result = assemble_fixture_only(synthetic_envelope())
    return result.eligibility.to_dict()


def test_v0_positive_artifact_preserved() -> None:
    pinned = json.loads((PINNED_V0 / "positive-output.json").read_text(encoding="utf-8"))
    assert pinned["contract_id"] == CONTRACT_ID
    assert pinned["eligibility"]["result"] == "ALLOW_FIXTURE"
    assert "chain_contract_id" not in pinned


@pytest.mark.parametrize("value", [float("inf"), float("-inf"), float("nan"), True, "3.0", None])
def test_nonfinite_or_nontype_margin_refuses_with_consistent_identity(value: object) -> None:
    env = synthetic_envelope()
    capture = env.l1_candidate["capture_id"]
    forecast_id = env.forecast.forecast_id
    with pytest.raises(FixtureHardRefuse) as exc:
        assemble_fixture_only(replace(env, forecast=replace(env.forecast, point_margin=value)))  # type: ignore[arg-type]
    assert exc.value.result is FixtureEligibilityResult.REFUSE_LINE
    assert "quote" not in exc.value.to_dict()
    assert env.l1_candidate["capture_id"] == capture
    assert env.forecast.forecast_id == forecast_id


@pytest.mark.parametrize("value", [float("inf"), float("-inf"), float("nan"), True, " -3", None])
def test_nonfinite_or_nontype_quote_line_refuses_with_consistent_identity(value: object) -> None:
    env = synthetic_envelope()
    capture = env.l1_candidate["capture_id"]
    with pytest.raises(FixtureHardRefuse) as exc:
        assemble_fixture_only(replace(env, quote_spec=replace(env.quote_spec, line=value)))  # type: ignore[arg-type]
    assert exc.value.result is FixtureEligibilityResult.REFUSE_LINE
    assert env.l1_candidate["capture_id"] == capture


@pytest.mark.parametrize("price", [0, 50, -50, True, 110.0, None])
def test_invalid_american_price_refuses(price: object) -> None:
    env = synthetic_envelope()
    with pytest.raises(FixtureHardRefuse) as exc:
        assemble_fixture_only(replace(env, quote_spec=replace(env.quote_spec, price=price)))  # type: ignore[arg-type]
    assert exc.value.result is FixtureEligibilityResult.REFUSE_LINE


def test_consume_fixture_eligibility_positive_original_passes() -> None:
    payload = _allow_payload()
    decision = consume_fixture_eligibility(payload, consumer="fixture")
    assert decision.result is FixtureEligibilityResult.ALLOW_FIXTURE
    assert decision.contract_id == CONTRACT_ID
    consume_eligibility(assemble_fixture_only(synthetic_envelope()).eligibility, consumer="fixture")


def test_consume_refuses_bare_allow_object() -> None:
    with pytest.raises(FixtureHardRefuse) as exc:
        consume_fixture_eligibility({"result": "ALLOW_FIXTURE"}, consumer="fixture")
    assert exc.value.result is FixtureEligibilityResult.REFUSE_MISSING


def test_consume_refuses_wrong_contract_id_not_rewritten() -> None:
    payload = _allow_payload()
    payload["contract_id"] = "some-other-contract"
    with pytest.raises(FixtureHardRefuse) as exc:
        consume_fixture_eligibility(payload, consumer="fixture")
    assert exc.value.result is FixtureEligibilityResult.REFUSE_VERSION


def test_consume_refuses_fixture_false_not_rewritten() -> None:
    payload = _allow_payload()
    payload["fixture"] = False
    with pytest.raises(FixtureHardRefuse) as exc:
        consume_fixture_eligibility(payload, consumer="fixture")
    assert exc.value.result is FixtureEligibilityResult.REFUSE_QUALIFICATION


def test_consume_refuses_production_channel_not_rewritten() -> None:
    payload = _allow_payload()
    payload["channel"] = "PRODUCTION"
    with pytest.raises(FixtureHardRefuse) as exc:
        consume_fixture_eligibility(payload, consumer="fixture")
    assert exc.value.result is FixtureEligibilityResult.REFUSE_PRODUCTION_CHANNEL


@pytest.mark.parametrize("key", ["subscriber_consumable", "cacheable", "env_bypass_honored"])
def test_consume_refuses_nonboolean_flags(key: str) -> None:
    payload = _allow_payload()
    payload[key] = 0
    with pytest.raises(FixtureHardRefuse) as exc:
        consume_fixture_eligibility(payload, consumer="fixture")
    assert exc.value.result is FixtureEligibilityResult.REFUSE_PARTIAL


def test_consume_refuses_missing_schema_version() -> None:
    payload = _allow_payload()
    payload.pop("schema_version")
    with pytest.raises(FixtureHardRefuse) as exc:
        consume_fixture_eligibility(payload, consumer="fixture")
    assert exc.value.result is FixtureEligibilityResult.REFUSE_MISSING


def test_chain_serialize_carries_context() -> None:
    env = synthetic_envelope()
    result = assemble_fixture_only(env)
    payload = serialize_fixture_chain(env, result)
    assert payload["chain_contract_id"] == CHAIN_CONTRACT_ID
    assert payload["chain_schema_version"] == CHAIN_SCHEMA_VERSION
    assert payload["forecast"]["game_id"] == env.forecast.game_id
    assert payload["forecast"]["forecast_id"] == env.forecast.forecast_id
    assert payload["provenance"]["protocol_sha"] == env.provenance.protocol_sha
    assert payload["cutoff"]["decision_ts"] == env.provenance.decision_ts
    assert payload["cutoff"]["kickoff_ts"] == env.provenance.kickoff_ts
    assert payload["capability"]["bits"] == ["POINT_MARGIN"]
    assert payload["l1_candidate"]["capture_id"] == result.admitted_capture_id
    assert payload["game_id"] == result.admitted_game_id
    consume_fixture_eligibility(payload["eligibility"], consumer="fixture")


def test_chain_producer_writes_pinned_digest(tmp_path: Path) -> None:
    dest = tmp_path / "chain.json"
    payload = produce_fixture_chain(dest=dest)
    assert dest.exists()
    digest = chain_digest(payload)
    pinned = json.loads((PINNED_CHAIN / "positive-output.json").read_text(encoding="utf-8"))
    assert chain_digest(pinned) == (PINNED_CHAIN / "positive-output.sha256").read_text(encoding="utf-8").strip()
    assert digest == chain_digest(pinned)
    assert payload["chain_contract_id"] == pinned["chain_contract_id"]


def test_chain_refuse_preserves_existing_out(tmp_path: Path) -> None:
    dest = tmp_path / "out.json"
    dest.write_text("ORIGINAL_SENTINEL\n", encoding="utf-8")
    env = synthetic_envelope()
    bad = replace(env, forecast=replace(env.forecast, point_margin=float("inf")))
    with pytest.raises(FixtureHardRefuse):
        produce_fixture_chain(dest=dest, envelope=bad)
    assert dest.read_text(encoding="utf-8") == "ORIGINAL_SENTINEL\n"


@pytest.mark.parametrize(
    "mutator,code",
    [
        (
            lambda env: replace(env, forecast=replace(env.forecast, point_margin=float("inf"))),
            FixtureEligibilityResult.REFUSE_LINE,
        ),
        (
            lambda env: replace(env, l1_candidate={**env.l1_candidate, "capture_id": "0" * 64}),
            FixtureEligibilityResult.REFUSE_IDENTITY,
        ),
        (
            lambda env: synthetic_envelope(forecast_id="0" * 64),
            FixtureEligibilityResult.REFUSE_HASH,
        ),
        (
            lambda env: replace(env, provenance=replace(env.provenance, schema_version="nope")),
            FixtureEligibilityResult.REFUSE_VERSION,
        ),
        (
            lambda env: synthetic_envelope(event_id="2026_99_OTHER"),
            FixtureEligibilityResult.REFUSE_GAME,
        ),
        (
            lambda env: synthetic_envelope(period="h1"),
            FixtureEligibilityResult.REFUSE_PERIOD,
        ),
        (
            lambda env: synthetic_envelope(quote_line=99.5),
            FixtureEligibilityResult.REFUSE_LINE,
        ),
        (
            lambda env: synthetic_envelope(quote_line=3.0, side=QuoteSide.HOME),
            FixtureEligibilityResult.REFUSE_SIGN,
        ),
        (
            lambda env: synthetic_envelope(quote_time="2026-11-08T12:00:00Z"),
            FixtureEligibilityResult.REFUSE_TIME,
        ),
        (
            lambda env: replace(
                env, provenance=replace(env.provenance, decision_ts="2026-11-08T10:00:00Z")
            ),
            FixtureEligibilityResult.REFUSE_CUTOFF,
        ),
        (
            lambda env: replace(env, capability=replace(env.capability, bits=frozenset())),
            FixtureEligibilityResult.REFUSE_PARTIAL,
        ),
        (
            lambda env: synthetic_envelope(fixture=False),
            FixtureEligibilityResult.REFUSE_QUALIFICATION,
        ),
    ],
)
def test_chain_faults_refuse_before_usable_output(mutator, code, tmp_path: Path) -> None:
    dest = tmp_path / "usable.json"
    env = mutator(synthetic_envelope())
    with pytest.raises(FixtureHardRefuse) as exc:
        produce_fixture_chain(dest=dest, envelope=env)
    assert exc.value.result is code
    assert not dest.exists()


def test_forbidden_call_is_instrumented_and_refused() -> None:
    FORBIDDEN_CALL_ATTEMPTS.clear()
    with pytest.raises(FixtureHardRefuse) as exc:
        note_forbidden_call("produce_mu")
    assert exc.value.result is FixtureEligibilityResult.REFUSE_QUALIFICATION
    assert FORBIDDEN_CALL_ATTEMPTS == ["produce_mu"]
    FORBIDDEN_CALL_ATTEMPTS.clear()


def test_channel_is_fixture_only() -> None:
    assert FIXTURE_CHANNEL == "FIXTURE"
    assert CHAIN_SCHEMA_VERSION == "nfl-fixture-chain-v1"
