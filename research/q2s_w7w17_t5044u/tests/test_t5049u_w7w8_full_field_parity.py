#!/usr/bin/env python3
"""t5049u — full-field W7–W8 compare (mutation / refusal).

CERT=0. No IF / emit / look. Proves pass-rate, pressure, RZ, and
matchup_diff_def_epa_allowed_5g diffs fail. Contract tolerances unchanged.
"""

from __future__ import annotations

import copy
import csv
import sys
import unittest
from pathlib import Path

PACKET = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKET / "gate2"))

from rebuild_w7w17 import (  # noqa: E402
    CONTRACT_27,
    EPA_FIELDS,
    EXACT_NUMERIC_FIELDS,
    INDEX_FIELDS,
    REST_FIELDS,
    TEXT_FIELDS,
    TOL_EPA,
    TOL_INDEX,
    RebuildRefuse,
    compare_cell_maps,
    compare_w7w8,
)


def _load_maps() -> tuple[dict, dict, list[dict]]:
    prior = {}
    with (PACKET / "gate2" / "stage_b_w7w8" / "RECON_MATRIX.csv").open() as handle:
        for row in csv.DictReader(handle):
            prior[(row["game_id"], row["field"])] = row
    rebuilt_rows = []
    rebuilt = {}
    with (PACKET / "gate2" / "RECON_MATRIX_W7W17.csv").open() as handle:
        for row in csv.DictReader(handle):
            if int(row["week"]) not in (7, 8):
                continue
            rebuilt_rows.append(row)
            rebuilt[(row["game_id"], row["field"])] = row
    return rebuilt, prior, rebuilt_rows


def _legacy_would_fail(field: str, delta: float) -> bool:
    """Old compare_w7w8: only INDEX / EPA / rest_* numeric fails."""
    if field in INDEX_FIELDS:
        return delta >= TOL_INDEX
    if field in EPA_FIELDS:
        return delta >= TOL_EPA
    if field.startswith("rest_") and delta >= 1e-9:
        return True
    return False


def _mutate(rebuilt: dict, field: str, delta: float) -> dict:
    clone = {k: copy.deepcopy(v) for k, v in rebuilt.items()}
    for (gid, fname), row in clone.items():
        if fname != field or row.get("status") != "DERIVED_PREGAME":
            continue
        value = float(row["reconstructed_value"])
        row["reconstructed_value"] = f"{value + delta:.8f}"
        return clone
    raise AssertionError(f"no DERIVED_PREGAME cell for {field}")


class T5049uFullFieldParityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.rebuilt, cls.prior, cls.rows = _load_maps()

    def test_asserted_fields_are_all_27(self) -> None:
        self.assertEqual(len(CONTRACT_27), 27)
        self.assertEqual(
            EXACT_NUMERIC_FIELDS,
            {
                "home_pass_rate_5g",
                "away_pass_rate_5g",
                "matchup_diff_pressure_allowed_5g",
                "matchup_diff_pressure_generated_5g",
                "matchup_diff_red_zone_td_rate_5g",
                "matchup_diff_def_epa_allowed_5g",
            },
        )
        self.assertTrue(TEXT_FIELDS.isdisjoint(INDEX_FIELDS | EPA_FIELDS | REST_FIELDS))

    def test_real_w7w8_still_passes_full_field(self) -> None:
        result = compare_cell_maps(self.rebuilt, self.prior)
        self.assertTrue(result["pass"], msg=result["fails"][:8])
        self.assertEqual(result["asserted_fields"], list(CONTRACT_27))
        self.assertEqual(result["n_cells"], 28 * 27)
        self.assertEqual(result["max_abs_delta_exact_numeric"], 0.0)
        compare_w7w8(self.rows)  # raises on fail

    def test_pass_rate_diff_refuses_and_legacy_would_pass(self) -> None:
        mutated = _mutate(self.rebuilt, "home_pass_rate_5g", 0.01)
        result = compare_cell_maps(mutated, self.prior)
        self.assertFalse(result["pass"])
        self.assertTrue(any(f.get("field") == "home_pass_rate_5g" for f in result["fails"]))
        self.assertFalse(_legacy_would_fail("home_pass_rate_5g", 0.01))

    def test_pressure_diff_refuses_and_legacy_would_pass(self) -> None:
        mutated = _mutate(self.rebuilt, "matchup_diff_pressure_generated_5g", 0.02)
        result = compare_cell_maps(mutated, self.prior)
        self.assertFalse(result["pass"])
        self.assertTrue(
            any(f.get("field") == "matchup_diff_pressure_generated_5g" for f in result["fails"])
        )
        self.assertFalse(_legacy_would_fail("matchup_diff_pressure_generated_5g", 0.02))

    def test_rz_diff_refuses_and_legacy_would_pass(self) -> None:
        mutated = _mutate(self.rebuilt, "matchup_diff_red_zone_td_rate_5g", 0.03)
        result = compare_cell_maps(mutated, self.prior)
        self.assertFalse(result["pass"])
        self.assertTrue(
            any(f.get("field") == "matchup_diff_red_zone_td_rate_5g" for f in result["fails"])
        )
        self.assertFalse(_legacy_would_fail("matchup_diff_red_zone_td_rate_5g", 0.03))

    def test_def_epa_diff_refuses_and_legacy_would_pass(self) -> None:
        mutated = _mutate(self.rebuilt, "matchup_diff_def_epa_allowed_5g", 0.04)
        result = compare_cell_maps(mutated, self.prior)
        self.assertFalse(result["pass"])
        self.assertTrue(
            any(f.get("field") == "matchup_diff_def_epa_allowed_5g" for f in result["fails"])
        )
        self.assertFalse(_legacy_would_fail("matchup_diff_def_epa_allowed_5g", 0.04))

    def test_index_within_contract_still_passes(self) -> None:
        mutated = _mutate(self.rebuilt, "offense_index_home", 1e-7)
        result = compare_cell_maps(mutated, self.prior)
        self.assertTrue(result["pass"], msg=result["fails"][:4])
        self.assertFalse(_legacy_would_fail("offense_index_home", 1e-7))

    def test_index_beyond_contract_refuses(self) -> None:
        mutated = _mutate(self.rebuilt, "offense_index_home", 1e-5)
        result = compare_cell_maps(mutated, self.prior)
        self.assertFalse(result["pass"])
        self.assertTrue(any(f.get("reason") == "index" for f in result["fails"]))
        self.assertTrue(_legacy_would_fail("offense_index_home", 1e-5))

    def test_epa_within_contract_still_passes(self) -> None:
        mutated = _mutate(self.rebuilt, "home_off_epa_5g", 1e-10)
        result = compare_cell_maps(mutated, self.prior)
        self.assertTrue(result["pass"], msg=result["fails"][:4])

    def test_epa_beyond_contract_refuses(self) -> None:
        mutated = _mutate(self.rebuilt, "home_off_epa_5g", 1e-8)
        result = compare_cell_maps(mutated, self.prior)
        self.assertFalse(result["pass"])
        self.assertTrue(any(f.get("reason") == "epa" for f in result["fails"]))

    def test_rest_beyond_contract_refuses(self) -> None:
        mutated = _mutate(self.rebuilt, "rest_days_home", 0.5)
        result = compare_cell_maps(mutated, self.prior)
        self.assertFalse(result["pass"])
        self.assertTrue(any(f.get("reason") == "rest" for f in result["fails"]))

    def test_compare_w7w8_raises_on_pass_rate_mutation(self) -> None:
        rows = [copy.deepcopy(r) for r in self.rows]
        for row in rows:
            if row["field"] == "away_pass_rate_5g" and row["status"] == "DERIVED_PREGAME":
                row["reconstructed_value"] = f"{float(row['reconstructed_value']) + 0.05:.8f}"
                break
        else:
            self.fail("no away_pass_rate_5g cell")
        with self.assertRaises(RebuildRefuse) as ctx:
            compare_w7w8(rows)
        self.assertIn("exact_numeric", str(ctx.exception))


if __name__ == "__main__":
    unittest.main(verbosity=2)
