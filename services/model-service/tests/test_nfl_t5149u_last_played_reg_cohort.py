"""t5149u — 2020 Wild Card excluded; 2021 REG week 18 retained. Identity only."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from src.services.nfl_t5107u.last_played_cohort import (
    COHORT_437_N,
    EXPECTED_REG,
    EXPECTED_REG_TOTAL,
    ORIGINAL_502_SHA256,
    RECOVERED_2021_PARTIALS,
    CohortRefuse,
    assert_original_502_bytes,
    derive_reg_only,
    exclusion_manifest,
    frozen_reg_w2plus_ids,
    record_identity_deviation,
)
from src.services.nfl_t5107u.metric_cohorts import WILDCARD_2020_W18

ROOT = Path(__file__).resolve().parents[3]
ORIGINAL = ROOT / "data/ops/nfl-t5146u-r4-last-played-dev/DEV_RECON_LAST_PLAYED_2020_2021.json"
MATRIX = ROOT / "data/ops/nfl-t5146u-r4-last-played-dev/DEV_RECON_LAST_PLAYED_2020_2021_MATRIX.csv"


def _original():
    payload = json.loads(ORIGINAL.read_text(encoding="utf-8"))
    with MATRIX.open(newline="", encoding="utf-8") as handle:
        payload["matrix"] = list(csv.DictReader(handle))
    return payload


def test_original_502_bytes_preserved():
    assert_original_502_bytes(ROOT)
    payload = json.loads(ORIGINAL.read_text(encoding="utf-8"))
    assert payload["n_complete_27"] == 502
    ids = [row["game_id"] for row in payload["identities"]]
    assert len(ids) == 502
    assert set(WILDCARD_2020_W18) <= set(ids)


def test_2020_wildcard_excluded_from_reg_derivative():
    original = _original()
    schedule = frozen_reg_w2plus_ids(ROOT)
    derived = derive_reg_only(original, schedule_ids=schedule)
    ids = set(derived["game_ids"])
    for gid in WILDCARD_2020_W18:
        assert gid not in ids
    assert derived["n"] == EXPECTED_REG_TOTAL
    assert derived["n_by_season"] == {str(k): v for k, v in EXPECTED_REG.items()}
    manifest = exclusion_manifest([row["game_id"] for row in original["identities"]])
    assert manifest["exclude_exactly"] == list(WILDCARD_2020_W18)
    assert manifest["n"] == 6
    assert manifest["not_a_week_le_18_filter"] is True


def test_2021_reg_week_18_retained():
    original = _original()
    schedule = frozen_reg_w2plus_ids(ROOT)
    derived = derive_reg_only(original, schedule_ids=schedule)
    w18 = [gid for gid in derived["game_ids"] if gid.startswith("2021_18_")]
    assert len(w18) == 16
    assert "2021_18_DAL_PHI" in w18
    assert "2021_18_KC_DEN" in w18
    assert not any(gid.startswith("2020_18_") for gid in derived["game_ids"])


def test_membership_is_frozen_reg_schedule_not_week_le_18():
    schedule = frozen_reg_w2plus_ids(ROOT)
    assert len(schedule) == 496
    assert not any(gid in set(WILDCARD_2020_W18) for gid in schedule)
    assert any(gid.startswith("2021_18_") for gid in schedule)
    assert not any(gid.startswith("2020_18_") for gid in schedule)
    original = _original()
    derived = derive_reg_only(original, schedule_ids=schedule)
    assert set(derived["game_ids"]) == set(schedule)


def test_496_is_not_the_437_previously_complete_cohort():
    original = _original()
    derived = derive_reg_only(original, schedule_ids=frozen_reg_w2plus_ids(ROOT))
    assert derived["n"] != COHORT_437_N
    assert derived["not_the_437_previously_complete_cohort"] is True
    for gid in RECOVERED_2021_PARTIALS:
        assert gid in set(derived["game_ids"])


def test_week_le_18_filter_is_not_accepted():
    """A naive week<=18 filter would keep the 6 Wild Cards. REG schedule does not."""
    original = _original()
    naive = [
        row["game_id"]
        for row in original["identities"]
        if int(str(row["game_id"]).split("_")[1]) <= 18
    ]
    assert len(naive) == 502
    schedule = frozen_reg_w2plus_ids(ROOT)
    assert set(naive) != set(schedule)


def test_deviation_record_refuses_502_as_reg():
    original = _original()
    ids = [row["game_id"] for row in original["identities"]]
    rec = record_identity_deviation(ids)
    assert rec["do_not_accept_as_regular_season_coverage"] is True
    assert rec["deviation"]["n"] == 6
    assert rec["original_artifact"]["preserved"] is True
    assert rec["original_artifact"]["sha256"] == ORIGINAL_502_SHA256


def test_missing_wildcard_in_original_refuses():
    with pytest.raises(CohortRefuse, match="not in original 502"):
        exclusion_manifest(["2021_02_NYG_WAS"])
