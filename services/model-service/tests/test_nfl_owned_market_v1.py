"""Isolated nfl_owned_market_v1 tests. CERT=0. RETURN 47318."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.services.nfl_owned_market_v1.clock_lineage import (
    build_clock_lineage_ledger,
    verify_staged_metadata,
)
from src.services.nfl_owned_market_v1.identity_join import (
    _require_full_name,
    build_identity_ledger,
    join_provider_events,
    verify_provider_identities,
)
from src.services.nfl_owned_market_v1.arithmetic import (
    RISK1_U,
    american_profit,
    grade_spread_ats,
    line_clv,
    portfolio_roi,
    settle_ticket,
)
from src.services.nfl_owned_market_v1.constants import (
    CERT,
    PIN_CSV_CLOCK_METADATA_PATH,
    PIN_CSV_CLOCK_METADATA_SHA256,
    PIN_CSV_PROVIDER_EVENT_N,
    PIN_CSV_PROVIDER_IDENTITIES_PATH,
    PIN_CSV_PROVIDER_IDENTITIES_SHA256,
    PIN_CSV_SELECTED_N,
    PIN_INTERSECTION_N,
    PIN_JSONL_143_PROJECTION_PATH,
    PIN_JSONL_143_PROJECTION_SHA256,
    PIN_JSONL_UNKNOWN_N,
    PIN_MISSING_N,
    PIN_REG496_N,
    PIN_SELECTED_187,
    PROFILE_OWNED_MARKET_TRACE,
    PROFILE_SYNTHETIC_MARKET_ECONOMIC_EVENTS,
    ROLE_FICTIONAL_ECONOMIC,
    ROLE_OWNED_READINESS,
)
from src.services.nfl_owned_market_v1.jsonl_trace import (
    build_jsonl_trace_ledger,
    verify_staged_143_projection,
)
from src.services.nfl_owned_market_v1.hashing import require_sha256_hex
from src.services.nfl_owned_market_v1.produce import (
    build_events_document,
    build_trace_document,
    produce_artifacts,
)
from src.services.nfl_owned_market_v1.profiles import handoff_interface
from src.services.nfl_owned_market_v1.refuse import OwnedMarketRefuse
from src.services.nfl_owned_market_v1.schema import schema_hash
from src.services.nfl_owned_market_v1.validate import (
    validate_join,
    validate_owned_market_trace,
    validate_synthetic_market_economic_events,
)


def test_american_profit_risk1_exact() -> None:
    assert american_profit(risk1_u=RISK1_U, juice=-110, won=True) == pytest.approx(100.0 / 110.0)
    assert american_profit(risk1_u=RISK1_U, juice=-110, won=False) == -1.0
    assert american_profit(risk1_u=RISK1_U, juice=150, won=True) == 1.5


def test_ats_win_push_loss() -> None:
    assert grade_spread_ats(side="home", line=-3.0, home_score=24, away_score=20) == "win"
    assert grade_spread_ats(side="home", line=-3.0, home_score=23, away_score=20) == "push"
    assert grade_spread_ats(side="home", line=-3.0, home_score=20, away_score=20) == "loss"


def test_missing_line_refuses() -> None:
    with pytest.raises(OwnedMarketRefuse, match="line required"):
        grade_spread_ats(side="home", line=None, home_score=24, away_score=20)


def test_missing_juice_refuses_roi() -> None:
    ticket = {
        "market": "spread",
        "side": "home",
        "line": -3.0,
        "open_line": -3.0,
        "close_line": -4.0,
        "open_price": -110,
        "close_price": -115,
        "home_score": 24,
        "away_score": 20,
        "juice": None,
        "juice_status": "DATA_GAP",
        "settlement_status": "final",
    }
    with pytest.raises(OwnedMarketRefuse, match="DATA_GAP"):
        settle_ticket(ticket)


def test_no_invent_minus_110() -> None:
    with pytest.raises(OwnedMarketRefuse, match="flat -110"):
        settle_ticket(
            {
                "market": "spread",
                "side": "home",
                "line": -3.0,
                "open_line": -3.0,
                "close_line": -3.0,
                "open_price": -110,
                "close_price": -110,
                "home_score": 24,
                "away_score": 20,
                "juice": None,
                "settlement_status": "final",
            }
        )


def test_line_clv_spread_home() -> None:
    assert line_clv(
        market="spread",
        side="home",
        open_line=-3.0,
        close_line=-4.5,
        open_price=None,
        close_price=None,
    ) == pytest.approx(1.5)


def test_void_excluded_from_roi() -> None:
    settled = [
        {"ats_result": "win", "profit_u": 100.0 / 110.0, "risked_u": 1.0, "roi_eligible": True},
        {"ats_result": "void", "profit_u": 0.0, "risked_u": 0.0, "roi_eligible": False},
        {"ats_result": "push", "profit_u": 0.0, "risked_u": 0.0, "roi_eligible": False},
    ]
    roi = portfolio_roi(settled)
    assert roi["status"] == "ok"
    assert roi["risked_u"] == 1.0
    assert roi["ats"]["v"] == 1
    assert roi["ats"]["p"] == 1


def test_produce_and_separate_profiles(tmp_path: Path) -> None:
    artifacts = produce_artifacts(repo_root=tmp_path)
    assert artifacts["trace_report"]["profile_role"] == ROLE_OWNED_READINESS
    assert artifacts["events_report"]["profile_role"] == ROLE_FICTIONAL_ECONOMIC
    assert artifacts["trace_report"]["owned_completion_claimed"] is False
    assert artifacts["trace"]["data_label"] == "OWNED_IDENTITIES_PROJECTED"
    assert artifacts["trace"]["projection"]["selected_187"]["n"] == 187
    assert artifacts["trace"]["projection"]["missingness_400"]["n"] == 400
    assert artifacts["trace"]["projection"]["selected_187"]["value_fields_copied"] == []
    assert artifacts["trace"]["projection"]["clock"]["invented"] is False
    assert "observations" not in artifacts["trace"]
    assert artifacts["join_report"]["profiles_separate"] is True
    assert artifacts["join_report"]["joined"] is False
    assert artifacts["events_report"]["n_tickets"] == 5
    assert artifacts["events"]["roi"]["status"] == "ok"


def test_handoff_names_roles(tmp_path: Path) -> None:
    artifacts = produce_artifacts(repo_root=tmp_path)
    interface = handoff_interface(artifacts)
    assert interface["worker"] == "B"
    assert interface["cert"] == CERT
    assert interface["profile_roles"][PROFILE_OWNED_MARKET_TRACE] == ROLE_OWNED_READINESS
    assert (
        interface["profile_roles"][PROFILE_SYNTHETIC_MARKET_ECONOMIC_EVENTS]
        == ROLE_FICTIONAL_ECONOMIC
    )
    assert interface["preserves"]["prior_handoff_sha256"].startswith("5b7ee2e4")
    require_sha256_hex(
        interface["profiles"][PROFILE_SYNTHETIC_MARKET_ECONOMIC_EVENTS]["fixture_sha256"],
        name="econ_fixture",
    )
    assert interface["profiles"][PROFILE_OWNED_MARKET_TRACE]["schema_hash"] == schema_hash(
        PROFILE_OWNED_MARKET_TRACE
    )


def test_owned_refuses_fictional_observations() -> None:
    doc = build_trace_document(repo_root=Path.cwd())
    doc["observations"] = [{"seq": 1}]
    with pytest.raises(OwnedMarketRefuse, match="fictional observations"):
        validate_owned_market_trace(doc)


def test_in_memory_builders_validate(tmp_path: Path) -> None:
    trace = build_trace_document(repo_root=tmp_path)
    events = build_events_document()
    assert validate_owned_market_trace(trace)["validated"] is True
    assert validate_synthetic_market_economic_events(events)["validated"] is True
    assert validate_join(trace, events)["profiles_separate"] is True


def test_identity_projection_no_values_no_2223() -> None:
    trace = build_trace_document(repo_root=Path.cwd())
    rows = trace["projection"]["selected_187"]["identities"]
    assert len(rows) == 187
    forbidden = {"line", "price", "spread_home", "home_margin", "price_home", "price_away"}
    seasons = set()
    for row in rows:
        seasons.add(row["season"])
        assert not (set(row) & forbidden)
    assert seasons <= {2020, 2021}


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for path in (here, *here.parents):
        if (path / ".git").exists():
            return path
    raise AssertionError("git root not found")


def test_csv_clock_metadata_sha256_match() -> None:
    raw = verify_staged_metadata(_repo_root() / PIN_CSV_CLOCK_METADATA_PATH)
    assert len(raw) == 19889


def test_clock_lineage_44_and_143_hold() -> None:
    ledger = build_clock_lineage_ledger(_repo_root())
    assert ledger["staged_sha256"] == PIN_CSV_CLOCK_METADATA_SHA256
    assert ledger["n_selected_csv_associations"] == PIN_CSV_SELECTED_N
    assert len(ledger["subset"]) == PIN_CSV_SELECTED_N
    assert ledger["n_jsonl_unknown_preserved"] == PIN_JSONL_UNKNOWN_N
    assert ledger["owned_completion_claimed"] is False
    assert ledger["freeze_limitations_marked_verified"] is False
    assert (
        ledger["provider_historical_timestamp_is_contemporaneous_model_availability"]
        is False
    )
    forbidden = {"line", "price", "spread_home", "home_margin"}
    for row in ledger["subset"]:
        assert not (set(row) & forbidden)
        assert row["pulled_at"].startswith("2026-08-18")
        assert row["request_date"] < "2023-01-01"
    locators = {row["field"] for row in ledger["unresolved"]}
    assert "publication_timestamp_status" in locators
    assert "observation_timestamp_status" in locators


def test_provider_identities_sha256_and_unique_join() -> None:
    root = _repo_root()
    verify_provider_identities(root / PIN_CSV_PROVIDER_IDENTITIES_PATH)
    joined = join_provider_events(root)
    assert joined["n_provider_events"] == PIN_CSV_PROVIDER_EVENT_N
    assert joined["n_proven"] == PIN_CSV_PROVIDER_EVENT_N
    assert joined["n_hold"] == 0
    assert joined["uniqueness"]["bijection"] is True
    assert joined["uniqueness"]["time_tolerance_seconds"] == 0
    assert joined["uniqueness"]["ambiguous_abbreviation_fallback"] is False
    gids = [row["game_id"] for row in joined["proven"]]
    eids = [row["provider_event_id"] for row in joined["proven"]]
    assert len(set(gids)) == len(gids) == PIN_CSV_PROVIDER_EVENT_N
    assert len(set(eids)) == len(eids) == PIN_CSV_PROVIDER_EVENT_N
    assert not (set(gids) & set(eids))


def test_identity_ledger_44_and_holds_honesty() -> None:
    ledger = build_identity_ledger(_repo_root())
    assert ledger["provider_identities_sha256"] == PIN_CSV_PROVIDER_IDENTITIES_SHA256
    assert ledger["n_44_mapped"] == PIN_CSV_SELECTED_N
    assert ledger["n_44_hold"] == 0
    assert ledger["n_jsonl_unknown_preserved"] == PIN_JSONL_UNKNOWN_N
    assert ledger["owned_completion_claimed"] is False
    assert ledger["freeze_limitations_marked_verified"] is False
    for row in ledger["subset"]:
        assert row["identity_status"] == "PROVEN"
        assert row["game_id"]
        assert row["kickoff_utc"] == row["commence_time"]


def test_refuse_ambiguous_short_team_name() -> None:
    with pytest.raises(OwnedMarketRefuse, match="ambiguous"):
        _require_full_name("Los Angeles", field="provider_home_team")
    with pytest.raises(OwnedMarketRefuse, match="ambiguous"):
        _require_full_name("LA", field="provider_home_team")
    assert _require_full_name("Los Angeles Rams", field="home") == "LA"
    assert _require_full_name("Los Angeles Chargers", field="home") == "LAC"


def test_schema_hashes_stable() -> None:
    a = schema_hash(PROFILE_OWNED_MARKET_TRACE)
    b = schema_hash(PROFILE_OWNED_MARKET_TRACE)
    c = schema_hash(PROFILE_SYNTHETIC_MARKET_ECONOMIC_EVENTS)
    require_sha256_hex(a, name="schema_trace")
    require_sha256_hex(c, name="schema_events")
    assert a == b
    assert a != c


def test_jsonl_trace_reconcile_187_44_143_and_96_400() -> None:
    ledger = build_jsonl_trace_ledger(_repo_root())
    rec = ledger["reconcile"]
    assert rec["n_187"] == PIN_SELECTED_187 == 187
    assert rec["n_44"] == PIN_CSV_SELECTED_N == 44
    assert rec["n_143"] == PIN_JSONL_UNKNOWN_N == 143
    assert rec["n_96"] == PIN_INTERSECTION_N == 96
    assert rec["n_400"] == PIN_MISSING_N == 400
    assert rec["n_496"] == PIN_REG496_N == 496
    assert rec["n_23"] == PIN_CSV_PROVIDER_EVENT_N == 23
    assert rec["eq_187_44_143"] is True
    assert rec["eq_496_96_400"] is True
    assert rec["mapped_not_in_quotes"] == 0
    assert len(ledger["bound_143"]) == PIN_JSONL_UNKNOWN_N
    assert len(ledger["mapped_44_pairs"]) == PIN_CSV_SELECTED_N
    assert len(ledger["selected_96_game_ids"]) == PIN_INTERSECTION_N
    assert len(ledger["missing_400_game_ids"]) == PIN_MISSING_N
    assert len(set(ledger["selected_96_game_ids"]) & set(ledger["missing_400_game_ids"])) == 0
    assert ledger["preserved"]["n_proven_events"] == 23
    assert ledger["preserved"]["n_44_mapped"] == 44


def test_jsonl_trace_unique_bind_and_clocks_partial() -> None:
    ledger = build_jsonl_trace_ledger(_repo_root())
    assert ledger["status"] == "PARTIAL"
    assert ledger["owned_completion_claimed"] is False
    assert ledger["freeze_limitations_marked_verified"] is False
    assert ledger["historical_economic_calculation"] is False
    assert ledger["ntbb_k_implemented"] is False
    ids = [(row["game_id"], row["book"]) for row in ledger["bound_143"]]
    assert len(set(ids)) == len(ids) == PIN_JSONL_UNKNOWN_N
    mapped = {(row["game_id"], row["book"]) for row in ledger["mapped_44_pairs"]}
    assert not (set(ids) & mapped)
    seasons = set()
    for row in ledger["bound_143"]:
        seasons.add(row["season"])
        assert row["market"] == "spread"
        assert row["side"] == "home"
        assert row["line_status"] == "BOUND_UNIQUE_FREEZE_AND_ADMISSIBLE"
        assert row["price_status"] == "BOUND_UNIQUE_ADMISSIBLE_SPREAD_ROW"
        assert row["price_home"] is not None
        assert row["price_away"] is not None
        assert row["snapshot_kind"] == "enterprise_snapshot"
        assert row["clocks"]["claimed_capture"]["status"] == "CLAIMED_FIELD_PRESENT_NOT_VERIFIED"
        assert row["clocks"]["claimed_capture"]["value"]
        for name in ("request", "provider", "book_update", "download", "availability"):
            assert row["clocks"][name]["status"] == "NOT_EVALUABLE"
            assert row["clocks"][name]["value"] is None
            assert row["clocks"][name]["count_present"] == 0
        if "snapshots-2022" in row["provenance"]:
            assert row["season"] == 2021
    assert seasons <= {2020, 2021}
    assert ledger["clocks_summary"]["request"] == "NOT_EVALUABLE"
    assert ledger["clocks_summary"]["not_evaluable_n"]["availability"] == PIN_JSONL_UNKNOWN_N
    staged = ledger["staged_143_projection"]
    assert staged["sha256"] == PIN_JSONL_143_PROJECTION_SHA256
    assert staged["sha256_match"] is True
    assert staged["value_pairs_match_bound_143"] is True
    assert staged["clock_semantics_verified_n"] == 0
    assert staged["contemporaneous_availability_verified_n"] == 0
    assert all(row["status"] == "NOT_EVALUABLE" for row in staged["raw_snapshot_files"])
    verify_staged_143_projection(_repo_root() / PIN_JSONL_143_PROJECTION_PATH)


def test_jsonl_trace_does_not_replace_risk1(tmp_path: Path) -> None:
    artifacts = produce_artifacts(repo_root=tmp_path)
    assert artifacts["events_report"]["profile_role"] == ROLE_FICTIONAL_ECONOMIC
    assert artifacts["events_report"]["n_tickets"] == 5
    assert artifacts["trace"]["owned_completion_claimed"] is False
    assert artifacts["join_report"]["joined"] is False
    settled = artifacts["events"]["settlements"]
    assert any(row.get("ats_result") == "win" for row in settled)
    assert artifacts["events"]["roi"]["status"] == "ok"
