"""Unit tests for 65b1c0fb pregame EPA rolling (no PBP / no DB)."""

from __future__ import annotations

import unittest

from rolling import (
    aggregate_team_weeks,
    expand_pregame_to_oos_weeks,
    join_game_id,
    join_oos_games,
    oos_team_from_pbp,
    pbp_team_from_oos,
    roll_pregame,
)


def _play(**kwargs):
    base = {
        "season": 2013,
        "week": 1,
        "game_id": "g1",
        "posteam": "DEN",
        "defteam": "BAL",
        "play_type": "pass",
        "down": 1,
        "first_down": 1,
        "yardline_100": 50,
        "touchdown": 0,
        "sack": 0,
        "qb_hit": 0,
        "passing_yards": 10,
        "success": 1,
        "epa": 0.5,
    }
    base.update(kwargs)
    return base


class AbbrTests(unittest.TestCase):
    def test_historical_oos_labels(self) -> None:
        self.assertEqual(oos_team_from_pbp("LA", 2013), "STL")
        self.assertEqual(oos_team_from_pbp("LA", 2016), "LAR")
        self.assertEqual(oos_team_from_pbp("LAC", 2016), "SD")
        self.assertEqual(oos_team_from_pbp("LAC", 2017), "LAC")
        self.assertEqual(oos_team_from_pbp("LV", 2019), "OAK")
        self.assertEqual(oos_team_from_pbp("LV", 2020), "LV")
        self.assertEqual(oos_team_from_pbp("WAS", 2013), "WSH")
        self.assertEqual(oos_team_from_pbp("JAC", 2013), "JAX")

    def test_reverse_map(self) -> None:
        self.assertEqual(pbp_team_from_oos("STL", 2013), "LA")
        self.assertEqual(pbp_team_from_oos("SD", 2016), "LAC")
        self.assertEqual(pbp_team_from_oos("OAK", 2019), "LV")
        self.assertEqual(pbp_team_from_oos("WSH", 2013), "WAS")


class AggregateTests(unittest.TestCase):
    def test_pass_run_only_and_epa_mean(self) -> None:
        plays = [
            _play(epa=0.2, play_type="pass"),
            _play(epa=0.4, play_type="run", passing_yards=None),
            _play(epa=9.9, play_type="punt"),  # excluded
        ]
        rows = aggregate_team_weeks(plays)
        self.assertEqual(len(rows), 1)
        self.assertAlmostEqual(rows[0]["epa_per_play_offense"], 0.3)
        self.assertEqual(rows[0]["oos_team"], "DEN")


class RollTests(unittest.TestCase):
    def test_week1_empty_week2_uses_only_week1(self) -> None:
        weeks = [
            {
                "season": 2013,
                "week": 1,
                "pbp_team": "DEN",
                "oos_team": "DEN",
                "epa_per_play_offense": 0.10,
                "epa_per_play_defense_allowed": -0.02,
                "pressure_rate_allowed": 0.2,
                "pressure_rate_generated": 0.3,
                "pass_rate": 0.55,
                "early_down_pass_rate": 0.50,
                "red_zone_td_rate": 0.4,
                "success_rate_offense": 0.45,
                "success_rate_defense_allowed": 0.40,
            },
            {
                "season": 2013,
                "week": 2,
                "pbp_team": "DEN",
                "oos_team": "DEN",
                "epa_per_play_offense": 0.99,
                "epa_per_play_defense_allowed": 0.99,
                "pressure_rate_allowed": 0.99,
                "pressure_rate_generated": 0.99,
                "pass_rate": 0.99,
                "early_down_pass_rate": 0.99,
                "red_zone_td_rate": 0.99,
                "success_rate_offense": 0.99,
                "success_rate_defense_allowed": 0.99,
            },
        ]
        rolled = {r["week"]: r for r in roll_pregame(weeks)}
        self.assertEqual(rolled[1]["games_in_window_5"], 0)
        self.assertIsNone(rolled[1]["off_epa_per_play_5g"])
        self.assertEqual(rolled[2]["games_in_window_5"], 1)
        self.assertAlmostEqual(rolled[2]["off_epa_per_play_5g"], 0.10)
        self.assertNotAlmostEqual(rolled[2]["off_epa_per_play_5g"], 0.99)

    def test_five_game_window_drops_oldest(self) -> None:
        weeks = []
        for w, epa in enumerate([0.1, 0.2, 0.3, 0.4, 0.5, 0.6], start=1):
            weeks.append(
                {
                    "season": 2014,
                    "week": w,
                    "pbp_team": "SEA",
                    "oos_team": "SEA",
                    "epa_per_play_offense": epa,
                    "epa_per_play_defense_allowed": 0.0,
                    "pressure_rate_allowed": 0.2,
                    "pressure_rate_generated": 0.2,
                    "pass_rate": 0.5,
                    "early_down_pass_rate": 0.5,
                    "red_zone_td_rate": 0.5,
                    "success_rate_offense": 0.5,
                    "success_rate_defense_allowed": 0.5,
                }
            )
        rolled = {r["week"]: r for r in roll_pregame(weeks)}
        # Week 6 pregame = weeks 1-5 mean = 0.3
        self.assertEqual(rolled[6]["games_in_window_5"], 5)
        self.assertAlmostEqual(rolled[6]["off_epa_per_play_5g"], 0.3)
        self.assertEqual(rolled[6]["games_in_window_3"], 3)
        self.assertAlmostEqual(rolled[6]["off_epa_per_play_3g"], (0.3 + 0.4 + 0.5) / 3)


class JoinTests(unittest.TestCase):
    def test_join_keys_match_t4422u_and_oos(self) -> None:
        self.assertEqual(join_game_id(2013, 1, "STL", "ARI"), "2013_01_ARI_STL")
        games = [
            {"season": 2013, "week": 1, "key": "ARI@STL", "home": "STL", "away": "ARI"},
            {"season": 2013, "week": 2, "key": "ARI@STL", "home": "STL", "away": "ARI"},
        ]
        team_weeks = [
            {
                "season": 2013,
                "week": 1,
                "pbp_team": "LA",
                "oos_team": "STL",
                "epa_per_play_offense": 0.11,
                "epa_per_play_defense_allowed": 0.0,
                "pressure_rate_allowed": 0.2,
                "pressure_rate_generated": 0.2,
                "pass_rate": 0.5,
                "early_down_pass_rate": 0.5,
                "red_zone_td_rate": 0.5,
                "success_rate_offense": 0.5,
                "success_rate_defense_allowed": 0.5,
            },
            {
                "season": 2013,
                "week": 1,
                "pbp_team": "ARI",
                "oos_team": "ARI",
                "epa_per_play_offense": -0.05,
                "epa_per_play_defense_allowed": 0.1,
                "pressure_rate_allowed": 0.2,
                "pressure_rate_generated": 0.2,
                "pass_rate": 0.5,
                "early_down_pass_rate": 0.5,
                "red_zone_td_rate": 0.5,
                "success_rate_offense": 0.5,
                "success_rate_defense_allowed": 0.5,
            },
        ]
        rolled = expand_pregame_to_oos_weeks(team_weeks, games)
        joined = join_oos_games(games, rolled)
        self.assertEqual(len(joined), 2)
        w1, w2 = joined
        self.assertEqual(w1["join_game_id"], "2013_01_ARI_STL")
        self.assertEqual(w1["feature_status"], "EMPTY_WINDOW")
        self.assertEqual(w1["cert_candidate"], 0)
        self.assertEqual(w1["epa_home_win_prob"], "")
        self.assertEqual(w2["feature_status"], "THIN_WINDOW")
        self.assertAlmostEqual(w2["home_off_epa_per_play_5g"], 0.11)
        self.assertAlmostEqual(w2["away_off_epa_per_play_5g"], -0.05)


if __name__ == "__main__":
    unittest.main()
