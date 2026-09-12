"""Official 2026 FBS lock is the priors / efficiency universe.

Root cause of the 11-team omission: priors were keyed off a stale 136-code
set plus FCS/alias extras, not ``cfb_fbs_universe_2026.json``. Missouri
(MIZZ) was dropped while Missouri State (MOST) was kept. The efficiency
packager then fail-closed (correctly) rather than inventing 50-fills.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src.services.cfb_season_engine.conferences import conference_for
from src.services.cfb_season_engine.fbs_universe import (
    NON_FBS_CODES,
    codes_excluded_from_priors,
    load_fbs_universe,
    membership_row,
    official_fbs_codes,
    prior_packaging_codes,
    prune_non_official_prior_teams,
)
from src.services.cfb_season_engine.name_to_code import (
    P0_REQUIRED_CODES,
    require_mapped_code,
)

DATA = (
    Path(__file__).resolve().parents[1]
    / "src/services/cfb_season_engine/data"
)
PRIORS = DATA / "cfb_fbs_team_priors_2026.json"
EFFICIENCY = DATA / "cfb_efficiency_snapshot_2025_carry_2026.json"
POWER = DATA / "cfb_power_sot_2026.json"

P0_CONFERENCES = {
    "MIZZ": "SEC",
    "ARST": "Sun Belt",
    "CSU": "Pac-12",
    "ECU": "AAC",
    "JVST": "CUSA",
    "NEV": "Mountain West",
    "ODU": "Sun Belt",
    "TOL": "MAC",
    "UAB": "AAC",
    "UNM": "Mountain West",
    "UNT": "AAC",
}


def test_official_lock_contains_the_eleven() -> None:
    official = official_fbs_codes()
    assert official_fbs_codes() == prior_packaging_codes(include_transition=False)
    for code in P0_REQUIRED_CODES:
        assert code in official, code
        row = membership_row(code)
        assert row is not None, code
        assert row["membership"] == "fbs_full", code
        assert row["conference"] == P0_CONFERENCES[code], code
        assert row.get("independent") is False, code


def test_jvst_is_full_member_not_2026_transition() -> None:
    jvst = membership_row("JVST")
    assert jvst is not None
    assert jvst["membership"] == "fbs_full"
    assert jvst["conference"] == "CUSA"
    assert jvst.get("display_name", "").startswith("Jacksonville State")
    book = load_fbs_universe()
    assert "JVST" not in (book.get("transitioning") or {})
    assert set(book.get("transitioning") or {}) == {"NDSU", "SAC"}
    ndsu = membership_row("NDSU")
    sac = membership_row("SAC")
    assert ndsu and ndsu["membership"] == "fbs_transition"
    assert sac and sac["membership"] == "fbs_transition"
    assert "not a full-member prior" in str(ndsu.get("notes") or "")
    assert "generic FCS -25" in str(ndsu.get("notes") or "")


def test_missouri_is_not_missouri_state() -> None:
    assert require_mapped_code("Missouri") == "MIZZ"
    assert require_mapped_code("Missouri State") == "MOST"
    mizz = membership_row("MIZZ")
    most = membership_row("MOST")
    assert mizz and most
    assert mizz["conference"] == "SEC"
    assert most["conference"] == "CUSA"
    assert mizz["display_name"] != most["display_name"]


def test_prune_drops_extras_keeps_official() -> None:
    teams = {
        "MIZZ": {"ok": True},
        "MOST": {"ok": True},
        "FAU": {"ok": True},
        "MISS": {"ok": True},
        "TAMU": {"ok": True},
        "UL": {"ok": True},
        "ORST": {"ok": True},
        "ACU": {"placeholder": True},
        "FAU2": {"alias": True},
        "OLE": {"alias": True},
        "ULL": {"alias": True},
        "FAY": {"unmatched": True},
    }
    removed = prune_non_official_prior_teams(teams)
    assert set(removed) == {"ACU", "FAU2", "OLE", "ULL", "FAY"}
    assert set(teams) == {"MIZZ", "MOST", "FAU", "MISS", "TAMU", "UL", "ORST"}
    assert "FAU" not in codes_excluded_from_priors()
    assert "FAU2" in codes_excluded_from_priors()
    assert NON_FBS_CODES <= codes_excluded_from_priors()


def test_roster_and_efficiency_scripts_use_official_lock() -> None:
    root = Path(__file__).resolve().parents[3]
    roster = (root / "scripts/cfb/package_real_roster_2026.py").read_text(
        encoding="utf-8"
    )
    efficiency = (root / "scripts/cfb/package_efficiency_2025_carry.py").read_text(
        encoding="utf-8"
    )
    assert "prior_packaging_codes" in roster
    assert "priors.get(\"teams\") or {}" not in roster.split("team_codes =")[1][:400]
    assert "codes = set(official)" in efficiency
    assert "codes = set(priors.get(\"teams\") or {})" not in efficiency
    assert "do not league-average fill" in efficiency
    assert "AUTHORITATIVE_SOURCE_PATH" in efficiency
    assert "rejected_2026_inseason_cfbupdate" in efficiency or "Live public SP+" in efficiency
    assert "--splice-p0-only" in efficiency


def test_independents_are_only_nd_and_conn() -> None:
    book = load_fbs_universe()
    assert set(book.get("independents") or []) == {"CONN", "ND"}
    official = official_fbs_codes(include_transition=True)
    unintended = []
    for code in official:
        if conference_for(code) == "Independent" and code not in {"ND", "CONN"}:
            unintended.append(code)
    assert unintended == []


def test_packaged_priors_match_official_full_members() -> None:
    blob = json.loads(PRIORS.read_text(encoding="utf-8"))
    teams = blob.get("teams") or {}
    official = official_fbs_codes()
    extras = sorted(set(teams) & codes_excluded_from_priors())
    missing = sorted(official - set(teams))
    assert extras == [], extras
    assert missing == [], missing
    notes = " ".join(blob.get("notes") or [])
    assert "EXTRA codes are explicit placeholder league-average rows" not in notes
    for code in P0_REQUIRED_CODES:
        row = teams[code]
        roster = row.get("roster") or {}
        assert roster.get("source") == "packaged_espn_roster_2026", code
        assert (row.get("qb") or {}).get("starter_name"), code


def test_efficiency_has_real_sp_plus_for_all_official() -> None:
    snap = json.loads(EFFICIENCY.read_text(encoding="utf-8"))
    teams = snap.get("teams") or {}
    official = official_fbs_codes()
    missing = []
    fills = []
    for code in official:
        row = teams.get(code) or {}
        src = str(row.get("source") or "")
        if src == "league_average_fill" or row.get("fidelity") == "placeholder":
            fills.append(code)
        off = row.get("off_eff")
        power = row.get("sp_plus")
        if off is None or not src.startswith("packaged_sp_plus"):
            missing.append(code)
        else:
            assert float(off) == float(off)  # finite
            assert power is not None
    assert fills == [], fills
    assert missing == [], missing
    for code in P0_REQUIRED_CODES:
        assert teams[code]["source"].startswith("packaged_sp_plus")
        assert teams[code]["off_eff"] != 50.0 or code == "JVST"
    # JVST may land near 50 from a real SP+ z-score; source must still be mapped.
    assert teams["JVST"]["source"].startswith("packaged_sp_plus")
    assert teams["JVST"]["sp_rank"] not in (None, "")
    assert teams["M-OH"]["source"].startswith("packaged_sp_plus")
    assert teams["M-OH"]["off_eff"] != 50.0 or teams["M-OH"]["sp_rank"] not in (None, "")
    assert snap.get("source", {}).get("vintage") == "espn_story_2025_final"
    assert snap.get("provenance_complete") == snap.get("team_count") == 136
    for code in official:
        row = teams[code]
        assert row.get("source_vintage") == "espn_story_2025_final", code
        assert row.get("source_published") == "2026-01-20", code
        assert row.get("source_url"), code
        assert row.get("source_table_name"), code
    assert "NDSU" not in teams
    assert "SAC" not in teams


def test_power_sot_eleven_are_finite_and_conferenced() -> None:
    pack = json.loads(POWER.read_text(encoding="utf-8"))
    by = {row["team"]: row for row in pack.get("teams") or []}
    for code, conf in P0_CONFERENCES.items():
        row = by[code]
        assert row["conference"] == conf, code
        assert row["offense_index"] not in (None, "")
        assert row["power_index"] not in (None, 0, 1.0)
        assert row["efficiency_source"] != "league_average_fill", code
        assert float(row["offense_index"]) == float(row["offense_index"])
    moh = by["M-OH"]
    assert moh["efficiency_source"] != "league_average_fill"
    assert moh["conference"] == "MAC"
    independents = [
        row["team"]
        for row in pack.get("teams") or []
        if row.get("conference") == "Independent"
        and row["team"] in official_fbs_codes()
    ]
    assert set(independents) <= {"ND", "CONN"}
