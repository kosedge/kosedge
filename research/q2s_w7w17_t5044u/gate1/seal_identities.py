#!/usr/bin/env python3
"""t5044u Gate 1 — identity seal BEFORE any PBP parse.

CERT=0 · NFL NO-GO · RETRO_FIT / DEV_RESEARCH · DRAFT
Seals all 165 scheduled 2017 REG W7–W17 identities from games 4fe1cdd7.
Does not open PBP. Does not load quarantined hist index 1ee90fac.
Does not apply outcome-based exclusion. No last-played / fills / replacements.
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

PACKET = Path(__file__).resolve().parents[1]
GATE1 = PACKET / "gate1"
PINS = PACKET / "pins"
GAMES_CSV = PINS / "games_4fe1cdd7.csv"

GAMES_SHA256 = "4fe1cdd7f2eb616103ee6107e6a5cb0d5280f8006be420b606af0995351abef8"
TARGET_SEASON = 2017
WEEKS = tuple(range(7, 18))
EXPECTED_N = 165
EXPECTED_BY_WEEK = {
    7: 15,
    8: 13,
    9: 13,
    10: 14,
    11: 14,
    12: 16,
    13: 16,
    14: 16,
    15: 16,
    16: 16,
    17: 16,
}
IDENTITY_COLS = (
    "season",
    "week",
    "game_id",
    "home",
    "away",
    "kickoff_utc",
)
GAMES_TO_CANON = {"LA": "LAR", "WAS": "WSH", "SD": "SD"}
ET = ZoneInfo("America/New_York")

# Schedule-derived T2 bye-return risks (t5039u inventory / Stage B W7–W8).
# rating_week = week-1; exact lookup_t2; no last-played fill.
SEALED_T2_RISKS = (
    {"week": 7, "game_id": "2017_07_TB_BUF", "bye_sides": ["BUF"], "bye_week": 6},
    {"week": 7, "game_id": "2017_07_DAL_SF", "bye_sides": ["DAL"], "bye_week": 6},
    {"week": 7, "game_id": "2017_07_CIN_PIT", "bye_sides": ["CIN"], "bye_week": 6},
    {"week": 7, "game_id": "2017_07_SEA_NYG", "bye_sides": ["SEA"], "bye_week": 6},
    {"week": 8, "game_id": "2017_08_HOU_SEA", "bye_sides": ["HOU"], "bye_week": 7},
    {"week": 8, "game_id": "2017_08_PIT_DET", "bye_sides": ["DET"], "bye_week": 7},
    {"week": 9, "game_id": "2017_09_ARI_SF", "bye_sides": ["ARI"], "bye_week": 8},
    {"week": 9, "game_id": "2017_09_BAL_TEN", "bye_sides": ["TEN"], "bye_week": 8},
    {"week": 9, "game_id": "2017_09_CIN_JAX", "bye_sides": ["JAX"], "bye_week": 8},
    {"week": 9, "game_id": "2017_09_LA_NYG", "bye_sides": ["NYG", "LAR"], "bye_week": 8},
    {"week": 9, "game_id": "2017_09_DET_GB", "bye_sides": ["GB"], "bye_week": 8},
    {"week": 10, "game_id": "2017_10_CLE_DET", "bye_sides": ["CLE"], "bye_week": 9},
    {"week": 10, "game_id": "2017_10_GB_CHI", "bye_sides": ["CHI"], "bye_week": 9},
    {"week": 10, "game_id": "2017_10_LAC_JAX", "bye_sides": ["LAC"], "bye_week": 9},
    {"week": 10, "game_id": "2017_10_MIN_WAS", "bye_sides": ["MIN"], "bye_week": 9},
    {"week": 10, "game_id": "2017_10_NE_DEN", "bye_sides": ["NE"], "bye_week": 9},
    {"week": 10, "game_id": "2017_10_PIT_IND", "bye_sides": ["PIT"], "bye_week": 9},
    {"week": 11, "game_id": "2017_11_BAL_GB", "bye_sides": ["BAL"], "bye_week": 10},
    {"week": 11, "game_id": "2017_11_KC_NYG", "bye_sides": ["KC"], "bye_week": 10},
    {"week": 11, "game_id": "2017_11_NE_OAK", "bye_sides": ["OAK"], "bye_week": 10},
    {"week": 11, "game_id": "2017_11_PHI_DAL", "bye_sides": ["PHI"], "bye_week": 10},
    {"week": 12, "game_id": "2017_12_CAR_NYJ", "bye_sides": ["NYJ", "CAR"], "bye_week": 11},
    {"week": 12, "game_id": "2017_12_SEA_SF", "bye_sides": ["SF"], "bye_week": 11},
    {"week": 12, "game_id": "2017_12_TEN_IND", "bye_sides": ["IND"], "bye_week": 11},
)

# Stage B t4923u W7–W8 selection hashes (eligible = all scheduled; 0 Irma-style drops).
STAGE_B_W7_HASH = "6030f79c2a9690b818c7ae2b4b9ac9edd0c5c47741b222f715429753d6b29856"
STAGE_B_W8_HASH = "3bf4a0dc29237f0b97ef6a4bf12396385f4564e4f7cd3470aeccbc1f7ecdc58e"

PBP_FORBIDDEN_AT_SEAL = (
    Path("/workspace/data/raw/nfl/pbp/t4696u_s1_restage/play_by_play_2017.parquet"),
    Path("/workspace/data/raw/nfl/pbp/t4696u_s1_restage/play_by_play_2016.parquet"),
    PACKET / "pbp" / "play_by_play_2017.parquet",
)

CONTRACT_FIELDS_27 = {
    "context": [
        "game_id",
        "home_team",
        "away_team",
        "matchup_season",
        "matchup_week",
        "rest_days_home",
        "rest_days_away",
    ],
    "efficiency": [
        "offense_index_home",
        "offense_index_away",
        "defense_index_home",
        "defense_index_away",
        "home_off_epa_5g",
        "away_off_epa_5g",
        "home_def_epa_allowed_5g",
        "away_def_epa_allowed_5g",
        "home_success_offense_5g",
        "away_success_offense_5g",
        "home_success_defense_allowed_5g",
        "away_success_defense_allowed_5g",
        "home_pass_rate_5g",
        "away_pass_rate_5g",
        "matchup_diff_off_epa_5g",
        "matchup_diff_def_epa_allowed_5g",
        "matchup_diff_success_rate_5g",
        "matchup_diff_pressure_allowed_5g",
        "matchup_diff_pressure_generated_5g",
        "matchup_diff_red_zone_td_rate_5g",
    ],
}

T2_SIDE_FIELDS = (
    "off_epa_5g",
    "def_epa_allowed_5g",
    "success_offense_5g",
    "success_defense_allowed_5g",
    "pass_rate_5g",
)
T2_MATCHUP_FIELDS = (
    "matchup_diff_off_epa_5g",
    "matchup_diff_def_epa_allowed_5g",
    "matchup_diff_success_rate_5g",
    "matchup_diff_pressure_allowed_5g",
    "matchup_diff_pressure_generated_5g",
    "matchup_diff_red_zone_td_rate_5g",
)


class SealRefuse(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def selection_hash(game_ids: list[str]) -> str:
    payload = "\n".join(sorted(game_ids)) + "\n"
    return sha256_text(payload)


def parse_utc(raw: str) -> datetime:
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    dt = datetime.fromisoformat(raw)
    if dt.tzinfo is None:
        raise SealRefuse(f"naive timestamp rejected: {raw!r}")
    return dt.astimezone(timezone.utc)


def rest_days_et(kickoff_utc: str) -> float:
    """Sealed ET DOW heuristic (hist packets 155d3ca0). Not IF re-derive."""
    dt = parse_utc(kickoff_utc).astimezone(ET)
    dow = dt.weekday()
    if dow == 3:
        return 4.0
    if dow == 0:
        return 6.0
    return 7.0


def rest_days_utc(kickoff_utc: str) -> float:
    dow = parse_utc(kickoff_utc).weekday()
    if dow == 3:
        return 4.0
    if dow == 0:
        return 6.0
    return 7.0


def normalize_games_abbr(token: str) -> str:
    return GAMES_TO_CANON.get(token, token)


def assert_pbp_absent() -> list[str]:
    present = [str(path) for path in PBP_FORBIDDEN_AT_SEAL if path.is_file()]
    if present:
        raise SealRefuse(
            "PBP present at Gate 1 seal start — abort. "
            "Identity must be sealed before remount/parse: " + "; ".join(present)
        )
    return [str(path) for path in PBP_FORBIDDEN_AT_SEAL]


def load_identity_rows() -> list[dict[str, str]]:
    digest = sha256_file(GAMES_CSV)
    if digest != GAMES_SHA256:
        raise SealRefuse(f"games.csv sha256 {digest} != pin {GAMES_SHA256}")
    rows: list[dict[str, str]] = []
    with GAMES_CSV.open(newline="") as handle:
        reader = csv.DictReader(handle)
        missing = set(IDENTITY_COLS) - set(reader.fieldnames or [])
        if missing:
            raise SealRefuse(f"games.csv missing identity columns {sorted(missing)}")
        for raw in reader:
            season = int(raw["season"])
            if season >= 2024:
                raise SealRefuse("abort: season>=2024 row in games.csv pin")
            if season != TARGET_SEASON:
                continue
            week = int(raw["week"])
            if week not in WEEKS:
                continue
            rows.append({col: raw[col] for col in IDENTITY_COLS})
    return rows


def derive_t2_risks(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    """Schedule-only T2 risks. W7 needs W6 byes from the sealed list."""
    by_id = {row["game_id"]: row for row in rows}
    derived: list[dict[str, object]] = []
    for spec in SEALED_T2_RISKS:
        gid = spec["game_id"]
        row = by_id.get(gid)
        if row is None:
            raise SealRefuse(f"sealed T2 risk {gid} missing from 4fe1cdd7 universe")
        home = normalize_games_abbr(row["home"])
        away = normalize_games_abbr(row["away"])
        sides = []
        if home in spec["bye_sides"]:
            sides.append({"team": home, "role": "home"})
        if away in spec["bye_sides"]:
            sides.append({"team": away, "role": "away"})
        if sorted(s["team"] for s in sides) != sorted(spec["bye_sides"]):
            raise SealRefuse(
                f"{gid} bye_sides {spec['bye_sides']} != schedule roles {sides}"
            )
        missing_cells = [
            f"{side['role']}_{field}" if not field.startswith("matchup_") else field
            for side in sides
            for field in T2_SIDE_FIELDS
        ]
        # matchup diffs miss if either side misses T2
        missing_cells.extend(T2_MATCHUP_FIELDS)
        derived.append(
            {
                "game_id": gid,
                "season": TARGET_SEASON,
                "week": spec["week"],
                "home_team": home,
                "away_team": away,
                "bye_week": spec["bye_week"],
                "rating_week": spec["week"] - 1,
                "bye_sides": list(spec["bye_sides"]),
                "sides": sides,
                "rule": "exact lookup_t2(rating_week); no last-played fill",
                "cells_expected_missing": sorted(set(missing_cells)),
                "n_cells_expected_missing": 5 * len(sides) + 6,
                "selection_excluded": False,
                "retained": True,
                "substituted": False,
            }
        )
    return derived


def main() -> int:
    pbp_paths_checked = assert_pbp_absent()
    rows = load_identity_rows()
    if len(rows) != EXPECTED_N:
        raise SealRefuse(f"scheduled n={len(rows)} != sealed {EXPECTED_N}")
    by_week = Counter(int(r["week"]) for r in rows)
    if dict(by_week) != EXPECTED_BY_WEEK:
        raise SealRefuse(f"week counts {dict(sorted(by_week.items()))} != {EXPECTED_BY_WEEK}")

    identities = []
    for row in sorted(rows, key=lambda r: (int(r["week"]), r["kickoff_utc"], r["game_id"])):
        if not row["kickoff_utc"]:
            raise SealRefuse(f"{row['game_id']} missing kickoff — do not impute")
        home = normalize_games_abbr(row["home"])
        away = normalize_games_abbr(row["away"])
        kick = row["kickoff_utc"]
        rest_et = rest_days_et(kick)
        rest_utc = rest_days_utc(kick)
        identities.append(
            {
                "game_id": row["game_id"],
                "season": TARGET_SEASON,
                "week": int(row["week"]),
                "home_team": home,
                "away_team": away,
                "kickoff_utc": kick,
                "forecast_cutoff_utc": kick,
                "rating_week_contiguous": int(row["week"]) - 1,
                "rest_days_et": rest_et,
                "rest_days_utc_contrast": rest_utc,
                "utc_et_dow_mismatch": rest_et != rest_utc,
                "rest_bind": "BIND_PACKET_ONLY",
                "rest_lineage": "155d3ca0_ET_DOW",
                "completed_same_season_games_home": None,
                "completed_same_season_games_away": None,
                "record_asof_home": None,
                "record_asof_away": None,
                "wl_count_status": "UNRESOLVED",
                "wl_count_note": (
                    "not taken from 1ee90fac; 50bda875 only after independent "
                    "parity to sealed input matrices"
                ),
            }
        )

    ids_sorted = sorted(r["game_id"] for r in identities)
    if len(ids_sorted) != len(set(ids_sorted)):
        raise SealRefuse("duplicate game_id in identity universe")
    combined_hash = selection_hash(ids_sorted)
    week_hashes = {
        week: selection_hash(
            [r["game_id"] for r in identities if r["week"] == week]
        )
        for week in WEEKS
    }
    if week_hashes[7] != STAGE_B_W7_HASH:
        raise SealRefuse(f"W7 selection_hash {week_hashes[7]} != Stage B {STAGE_B_W7_HASH}")
    if week_hashes[8] != STAGE_B_W8_HASH:
        raise SealRefuse(f"W8 selection_hash {week_hashes[8]} != Stage B {STAGE_B_W8_HASH}")

    t2 = derive_t2_risks(rows)
    t2_ids = [item["game_id"] for item in t2]
    if t2_ids != [spec["game_id"] for spec in SEALED_T2_RISKS]:
        raise SealRefuse("T2 risk order/id drift vs sealed 24")
    if len(t2_ids) != 24:
        raise SealRefuse(f"T2 risk n={len(t2_ids)} != 24")

    recipe = (
        "sha256(utf-8 of sorted canonical game_id list joined by \\n "
        "with trailing \\n)"
    )
    seal = {
        "ticket": "t5044u",
        "owner_clear_tip": "12763c08",
        "artifact": "GATE1_IDENTITY_SEAL_2017_W7_W17",
        "labels": ["RETRO_FIT", "DEV_RESEARCH", "A1"],
        "cert": 0,
        "nfl_nogo": True,
        "phase": 1,
        "if_authorized": False,
        "q2s_emit_authorized": False,
        "look_authorized": False,
        "stage_c_authorized": False,
        "sealed_before_pbp_open": True,
        "pbp_opened_at_seal": False,
        "pbp_absent_at_seal_start": True,
        "pbp_paths_checked_absent": pbp_paths_checked,
        "selection_hash_recipe": recipe,
        "n_scheduled": EXPECTED_N,
        "n_identity_sealed": len(identities),
        "n_outcome_excluded": 0,
        "n_t2_bye_return_risks": 24,
        "n_replaced": 0,
        "n_filled": 0,
        "selection_hash_combined": combined_hash,
        "selection_hash_by_week": {str(k): v for k, v in week_hashes.items()},
        "stage_b_w7_hash_match": True,
        "stage_b_w8_hash_match": True,
        "games_csv_pin": {
            "sha256": GAMES_SHA256,
            "sha8": "4fe1cdd7",
            "path": "pins/games_4fe1cdd7.csv",
            "columns_read": list(IDENTITY_COLS),
            "columns_not_read": [
                "market_*",
                "epa_*",
                "*_prob",
                "trailing_*",
                "packaged_*",
                "record_offense_index_*",
                "record_defense_index_*",
                "rest_days_*",
            ],
        },
        "quarantined_index": {
            "sha8": "1ee90fac",
            "gate": "83646d78",
            "opened": False,
            "scored_from": False,
        },
        "outcomes_50bda875": {
            "opened_at_gate1": False,
            "use": "deferred_until_independent_matrix_parity",
        },
        "exclusion_rule": (
            "All 4fe1cdd7 scheduled rows for 2017 REG W7–W17 stay in the "
            "identity universe. Zero-completed-as-of is a completeness rule, "
            "not an identity drop. T2 exact-week misses stay listed. No "
            "last-played, fills, replacement games, or outcome-based exclusion."
        ),
        "completeness_rules": {
            "contract": "b41f4b43",
            "builder": "7e77c57f",
            "fields_per_game": 27,
            "context_fields": CONTRACT_FIELDS_27["context"],
            "efficiency_fields": CONTRACT_FIELDS_27["efficiency"],
            "zero_completed_asof": (
                "If either side has 0 completed same-season games as-of "
                "kickoff (cf514078), mark ineligible/MISSING — retain, do "
                "not replace. Count source unresolved at this seal "
                "(not 1ee90fac). Expected 0 in this window."
            ),
            "t2_exact_week": (
                "lookup_t2(rating_week=week-1) only. Bye-return sides keep "
                "MISSING_RECORD on T2 cells. No last-played-week fill."
            ),
            "complete_for_later_if": "27/27 DERIVED_PREGAME only (phase 4; not this run)",
            "no_new_index_formula": True,
        },
        "cites": [
            "12763c08",
            "189ed49d",
            "8be58684",
            "51d02c20",
            "d7e0a6bc",
            "2db90f76",
            "404a4ab2",
            "4334b7a3",
        ],
        "rest": {
            "bind": "BIND_PACKET_ONLY",
            "heuristic": "155d3ca0_ET_DOW",
            "if_tip_later": "6ca03716",
            "if_tip_forbidden": "90bf65ab",
        },
    }

    GATE1.mkdir(parents=True, exist_ok=True)
    manifest = {
        "artifact": "IDENTITY_MANIFEST_2017_W7_W17",
        "ticket": "t5044u",
        "n": len(identities),
        "selection_hash": combined_hash,
        "games": identities,
    }
    t2_doc = {
        "artifact": "T2_BYE_RETURN_RISKS",
        "ticket": "t5044u",
        "n": len(t2),
        "rule": "exact lookup_t2(rating_week); no last-played fill; retain",
        "risks": t2,
    }

    (GATE1 / "SELECTION_HASH_SEAL.json").write_text(
        json.dumps(seal, indent=2, sort_keys=True) + "\n"
    )
    (GATE1 / "IDENTITY_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    )
    (GATE1 / "T2_BYE_RETURN_RISKS.json").write_text(
        json.dumps(t2_doc, indent=2, sort_keys=True) + "\n"
    )
    seal_sha = sha256_file(GATE1 / "SELECTION_HASH_SEAL.json")
    (GATE1 / "SELECTION_HASH_SEAL.json.sha256").write_text(
        f"{seal_sha}  SELECTION_HASH_SEAL.json\n"
    )
    print(
        json.dumps(
            {
                "ok": True,
                "n": len(identities),
                "selection_hash": combined_hash,
                "n_t2": len(t2),
                "seal_sha256": seal_sha,
                "pbp_opened": False,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SealRefuse as exc:
        print(f"SEAL_REFUSE: {exc}", file=sys.stderr)
        raise SystemExit(2)
