#!/usr/bin/env python3
"""t4923u Stage B — SEAL ONLY (Step 0).

Determines eligible game_ids from games.csv 4fe1cdd7 + OOS 1ee90fac
as-of counts ONLY. Writes SELECTION_HASH_SEAL.json used by
STAGE_B_GAME_SELECTION_t4923u.md.

Does not open PBP. Does not import pandas. Does not rebuild 5g fields.

Transforms copied verbatim from
data/ops/nfl-hist-bt-stage1b-w3w6-t4893u/seal_selection_t4893u.py
(itself copied from W2 build_recon_t4893u.py 7e77c57f):
  sha256_file, sha256_text, parse_utc, rest_days_et, rest_days_utc,
  normalize_games_abbr, selection_hash, load_games, load_oos_2016_2017,
  build_completed, record_asof.
No new selection transforms. Week/season *scope* only is extended to
the frozen t4923u sample: 2017 W2 (parity 14) + 2017 W7–W8 + 2016 W8.

Index 1ee90fac is PILOT-ONLY (gate 83646d78).
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

PACKET = Path(__file__).resolve().parent
REPO = PACKET.parents[2]

GAMES_CSV = (
    REPO / "data/ops/nfl-t4422u-walkforward-pergame-unblended-2013-2023/games.csv"
)
GAMES_CSV_FALLBACK = Path("/tmp/t4893u_refs/games.csv")
OOS_CSV = (
    REPO
    / "data/ops/nfl-reopening-packet-20260916/historical-oos/historical_oos_games.csv"
)

GAMES_SHA256 = "4fe1cdd7f2eb616103ee6107e6a5cb0d5280f8006be420b606af0995351abef8"
OOS_SHA256 = "1ee90facf7d44dfd19758cbf89d5518417cbc1fba6faec4e76fb33d8532adaed"

GAMES_TO_CANON = {"LA": "LAR", "WAS": "WSH", "SD": "SD"}
ET = ZoneInfo("America/New_York")

# Frozen t4923u sample slices. Do not add weeks here after seal.
SLICES = (
    {"key": "2017_W2_PARITY", "season": 2017, "week": 2, "role": "parity_vs_708513db"},
    {"key": "2017_W7", "season": 2017, "week": 7, "role": "pilot_coverage"},
    {"key": "2017_W8", "season": 2017, "week": 8, "role": "pilot_coverage"},
    {"key": "2016_W8", "season": 2016, "week": 8, "role": "season_hardcode_check"},
)

# Sealed W2 eligible 14 (t4893u SELECTION_HASH_SEAL). Must match exactly.
W2_SEALED_ELIGIBLE = [
    "2017_02_ARI_IND",
    "2017_02_BUF_CAR",
    "2017_02_CLE_BAL",
    "2017_02_DAL_DEN",
    "2017_02_DET_NYG",
    "2017_02_GB_ATL",
    "2017_02_HOU_CIN",
    "2017_02_MIN_PIT",
    "2017_02_NE_NO",
    "2017_02_NYJ_OAK",
    "2017_02_PHI_KC",
    "2017_02_SF_SEA",
    "2017_02_TEN_JAX",
    "2017_02_WAS_LA",
]
W2_SELECTION_HASH = (
    "96a1317613d695fe027caf4a9230028480f64facfe460736702bd66328708640"
)
W2_PREDECLARED_MISSING = {
    "2017_02_CHI_TB": "TB home — 0 completed 2017 games as-of kickoff (Irma postpone)",
    "2017_02_MIA_LAC": "MIA away — 0 completed 2017 games as-of kickoff (Irma postpone)",
}

PBP_2016 = Path(
    "/workspace/data/raw/nfl/pbp/t4696u_s1_restage/play_by_play_2016.parquet"
)
PBP_2017 = Path(
    "/workspace/data/raw/nfl/pbp/t4696u_s1_restage/play_by_play_2017.parquet"
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def parse_utc(raw: str) -> datetime:
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    dt = datetime.fromisoformat(raw)
    if dt.tzinfo is None:
        raise ValueError(f"naive timestamp rejected: {raw!r}")
    return dt.astimezone(timezone.utc)


def rest_days_et(kickoff_utc: str) -> float:
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


def selection_hash(game_ids: list[str]) -> str:
    payload = "\n".join(sorted(game_ids)) + "\n"
    return sha256_text(payload)


def load_games() -> tuple[Path, list[dict]]:
    path = GAMES_CSV if GAMES_CSV.is_file() else GAMES_CSV_FALLBACK
    digest = sha256_file(path)
    if digest != GAMES_SHA256:
        raise SystemExit(f"games.csv sha256 {digest} != pin {GAMES_SHA256}")
    rows = []
    with path.open(newline="") as fh:
        for row in csv.DictReader(fh):
            season = int(row["season"])
            if season >= 2024:
                raise SystemExit("abort: season>=2024 row in games.csv pin")
            rows.append(row)
    return path, rows


def load_oos_2016_2017() -> list[dict]:
    digest = sha256_file(OOS_CSV)
    if digest != OOS_SHA256:
        raise SystemExit(f"historical_oos sha256 {digest} != pin {OOS_SHA256}")
    kept = []
    with OOS_CSV.open(newline="") as fh:
        for row in csv.DictReader(fh):
            season = int(float(row["season"]))
            if season in (2016, 2017):
                kept.append(row)
    return kept


def build_completed(all_games: list[dict], oos: list[dict]) -> list[dict]:
    oos_by_key = {}
    for row in oos:
        key = (
            int(float(row["season"])),
            int(float(row["week"])),
            normalize_games_abbr(row["home"]),
            normalize_games_abbr(row["away"]),
        )
        oos_by_key[key] = row
    completed = []
    for row in all_games:
        season = int(row["season"])
        week = int(row["week"])
        if season not in (2016, 2017) or week > 17:
            continue
        oos_row = oos_by_key.get(
            (
                season,
                week,
                normalize_games_abbr(row["home"]),
                normalize_games_abbr(row["away"]),
            )
        )
        if oos_row is None:
            continue
        hs, aws = oos_row.get("home_score"), oos_row.get("away_score")
        if hs in (None, "") or aws in (None, ""):
            continue
        completed.append(
            {
                "season": season,
                "week": week,
                "game_id": row["game_id"],
                "home": normalize_games_abbr(row["home"]),
                "away": normalize_games_abbr(row["away"]),
                "kickoff_utc": row["kickoff_utc"],
                "home_score": float(hs),
                "away_score": float(aws),
            }
        )
    return completed


def record_asof(
    completed: list[dict], team: str, cutoff: datetime, season: int
) -> tuple[int, int, int]:
    w = l = n = 0
    for g in completed:
        if g["season"] != season:
            continue
        if parse_utc(g["kickoff_utc"]) >= cutoff:
            continue
        if team not in (g["home"], g["away"]):
            continue
        n += 1
        if g["home_score"] == g["away_score"]:
            continue
        won = (team == g["home"] and g["home_score"] > g["away_score"]) or (
            team == g["away"] and g["away_score"] > g["home_score"]
        )
        if won:
            w += 1
        else:
            l += 1
    return w, l, n


def eligible_for_slice(all_games: list[dict], completed: list[dict], slc: dict):
    season = slc["season"]
    week = slc["week"]
    source = [
        r
        for r in all_games
        if int(r["season"]) == season and int(r["week"]) == week
    ]
    if not source:
        raise SystemExit(f"no games.csv rows for {season} W{week}")
    if any(not r.get("kickoff_utc") for r in source):
        raise SystemExit(
            f"{season} W{week} row missing kickoff — exclude rule, do not impute"
        )

    source_rows = []
    exclusions = []
    for row in sorted(source, key=lambda r: (r["kickoff_utc"], r["game_id"])):
        gid = row["game_id"]
        home = normalize_games_abbr(row["home"])
        away = normalize_games_abbr(row["away"])
        kick = row["kickoff_utc"]
        cutoff = parse_utc(kick)
        w_h, l_h, n_h = record_asof(completed, home, cutoff, season)
        w_a, l_a, n_a = record_asof(completed, away, cutoff, season)
        rec = {
            "game_id": gid,
            "season": season,
            "week": week,
            "home_team": home,
            "away_team": away,
            "kickoff_utc": kick,
            "forecast_cutoff_utc": kick,
            "rating_week_contiguous": week - 1,
            "rest_days_et": rest_days_et(kick),
            "rest_days_utc_contrast": rest_days_utc(kick),
            "utc_et_dow_mismatch": rest_days_et(kick) != rest_days_utc(kick),
            "record_asof_home": f"{w_h}-{l_h}",
            "record_asof_away": f"{w_a}-{l_a}",
            "completed_same_season_games_home": n_h,
            "completed_same_season_games_away": n_a,
            "games_csv_record_entering_home": row["record_entering_home"],
            "games_csv_record_entering_away": row["record_entering_away"],
            "games_csv_offense_index_home": row["record_offense_index_home"],
            "games_csv_offense_index_away": row["record_offense_index_away"],
            "games_csv_defense_index_home": row["record_defense_index_home"],
            "games_csv_defense_index_away": row["record_defense_index_away"],
            "epa_status_games_csv": row["epa_status"],
            "epa_blocker_games_csv": row["epa_blocker"],
        }
        if n_h < 1 or n_a < 1:
            zero_side = []
            if n_h < 1:
                zero_side.append(f"{home} home")
            if n_a < 1:
                zero_side.append(f"{away} away")
            reason = (
                f"{' / '.join(zero_side)} — 0 completed {season} games "
                "as-of kickoff"
            )
            if gid in W2_PREDECLARED_MISSING:
                reason = W2_PREDECLARED_MISSING[gid]
            exclusions.append(
                {
                    "game_id": gid,
                    "reason": reason,
                    "predeclared": gid in W2_PREDECLARED_MISSING,
                    "retained_missing": True,
                    "substituted": False,
                    "completed_same_season_games_home": n_h,
                    "completed_same_season_games_away": n_a,
                    "home_team": home,
                    "away_team": away,
                    "season": season,
                    "week": week,
                    "rule": (
                        "exclude any game where either side has 0 completed "
                        "same-season games as-of kickoff; leave MISSING, no fills, "
                        "no substitute games"
                    ),
                }
            )
            continue
        source_rows.append(rec)

    ids_sorted = sorted(r["game_id"] for r in source_rows)
    return {
        "key": slc["key"],
        "role": slc["role"],
        "season": season,
        "week": week,
        "n_source": len(source),
        "n_excluded_missing": len(exclusions),
        "n_eligible": len(source_rows),
        "exclusions": exclusions,
        "source_rows": source_rows,
        "game_ids_sorted": ids_sorted,
        "selection_hash": selection_hash(ids_sorted),
        "excluded_game_ids": [e["game_id"] for e in exclusions],
    }


def main() -> None:
    if PBP_2016.exists() or PBP_2017.exists():
        raise SystemExit(
            "PBP present at seal start — abort. Step 0 must run before remount."
        )

    _games_path, all_games = load_games()
    oos = load_oos_2016_2017()
    completed = build_completed(all_games, oos)

    slices = []
    all_eligible: list[str] = []
    all_missing: list[str] = []
    for slc in SLICES:
        blk = eligible_for_slice(all_games, completed, slc)
        slices.append(blk)
        all_eligible.extend(blk["game_ids_sorted"])
        all_missing.extend(blk["excluded_game_ids"])

    w2 = next(s for s in slices if s["key"] == "2017_W2_PARITY")
    if w2["game_ids_sorted"] != W2_SEALED_ELIGIBLE:
        raise SystemExit(
            "W2 eligible set != sealed t4893u 14 — abort, do not re-slice"
        )
    if w2["selection_hash"] != W2_SELECTION_HASH:
        raise SystemExit(
            f"W2 selection_hash {w2['selection_hash']} != sealed {W2_SELECTION_HASH}"
        )
    if sorted(w2["excluded_game_ids"]) != sorted(W2_PREDECLARED_MISSING):
        raise SystemExit("W2 MISSING set != sealed Irma pair — retain, do not replace")

    recipe = (
        "sha256(utf-8 of sorted canonical game_id list joined by \\n "
        "with trailing \\n)"
    )
    combined_eligible = sorted(all_eligible)
    combined_missing = sorted(all_missing)
    seal = {
        "ticket": "t4923u",
        "artifact": "STAGE_B_GAME_SELECTION",
        "labels": ["RETRO_FIT", "DEV_RESEARCH"],
        "cert": 0,
        "nfl_nogo": True,
        "stage_c_authorized": False,
        "sealed_before_rebuild": True,
        "sealed_before_pbp_open": True,
        "pbp_opened_at_seal": False,
        "pbp_absent_at_seal_start": True,
        "selection_hash_recipe": recipe,
        "exclusion_rule": (
            "All games.csv rows for the frozen slices, minus any game where "
            "either side has 0 completed same-season games as-of kickoff. "
            "Ineligible games are RETAINED as MISSING — not replaced, not "
            "filled, not swapped for another week/season game."
        ),
        "w2_parity_rule": (
            "The 14 eligible W2 games are the sealed t4893u list "
            "(selection_hash 96a13176). Re-derived here only to verify "
            "identity. Not a new slice (e.g. not 'first 14 by game_id')."
        ),
        "index_pin": {
            "sha256": OOS_SHA256,
            "sha8": "1ee90fac",
            "use": "PILOT_ONLY",
            "gate": "83646d78",
            "path": str(OOS_CSV.relative_to(REPO)),
        },
        "games_csv_pin": {
            "sha256": GAMES_SHA256,
            "sha8": "4fe1cdd7",
            "path": str(GAMES_CSV.relative_to(REPO)),
        },
        "pbp_receipt_sha8": "6ee24b44",
        "recon_parity_refs": {
            "w2_content_sha256": (
                "708513db885fe362aca9446578154d58e9d8265857ec2385e475323b24f24182"
            ),
            "w2_content_sha8": "708513db",
            "w3w6_content_sha256": (
                "cdff011536a7cd9224b1238e08b707c36222243833f778f2df61b577e0c80235"
            ),
            "w3w6_content_sha8": "cdff0115",
            "note": (
                "Field-level 5g EPA/success parity is scored only on the W2 14 "
                "vs RECON 708513db. cdff0115 is a cited pin / lineage, not a "
                "sample member."
            ),
        },
        "tolerances_preregistered": {
            "registered_before_rebuild": True,
            "post_hoc_change_forbidden": True,
            "index_abs_delta": 1e-6,
            "epa_success_5g_abs_delta": 1e-9,
            "rationale": (
                "Index fields are float reconstructions of T5/record indices "
                "already verified on sealed RECON at |Δ|<1e-6 (Stage A "
                "c0cb608c). 5g EPA/success must rematerialize from the same "
                "PBP pin + T1 port (7e77c57f / 5fc97157); |Δ|<1e-9 is the "
                "pre-run numeric identity bar (near-exact float). No "
                "loosening after seeing residuals."
            ),
            "applies_to": {
                "w2_14_vs_708513db": [
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
                    "matchup_diff_off_epa_5g",
                    "matchup_diff_success_rate_5g",
                ],
                "index_tolerance_fields": [
                    "offense_index_home",
                    "offense_index_away",
                    "defense_index_home",
                    "defense_index_away",
                ],
                "epa_success_tolerance_fields": [
                    "home_off_epa_5g",
                    "away_off_epa_5g",
                    "home_def_epa_allowed_5g",
                    "away_def_epa_allowed_5g",
                    "home_success_offense_5g",
                    "away_success_offense_5g",
                    "home_success_defense_allowed_5g",
                    "away_success_defense_allowed_5g",
                    "matchup_diff_off_epa_5g",
                    "matchup_diff_success_rate_5g",
                ],
            },
            "w7w8_and_2016w8": (
                "No sealed 5g RECON exists for these games. Tolerances do "
                "not invent a compare target. Coverage + as-of eligibility "
                "only; index vs games.csv 4fe1cdd7 uses |Δ|<1e-6 when the "
                "games.csv index cell is populated and finite."
            ),
        },
        "n_source": sum(s["n_source"] for s in slices),
        "n_excluded_missing_retained": sum(s["n_excluded_missing"] for s in slices),
        "n_eligible": sum(s["n_eligible"] for s in slices),
        "selection_hash_eligible_combined": selection_hash(combined_eligible),
        "selection_hash_missing_retained_combined": selection_hash(combined_missing)
        if combined_missing
        else None,
        "game_ids_eligible_sorted": combined_eligible,
        "game_ids_missing_retained_sorted": combined_missing,
        "slices": {
            s["key"]: {
                "role": s["role"],
                "season": s["season"],
                "week": s["week"],
                "n_source": s["n_source"],
                "n_excluded_missing": s["n_excluded_missing"],
                "n_eligible": s["n_eligible"],
                "selection_hash": s["selection_hash"],
                "game_ids_sorted": s["game_ids_sorted"],
                "excluded_game_ids": s["excluded_game_ids"],
                "exclusions": s["exclusions"],
                "source_rows": [
                    {
                        "game_id": r["game_id"],
                        "season": r["season"],
                        "week": r["week"],
                        "home_team": r["home_team"],
                        "away_team": r["away_team"],
                        "kickoff_utc": r["kickoff_utc"],
                        "completed_same_season_games_home": r[
                            "completed_same_season_games_home"
                        ],
                        "completed_same_season_games_away": r[
                            "completed_same_season_games_away"
                        ],
                        "record_asof_home": r["record_asof_home"],
                        "record_asof_away": r["record_asof_away"],
                    }
                    for r in s["source_rows"]
                ],
            }
            for s in slices
        },
        "w2_lineage": {
            "packet": "data/ops/nfl-hist-bt-stage1b-w2-t4893u",
            "selection_hash": W2_SELECTION_HASH,
            "recon_content_sha8": "708513db",
            "builder_sha8": "7e77c57f",
            "n_eligible": 14,
            "n_missing_retained": 2,
            "missing_game_ids": list(W2_PREDECLARED_MISSING),
        },
        "method": (
            "Identical as-of rule to W2/W3–W6 t4893u: games.csv 4fe1cdd7 + "
            "OOS 1ee90fac as-of counts only. No PBP. Hash recipe unchanged."
        ),
        "order": {
            "file": "COS_ORDER_CURSOR_t4923u_STAGE_B_EXEC.md",
            "tip_sha8": "62ca041c",
            "tip_sha256": (
                "62ca041cf6289b2fc12b2964eaedee613cf5a0363f8f66ee75753c1feaf9c17a"
            ),
            "supersedes": "ce807d95",
            "alex_ro_after_seal": "ba1c89f5",
        },
        "prohibited": [
            "outcome_analysis",
            "model_scoring",
            "fit_tune",
            "new_acquisition",
            "2024_25",
            "stage_c",
            "q2_phase_b",
            "merge_deploy_publish",
            "touch_02197f58",
            "touch_SCORE_RESULTS_2b9f302e",
        ],
        "sealed_at_utc": datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
    }

    seal_path = PACKET / "SELECTION_HASH_SEAL.json"
    if seal_path.exists():
        existing = json.loads(seal_path.read_text(encoding="utf-8"))
        keys = (
            "selection_hash_eligible_combined",
            "game_ids_eligible_sorted",
            "game_ids_missing_retained_sorted",
            "n_eligible",
            "n_excluded_missing_retained",
            "n_source",
            "slices",
            "selection_hash_recipe",
            "exclusion_rule",
            "tolerances_preregistered",
        )
        for key in keys:
            if key == "slices":
                for sk, blk in existing.get("slices", {}).items():
                    want = seal["slices"][sk]
                    for sub in (
                        "game_ids_sorted",
                        "excluded_game_ids",
                        "selection_hash",
                        "n_eligible",
                        "n_source",
                    ):
                        if blk.get(sub) != want.get(sub):
                            raise SystemExit(
                                f"SELECTION already written with different slices.{sk}.{sub}"
                            )
                continue
            if existing.get(key) != seal.get(key):
                raise SystemExit(
                    f"SELECTION_HASH_SEAL.json already written with different {key} — abort"
                )
        print(
            json.dumps(
                {
                    "phase": "SEAL_VERIFIED",
                    "selection_hash_eligible_combined": seal[
                        "selection_hash_eligible_combined"
                    ],
                    "n_eligible": seal["n_eligible"],
                    "n_missing_retained": seal["n_excluded_missing_retained"],
                    "path": str(seal_path),
                },
                indent=2,
            )
        )
        return

    seal_path.write_text(json.dumps(seal, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "phase": "SEALED",
                "selection_hash_eligible_combined": seal[
                    "selection_hash_eligible_combined"
                ],
                "n_source": seal["n_source"],
                "n_eligible": seal["n_eligible"],
                "n_missing_retained": seal["n_excluded_missing_retained"],
                "per_slice": {
                    k: {
                        "n_source": v["n_source"],
                        "n_eligible": v["n_eligible"],
                        "n_missing": v["n_excluded_missing"],
                        "hash": v["selection_hash"],
                        "missing_ids": v["excluded_game_ids"],
                    }
                    for k, v in seal["slices"].items()
                },
                "pbp_opened": False,
                "path": str(seal_path),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    sys.exit(main())
