"""t5178u W-FIX-A — OPT-IN fixture assembly. Synthetic only.

Zero simulator / produce_mu / forecast / result-loader / network / DB / jobs.
Does not read real outcomes. Does not mutate pinned artifacts.
"""

from __future__ import annotations

import ast
import json
from dataclasses import replace
from datetime import timedelta
from pathlib import Path

import pytest

from src.services.nfl_fixture_assembly.assemble import (
    NON_FIXTURE_CONSUMERS,
    assemble_fixture_batch,
    assemble_fixture_only,
    consume_eligibility,
    forbidden_import_names,
    forbidden_name_tokens,
)
from src.services.nfl_fixture_assembly.contract import (
    CONTRACT_ID,
    SYNTHETIC_ADJUSTMENT_POLICY,
    CapabilityRecord,
    FixtureEligibilityResult,
    FixtureHardRefuse,
    FixturePeriod,
    ForecastCapability,
    QuoteSide,
    RequestedOutput,
    expected_quote_line,
)
from src.services.nfl_fixture_assembly.synth import (
    SYNTH_BOOK,
    SYNTH_GAME_ID,
    synthetic_envelope,
    synthetic_l1_row,
)
from src.services.nfl_hhl1_capture import validate_l1_candidate
from src.services.nfl_hhl1_capture.identity import make_capture_id

PACKAGE_DIR = Path(__file__).resolve().parents[1] / "src" / "services" / "nfl_fixture_assembly"
PINNED_DIR = Path(__file__).resolve().parents[3] / "data" / "ops" / "t5178u-wfix-a"


def _refuse(envelope, expected: FixtureEligibilityResult) -> FixtureHardRefuse:
    with pytest.raises(FixtureHardRefuse) as exc:
        assemble_fixture_only(envelope)
    assert exc.value.result is expected
    assert exc.value.partial is False
    assert "partial" not in exc.value.to_dict() or exc.value.to_dict()["partial"] is False
    assert "quote" not in exc.value.to_dict()
    return exc.value


def test_positive_point_margin_allow_fixture(tmp_path: Path) -> None:
    envelope = synthetic_envelope(point_margin=3.0, side=QuoteSide.HOME)
    result = assemble_fixture_only(envelope)
    assert result.eligibility.result is FixtureEligibilityResult.ALLOW_FIXTURE
    assert result.eligibility.fixture is True
    assert result.eligibility.subscriber_consumable is False
    assert result.eligibility.betting_consumable is False
    assert result.eligibility.production_consumable is False
    assert result.eligibility.env_bypass_honored is False
    assert result.eligibility.cacheable is False
    assert result.quote.fixture is True
    assert result.quote.transport_only is True
    assert result.quote.injury_policy_approved is False
    assert result.quote.book == SYNTH_BOOK
    assert result.quote.event_id == SYNTH_GAME_ID
    assert result.quote.side == "HOME"
    assert result.quote.period == "full_game"
    assert result.quote.line == -3.0
    assert result.quote.price == -110
    assert result.offense_raw == 0.12
    assert result.defense_raw == -0.08
    assert result.offense_multiplier == 0.97
    assert result.defense_multiplier == 1.03
    assert result.adjustment_policy == SYNTHETIC_ADJUSTMENT_POLICY
    assert result.capability_bits == ("POINT_MARGIN",)
    admitted = validate_l1_candidate(envelope.l1_candidate)
    assert admitted.capture_id == result.admitted_capture_id
    consume_eligibility(result.eligibility, consumer="fixture")

    payload = result.to_dict()
    out = tmp_path / "positive-output.json"
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    pinned = PINNED_DIR / "positive-output.json"
    assert pinned.exists(), "pinned positive-output.json missing"
    expected = json.loads(pinned.read_text(encoding="utf-8"))
    assert expected["eligibility"]["result"] == "ALLOW_FIXTURE"
    assert expected["quote"]["line"] == -3.0
    assert expected["adjustment_policy"] == SYNTHETIC_ADJUSTMENT_POLICY
    assert expected["contract_id"] == CONTRACT_ID


def test_away_side_line_sign() -> None:
    result = assemble_fixture_only(synthetic_envelope(point_margin=3.0, side=QuoteSide.AWAY))
    assert result.quote.side == "AWAY"
    assert result.quote.line == 3.0
    assert expected_quote_line(point_margin=3.0, side=QuoteSide.AWAY) == 3.0


def test_batch_two_teams_atomic() -> None:
    home = synthetic_envelope(team_ignored=True)
    away_l1 = synthetic_l1_row(team="TST", game_id=SYNTH_GAME_ID)
    away = synthetic_envelope(l1_candidate=away_l1, game_id=SYNTH_GAME_ID)
    rows = assemble_fixture_batch([home, away])
    assert len(rows) == 2
    assert {r.admitted_game_id for r in rows} == {SYNTH_GAME_ID}


@pytest.mark.parametrize(
    "requested,code",
    [
        (RequestedOutput.TOTAL, FixtureEligibilityResult.REFUSE_TOTALS),
        (RequestedOutput.MONEYLINE, FixtureEligibilityResult.REFUSE_MONEYLINE),
        (RequestedOutput.COVER_PROBABILITY, FixtureEligibilityResult.REFUSE_COVER_PROBABILITY),
        (RequestedOutput.ECONOMIC_ELIGIBILITY, FixtureEligibilityResult.REFUSE_ECONOMIC_ELIGIBILITY),
    ],
)
def test_point_margin_hard_refuses_unsupported_outputs(
    requested: RequestedOutput, code: FixtureEligibilityResult
) -> None:
    _refuse(synthetic_envelope(requested_output=requested), code)


def test_joint_score_bit_does_not_unlock_totals() -> None:
    _refuse(
        synthetic_envelope(
            capability_bits=frozenset(
                {ForecastCapability.POINT_MARGIN, ForecastCapability.JOINT_SCORE}
            ),
            requested_output=RequestedOutput.TOTAL,
        ),
        FixtureEligibilityResult.REFUSE_QUALIFICATION,
    )


def test_refuse_identity_bad_capture_id() -> None:
    l1 = synthetic_l1_row()
    l1["capture_id"] = "0" * 64
    _refuse(synthetic_envelope(l1_candidate=l1), FixtureEligibilityResult.REFUSE_IDENTITY)


def test_refuse_hash_bad_forecast_id() -> None:
    _refuse(synthetic_envelope(forecast_id="0" * 64), FixtureEligibilityResult.REFUSE_HASH)


def test_refuse_version_schema_mismatch() -> None:
    env = synthetic_envelope()
    _refuse(
        replace(env, provenance=replace(env.provenance, schema_version="not-the-l1-version")),
        FixtureEligibilityResult.REFUSE_VERSION,
    )


def test_refuse_game_event_mismatch() -> None:
    _refuse(synthetic_envelope(event_id="2026_99_OTHER"), FixtureEligibilityResult.REFUSE_GAME)


def test_refuse_period_h1() -> None:
    _refuse(synthetic_envelope(period=FixturePeriod.H1), FixtureEligibilityResult.REFUSE_PERIOD)


def test_refuse_line_wrong_number() -> None:
    _refuse(synthetic_envelope(quote_line=99.5), FixtureEligibilityResult.REFUSE_LINE)


def test_refuse_sign_flipped() -> None:
    _refuse(synthetic_envelope(quote_line=3.0, side=QuoteSide.HOME), FixtureEligibilityResult.REFUSE_SIGN)


def test_refuse_time_quote_clock() -> None:
    _refuse(
        synthetic_envelope(quote_time="2026-11-08T12:00:00Z"),
        FixtureEligibilityResult.REFUSE_TIME,
    )


def test_refuse_cutoff_decision_not_kickoff_minus_90() -> None:
    env = synthetic_envelope()
    _refuse(
        replace(env, provenance=replace(env.provenance, decision_ts="2026-11-08T10:00:00Z")),
        FixtureEligibilityResult.REFUSE_CUTOFF,
    )


def test_refuse_capability_missing_point_margin_bit() -> None:
    _refuse(
        synthetic_envelope(capability=CapabilityRecord(bits=frozenset({ForecastCapability.JOINT_SCORE}))),
        FixtureEligibilityResult.REFUSE_CAPABILITY,
    )


def test_refuse_qualification_fixture_flag_off() -> None:
    _refuse(synthetic_envelope(fixture=False), FixtureEligibilityResult.REFUSE_QUALIFICATION)


def test_refuse_missing_l1_registry() -> None:
    l1 = synthetic_l1_row()
    l1.pop("registry_id", None)
    _refuse(synthetic_envelope(l1_candidate=l1), FixtureEligibilityResult.REFUSE_MISSING)


def test_refuse_stale_after_kickoff() -> None:
    from src.services.nfl_fixture_assembly.synth import KICKOFF, iso

    late = iso(KICKOFF + timedelta(minutes=5))
    l1 = synthetic_l1_row()
    l1["captured_at"] = late
    l1["as_of_ts"] = late
    payload = {
        k: l1[k]
        for k in (
            "game_id",
            "team",
            "factor",
            "as_of_ts",
            "decision_ts",
            "kickoff_ts",
            "baseline_personnel_ref",
            "expected_starters_asof",
            "registry_id",
            "source_snapshot_id",
            "offense_raw",
            "defense_raw",
            "offense_multiplier",
            "defense_multiplier",
            "delta_players",
            "missing_enum",
            "supersedes_capture_id",
            "uncertainty",
            "schema_version",
        )
    }
    payload["baseline_personnel_ref"] = dict(l1["baseline_personnel_ref"])
    l1["capture_id"] = make_capture_id(
        payload=payload,
        source_id=l1["provenance"]["source_id"],
        source_published_at=l1["source_published_at"],
        captured_at=late,
    )
    env = synthetic_envelope(l1_candidate=l1, quote_time=late)
    _refuse(env, FixtureEligibilityResult.REFUSE_STALE)


def test_refuse_partial_empty_capability() -> None:
    _refuse(
        synthetic_envelope(capability=CapabilityRecord(bits=frozenset())),
        FixtureEligibilityResult.REFUSE_PARTIAL,
    )


def test_refuse_cache_shared() -> None:
    _refuse(synthetic_envelope(cacheable=True), FixtureEligibilityResult.REFUSE_CACHE)


def test_refuse_production_mode() -> None:
    _refuse(synthetic_envelope(production_mode=True), FixtureEligibilityResult.REFUSE_PRODUCTION_CHANNEL)


def test_refuse_env_bypass_flag() -> None:
    _refuse(synthetic_envelope(honor_env_bypass=True), FixtureEligibilityResult.REFUSE_ENV_BYPASS)


def test_env_var_does_not_upgrade_allow_fixture(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NFL_EDGE_BOARD_INTERNAL", "1")
    monkeypatch.setenv("NFL_FIXTURE_ALLOW_PRODUCTION", "true")
    result = assemble_fixture_only(synthetic_envelope())
    assert result.eligibility.result is FixtureEligibilityResult.ALLOW_FIXTURE
    assert result.eligibility.production_consumable is False
    assert result.eligibility.env_bypass_honored is False
    for consumer in sorted(NON_FIXTURE_CONSUMERS):
        with pytest.raises(FixtureHardRefuse) as exc:
            consume_eligibility(result.eligibility, consumer=consumer)
        assert exc.value.result is FixtureEligibilityResult.REFUSE_PRODUCTION_CHANNEL


def test_refuse_market_fields_on_l1() -> None:
    l1 = synthetic_l1_row(extra={"price": -110})
    _refuse(synthetic_envelope(l1_candidate=l1), FixtureEligibilityResult.REFUSE_MARKET_FIELDS)


def test_hard_refuse_has_no_partial_object() -> None:
    with pytest.raises(FixtureHardRefuse) as exc:
        assemble_fixture_only(synthetic_envelope(requested_output=RequestedOutput.TOTAL))
    dumped = exc.value.to_dict()
    assert dumped["result"] == "REFUSE_TOTALS"
    assert dumped["partial"] is False
    assert "quote" not in dumped
    assert "admitted_capture_id" not in dumped


def test_package_imports_no_simulator_network_db_jobs() -> None:
    forbidden = forbidden_import_names()
    tokens = forbidden_name_tokens()
    for path in PACKAGE_DIR.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text, filename=str(path))
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
                imported.add(node.module.split(".")[0])
        overlap = imported & forbidden
        assert not overlap, f"{path.name} imports forbidden {overlap}"
        lowered = text.lower()
        for token in tokens:
            if token in ("produce_mu", "result_loader", "fetch_nowcast", "acquire_odds"):
                assert f"{token}(" not in text, f"{path.name} calls {token}"
                continue
            assert token not in lowered, f"{path.name} mentions forbidden token {token}"


def test_tests_do_not_import_live_or_outcome_loaders() -> None:
    text = Path(__file__).read_text(encoding="utf-8")
    tree = ast.parse(text)
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
        elif isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
    assert "src.services.nfl_simulator" not in imported
    assert "src.tasks" not in imported
    assert "src.services.nfl_props_eligibility" not in imported
    assert "src.services.nfl_injury_nowcast" not in imported
