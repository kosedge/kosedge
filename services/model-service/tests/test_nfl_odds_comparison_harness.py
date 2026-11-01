"""End-to-end path tests for the synthetic NFL odds comparison harness."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from src.services.nfl_odds_comparison_harness import (
    AMBIGUOUS_IDENTITY,
    DUPLICATE_GAME,
    FORECAST_SCHEMA,
    INCOMPATIBLE_LINE,
    MANIFEST_SCHEMA,
    MISSING_PROBABILITY,
    NOT_SYNTHETIC,
    REAL_OUTCOME_REFUSED,
    REPORT_SCHEMA,
    SEASON_OUT_OF_BOUNDS,
    SYNTHETIC_LABEL,
    SYNTHETIC_PURPOSE,
    HarnessRefusal,
    american_implied_prob,
    compare_forecasts_to_manifest,
    grade_synthetic_outcome,
    line_for_side,
    load_forecast_file,
    load_odds_manifest,
    run_comparison_files,
)
from src.services.nfl_odds_reader import POST_CUTOFF, SIGN_CONVENTION, line_for_side as reader_line_for_side

ROOT = Path(__file__).resolve().parents[3]
EXAMPLE_DIR = ROOT / "data" / "ops" / "nfl-odds-comparison-harness-t5100u"
EXAMPLE_FORECASTS = EXAMPLE_DIR / "fixtures" / "example-forecasts.json"
EXAMPLE_MANIFEST = EXAMPLE_DIR / "fixtures" / "example-odds-manifest.json"
CLI = ROOT / "scripts" / "nfl" / "run_nfl_odds_comparison_harness.py"

CUTOFF = "2020-09-10T20:00:00Z"


def _header(schema: str) -> dict:
    return {
        "schema_version": schema,
        "label": SYNTHETIC_LABEL,
        "cert_candidate": 0,
        "purpose": SYNTHETIC_PURPOSE,
        "sport": "nfl",
    }


def _game(**overrides) -> dict:
    row = {
        "game_id": "2020_01_HOU_KC",
        "event_id": "evt-kc-hou",
        "season": 2020,
        "game_date": "2020-09-10",
        "home_team": "KC",
        "away_team": "HOU",
        "kickoff": "2020-09-10T20:20:00Z",
        "forecast_cutoff": CUTOFF,
    }
    row.update(overrides)
    return row


def _quote(**overrides) -> dict:
    row = {
        "event_id": "evt-kc-hou",
        "season": 2020,
        "game_date": "2020-09-10",
        "home": "Kansas City Chiefs",
        "away": "Houston Texans",
        "book": "draftkings",
        "market": "spreads",
        "spread_home": -9.5,
        "price_home": -110,
        "price_away": -110,
        "captured_at": "2020-09-10T19:50:00Z",
        "snapshot_kind": "mid",
        "source": "synthetic",
        "provenance": "synthetic_owned_odds",
    }
    row.update(overrides)
    return row


def _forecast(**overrides) -> dict:
    row = {
        "game_id": "2020_01_HOU_KC",
        "event_id": "evt-kc-hou",
        "season": 2020,
        "game_date": "2020-09-10",
        "home_team": "KC",
        "away_team": "HOU",
        "forecast_cutoff": CUTOFF,
        "provenance": "synthetic_forecast",
        "markets": {
            "spread": {"prediction": -9.0, "p_home_cover": 0.58},
        },
    }
    row.update(overrides)
    return row


def _payloads(forecasts, games, quotes, outcomes=None):
    forecast_payload = {
        **_header(FORECAST_SCHEMA),
        "forecast_cutoff": CUTOFF,
        "forecasts": forecasts,
        "synthetic_outcomes": outcomes or [],
    }
    manifest_payload = {
        **_header(MANIFEST_SCHEMA),
        "games": games,
        "quotes": quotes,
    }
    return forecast_payload, manifest_payload


def _run(forecasts, games, quotes, outcomes=None):
    forecast_payload, manifest_payload = _payloads(forecasts, games, quotes, outcomes)
    return compare_forecasts_to_manifest(forecast_payload, manifest_payload)


def test_e2e_home_away_signs_are_preserved_and_away_flip_is_explicit() -> None:
    home_fav = _run(
        [_forecast(markets={"spread": {"prediction": -9.0, "p_home_cover": 0.58}})],
        [_game()],
        [_quote(spread_home=-9.5)],
    )
    assert len(home_fav.comparisons) == 1
    row = home_fav.comparisons[0]
    assert row.market_line == -9.5
    assert row.home_line == -9.5
    assert row.away_line == 9.5
    assert row.away_line == reader_line_for_side(row.home_line, "away")
    assert row.sign_convention == SIGN_CONVENTION
    assert row.line_delta == pytest.approx(0.5)

    home_dog = _run(
        [
            _forecast(
                game_id="2020_01_NYJ_BUF",
                event_id="evt-buf-nyj",
                game_date="2020-09-13",
                home_team="BUF",
                away_team="NYJ",
                forecast_cutoff="2020-09-13T17:00:00Z",
                markets={"spread": {"prediction": 2.5, "p_home_cover": 0.47}},
            )
        ],
        [
            _game(
                game_id="2020_01_NYJ_BUF",
                event_id="evt-buf-nyj",
                game_date="2020-09-13",
                home_team="BUF",
                away_team="NYJ",
                forecast_cutoff="2020-09-13T17:00:00Z",
            )
        ],
        [
            _quote(
                event_id="evt-buf-nyj",
                game_date="2020-09-13",
                home="Buffalo Bills",
                away="New York Jets",
                book="fanduel",
                spread_home=3.0,
                captured_at="2020-09-13T16:30:00Z",
            )
        ],
    )
    dog = home_dog.comparisons[0]
    assert dog.home_line == 3.0
    assert dog.away_line == -3.0
    assert line_for_side(dog.home_line, "home") == 3.0
    assert line_for_side(dog.home_line, "away") == -3.0
    assert dog.line_delta == pytest.approx(-0.5)


def test_e2e_incompatible_lines_are_excluded_not_compared() -> None:
    report = _run(
        [_forecast(markets={"spread": {"prediction": -9.0, "p_home_cover": 0.58}})],
        [_game()],
        [_quote(market="totals", spread_home=None, total_points=54.5, over_price=-110)],
    )
    assert report.comparisons == []
    assert report.reason_tallies[INCOMPATIBLE_LINE] == 1
    assert all(row.reason != "" for row in report.excluded)


def test_e2e_duplicate_games_are_excluded_not_merged() -> None:
    report = _run(
        [
            _forecast(game_id="2020_01_HOU_KC"),
            _forecast(game_id="2020_01_HOU_KC", markets={"spread": {"prediction": -3.0, "p_home_cover": 0.40}}),
        ],
        [_game()],
        [_quote()],
    )
    assert report.comparisons == []
    assert report.reason_tallies[DUPLICATE_GAME] == 2


def test_e2e_missing_probabilities_are_excluded_not_filled() -> None:
    report = _run(
        [_forecast(markets={"spread": {"prediction": -9.0}})],
        [_game()],
        [_quote()],
    )
    assert report.comparisons == []
    assert report.reason_tallies[MISSING_PROBABILITY] == 1
    assert all("forecast_p" not in item.row for item in report.excluded)


def test_e2e_ties_and_pushes_use_synthetic_outcomes_only() -> None:
    push = _run(
        [_forecast()],
        [_game()],
        [_quote(spread_home=-7.0)],
        outcomes=[{"game_id": "2020_01_HOU_KC", "home_score": 24, "away_score": 17, "source": "synthetic"}],
    )
    assert push.comparisons[0].synthetic_outcome["result"] == "push"
    assert push.comparisons[0].synthetic_outcome["source"] == "synthetic"
    assert grade_synthetic_outcome("spread", -7.0, 24, 17) == "push"

    tie = _run(
        [_forecast(markets={"moneyline": {"p_home": 0.61}})],
        [_game()],
        [_quote(market="h2h", spread_home=None, price_home=-150, price_away=130)],
        outcomes=[{"game_id": "2020_01_HOU_KC", "home_score": 20, "away_score": 20, "source": "synthetic"}],
    )
    assert tie.comparisons[0].synthetic_outcome["result"] == "tie"

    total_push = _run(
        [_forecast(markets={"total": {"prediction": 44.0, "p_over": 0.50}})],
        [_game()],
        [_quote(market="totals", spread_home=None, total_points=44.0, over_price=-110)],
        outcomes=[{"game_id": "2020_01_HOU_KC", "home_score": 21, "away_score": 23, "source": "synthetic"}],
    )
    assert total_push.comparisons[0].synthetic_outcome["result"] == "push"


def test_e2e_post_cutoff_quotes_are_excluded_and_later_close_is_not_used() -> None:
    report = _run(
        [_forecast()],
        [_game()],
        [
            _quote(spread_home=-3.5, captured_at="2020-09-10T19:00:00Z", snapshot_kind="open"),
            _quote(spread_home=-9.5, captured_at="2020-09-10T20:15:00Z", snapshot_kind="close"),
        ],
    )
    assert len(report.comparisons) == 1
    assert report.comparisons[0].market_line == -3.5
    assert report.comparisons[0].captured_at.endswith("19:00:00Z")
    assert report.reason_tallies[POST_CUTOFF] == 1
    assert all(row.market_line != -9.5 for row in report.comparisons)


def test_e2e_ambiguous_identities_are_excluded() -> None:
    report = _run(
        [
            _forecast(
                game_id="2020_01_LA_SF",
                event_id="",
                home_team="Los Angeles",
                away_team="SF",
                markets={"spread": {"prediction": -3.0, "p_home_cover": 0.55}},
            )
        ],
        [
            _game(
                game_id="2020_01_LA_SF",
                event_id="",
                home_team="LA",
                away_team="SF",
            )
        ],
        [
            _quote(
                event_id="",
                home="Los Angeles",
                away="San Francisco 49ers",
                spread_home=-3.0,
            )
        ],
    )
    assert report.comparisons == []
    assert report.reason_tallies[AMBIGUOUS_IDENTITY] >= 1


def test_e2e_invalid_inputs_refuse_and_never_fabricate(tmp_path: Path) -> None:
    real_forecast = {
        **_header(FORECAST_SCHEMA),
        "label": "RESEARCH_ENG",
        "forecasts": [_forecast()],
    }
    bad = tmp_path / "real-forecasts.json"
    bad.write_text(json.dumps(real_forecast), encoding="utf-8")
    with pytest.raises(HarnessRefusal) as refused:
        load_forecast_file(bad)
    assert refused.value.reason == NOT_SYNTHETIC

    real_outcome = {
        **_header(FORECAST_SCHEMA),
        "forecasts": [_forecast()],
        "synthetic_outcomes": [
            {"game_id": "2020_01_HOU_KC", "home_score": 34, "away_score": 20, "source": "nflverse"}
        ],
    }
    real_path = tmp_path / "real-outcomes.json"
    real_path.write_text(json.dumps(real_outcome), encoding="utf-8")
    with pytest.raises(HarnessRefusal) as real_exc:
        load_forecast_file(real_path)
    assert real_exc.value.reason == REAL_OUTCOME_REFUSED

    late = {
        **_header(FORECAST_SCHEMA),
        "forecasts": [_forecast(season=2024)],
    }
    late_path = tmp_path / "late.json"
    late_path.write_text(json.dumps(late), encoding="utf-8")
    with pytest.raises(HarnessRefusal) as late_exc:
        load_forecast_file(late_path)
    assert late_exc.value.reason == SEASON_OUT_OF_BOUNDS

    paid = {
        **_header(MANIFEST_SCHEMA),
        "games": [_game()],
        "quotes": [_quote(source="https://the-odds-api.com/v4", provenance="synthetic")],
    }
    paid_path = tmp_path / "paid.json"
    paid_path.write_text(json.dumps(paid), encoding="utf-8")
    with pytest.raises(HarnessRefusal):
        load_odds_manifest(paid_path)


def test_e2e_cli_example_fixtures_are_reproducible(tmp_path: Path) -> None:
    assert EXAMPLE_FORECASTS.is_file()
    assert EXAMPLE_MANIFEST.is_file()
    dest = tmp_path / "example-output.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(CLI),
            "--forecasts",
            str(EXAMPLE_FORECASTS),
            "--odds-manifest",
            str(EXAMPLE_MANIFEST),
            "--output",
            str(dest),
        ],
        check=False,
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        env={**dict(**{k: v for k, v in __import__("os").environ.items()}), "PYTHONPATH": str(ROOT / "services" / "model-service")},
    )
    assert proc.returncode == 0, proc.stderr
    report = json.loads(dest.read_text(encoding="utf-8"))
    assert report["schema_version"] == REPORT_SCHEMA
    assert report["label"] == SYNTHETIC_LABEL
    assert report["cert_candidate"] == 0
    assert report["eval"] is None
    assert report["scoring"] is None
    assert report["comparison_n"] == 4
    books_markets = {(row["book"], row["market"]) for row in report["comparisons"]}
    assert ("draftkings", "spread") in books_markets
    assert ("draftkings", "total") in books_markets
    assert ("draftkings", "moneyline") in books_markets
    assert ("fanduel", "spread") in books_markets
    kc = next(row for row in report["comparisons"] if row["game_id"] == "2020_01_HOU_KC" and row["market"] == "spread")
    assert kc["home_line"] == -9.5
    assert kc["away_line"] == 9.5
    assert kc["captured_at"].endswith("19:50:00Z")
    assert report["reason_tallies"].get(POST_CUTOFF) == 1
    buf = next(row for row in report["comparisons"] if row["game_id"] == "2020_01_NYJ_BUF")
    assert buf["home_line"] == 3.0
    assert buf["away_line"] == -3.0
    assert buf["synthetic_outcome"]["result"] == "home_cover"

    saved = json.loads((EXAMPLE_DIR / "example-output.json").read_text(encoding="utf-8"))
    assert saved["comparison_n"] == report["comparison_n"]
    assert saved["reason_tallies"] == report["reason_tallies"]
    assert [
        (row["game_id"], row["book"], row["market"], row["market_line"], row["home_line"], row["away_line"])
        for row in saved["comparisons"]
    ] == [
        (row["game_id"], row["book"], row["market"], row["market_line"], row["home_line"], row["away_line"])
        for row in report["comparisons"]
    ]


def test_e2e_library_path_matches_cli_on_example_files() -> None:
    report = run_comparison_files(EXAMPLE_FORECASTS, EXAMPLE_MANIFEST)
    assert report.cert_candidate == 0
    assert report.refused is False
    assert len(report.comparisons) == 4
    assert american_implied_prob(-110) == pytest.approx(110 / 210)
    assert report.as_dict()["eval"] is None
