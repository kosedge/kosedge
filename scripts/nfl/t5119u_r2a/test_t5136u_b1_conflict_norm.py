"""t5136u B-1 — finite-numeric fingerprint tests. No outcomes. No EVAL."""

from __future__ import annotations

import math
import unittest

from build_owned_coverage import collapse, finite_numeric, fingerprint, fingerprint_raw, store_number


def quote(
    *,
    game_id="2020_01_HOU_KC",
    book="draftkings",
    market="moneyline",
    captured_at="2020-09-10T00:15:00Z",
    price_home,
    price_away,
    spread_home=None,
    total_points=None,
    line=None,
    provenance="open_close_csv",
):
    raw = {
        "spread_home": spread_home,
        "price_home": price_home,
        "price_away": price_away,
        "total_points": total_points,
        "line": line,
    }
    return {
        "game_id": game_id,
        "book": book,
        "market": market,
        "captured_at": captured_at,
        "spread_home": store_number(spread_home),
        "price_home": store_number(price_home),
        "price_away": store_number(price_away),
        "total_points": store_number(total_points),
        "line": store_number(line),
        "provenance": provenance,
        "_raw": raw,
    }


class FiniteNumericTests(unittest.TestCase):
    def test_string_int_float_equivalent(self):
        self.assertEqual(finite_numeric("-110"), -110.0)
        self.assertEqual(finite_numeric(-110), -110.0)
        self.assertEqual(finite_numeric(-110.0), -110.0)
        self.assertEqual(finite_numeric("360.0"), 360.0)
        self.assertEqual(finite_numeric("  -109.0 "), -109.0)

    def test_blank_and_none(self):
        self.assertIsNone(finite_numeric(None))
        self.assertIsNone(finite_numeric(""))
        self.assertIsNone(finite_numeric("   "))

    def test_bool_and_nonfinite_do_not_become_numbers(self):
        self.assertEqual(finite_numeric(True)[0], "non_numeric")
        self.assertEqual(finite_numeric("nan")[0], "non_finite")
        self.assertEqual(finite_numeric(math.inf)[0], "non_finite")
        self.assertEqual(finite_numeric("not-a-price")[0], "non_numeric")

    def test_no_rounding_or_tolerance(self):
        self.assertNotEqual(finite_numeric("-110"), finite_numeric("-111"))
        self.assertNotEqual(finite_numeric(-3.5), finite_numeric(-3.0))
        self.assertNotEqual(finite_numeric("3.5"), finite_numeric("3"))


class FingerprintEquivalenceTests(unittest.TestCase):
    def test_string_vs_number_same_fingerprint(self):
        csv_q = quote(price_home="-110", price_away="360.0", provenance="open_close_csv")
        sql_q = quote(price_home=-110.0, price_away=360.0, provenance="odds_gapfill_sqlite")
        self.assertNotEqual(fingerprint_raw(csv_q), fingerprint_raw(sql_q))
        self.assertEqual(fingerprint(csv_q), fingerprint(sql_q))

    def test_spread_string_point_already_float_prices_string(self):
        csv_q = quote(
            market="spread",
            spread_home=-3.5,
            line=-3.5,
            price_home="-108",
            price_away="-112",
        )
        sql_q = quote(
            market="spread",
            spread_home=-3.5,
            line=-3.5,
            price_home=-108.0,
            price_away=-112.0,
            provenance="odds_gapfill_sqlite",
        )
        self.assertEqual(fingerprint(csv_q), fingerprint(sql_q))


class CollapseTests(unittest.TestCase):
    def test_synthetic_string_number_collapses(self):
        csv_q = quote(price_home="-110", price_away="250", provenance="open_close_csv")
        sql_q = quote(price_home=-110.0, price_away=250.0, provenance="odds_gapfill_sqlite")
        raw_latest, raw_ident, raw_conflicts = collapse([csv_q, sql_q], fingerprint_fn=fingerprint_raw)
        norm_latest, norm_ident, norm_conflicts = collapse([csv_q, sql_q], fingerprint_fn=fingerprint)
        self.assertEqual(len(raw_conflicts), 1)
        self.assertEqual(len(raw_latest), 0)
        self.assertEqual(len(norm_conflicts), 0)
        self.assertEqual(len(norm_latest), 1)
        self.assertEqual(norm_ident, 1)

    def test_genuine_price_conflict_still_refuses(self):
        csv_q = quote(price_home="-110", price_away="250", provenance="open_close_csv")
        sql_q = quote(price_home=-105.0, price_away=250.0, provenance="odds_gapfill_sqlite")
        latest, ident, conflicts = collapse([csv_q, sql_q], fingerprint_fn=fingerprint)
        self.assertEqual(len(latest), 0)
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0]["reason"], "duplicate_conflict")
        self.assertEqual(ident, 0)

    def test_genuine_spread_conflict_still_refuses(self):
        a = quote(
            market="spread",
            spread_home=-3.5,
            line=-3.5,
            price_home=-110,
            price_away=-110,
        )
        b = quote(
            market="spread",
            spread_home=-3.0,
            line=-3.0,
            price_home=-110.0,
            price_away=-110.0,
            provenance="odds_gapfill_sqlite",
        )
        latest, _, conflicts = collapse([a, b], fingerprint_fn=fingerprint)
        self.assertEqual(len(latest), 0)
        self.assertEqual(len(conflicts), 1)

    def test_real_pair_2020_01_hou_kc_dk_ml_type_only(self):
        """Frozen evidence shape from sealed extracts: same economics, different types."""
        csv_q = quote(
            game_id="2020_01_HOU_KC",
            book="draftkings",
            market="moneyline",
            captured_at="2020-09-10T00:15:00Z",
            price_home="-435.0",
            price_away="330.0",
            provenance="open_close_csv",
        )
        sql_q = quote(
            game_id="2020_01_HOU_KC",
            book="draftkings",
            market="moneyline",
            captured_at="2020-09-10T00:15:00Z",
            price_home=-435.0,
            price_away=330.0,
            provenance="odds_gapfill_sqlite",
        )
        self.assertNotEqual(type(csv_q["_raw"]["price_home"]), type(sql_q["_raw"]["price_home"]))
        self.assertEqual(fingerprint(csv_q), fingerprint(sql_q))
        latest, ident, conflicts = collapse([csv_q, sql_q])
        self.assertEqual(conflicts, [])
        self.assertEqual(len(latest), 1)
        self.assertEqual(ident, 1)


if __name__ == "__main__":
    unittest.main()
