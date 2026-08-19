"""NFL odds-lake open/close/path reduction (no Postgres, no HD required)."""

from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src.services.nfl_clv_semantics import spread_clv
from src.services.nfl_warehouse.odds_lake import overlay_closing_lines, reduce_open_close, reduce_path, team_abbr
from src.services.nfl_warehouse.path_features import sides_agree, steam_home_favored
from src.services.nfl_warehouse.period_diagnostics import diagnose_mainline
from src.services.nfl_warehouse.sb_residual import sb_residuals
from src.services.nfl_warehouse.weekly_prop_means import overlay_weekly_mean, should_touch_season_artifacts


def test_team_abbr_accepts_full_name_and_code() -> None:
    assert team_abbr("Kansas City Chiefs") == "KC"
    assert team_abbr("KC") == "KC"
    assert team_abbr("LAR") == "LA"
    assert team_abbr("Washington Football Team") == "WAS"


def test_overlay_joins_nflverse_abbrs_to_full_lake_names() -> None:
    snaps = [
        {
            "game_date": "2020-09-11",
            "home": "Kansas City Chiefs",
            "away": "Houston Texans",
            "home_abbr": "KC",
            "away_abbr": "HOU",
            "market": "spread",
            "book": "draftkings",
            "spread_home": -9.5,
            "snapshot_kind": "close",
            "captured_at": "2020-09-10T23:50:00+00:00",
        }
    ]
    games = [
        {
            "game_date": "2020-09-11",
            "kickoff": "2020-09-11T00:20:00+00:00",
            "home_team": "KC",
            "away_team": "HOU",
            "season": 2020,
        }
    ]
    merged, stats = overlay_closing_lines(games, snaps)
    assert stats["matched_with_close_spread"] == 1
    assert merged[0]["owned_close_spread_home_favored"] == 9.5


def test_steam_agreement_uses_home_favored_sign() -> None:
    assert steam_home_favored(-3.0) == 3.0
    assert sides_agree(2.5, 3.0) is True
    assert sides_agree(2.5, -3.0) is False
    assert sides_agree(2.5, 0.5) is False


def test_post_kickoff_snapshot_is_not_the_close() -> None:
    snaps = [
        {
            "market": "spread",
            "book": "draftkings",
            "spread_home": -3.5,
            "snapshot_kind": "open",
            "captured_at": "2024-09-05T17:00:00+00:00",
        },
        {
            "market": "spread",
            "book": "draftkings",
            "spread_home": -6.5,
            "snapshot_kind": "close",
            "captured_at": "2024-09-08T16:50:00+00:00",
        },
        {
            "market": "spread",
            "book": "draftkings",
            "spread_home": -2.5,
            "snapshot_kind": "close",
            "captured_at": "2024-09-08T17:05:00+00:00",
        },
    ]
    reduced = reduce_open_close(
        snaps,
        kickoff="2024-09-08T17:00:00+00:00",
        game_date="2024-09-08",
    )
    assert reduced["open_spread_home"] == -3.5
    assert reduced["close_spread_home"] == -6.5


def test_path_steam_is_close_minus_earlier() -> None:
    snaps = [
        {
            "market": "spread",
            "book": "draftkings",
            "spread_home": -3.0,
            "snapshot_kind": "pre7d",
            "captured_at": "2024-09-01T17:00:00+00:00",
        },
        {
            "market": "spread",
            "book": "draftkings",
            "spread_home": -6.0,
            "snapshot_kind": "close",
            "captured_at": "2024-09-08T16:50:00+00:00",
        },
    ]
    path = reduce_path(snaps, kickoff="2024-09-08T17:00:00+00:00", game_date="2024-09-08")
    assert path["steam_spread_pre7d"] == -3.0


def test_spread_clv_home_beats_when_line_moves_toward_home() -> None:
    assert spread_clv(side="home", open_spread_home=-3.0, close_spread_home=-6.0) == 3.0
    assert spread_clv(side="away", open_spread_home=-3.0, close_spread_home=-6.0) == -3.0


def test_period_diagnostics_are_not_a_product() -> None:
    out = diagnose_mainline(
        actual_home_margin=-3.0,
        actual_total=41.0,
        close_spread_home=-6.5,
        close_total=44.5,
        open_spread_home=-2.5,
        h1_spread_home=-2.5,
    )
    assert out["product"] is False
    assert any("key_number" in r for r in out["reasons"])


def test_sb_residual_does_not_train_on_small_error() -> None:
    report = sb_residuals(
        [
            {"team": "KC", "market_price": -200, "model_title_prob": 0.66},
            {"team": "SF", "market_price": 250, "model_title_prob": 0.28},
        ]
    )
    assert report["n"] == 2
    assert report["train_new_futures_model"] in {True, False}


def test_season_artifacts_stay_untouched() -> None:
    assert should_touch_season_artifacts() is False
    assert overlay_weekly_mean("pass_yds", 260.0, close_line=250.0, enabled=False) == 260.0


def test_prop_name_key_matches_usage_abbrev() -> None:
    from src.services.nfl_warehouse.prop_join import normalize_player_key, pick_close_by_player

    assert normalize_player_key("Patrick Mahomes") == normalize_player_key("P.Mahomes")
    assert normalize_player_key("Amon-Ra St. Brown") == normalize_player_key("A.St. Brown")
    assert normalize_player_key("Patrick Mahomes|Over") == "p.mahomes"
    picked = pick_close_by_player(
        [
            {"event_id": "e1", "player_key": "p.mahomes", "market": "pass_yds", "book": "betmgm", "captured_at": "b", "line": 270},
            {"event_id": "e1", "player_key": "p.mahomes", "market": "pass_yds", "book": "draftkings", "captured_at": "a", "line": 275},
        ]
    )
    assert len(picked) == 1
    assert picked[0]["line"] == 275


def test_labeled_dk_fd_close_beats_unlabeled_path_mid() -> None:
    snaps = [
        {
            "market": "spread",
            "book": "draftkings",
            "spread_home": -3.0,
            "snapshot_kind": "mid",
            "captured_at": "2024-09-05T17:00:00+00:00",
        },
        {
            "market": "spread",
            "book": "fanduel",
            "spread_home": -7.0,
            "snapshot_kind": "close",
            "captured_at": "2024-09-08T16:40:00+00:00",
        },
        {
            "market": "spread",
            "book": "nflverse",
            "spread_home": -6.5,
            "snapshot_kind": "close",
            "captured_at": "2024-09-08T08:00:00+00:00",
        },
    ]
    reduced = reduce_open_close(
        snaps,
        kickoff="2024-09-08T17:00:00+00:00",
        game_date="2024-09-08",
    )
    assert reduced["close_spread_home"] == -7.0


def test_true_close_is_kickoff_safe_and_flips_nflverse_sign() -> None:
    from src.services.nfl_warehouse.true_close import nflverse_close_row, reduce_labeled_open_close

    labeled = reduce_labeled_open_close(
        [
            {
                "market": "spread",
                "book": "draftkings",
                "spread_home": -3.5,
                "captured_at": "2024-09-08T16:50:00+00:00",
            },
            {
                "market": "spread",
                "book": "draftkings",
                "spread_home": -2.5,
                "captured_at": "2024-09-08T17:05:00+00:00",
            },
        ],
        kickoff="2024-09-08T17:00:00+00:00",
        game_date="2024-09-08",
        season=2024,
        home="KC",
        away="BAL",
    )
    closes = [r for r in labeled if r["snapshot_kind"] == "close"]
    assert len(closes) == 1
    assert closes[0]["spread_home"] == -3.5

    nv = nflverse_close_row(
        {
            "game_date": "2024-09-08",
            "home_team": "KC",
            "away_team": "BAL",
            "spread_line": 3.5,
            "total_line": 47.5,
            "kickoff": "2024-09-08T17:00:00+00:00",
            "season": 2024,
        }
    )
    spread = next(r for r in nv if r["market"] == "spread")
    assert spread["spread_home"] == -3.5
    assert spread["snapshot_kind"] == "close"


def test_last12h_residual_is_not_a_feature() -> None:
    from src.services.nfl_warehouse.dense_residual import last12h_vs_close

    out = last12h_vs_close(
        [
            {
                "market": "spread",
                "snapshot_kind": "close",
                "spread_home": -6.5,
                "captured_at": "2024-09-08T16:55:00+00:00",
            },
            {
                "market": "spread",
                "snapshot_kind": "mid",
                "spread_home": -3.5,
                "captured_at": "2024-09-08T10:00:00+00:00",
            },
        ],
        kickoff="2024-09-08T17:00:00+00:00",
        game_date="2024-09-08",
    )
    assert out["product"] is False
    assert out["spread_residual"] == 3.0
