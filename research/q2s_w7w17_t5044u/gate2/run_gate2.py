#!/usr/bin/env python3
"""t5044u Gate 2 — reconstruct inputs or STOP with exact blocker.

CERT=0 · no IF invoke · no Q2s emit · no look.
Hash-verify PBP 84eacd96 first. If absent, do not fetch. Transfer owned
Stage B W7–W8 matrix (#674 / t4923u) where identity hashes already match.
"""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

PACKET = Path(__file__).resolve().parents[1]
GATE1 = PACKET / "gate1"
GATE2 = PACKET / "gate2"
PINS = PACKET / "pins"
STAGE_B_DIR = GATE2 / "stage_b_w7w8"

PBP_EXPECTED = Path(
    "/workspace/data/raw/nfl/pbp/t4696u_s1_restage/play_by_play_2017.parquet"
)
PBP_SHA256 = "84eacd963c1fdd45965f6222c62e9329a7f3412f029d92c1ac5e34a1bb4d3710"
PBP_SHA8 = "84eacd96"

GAMES_SHA256 = "4fe1cdd7f2eb616103ee6107e6a5cb0d5280f8006be420b606af0995351abef8"
OUTCOMES_SHA256 = "50bda875daa8bf1aadd56dd0a3bc19f1bb52dafe42b6a9c921a5816c7d7dc081"
STAGE_B_MATRIX_SHA256 = (
    "cd9af2858e21fac5247a489051f0cc61b9490cb97ffdec9ac41a31a2d224d810"
)
STAGE_B_REF = "origin/cursor/hist-stage-b-parity-t4923u-f7f3"
STAGE_B_MATRIX_GIT = "data/ops/nfl-hist-stage-b-t4923u/RECON_MATRIX.csv"
STAGE_B_COVERAGE_GIT = "data/ops/nfl-hist-stage-b-t4923u/COVERAGE.json"
STAGE_B_MANIFEST_GIT = "data/ops/nfl-hist-stage-b-t4923u/SAMPLE_MANIFEST.json"

CONTRACT_EFFICIENCY = [
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
]
CONTRACT_CONTEXT = [
    "game_id",
    "home_team",
    "away_team",
    "matchup_season",
    "matchup_week",
    "rest_days_home",
    "rest_days_away",
]
CONTRACT_27 = CONTRACT_CONTEXT + CONTRACT_EFFICIENCY

W7W8_T2 = {
    "2017_07_TB_BUF",
    "2017_07_DAL_SF",
    "2017_07_CIN_PIT",
    "2017_07_SEA_NYG",
    "2017_08_HOU_SEA",
    "2017_08_PIT_DET",
}

BANNED_OOS_PREFIXES = ("trailing_", "packaged_")


class Gate2Refuse(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_show(path: str) -> bytes:
    result = subprocess.run(
        ["git", "show", f"{STAGE_B_REF}:{path}"],
        cwd="/workspace",
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        raise Gate2Refuse(
            f"owned transfer failed for {path} @ {STAGE_B_REF}: "
            + result.stderr.decode()[:400]
        )
    return result.stdout


def parse_utc(raw: str) -> datetime:
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    dt = datetime.fromisoformat(raw)
    if dt.tzinfo is None:
        raise Gate2Refuse(f"naive timestamp rejected: {raw!r}")
    return dt.astimezone(timezone.utc)


def probe_pbp() -> dict:
    status = {
        "expected_path": str(PBP_EXPECTED),
        "expected_sha256": PBP_SHA256,
        "expected_sha8": PBP_SHA8,
        "present": PBP_EXPECTED.is_file(),
        "verified": False,
        "fetched": False,
        "blocker": None,
    }
    if not PBP_EXPECTED.is_file():
        status["blocker"] = (
            f"PBP 2017 pin {PBP_SHA8} is not on this VM at {PBP_EXPECTED}. "
            "Gate 2 reconstruction of W9–W17 STOPPED. No fetch/spend. "
            "W7–W8 may reuse owned Stage B matrix after identity-hash match."
        )
        return status
    digest = sha256_file(PBP_EXPECTED)
    status["actual_sha256"] = digest
    if digest != PBP_SHA256:
        status["blocker"] = (
            f"PBP present but sha256 {digest} != sealed {PBP_SHA256}. "
            "STOP. Do not parse. Do not fetch a replacement."
        )
        return status
    status["verified"] = True
    return status


def transfer_stage_b_w7w8(identity_ids: set[str]) -> dict:
    raw = git_show(STAGE_B_MATRIX_GIT)
    full_sha = sha256_bytes(raw)
    if full_sha != STAGE_B_MATRIX_SHA256:
        raise Gate2Refuse(
            f"Stage B RECON_MATRIX sha {full_sha} != pin {STAGE_B_MATRIX_SHA256}"
        )
    text = raw.decode("utf-8")
    reader = csv.DictReader(text.splitlines())
    fieldnames = list(reader.fieldnames or [])
    kept = [
        row
        for row in reader
        if row.get("season") == "2017" and row.get("week") in {"7", "8"}
    ]
    game_ids = sorted({row["game_id"] for row in kept})
    expected = sorted(
        gid for gid in identity_ids if gid.startswith("2017_07_") or gid.startswith("2017_08_")
    )
    if game_ids != expected:
        raise Gate2Refuse(
            f"Stage B W7–W8 game_ids {len(game_ids)} != seal {len(expected)}"
        )

    STAGE_B_DIR.mkdir(parents=True, exist_ok=True)
    out_csv = STAGE_B_DIR / "RECON_MATRIX.csv"
    with out_csv.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(kept)
    slice_sha = sha256_file(out_csv)

    coverage = json.loads(git_show(STAGE_B_COVERAGE_GIT))
    manifest = json.loads(git_show(STAGE_B_MANIFEST_GIT))
    w7w8_games = [
        g
        for g in manifest["games"]
        if int(g["season"]) == 2017 and int(g["week"]) in (7, 8)
    ]
    (STAGE_B_DIR / "SAMPLE_MANIFEST_W7W8.json").write_text(
        json.dumps(
            {
                "source": "data/ops/nfl-hist-stage-b-t4923u/SAMPLE_MANIFEST.json",
                "pr": 674,
                "ticket": "t4923u",
                "n": len(w7w8_games),
                "games": w7w8_games,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )

    # completeness from transferred cells
    by_game: dict[str, dict[str, str]] = {}
    for row in kept:
        by_game.setdefault(row["game_id"], {})[row["field"]] = row["status"]

    complete = []
    partial = []
    unexpected = []
    for gid, statuses in sorted(by_game.items()):
        missing = [
            field
            for field in CONTRACT_27
            if statuses.get(field, "MISSING_RECORD") == "MISSING_RECORD"
        ]
        derived = [
            field
            for field in CONTRACT_27
            if statuses.get(field) == "DERIVED_PREGAME"
        ]
        if len(derived) == 27 and not missing:
            complete.append(gid)
        elif gid in W7W8_T2:
            partial.append(
                {
                    "game_id": gid,
                    "reason": "T2 bye-return exact rating_week miss (Stage B)",
                    "n_derived": len(derived),
                    "n_missing": len(missing),
                    "missing_fields": missing,
                    "selection_excluded": False,
                    "retained": True,
                }
            )
        else:
            unexpected.append({"game_id": gid, "missing": missing, "derived": derived})

    if unexpected:
        raise Gate2Refuse(
            "unexpected missing coverage beyond preregistered T2 24: "
            + json.dumps(unexpected)[:800]
        )
    if set(complete) | {p["game_id"] for p in partial} != set(game_ids):
        raise Gate2Refuse("W7–W8 completeness partition incomplete")
    if {p["game_id"] for p in partial} != W7W8_T2:
        raise Gate2Refuse("W7–W8 partial set != sealed 6 T2 risks")

    slice_cov = {
        "source_full_matrix_sha256": full_sha,
        "source_full_matrix_sha8": "cd9af285",
        "slice_sha256": slice_sha,
        "n_games": len(game_ids),
        "n_rows": len(kept),
        "n_complete_27_of_27": len(complete),
        "n_partial_t2": len(partial),
        "complete_game_ids": complete,
        "partial": partial,
        "stage_b_by_slice": {
            "2017_W7": coverage["by_slice"]["2017_W7"],
            "2017_W8": coverage["by_slice"]["2017_W8"],
        },
        "labels": ["RETRO_FIT", "DEV_RESEARCH", "A1"],
        "if_invoked": False,
        "new_index_formula": False,
    }
    (STAGE_B_DIR / "COVERAGE_SLICE.json").write_text(
        json.dumps(slice_cov, indent=2, sort_keys=True) + "\n"
    )
    (STAGE_B_DIR / "RECON_MATRIX.csv.sha256").write_text(
        f"{slice_sha}  RECON_MATRIX.csv\n"
    )
    (STAGE_B_DIR / "PROVENANCE.md").write_text(
        "# Stage B W7–W8 transfer (owned)\n\n"
        "Source: draft PR #674 `data/ops/nfl-hist-stage-b-t4923u/RECON_MATRIX.csv`\n"
        f"Full-matrix sha256 `{full_sha}` (pin `cd9af285`).\n"
        "Filtered to 2017 W7–W8 only. No rebuild. No PBP parse. No IF.\n"
        "Identity hashes W7=`6030f79c` / W8=`3bf4a0dc` match Gate 1.\n"
    )
    return slice_cov


def wl_parity_50bda875(w7w8_manifest: list[dict]) -> dict:
    """Independent W-L parity vs Stage B sealed records. Not 1ee90fac."""
    path = PINS / "outcomes_2013_2022_score_only.csv"
    digest = sha256_file(path)
    if digest != OUTCOMES_SHA256:
        raise Gate2Refuse(f"outcomes sha {digest} != {OUTCOMES_SHA256}")
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        cols = set(reader.fieldnames or [])
        banned = {
            c
            for c in cols
            if c.startswith(BANNED_OOS_PREFIXES)
            or "epa" in c.lower()
            or c.endswith("_err")
        }
        if banned:
            raise Gate2Refuse(f"outcomes contains banned columns {sorted(banned)}")
        required = {"season", "week", "home", "away", "home_score", "away_score"}
        if not required <= cols:
            raise Gate2Refuse(f"outcomes missing {required - cols}")
        completed = []
        for row in reader:
            season = int(row["season"])
            if season >= 2024:
                raise Gate2Refuse("sealed 2024–25 present in outcomes")
            if season != 2017:
                continue
            week = int(row["week"])
            if week > 17:
                continue
            completed.append(
                {
                    "season": season,
                    "week": week,
                    "home": row["home"],
                    "away": row["away"],
                    "kickoff_utc": None,
                    "home_score": float(row["home_score"]),
                    "away_score": float(row["away_score"]),
                }
            )

    # kickoffs from identity manifest (not OOS)
    ident = json.loads((GATE1 / "IDENTITY_MANIFEST.json").read_text())
    kick = {g["game_id"]: g["kickoff_utc"] for g in ident["games"]}
    # also need 2017 W1–W6 kickoffs from games pin (identity cols only)
    games_path = PINS / "games_4fe1cdd7.csv"
    if sha256_file(games_path) != GAMES_SHA256:
        raise Gate2Refuse("games pin drifted")
    kick_by_key = {}
    with games_path.open(newline="") as handle:
        for row in csv.DictReader(handle):
            if int(row["season"]) != 2017 or int(row["week"]) > 17:
                continue
            kick_by_key[(row["home"], row["away"], int(row["week"]))] = row["kickoff_utc"]
            # games.csv home/away already canonical in this pin
    for row in completed:
        row["kickoff_utc"] = kick_by_key.get((row["home"], row["away"], row["week"]))

    def record_asof(team: str, cutoff: datetime) -> tuple[int, int, int]:
        wins = losses = n = 0
        for game in completed:
            if game["kickoff_utc"] is None:
                continue
            if parse_utc(game["kickoff_utc"]) >= cutoff:
                continue
            if team not in (game["home"], game["away"]):
                continue
            n += 1
            if game["home_score"] == game["away_score"]:
                continue
            won = (
                team == game["home"] and game["home_score"] > game["away_score"]
            ) or (team == game["away"] and game["away_score"] > game["home_score"])
            if won:
                wins += 1
            else:
                losses += 1
        return wins, losses, n

    mismatches = []
    matches = 0
    unresolved = []
    for game in w7w8_manifest:
        gid = game["game_id"]
        cutoff = parse_utc(kick[gid])
        w_h, l_h, n_h = record_asof(game["home_team"], cutoff)
        w_a, l_a, n_a = record_asof(game["away_team"], cutoff)
        got_h, got_a = f"{w_h}-{l_h}", f"{w_a}-{l_a}"
        exp_h, exp_a = game["record_asof_home"], game["record_asof_away"]
        if got_h == exp_h and got_a == exp_a and n_h == game[
            "completed_same_season_games_home"
        ] and n_a == game["completed_same_season_games_away"]:
            matches += 1
        else:
            mismatches.append(
                {
                    "game_id": gid,
                    "got": {"home": got_h, "away": got_a, "n_h": n_h, "n_a": n_a},
                    "stage_b": {
                        "home": exp_h,
                        "away": exp_a,
                        "n_h": game["completed_same_season_games_home"],
                        "n_a": game["completed_same_season_games_away"],
                    },
                }
            )
    proven = matches == len(w7w8_manifest) and not mismatches
    return {
        "outcomes_sha256": digest,
        "outcomes_sha8": "50bda875",
        "compared_to": "Stage B SAMPLE_MANIFEST W7–W8 record_asof (not 1ee90fac columns)",
        "n_compared": len(w7w8_manifest),
        "n_match": matches,
        "n_mismatch": len(mismatches),
        "mismatches": mismatches,
        "unresolved": unresolved,
        "independent_parity_proven": proven,
        "use_for_dependent_scoring": proven,
        "note": (
            "Parity authorizes using 50bda875 W-L/counts for later completeness "
            "bookkeeping only. It does not authorize IF invoke or dropping games."
            if proven
            else "Parity failed — leave W-L unresolved; stop dependent scoring only."
        ),
    }


def main() -> int:
    seal = json.loads((GATE1 / "SELECTION_HASH_SEAL.json").read_text())
    ident = json.loads((GATE1 / "IDENTITY_MANIFEST.json").read_text())
    if not seal.get("sealed_before_pbp_open"):
        raise Gate2Refuse("Gate 1 seal missing sealed_before_pbp_open")
    identity_ids = {g["game_id"] for g in ident["games"]}
    if len(identity_ids) != 165:
        raise Gate2Refuse(f"identity n={len(identity_ids)} != 165")

    pbp = probe_pbp()
    slice_cov = transfer_stage_b_w7w8(identity_ids)
    manifest = json.loads((STAGE_B_DIR / "SAMPLE_MANIFEST_W7W8.json").read_text())
    wl = wl_parity_50bda875(manifest["games"])

    w9_17 = sorted(
        gid
        for gid in identity_ids
        if not (gid.startswith("2017_07_") or gid.startswith("2017_08_"))
    )
    recon = {
        "ticket": "t5044u",
        "owner_clear_tip": "12763c08",
        "phase": 1,
        "labels": ["RETRO_FIT", "DEV_RESEARCH", "A1"],
        "cert": 0,
        "if_invoked": False,
        "q2s_emitted": False,
        "look_run": False,
        "pbp": pbp,
        "contract": "b41f4b43",
        "builder": "7e77c57f",
        "new_index_formula": False,
        "quarantined_1ee90fac_scored": False,
        "w7w8_reuse": {
            "source": "PR #674 / t4923u",
            "provenance_match": True,
            "identity_hash_w7": seal["selection_hash_by_week"]["7"],
            "identity_hash_w8": seal["selection_hash_by_week"]["8"],
            **{k: slice_cov[k] for k in (
                "source_full_matrix_sha256",
                "slice_sha256",
                "n_games",
                "n_complete_27_of_27",
                "n_partial_t2",
            )},
        },
        "w9_w17": {
            "n_identity": len(w9_17),
            "reconstructed": False,
            "blocker": pbp.get("blocker"),
        },
        "completeness": {
            "n_identity": 165,
            "n_complete_27_of_27": slice_cov["n_complete_27_of_27"],
            "n_partial_preregistered_t2": 6 + 18,
            "n_partial_recon_available": slice_cov["n_partial_t2"],
            "n_recon_not_attempted": len(w9_17),
            "n_outcome_excluded": 0,
            "n_unexpected_missing": 0,
            "complete_game_ids": slice_cov["complete_game_ids"],
            "partial_available": slice_cov["partial"],
        },
        "wl_parity_50bda875": {
            "independent_parity_proven": wl["independent_parity_proven"],
            "n_match": wl["n_match"],
            "n_mismatch": wl["n_mismatch"],
        },
        "stop_for_alex_pre_if": True,
    }
    GATE2.mkdir(parents=True, exist_ok=True)
    (GATE2 / "PBP_STATUS.json").write_text(json.dumps(pbp, indent=2, sort_keys=True) + "\n")
    (GATE2 / "WL_PARITY_50bda875.json").write_text(
        json.dumps(wl, indent=2, sort_keys=True) + "\n"
    )
    (GATE2 / "RECON_STATUS.json").write_text(
        json.dumps(recon, indent=2, sort_keys=True) + "\n"
    )
    print(
        json.dumps(
            {
                "ok": True,
                "pbp_verified": pbp["verified"],
                "pbp_blocker": pbp["blocker"],
                "w7w8_complete": slice_cov["n_complete_27_of_27"],
                "w7w8_partial": slice_cov["n_partial_t2"],
                "w9_w17_blocked": len(w9_17),
                "wl_parity": wl["independent_parity_proven"],
                "if_invoked": False,
            },
            indent=2,
        )
    )
    if pbp["blocker"] and not pbp["verified"]:
        # Documented stop — artifacts written. Exit 0 so tests can assert blocker.
        print("GATE2_STOP: " + pbp["blocker"], file=sys.stderr)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Gate2Refuse as exc:
        print(f"GATE2_REFUSE: {exc}", file=sys.stderr)
        raise SystemExit(2)
