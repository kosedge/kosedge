#!/usr/bin/env python3
"""Unit guards for Q2 Phase B: as-of leakage, wl_diff, season firewalls."""

from __future__ import annotations

import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from q2pb.data import Game, DataGuardError, load_games, parse_record, win_pct
from q2pb.metrics import asof_wl_diff, record_wl_diff
from q2pb.strength import asof_for_targets, assert_asof_leakage, solve_ridge


def _g(
    season: int,
    week: int,
    home: str,
    away: str,
    kickoff: datetime,
    hs: float,
    aws: float,
    rec_h: str = "0-0",
    rec_a: str = "0-0",
    gid: str | None = None,
) -> Game:
    return Game(
        season=season,
        week=week,
        game_id=gid or f"{season}_{week:02d}_{away}_{home}",
        home=home,
        away=away,
        kickoff_utc=kickoff,
        home_score=hs,
        away_score=aws,
        record_entering_home=rec_h,
        record_entering_away=rec_a,
        market_spread_home=None,
    )


T0 = datetime(2013, 9, 8, 17, 0, tzinfo=timezone.utc)


class TestAsOfLeakage(unittest.TestCase):
    def test_same_kickoff_excluded_and_later_excluded(self) -> None:
        a = _g(2013, 1, "DEN", "BAL", T0, 49, 27)
        b = _g(2013, 1, "STL", "ARI", T0, 27, 24)  # same kickoff
        c = _g(2013, 2, "NE", "NYJ", T0 + timedelta(days=4), 13, 10)
        d = _g(2013, 3, "DEN", "NYG", T0 + timedelta(days=11), 41, 23)
        hist = [a, b, c, d]
        feats = asof_for_targets(hist, [a, b, c, d], lam=5.0, regress_frac=0.5)
        by_id = {f.game.game_id: f for f in feats}
        self.assertEqual(by_id[a.game_id].n_asof_games, 0)
        self.assertEqual(by_id[b.game_id].n_asof_games, 0)
        self.assertEqual(by_id[c.game_id].n_asof_games, 2)
        self.assertEqual(by_id[d.game_id].n_asof_games, 3)
        assert_asof_leakage(hist, feats)

    def test_ridge_recovers_strength_direction(self) -> None:
        games = [
            _g(2013, 1, "AAA", "BBB", T0, 30, 10),
            _g(2013, 1, "AAA", "CCC", T0 + timedelta(hours=1), 27, 13),
            _g(2013, 1, "BBB", "CCC", T0 + timedelta(hours=2), 20, 17),
        ]
        sol = solve_ridge(games, lam=1.0, prior={})
        self.assertGreater(sol.ratings["AAA"], sol.ratings["BBB"])
        self.assertGreater(sol.ratings["AAA"], sol.ratings["CCC"])


class TestWlDiff(unittest.TestCase):
    def test_recompute_matches_manual(self) -> None:
        w1 = _g(2013, 1, "DEN", "BAL", T0, 49, 27)
        w2 = _g(2013, 2, "NYG", "DEN", T0 + timedelta(days=7), 23, 41, rec_h="0-1", rec_a="1-0")
        diff = asof_wl_diff(w2, [w1, w2])
        # DEN 1-0, NYG 0-0 → 0.5 - 1.0 = -0.5 (home NYG)
        self.assertAlmostEqual(diff, 0.5 - 1.0)
        rec = record_wl_diff(w2)
        self.assertAlmostEqual(rec, win_pct(0, 1, 0) - win_pct(1, 0, 0))

    def test_parse_record(self) -> None:
        self.assertEqual(parse_record("2-1"), (2, 1, 0))
        self.assertEqual(parse_record("1-0-1"), (1, 0, 1))
        self.assertAlmostEqual(win_pct(1, 0, 1), 0.75)


class TestSeasonFirewall(unittest.TestCase):
    def test_phase1_rejects_eval_seasons(self) -> None:
        with self.assertRaises(DataGuardError):
            load_games(Path("/dev/null"), {}, (2018,), phase="phase1_dev")


if __name__ == "__main__":
    unittest.main()
