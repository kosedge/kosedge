#!/usr/bin/env python3
"""t5044u Gate 2 rebuild — 2017 REG W7–W17 after hash-verified PBP 84eacd96.

Uses builder 7e77c57f T1–T4 / T5 helpers. Contract b41f4b43.
T5 W-L from score-only 50bda875 (parity-proven). Does NOT open 1ee90fac.
Does NOT invoke IF, emit Q2s, freeze, or look.
"""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import math
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

PACKET = Path(__file__).resolve().parents[1]
GATE1 = PACKET / "gate1"
GATE2 = PACKET / "gate2"
PINS = PACKET / "pins"
W2_PATH = GATE2 / "method_7e77c57f" / "build_recon_t4893u.py"
STAGE_B_SLICE = GATE2 / "stage_b_w7w8" / "RECON_MATRIX.csv"
PBP_PATH = Path("/workspace/data/raw/nfl/pbp/t4696u_s1_restage/play_by_play_2017.parquet")

PBP_SHA256 = "84eacd963c1fdd45965f6222c62e9329a7f3412f029d92c1ac5e34a1bb4d3710"
GAMES_SHA256 = "4fe1cdd7f2eb616103ee6107e6a5cb0d5280f8006be420b606af0995351abef8"
OUTCOMES_SHA256 = "50bda875daa8bf1aadd56dd0a3bc19f1bb52dafe42b6a9c921a5816c7d7dc081"
BUILDER_SHA256 = "7e77c57f3cc7c1b00527309cdcb556a3f4af8e50b0112bbaedc08ca1049fec64"
SEALED_T2 = {
    "2017_07_TB_BUF",
    "2017_07_DAL_SF",
    "2017_07_CIN_PIT",
    "2017_07_SEA_NYG",
    "2017_08_HOU_SEA",
    "2017_08_PIT_DET",
    "2017_09_ARI_SF",
    "2017_09_BAL_TEN",
    "2017_09_CIN_JAX",
    "2017_09_LA_NYG",
    "2017_09_DET_GB",
    "2017_10_CLE_DET",
    "2017_10_GB_CHI",
    "2017_10_LAC_JAX",
    "2017_10_MIN_WAS",
    "2017_10_NE_DEN",
    "2017_10_PIT_IND",
    "2017_11_BAL_GB",
    "2017_11_KC_NYG",
    "2017_11_NE_OAK",
    "2017_11_PHI_DAL",
    "2017_12_CAR_NYJ",
    "2017_12_SEA_SF",
    "2017_12_TEN_IND",
}
TOL_INDEX = 1e-6
TOL_EPA = 1e-9
TOL_REST = 1e-9  # existing rest_ bar; do not loosen
# Remaining numeric 5g rates have no sealed slack — any difference fails.
CONTRACT_27 = (
    "game_id",
    "home_team",
    "away_team",
    "matchup_season",
    "matchup_week",
    "rest_days_home",
    "rest_days_away",
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
)
TEXT_FIELDS = {
    "game_id",
    "home_team",
    "away_team",
    "matchup_season",
    "matchup_week",
}
INDEX_FIELDS = {
    "offense_index_home",
    "offense_index_away",
    "defense_index_home",
    "defense_index_away",
}
EPA_FIELDS = {
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
}
REST_FIELDS = {"rest_days_home", "rest_days_away"}
# Previously unasserted: pass-rate, pressure, RZ, matchup_diff_def_epa_allowed_5g.
EXACT_NUMERIC_FIELDS = (
    set(CONTRACT_27) - TEXT_FIELDS - INDEX_FIELDS - EPA_FIELDS - REST_FIELDS
)
PBP_COLS = [
    "game_id",
    "season",
    "week",
    "season_type",
    "posteam",
    "defteam",
    "play_type",
    "epa",
    "success",
    "sack",
    "qb_hit",
    "yardline_100",
    "touchdown",
    "down",
    "first_down",
    "home_team",
    "away_team",
]


class RebuildRefuse(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_w2():
    spec = importlib.util.spec_from_file_location("w2_recon_t4893u", W2_PATH)
    if spec is None or spec.loader is None:
        raise RebuildRefuse(f"cannot load builder at {W2_PATH}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _finite(value) -> bool:
    return value is not None and isinstance(value, (int, float)) and math.isfinite(
        float(value)
    )


def _fmt(value: float, digits: int = 8) -> str:
    return f"{float(value):.{digits}f}"


def _window_game_ids(t1, team: str, rating_week: int) -> list[str]:
    hit = t1[(t1["team"] == team) & (t1["week"] <= rating_week)]
    ids: list[str] = []
    for raw in hit["source_game_ids"].tolist():
        ids.extend(str(raw).split("|"))
    return sorted({i for i in ids if i and i != "nan"})


def parse_utc(raw: str) -> datetime:
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    dt = datetime.fromisoformat(raw)
    if dt.tzinfo is None:
        raise RebuildRefuse(f"naive timestamp rejected: {raw!r}")
    return dt.astimezone(timezone.utc)


def load_2017_games() -> list[dict]:
    path = PINS / "games_4fe1cdd7.csv"
    if sha256_file(path) != GAMES_SHA256:
        raise RebuildRefuse("games pin drifted")
    rows = []
    with path.open(newline="") as handle:
        for row in csv.DictReader(handle):
            if int(row["season"]) != 2017:
                continue
            if int(row["week"]) > 17:
                continue
            rows.append(
                {
                    "season": 2017,
                    "week": int(row["week"]),
                    "game_id": row["game_id"],
                    "home": row["home"],
                    "away": row["away"],
                    "kickoff_utc": row["kickoff_utc"],
                }
            )
    return rows


def load_completed_50bda875(games: list[dict]) -> list[dict]:
    path = PINS / "outcomes_2013_2022_score_only.csv"
    if sha256_file(path) != OUTCOMES_SHA256:
        raise RebuildRefuse("outcomes pin drifted")
    scores = {}
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        banned = {
            c
            for c in (reader.fieldnames or [])
            if c.startswith(("trailing_", "packaged_"))
            or "epa" in c.lower()
            or c.endswith("_err")
        }
        if banned:
            raise RebuildRefuse(f"outcomes banned columns {sorted(banned)}")
        for row in reader:
            if int(row["season"]) != 2017:
                continue
            scores[(int(row["week"]), row["home"], row["away"])] = (
                float(row["home_score"]),
                float(row["away_score"]),
            )
    completed = []
    for row in games:
        key = (row["week"], row["home"], row["away"])
        if key not in scores:
            continue
        hs, aws = scores[key]
        completed.append({**row, "home_score": hs, "away_score": aws})
    return completed


def record_asof(completed: list[dict], team: str, cutoff: datetime) -> tuple[str, int]:
    wins = losses = n = 0
    for game in completed:
        if parse_utc(game["kickoff_utc"]) >= cutoff:
            continue
        if team not in (game["home"], game["away"]):
            continue
        n += 1
        if game["home_score"] == game["away_score"]:
            continue
        won = (team == game["home"] and game["home_score"] > game["away_score"]) or (
            team == game["away"] and game["away_score"] > game["home_score"]
        )
        if won:
            wins += 1
        else:
            losses += 1
    return f"{wins}-{losses}", n


def verify_pbp() -> dict:
    if not PBP_PATH.is_file():
        raise RebuildRefuse(f"PBP missing at {PBP_PATH}")
    digest = sha256_file(PBP_PATH)
    if digest != PBP_SHA256:
        raise RebuildRefuse(f"PBP sha256 {digest} != {PBP_SHA256} — STOP")
    return {
        "path": str(PBP_PATH),
        "sha256": digest,
        "sha8": "84eacd96",
        "bytes": PBP_PATH.stat().st_size,
        "verified": True,
        "fetched": False,
        "transfer": "uploads/t5044u_pbp_2017_84eacd96.parquet.gz gunzip owned",
        "receipt_tip": "cce2414a",
        "clear_tip": "12763c08",
    }


def _as_float(raw: object) -> float | None:
    if raw is None or raw == "":
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def compare_cell_maps(
    rebuilt: dict[tuple[str, str], dict],
    prior: dict[tuple[str, str], dict],
) -> dict:
    """Full-field W7–W8 compare. All 27 contract fields are asserted.

    Contract-bound slack only:
      index |Δ| < 1e-6; listed 5g EPA/success |Δ| < 1e-9; rest_* |Δ| < 1e-9.
    Any other numeric difference (pass-rate, pressure, RZ,
    matchup_diff_def_epa_allowed_5g) is unauthorized and fails.
    Text identity fields must match exactly. Do not loosen.
    """
    fails: list[dict] = []
    counts = {
        "index": 0,
        "epa": 0,
        "rest": 0,
        "exact_numeric": 0,
        "text": 0,
        "missing_status": 0,
    }
    max_delta = {
        "index": 0.0,
        "epa": 0.0,
        "rest": 0.0,
        "exact_numeric": 0.0,
    }
    asserted = set()

    if set(rebuilt) != set(prior):
        fails.append(
            {
                "reason": "keyset",
                "n_rebuilt": len(rebuilt),
                "n_prior": len(prior),
                "only_rebuilt": sorted(set(rebuilt) - set(prior))[:8],
                "only_prior": sorted(set(prior) - set(rebuilt))[:8],
            }
        )

    games = {gid for gid, _ in prior} | {gid for gid, _ in rebuilt}
    for gid in sorted(games):
        have = {field for g, field in rebuilt if g == gid}
        missing = [field for field in CONTRACT_27 if field not in have]
        extra = sorted(have - set(CONTRACT_27))
        if missing:
            fails.append({"reason": "missing_fields", "game_id": gid, "fields": missing})
        if extra:
            fails.append({"reason": "unknown_fields", "game_id": gid, "fields": extra})

    for key in sorted(set(rebuilt) & set(prior)):
        gid, field = key
        asserted.add(field)
        new = rebuilt[key]
        old = prior[key]
        if new.get("status") != old.get("status"):
            fails.append(
                {
                    "key": list(key),
                    "reason": "status",
                    "new": new.get("status"),
                    "old": old.get("status"),
                }
            )
            continue
        if new.get("status") == "MISSING_RECORD":
            counts["missing_status"] += 1
            continue
        if field not in CONTRACT_27:
            fails.append({"key": list(key), "reason": "unknown_field"})
            continue
        if field in TEXT_FIELDS:
            counts["text"] += 1
            if str(new.get("reconstructed_value", "")) != str(
                old.get("reconstructed_value", "")
            ):
                fails.append({"key": list(key), "reason": "text"})
            continue
        nv = _as_float(new.get("reconstructed_value"))
        ov = _as_float(old.get("reconstructed_value"))
        if nv is None or ov is None:
            if new.get("reconstructed_value") != old.get("reconstructed_value"):
                fails.append({"key": list(key), "reason": "value_text"})
            continue
        delta = abs(nv - ov)
        if field in INDEX_FIELDS:
            counts["index"] += 1
            max_delta["index"] = max(max_delta["index"], delta)
            if delta >= TOL_INDEX:
                fails.append({"key": list(key), "reason": "index", "delta": delta})
        elif field in EPA_FIELDS:
            counts["epa"] += 1
            max_delta["epa"] = max(max_delta["epa"], delta)
            if delta >= TOL_EPA:
                fails.append({"key": list(key), "reason": "epa", "delta": delta})
        elif field in REST_FIELDS:
            counts["rest"] += 1
            max_delta["rest"] = max(max_delta["rest"], delta)
            if delta >= TOL_REST:
                fails.append({"key": list(key), "reason": "rest", "delta": delta})
        elif field in EXACT_NUMERIC_FIELDS:
            counts["exact_numeric"] += 1
            max_delta["exact_numeric"] = max(max_delta["exact_numeric"], delta)
            if delta != 0.0 or str(new.get("reconstructed_value")) != str(
                old.get("reconstructed_value")
            ):
                fails.append(
                    {
                        "key": list(key),
                        "reason": "exact_numeric",
                        "field": field,
                        "delta": delta,
                    }
                )
        else:
            fails.append({"key": list(key), "reason": "unclassified_field"})

    unasserted = [field for field in CONTRACT_27 if field not in asserted]
    if unasserted and not any(f.get("reason") == "keyset" for f in fails):
        fails.append({"reason": "fields_not_compared", "fields": unasserted})

    return {
        "n_cells": len(rebuilt),
        "n_index_compared": counts["index"],
        "n_epa_compared": counts["epa"],
        "n_rest_compared": counts["rest"],
        "n_exact_numeric_compared": counts["exact_numeric"],
        "n_text_compared": counts["text"],
        "max_abs_delta_index": max_delta["index"],
        "max_abs_delta_epa_success": max_delta["epa"],
        "max_abs_delta_rest": max_delta["rest"],
        "max_abs_delta_exact_numeric": max_delta["exact_numeric"],
        "asserted_fields": list(CONTRACT_27),
        "exact_numeric_fields": sorted(EXACT_NUMERIC_FIELDS),
        "n_fails": len(fails),
        "fails": fails,
        "pass": not fails,
        "tolerances": {
            "index": TOL_INDEX,
            "epa_success": TOL_EPA,
            "rest": TOL_REST,
            "pass_rate_pressure_rz_def_epa_diff": 0.0,
        },
    }


def compare_w7w8(matrix: list[dict]) -> dict:
    if not STAGE_B_SLICE.is_file():
        raise RebuildRefuse("Stage B W7–W8 slice missing")
    prior = {}
    with STAGE_B_SLICE.open() as handle:
        for row in csv.DictReader(handle):
            prior[(row["game_id"], row["field"])] = row
    rebuilt = {
        (row["game_id"], row["field"]): row
        for row in matrix
        if int(row["week"]) in (7, 8)
    }
    result = compare_cell_maps(rebuilt, prior)
    if not result["pass"]:
        raise RebuildRefuse(
            "W7–W8 full-field parity vs Stage B failed: "
            + json.dumps(result["fails"][:12], default=str)
        )
    return result


def main() -> int:
    if sha256_file(W2_PATH) != BUILDER_SHA256:
        raise RebuildRefuse("builder 7e77c57f drifted")
    w2 = _load_w2()
    selfcheck = w2.synthetic_t1_selfcheck()
    pbp_receipt = verify_pbp()
    ident = json.loads((GATE1 / "IDENTITY_MANIFEST.json").read_text())
    if ident["n"] != 165:
        raise RebuildRefuse(f"identity n={ident['n']} != 165")
    targets = ident["games"]
    games = load_2017_games()
    completed = load_completed_50bda875(games)
    kickoff_by_gid = {row["game_id"]: row["kickoff_utc"] for row in games}

    # week gaps W1–W16 vs next week
    bounds = {}
    for week in range(1, 18):
        rows = [r for r in games if r["week"] == week]
        if not rows:
            raise RebuildRefuse(f"missing 2017 W{week} in games pin")
        kicks = [parse_utc(r["kickoff_utc"]) for r in rows]
        bounds[week] = (min(kicks), max(kicks))
    for week in range(1, 17):
        if not (bounds[week][1] < bounds[week + 1][0]):
            raise RebuildRefuse(
                f"as-of fail: latest W{week} not < earliest W{week+1}"
            )

    pbp = pd.read_parquet(PBP_PATH, columns=PBP_COLS)
    seasons = [int(x) for x in pbp["season"].dropna().astype(int).unique().tolist()]
    if seasons != [2017]:
        raise RebuildRefuse(f"PBP seasons {seasons} != [2017]")

    prior_ids = {r["game_id"] for r in games if r["week"] <= 16}
    plays = pbp[
        (pbp["season"] == 2017)
        & (pbp["season_type"] == "REG")
        & (pbp["week"].isin(list(range(1, 17))))
        & pbp["week"].notna()
        & pbp["posteam"].notna()
        & pbp["play_type"].isin(["pass", "run"])
        & pbp["game_id"].isin(prior_ids)
    ].copy()
    if plays.empty:
        raise RebuildRefuse("no 2017 W1–W16 REG pass/run plays")
    leaked = []
    consumed = sorted(plays["game_id"].dropna().unique().tolist())
    for gid in consumed:
        if gid not in kickoff_by_gid:
            leaked.append({"game_id": gid, "reason": "not in games.csv 2017 W1–W16"})
        if "_17_" in gid:
            leaked.append({"game_id": gid, "reason": "W17 game in T1 consume set"})
    if leaked:
        raise RebuildRefuse(f"leakage: {leaked[:5]}")

    t1 = w2.t1_from_plays(plays)
    t2 = w2.rolling_5g(t1)

    matrix: list[dict] = []
    status_counts: Counter[str] = Counter()
    complete: list[str] = []
    partial: list[dict] = []
    unexpected: list[dict] = []
    t2_misses: list[dict] = []

    def add_row(gid, week, home, away, kick, rating_week, field, status, **kw):
        src = kw.get("source_sha256", "")
        matrix.append(
            {
                "game_id": gid,
                "season": 2017,
                "week": week,
                "home_team": home,
                "away_team": away,
                "field": field,
                "status": status,
                "reconstructed_value": kw.get("value", ""),
                "source_path": kw.get("source_path", ""),
                "source_sha256": src,
                "source_sha8": src[:8] if src else "",
                "pregame_cutoff_utc": kick,
                "rating_week": str(rating_week),
                "derivation_lineage": kw.get("lineage", ""),
                "availability_evidence": kw.get("evidence", ""),
                "exclusion_reason": kw.get("exclusion_reason", ""),
                "notes": kw.get("notes", ""),
            }
        )
        status_counts[status] += 1

    for rec in targets:
        gid = rec["game_id"]
        home = rec["home_team"]
        away = rec["away_team"]
        kick = rec["kickoff_utc"]
        week = int(rec["week"])
        rating_week = int(rec["rating_week_contiguous"])
        rest_et = rec["rest_days_et"]
        cutoff = parse_utc(kick)
        rec_h, n_h = record_asof(completed, home, cutoff)
        rec_a, n_a = record_asof(completed, away, cutoff)
        if n_h < 1 or n_a < 1:
            unexpected.append(
                {
                    "game_id": gid,
                    "reason": "zero completed as-of (not preregistered in W7–W17)",
                    "n_h": n_h,
                    "n_a": n_a,
                }
            )
            continue

        h = w2.lookup_t2(t2, home, rating_week)
        a = w2.lookup_t2(t2, away, rating_week)
        if h is None:
            t2_misses.append(
                {
                    "game_id": gid,
                    "side": "home",
                    "team": home,
                    "rating_week": rating_week,
                    "reason": "no T2 row at exact rating_week; no last-played fill",
                }
            )
        if a is None:
            t2_misses.append(
                {
                    "game_id": gid,
                    "side": "away",
                    "team": away,
                    "rating_week": rating_week,
                    "reason": "no T2 row at exact rating_week; no last-played fill",
                }
            )

        for team, side_row in ((home, h), (away, a)):
            for cgid in _window_game_ids(t1, team, rating_week):
                ck = kickoff_by_gid.get(cgid)
                if ck is None or parse_utc(ck) >= cutoff:
                    raise RebuildRefuse(
                        f"per-target leakage {gid}: consumed {cgid} kickoff={ck}"
                    )
            if side_row is not None:
                for cgid in str(side_row.get("source_game_ids", "")).split("|"):
                    if not cgid or cgid == "nan":
                        continue
                    ck = kickoff_by_gid.get(cgid)
                    if ck is None or parse_utc(ck) >= cutoff:
                        raise RebuildRefuse(
                            f"per-target leakage {gid}: T2 {cgid} kickoff={ck}"
                        )

        t1_lineage = (
            "T1=nfl_dp_team_situational_weekly port @5fc97157 from owned PBP 84eacd96. "
            "T2=rolling_5g ROWS 4 PRECEDING AND CURRENT (7e77c57f). "
            "T3=exact rating_week=week-1; no last-played. T4 contract diffs. "
            "T5 from 50bda875 W-L (not 1ee90fac). RETRO_FIT / DEV_RESEARCH / A1."
        )
        for field, value in {
            "game_id": gid,
            "home_team": home,
            "away_team": away,
            "matchup_season": "2017",
            "matchup_week": str(week),
        }.items():
            add_row(
                gid,
                week,
                home,
                away,
                kick,
                rating_week,
                field,
                "DERIVED_PREGAME",
                source_path="pins/games_4fe1cdd7.csv",
                source_sha256=GAMES_SHA256,
                lineage="Gate 1 identity seal",
                evidence=f"sealed 165; game_id={gid}",
                value=value,
            )
        for side in ("home", "away"):
            add_row(
                gid,
                week,
                home,
                away,
                kick,
                rating_week,
                f"rest_days_{side}",
                "DERIVED_PREGAME",
                source_path="155d3ca0 ET DOW",
                source_sha256=w2.NFL_DATA_SHA256,
                lineage="ET DOW heuristic (Thu=4, Mon=6, else=7). BIND_PACKET_ONLY.",
                evidence=f"kickoff_utc={kick} rest_et={rest_et}",
                value=str(rest_et),
            )
        for side, rec_wl, n_played in (
            ("home", rec_h, n_h),
            ("away", rec_a, n_a),
        ):
            off_i, def_i = w2.team_strength_from_record(rec_wl)
            for field, val, lin in (
                (
                    f"offense_index_{side}",
                    off_i,
                    "T5: off=clamp(0.90+0.22*wp, 0.82, 1.18) same-season as-of",
                ),
                (
                    f"defense_index_{side}",
                    def_i,
                    "T5: def=clamp(0.92+0.20*wp, 0.82, 1.20) same-season as-of",
                ),
            ):
                add_row(
                    gid,
                    week,
                    home,
                    away,
                    kick,
                    rating_week,
                    field,
                    "DERIVED_PREGAME",
                    source_path="pins/outcomes_2013_2022_score_only.csv",
                    source_sha256=OUTCOMES_SHA256,
                    lineage=lin,
                    evidence=f"record_asof={rec_wl} n={n_played} cutoff={kick}",
                    notes="50bda875 after independent Stage B W7–W8 parity; not 1ee90fac",
                    value=_fmt(val, 6),
                )

        def _side_metrics(row):
            if row is None:
                return {k: None for k in ("off", "def", "pr", "so", "sd", "pg", "pa", "rz")}
            return {
                "off": float(row["epa_per_play_offense_5g"]),
                "def": float(row["epa_per_play_defense_allowed_5g"]),
                "pr": float(row["pass_rate_5g"]),
                "so": float(row["success_rate_offense_5g"]),
                "sd": float(row["success_rate_defense_allowed_5g"]),
                "pg": float(row["pressure_rate_generated_5g"]),
                "pa": float(row["pressure_rate_allowed_5g"]),
                "rz": float(row["red_zone_td_rate_5g"]),
            }

        hm = _side_metrics(h)
        am = _side_metrics(a)

        def _diff(h_v, a_v, how: str):
            if h_v is None or a_v is None:
                return None
            return h_v - a_v if how == "h-a" else a_v - h_v

        if None in (hm["so"], am["so"], hm["sd"], am["sd"]):
            diff_sr = None
        else:
            diff_sr = ((hm["so"] - am["so"]) + (am["sd"] - hm["sd"])) / 2.0
        side_values = {
            "home_off_epa_5g": hm["off"],
            "away_off_epa_5g": am["off"],
            "home_def_epa_allowed_5g": hm["def"],
            "away_def_epa_allowed_5g": am["def"],
            "home_pass_rate_5g": hm["pr"],
            "away_pass_rate_5g": am["pr"],
            "home_success_offense_5g": hm["so"],
            "away_success_offense_5g": am["so"],
            "home_success_defense_allowed_5g": hm["sd"],
            "away_success_defense_allowed_5g": am["sd"],
        }
        diff_values = {
            "matchup_diff_off_epa_5g": _diff(hm["off"], am["off"], "h-a"),
            "matchup_diff_def_epa_allowed_5g": _diff(hm["def"], am["def"], "a-h"),
            "matchup_diff_success_rate_5g": diff_sr,
            "matchup_diff_pressure_generated_5g": _diff(hm["pg"], am["pg"], "h-a"),
            "matchup_diff_pressure_allowed_5g": _diff(hm["pa"], am["pa"], "a-h"),
            "matchup_diff_red_zone_td_rate_5g": _diff(hm["rz"], am["rz"], "h-a"),
        }
        for field, val in {**side_values, **diff_values}.items():
            if not _finite(val):
                add_row(
                    gid,
                    week,
                    home,
                    away,
                    kick,
                    rating_week,
                    field,
                    "MISSING_RECORD",
                    source_path=str(PBP_PATH),
                    source_sha256=PBP_SHA256,
                    lineage=t1_lineage,
                    evidence=f"T2 rating_week={rating_week}; fail-closed",
                    notes="no default; no last-played-week T2 fill",
                    exclusion_reason="T2 row absent at exact rating_week or non-finite metric",
                )
                continue
            add_row(
                gid,
                week,
                home,
                away,
                kick,
                rating_week,
                field,
                "DERIVED_PREGAME",
                source_path=str(PBP_PATH),
                source_sha256=PBP_SHA256,
                lineage=t1_lineage,
                evidence=f"T2 rating_week={rating_week} pbp=84eacd96 cutoff={kick}",
                notes="Same T1–T4 as 7e77c57f. RETRO_FIT / DEV_RESEARCH / A1.",
                value=_fmt(val, 8),
            )

        derived_here = sum(
            1
            for row in matrix
            if row["game_id"] == gid and row["status"] == "DERIVED_PREGAME"
        )
        missing_here = sum(
            1
            for row in matrix
            if row["game_id"] == gid and row["status"] == "MISSING_RECORD"
        )
        if derived_here == 27 and missing_here == 0:
            complete.append(gid)
        elif gid in SEALED_T2:
            partial.append(
                {
                    "game_id": gid,
                    "week": week,
                    "derived": derived_here,
                    "missing": missing_here,
                    "reason": "T2 bye-return exact rating_week miss",
                    "retained": True,
                    "selection_excluded": False,
                }
            )
        else:
            unexpected.append(
                {
                    "game_id": gid,
                    "week": week,
                    "derived": derived_here,
                    "missing": missing_here,
                    "reason": "missing coverage beyond preregistered T2 24",
                }
            )

    if unexpected:
        raise RebuildRefuse(
            "unexpected missing coverage — escalate, do not score: "
            + json.dumps(unexpected)[:1200]
        )
    if len(matrix) != 165 * 27:
        raise RebuildRefuse(f"matrix cells {len(matrix)} != 165*27")
    if set(complete) | {p["game_id"] for p in partial} != {t["game_id"] for t in targets}:
        raise RebuildRefuse("completeness partition != 165 identities")
    if {p["game_id"] for p in partial} != SEALED_T2:
        raise RebuildRefuse("partial set != sealed 24 T2 risks")

    w7w8_parity = compare_w7w8(matrix)

    fieldnames = [
        "game_id",
        "season",
        "week",
        "home_team",
        "away_team",
        "field",
        "status",
        "reconstructed_value",
        "source_path",
        "source_sha256",
        "source_sha8",
        "pregame_cutoff_utc",
        "rating_week",
        "derivation_lineage",
        "availability_evidence",
        "exclusion_reason",
        "notes",
    ]
    out_csv = GATE2 / "RECON_MATRIX_W7W17.csv"
    with out_csv.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(matrix)
    matrix_sha = sha256_file(out_csv)

    by_week = defaultdict(lambda: {"complete": 0, "partial": 0})
    for gid in complete:
        week = int(gid[5:7])
        by_week[week]["complete"] += 1
    for item in partial:
        by_week[item["week"]]["partial"] += 1

    coverage = {
        "ticket": "t5044u",
        "phase": 1,
        "labels": ["RETRO_FIT", "DEV_RESEARCH", "A1"],
        "cert": 0,
        "n_identity": 165,
        "n_cells": len(matrix),
        "status_counts": dict(status_counts),
        "n_complete_27_of_27": len(complete),
        "n_partial_t2": len(partial),
        "n_outcome_excluded": 0,
        "n_unexpected_missing": 0,
        "n_filled": 0,
        "n_replaced": 0,
        "complete_game_ids": complete,
        "partial": partial,
        "t2_exact_week_misses": t2_misses,
        "by_week": {str(k): v for k, v in sorted(by_week.items())},
        "matrix_path": "gate2/RECON_MATRIX_W7W17.csv",
        "matrix_sha256": matrix_sha,
        "pbp": pbp_receipt,
        "builder_sha256": BUILDER_SHA256,
        "t1_selfcheck": selfcheck,
        "w7w8_parity_vs_stage_b": w7w8_parity,
        "consumed_pbp": {
            "n_plays": int(len(plays)),
            "n_games": len(consumed),
            "weeks": sorted(int(x) for x in plays["week"].dropna().unique().tolist()),
        },
        "if_invoked": False,
        "q2s_emitted": False,
        "look_run": False,
        "quarantined_1ee90fac_scored": False,
        "new_index_formula": False,
    }
    (GATE2 / "PBP_VERIFY_RECEIPT.json").write_text(
        json.dumps(pbp_receipt, indent=2, sort_keys=True) + "\n"
    )
    (GATE2 / "COVERAGE_W7W17.json").write_text(
        json.dumps(coverage, indent=2, sort_keys=True) + "\n"
    )
    (out_csv.with_suffix(".csv.sha256")).write_text(
        f"{matrix_sha}  RECON_MATRIX_W7W17.csv\n"
    )

    # refresh RECON_STATUS / PBP_STATUS
    status = {
        "ticket": "t5044u",
        "owner_clear_tip": "12763c08",
        "phase1_receipt_tip": "cce2414a",
        "phase": 1,
        "labels": ["RETRO_FIT", "DEV_RESEARCH", "A1"],
        "cert": 0,
        "if_invoked": False,
        "q2s_emitted": False,
        "look_run": False,
        "stop_for_alex_pre_if": True,
        "pbp": pbp_receipt,
        "contract": "b41f4b43",
        "builder": "7e77c57f",
        "new_index_formula": False,
        "quarantined_1ee90fac_scored": False,
        "completeness": {
            "n_identity": 165,
            "n_complete_27_of_27": len(complete),
            "n_partial_preregistered_t2": 24,
            "n_partial_recon_available": len(partial),
            "n_recon_not_attempted": 0,
            "n_outcome_excluded": 0,
            "n_unexpected_missing": 0,
            "complete_game_ids": complete,
            "partial_available": partial,
        },
        "w7w8_parity_vs_stage_b": w7w8_parity,
        "matrix_sha256": matrix_sha,
    }
    (GATE2 / "PBP_STATUS.json").write_text(
        json.dumps(pbp_receipt, indent=2, sort_keys=True) + "\n"
    )
    (GATE2 / "RECON_STATUS.json").write_text(
        json.dumps(status, indent=2, sort_keys=True) + "\n"
    )
    print(
        json.dumps(
            {
                "ok": True,
                "pbp_verified": True,
                "n_complete": len(complete),
                "n_partial": len(partial),
                "matrix_sha256": matrix_sha,
                "w7w8_parity": w7w8_parity["pass"],
                "if_invoked": False,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RebuildRefuse as exc:
        print(f"REBUILD_REFUSE: {exc}", file=sys.stderr)
        raise SystemExit(2)
