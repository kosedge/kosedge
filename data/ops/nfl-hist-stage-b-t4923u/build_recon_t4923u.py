#!/usr/bin/env python3
"""t4923u Stage B rebuild — AFTER Step 0 selection seal.

Reuses T1–T4 transforms from sealed W2 builder 7e77c57f
(data/ops/nfl-hist-bt-stage1b-w2-t4893u/build_recon_t4893u.py).
Season hardcode generalized only as far as:
  2017 REG W2 (parity 14) + W7–W8, and 2016 REG W8.

Does not invent new pressure/RZ/T4 signs/rest_days/T5 formulas.
Does not fit, score, tune, call Odds, or touch 2024–25.
Labels: RETRO_FIT / DEV_RESEARCH. CERT=0. Stage C not authorized.
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

PACKET = Path(__file__).resolve().parent
REPO = PACKET.parents[2]
W2_BUILDER = (
    REPO / "data/ops/nfl-hist-bt-stage1b-w2-t4893u" / "build_recon_t4893u.py"
)
SEAL_MOD = PACKET / "seal_selection_t4923u.py"
SEAL_JSON = PACKET / "SELECTION_HASH_SEAL.json"
W2_RECON = REPO / "data/ops/nfl-hist-bt-stage1b-w2-t4893u" / "RECON_MATRIX.csv"

PBP_DIR = Path("/workspace/data/raw/nfl/pbp/t4696u_s1_restage")
PBP_PINS = {
    2016: "95eba04e2145e3c1c8ca502f2a3a76cfb0a5990680c3fb480f02a74a45f54a3b",
    2017: "84eacd963c1fdd45965f6222c62e9329a7f3412f029d92c1ac5e34a1bb4d3710",
}
# Identity join only (2016 nflverse modern codes → games.csv 4fe1cdd7 tokens).
# Same class as W2 PBP_TO_CANON LA/WAS/LV. Not a statistical fill.
PBP_IDENTITY_EXTRA = {"LAC": "SD"}

INDEX_FIELDS = (
    "offense_index_home",
    "offense_index_away",
    "defense_index_home",
    "defense_index_away",
)
EPA_SUCCESS_FIELDS = (
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
)
TOL_INDEX = 1e-6
TOL_EPA = 1e-9

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
    "qb_dropback",
]


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot load {name} at {path}")
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


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_seal(sealmod) -> dict:
    if not SEAL_JSON.is_file():
        raise SystemExit("SELECTION_HASH_SEAL.json missing — Step 0 first")
    existing = json.loads(SEAL_JSON.read_text(encoding="utf-8"))
    _, all_games = sealmod.load_games()
    oos = sealmod.load_oos_2016_2017()
    completed = sealmod.build_completed(all_games, oos)
    recomputed = {}
    for slc in sealmod.SLICES:
        blk = sealmod.eligible_for_slice(all_games, completed, slc)
        recomputed[slc["key"]] = blk
        want = existing["slices"][slc["key"]]
        if blk["game_ids_sorted"] != want["game_ids_sorted"]:
            raise SystemExit(f"seal drift {slc['key']} eligible ids")
        if blk["selection_hash"] != want["selection_hash"]:
            raise SystemExit(f"seal drift {slc['key']} hash")
        if blk["excluded_game_ids"] != want["excluded_game_ids"]:
            raise SystemExit(f"seal drift {slc['key']} missing ids")
    if existing["tolerances_preregistered"]["index_abs_delta"] != TOL_INDEX:
        raise SystemExit("index tolerance drift vs sealed pre-register")
    if existing["tolerances_preregistered"]["epa_success_5g_abs_delta"] != TOL_EPA:
        raise SystemExit("epa/success tolerance drift vs sealed pre-register")
    return existing, all_games, recomputed


def load_season_pbp(season: int):
    import pandas as pd

    path = PBP_DIR / f"play_by_play_{season}.parquet"
    if not path.is_file():
        raise SystemExit(f"PBP missing at {path}")
    digest = sha256_file(path)
    pin = PBP_PINS[season]
    if digest != pin:
        raise SystemExit(f"PBP {season} sha256 {digest} != pin {pin}")
    pbp = pd.read_parquet(path, columns=PBP_COLS)
    seasons = [int(x) for x in pbp["season"].dropna().astype(int).unique().tolist()]
    if seasons != [season]:
        raise SystemExit(f"PBP season != {season} only: {seasons}")
    return path, digest, pbp


def apply_identity(plays, season: int):
    """Identity remap only. 2016 extra LAC→SD for games.csv SD token."""
    extra = PBP_IDENTITY_EXTRA if season == 2016 else {}
    if not extra:
        return plays, extra
    out = plays.copy()
    for col in ("posteam", "defteam"):
        out[col] = out[col].replace(extra)
    return out, extra


def main() -> None:
    w2 = _load_module("w2_recon_t4893u", W2_BUILDER)
    sealmod = _load_module("seal_selection_t4923u", SEAL_MOD)
    existing, all_games, by_slice = verify_seal(sealmod)
    print(
        json.dumps(
            {
                "phase": "SEAL_VERIFIED",
                "selection_hash_eligible_combined": existing[
                    "selection_hash_eligible_combined"
                ],
                "n_eligible": existing["n_eligible"],
            },
            indent=2,
        )
    )

    source_rows = []
    exclusions = []
    for slc in sealmod.SLICES:
        source_rows.extend(by_slice[slc["key"]]["source_rows"])
        exclusions.extend(by_slice[slc["key"]]["exclusions"])
    if len(source_rows) != 55:
        raise SystemExit(f"eligible N target 55, got {len(source_rows)}")

    selfcheck = w2.synthetic_t1_selfcheck()

    t1_by_season = {}
    t2_by_season = {}
    pbp_meta = {}
    consumed_by_season = {}
    identity_applied = {}
    week_gaps = {}

    for season, max_consume_week in ((2016, 7), (2017, 7)):
        path, digest, pbp = load_season_pbp(season)
        pbp_meta[season] = {
            "path": str(path),
            "sha256": digest,
            "bytes": path.stat().st_size,
        }
        kickoff_by_gid = {
            r["game_id"]: r["kickoff_utc"]
            for r in all_games
            if int(r["season"]) == season and int(r["week"]) <= max_consume_week + 1
        }
        prior_ids = {
            r["game_id"]
            for r in all_games
            if int(r["season"]) == season and int(r["week"]) <= max_consume_week
        }
        bounds = {}
        for wk in range(1, max_consume_week + 2):
            rows = [
                r
                for r in all_games
                if int(r["season"]) == season and int(r["week"]) == wk
            ]
            if not rows:
                continue
            kicks = [w2.parse_utc(r["kickoff_utc"]) for r in rows]
            bounds[wk] = (min(kicks), max(kicks))
        for wk in range(1, max_consume_week + 1):
            if wk not in bounds or (wk + 1) not in bounds:
                raise SystemExit(f"missing week bounds {season} W{wk}")
            if not (bounds[wk][1] < bounds[wk + 1][0]):
                raise SystemExit(
                    f"as-of fail {season}: latest W{wk} {bounds[wk][1].isoformat()} "
                    f"not < earliest W{wk+1} {bounds[wk+1][0].isoformat()}"
                )
        week_gaps[season] = {
            str(wk): True for wk in range(1, max_consume_week + 1)
        }

        plays = pbp[
            (pbp["season"] == season)
            & (pbp["season_type"] == "REG")
            & (pbp["week"].isin(list(range(1, max_consume_week + 1))))
            & pbp["week"].notna()
            & pbp["posteam"].notna()
            & pbp["play_type"].isin(["pass", "run"])
            & pbp["game_id"].isin(prior_ids)
        ].copy()
        plays, extra = apply_identity(plays, season)
        identity_applied[season] = extra
        if plays.empty:
            raise SystemExit(f"no {season} W1–W{max_consume_week} REG pass/run plays")

        leaked = []
        consumed = sorted(plays["game_id"].dropna().unique().tolist())
        for gid in consumed:
            if gid not in kickoff_by_gid:
                leaked.append(
                    {
                        "game_id": gid,
                        "reason": f"consumed PBP game_id not in games.csv {season} W1–W{max_consume_week}",
                    }
                )
            if f"_{max_consume_week+1:02d}_" in gid:
                leaked.append(
                    {
                        "game_id": gid,
                        "reason": f"target week {max_consume_week+1} game in T1 consume set",
                    }
                )
        if leaked:
            raise SystemExit(f"leakage test failed {season}: {leaked}")

        t1 = w2.t1_from_plays(plays)
        t2 = w2.rolling_5g(t1)
        t1_by_season[season] = t1
        t2_by_season[season] = t2
        consumed_by_season[season] = {
            "game_ids": consumed,
            "n_plays": int(len(plays)),
            "weeks": sorted(int(x) for x in plays["week"].dropna().unique().tolist()),
            "leaked_rows": leaked,
            "kickoff_by_gid": kickoff_by_gid,
        }

    t1_out_cols = [
        "season",
        "week",
        "team",
        "games_played",
        "offensive_plays",
        "defensive_plays",
        "pass_plays",
        "run_plays",
        "epa_per_play_offense",
        "epa_per_play_defense_allowed",
        "pass_rate",
        "success_rate_offense",
        "success_rate_defense_allowed",
        "pressure_rate_allowed",
        "pressure_rate_generated",
        "red_zone_td_rate",
        "red_zone_plays",
        "red_zone_touchdowns",
        "source_game_ids",
    ]
    for season, t1 in t1_by_season.items():
        t1.to_csv(
            PACKET / f"t1_team_week_{season}_w1w7.csv",
            index=False,
            columns=t1_out_cols,
        )

    games_out = []
    matrix = []
    status_counts: Counter[str] = Counter()
    complete_games = []
    partial_games = []
    t2_misses = []

    def add_row(gid, season, week, home, away, kick, rating_week, field, status, **kw):
        src_sha = kw.get("source_sha256", "")
        matrix.append(
            {
                "game_id": gid,
                "season": season,
                "week": week,
                "home_team": home,
                "away_team": away,
                "field": field,
                "status": status,
                "reconstructed_value": kw.get("value", ""),
                "source_path": kw.get("source_path", ""),
                "source_sha256": src_sha,
                "source_sha8": src_sha[:8] if src_sha else "",
                "pregame_cutoff_utc": kick,
                "rating_week": str(rating_week),
                "derivation_lineage": kw.get("lineage", ""),
                "availability_evidence": kw.get("evidence", ""),
                "exclusion_reason": kw.get("exclusion_reason", ""),
                "notes": kw.get("notes", ""),
            }
        )
        status_counts[status] += 1

    for rec in source_rows:
        gid = rec["game_id"]
        home = rec["home_team"]
        away = rec["away_team"]
        kick = rec["kickoff_utc"]
        season = int(rec["season"])
        week = int(rec["week"])
        rating_week = int(rec["rating_week_contiguous"])
        rest_et = rec["rest_days_et"]
        rest_utc = rec["rest_days_utc_contrast"]
        t1 = t1_by_season[season]
        t2 = t2_by_season[season]
        kickoff_by_gid = consumed_by_season[season]["kickoff_by_gid"]
        pbp_sha = pbp_meta[season]["sha256"]
        pbp_path = pbp_meta[season]["path"]

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
            window_ids = _window_game_ids(t1, team, rating_week)
            for cgid in window_ids:
                ck = kickoff_by_gid.get(cgid)
                if ck is None or w2.parse_utc(ck) >= w2.parse_utc(kick):
                    raise SystemExit(
                        f"per-target leakage {gid}: consumed {cgid} kickoff={ck}"
                    )
            if side_row is not None:
                for cgid in str(side_row.get("source_game_ids", "")).split("|"):
                    if not cgid or cgid == "nan":
                        continue
                    ck = kickoff_by_gid.get(cgid)
                    if ck is None or w2.parse_utc(ck) >= w2.parse_utc(kick):
                        raise SystemExit(
                            f"per-target leakage {gid}: T2-current {cgid} kickoff={ck}"
                        )

        rec_out = dict(rec)
        rec_out["t2_home_present"] = h is not None
        rec_out["t2_away_present"] = a is not None
        rec_out["t2_home_games_in_window"] = (
            int(h["games_in_window_5"]) if h is not None else None
        )
        rec_out["t2_away_games_in_window"] = (
            int(a["games_in_window_5"]) if a is not None else None
        )
        games_out.append(rec_out)

        t1_lineage = (
            "T1=nfl_dp_team_situational_weekly port of ingest.py offense/defense CTEs "
            f"@sha256 {w2.INGEST_SHA256[:8]}… from owned PBP {season} pin {pbp_sha[:8]}. "
            "play_type IN ('pass','run'). "
            "T2=season-partitioned ROWS BETWEEN 4 PRECEDING AND CURRENT ROW "
            "(W2 builder rolling_5g; T1 frames kept per-season so 2016 does not "
            "roll into 2017). "
            "T3 home/away = T2 at rating_week=target_week-1 (cf514078; never "
            "target-week CURRENT ROW). Exact week lookup. No last-played fill. "
            "T4 diffs per contract §4 / ingest matchup SQL. "
            "nflverse EPA/success are retro-scored by a later EP model — "
            "metric-definition look-ahead, not target-week outcome leakage. "
            "RETRO_FIT / DEV_RESEARCH."
        )

        identity = {
            "game_id": gid,
            "home_team": home,
            "away_team": away,
            "matchup_season": str(season),
            "matchup_week": str(week),
        }
        for field, value in identity.items():
            add_row(
                gid,
                season,
                week,
                home,
                away,
                kick,
                rating_week,
                field,
                "DERIVED_PREGAME",
                source_path="data/ops/nfl-t4422u-walkforward-pergame-unblended-2013-2023/games.csv",
                source_sha256=w2.GAMES_SHA256,
                lineage="sample identity from sealed games.csv pin 4fe1cdd7",
                evidence=f"row present season={season} week={week} game_id={gid}",
                notes="canonical game_id from walkforward export; not invented",
                value=value,
            )

        for side in ("home", "away"):
            add_row(
                gid,
                season,
                week,
                home,
                away,
                kick,
                rating_week,
                f"rest_days_{side}",
                "DERIVED_PREGAME",
                source_path="services/model-service/src/services/nfl_offline_if_eval_w8.py:rest_days_from_schedule (ET) @155d3ca0",
                source_sha256=w2.NFL_DATA_SHA256,
                lineage="ET DOW heuristic (Thu=4, Mon=6, else=7). Same as W2.",
                evidence=f"kickoff_utc={kick} rest_et={rest_et} rest_utc_contrast={rest_utc}",
                notes=f"utc_et_dow_mismatch={rest_et != rest_utc}",
                value=str(rest_et),
            )

        for side, team, n_played, rec_wl in (
            ("home", home, rec["completed_same_season_games_home"], rec["record_asof_home"]),
            ("away", away, rec["completed_same_season_games_away"], rec["record_asof_away"]),
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
                    season,
                    week,
                    home,
                    away,
                    kick,
                    rating_week,
                    field,
                    "DERIVED_PREGAME",
                    source_path=(
                        "data/ops/nfl-reopening-packet-20260916/historical-oos/"
                        "historical_oos_games.csv + games.csv kickoff join; "
                        "T5 team_strength_from_record"
                    ),
                    source_sha256=w2.OOS_SHA256,
                    lineage=lin,
                    evidence=(
                        f"record_asof={rec_wl} n={n_played} cutoff={kick}; "
                        f"games.csv entering={rec[f'games_csv_record_entering_{side}']}"
                    ),
                    notes="recomputed as-of; index 1ee90fac PILOT-ONLY gate 83646d78",
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
            if how == "h-a":
                return h_v - a_v
            if how == "a-h":
                return a_v - h_v
            raise SystemExit(f"unknown diff {how}")

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

        def _t2_evidence() -> str:
            parts = [f"T2 rating_week={rating_week}"]
            if h is not None:
                parts.append(
                    f"home_window={int(h['games_in_window_5'])} home_t2_week={int(h['week'])}"
                )
            else:
                parts.append(f"home_t2=MISSING exact week={rating_week}")
            if a is not None:
                parts.append(
                    f"away_window={int(a['games_in_window_5'])} away_t2_week={int(a['week'])}"
                )
            else:
                parts.append(f"away_t2=MISSING exact week={rating_week}")
            parts.append(f"pbp_sha8={pbp_sha[:8]} cutoff={kick}")
            return "; ".join(parts)

        for field, val in {**side_values, **diff_values}.items():
            if not _finite(val):
                add_row(
                    gid,
                    season,
                    week,
                    home,
                    away,
                    kick,
                    rating_week,
                    field,
                    "MISSING_RECORD",
                    source_path=pbp_path,
                    source_sha256=pbp_sha,
                    lineage=t1_lineage,
                    evidence="non-finite or unavailable T1/T2; " + _t2_evidence(),
                    notes="fail-closed; no default; no last-played-week T2 fill",
                    exclusion_reason="T2 row absent at exact rating_week or non-finite metric",
                )
                continue
            add_row(
                gid,
                season,
                week,
                home,
                away,
                kick,
                rating_week,
                field,
                "DERIVED_PREGAME",
                source_path=pbp_path,
                source_sha256=pbp_sha,
                lineage=t1_lineage,
                evidence=_t2_evidence(),
                notes="Same T1–T4 as W2 7e77c57f. RETRO_FIT / DEV_RESEARCH.",
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
            complete_games.append(gid)
        else:
            partial_games.append(
                {
                    "game_id": gid,
                    "season": season,
                    "week": week,
                    "derived": derived_here,
                    "missing": missing_here,
                    "home": home,
                    "away": away,
                    "t2_home": h is not None,
                    "t2_away": a is not None,
                    "rating_week": rating_week,
                }
            )

    fields_per_game = 27
    if len(matrix) != 55 * fields_per_game:
        raise SystemExit(f"matrix cells {len(matrix)} != 55*27")

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
    with (PACKET / "RECON_MATRIX.csv").open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(matrix)

    # --- coverage ---
    by_field = defaultdict(Counter)
    for rec_row in matrix:
        by_field[rec_row["field"]][rec_row["status"]] += 1
    coverage = {
        "n_source": existing["n_source"],
        "n_excluded_missing_retained": existing["n_excluded_missing_retained"],
        "excluded_game_ids": existing["game_ids_missing_retained_sorted"],
        "n_eligible": 55,
        "fields_per_game": fields_per_game,
        "n_cells": len(matrix),
        "status_counts": dict(status_counts),
        "derived_pregame": status_counts["DERIVED_PREGAME"],
        "missing_record": status_counts.get("MISSING_RECORD", 0),
        "pct_fields_present": round(
            100.0 * status_counts["DERIVED_PREGAME"] / len(matrix), 4
        ),
        "complete_eligible_games_27_of_27": sorted(complete_games),
        "n_complete_eligible": len(complete_games),
        "partial_eligible_games": partial_games,
        "n_partial_eligible": len(partial_games),
        "by_slice": {
            k: {
                "n_source": v["n_source"],
                "n_eligible": v["n_eligible"],
                "n_missing_selection": v["n_excluded_missing"],
                "n_complete": sum(
                    1 for g in complete_games if g in v["game_ids_sorted"]
                ),
                "n_partial": sum(
                    1
                    for p in partial_games
                    if p["game_id"] in v["game_ids_sorted"]
                ),
            }
            for k, v in existing["slices"].items()
        },
        "by_field": {k: dict(v) for k, v in sorted(by_field.items())},
        "t2_exact_week_misses": t2_misses,
        "identity_remap_2016": identity_applied.get(2016, {}),
        "epa_retrofit_caveat": (
            "nflverse epa/success are retro-scored by a later-fitted EP model. "
            "Metric-definition look-ahead; not consumption of target-week outcomes. "
            "RETRO_FIT."
        ),
    }
    (PACKET / "COVERAGE.json").write_text(
        json.dumps(coverage, indent=2) + "\n", encoding="utf-8"
    )

    leakage = {
        "rule": (
            "no consumed play/game with kickoff >= target kickoff; "
            "T1 weeks strictly < target week; T1 frames per-season"
        ),
        "by_season": {
            str(season): {
                "consumed_pbp_game_ids": consumed_by_season[season]["game_ids"],
                "n_consumed_games": len(consumed_by_season[season]["game_ids"]),
                "n_consumed_plays": consumed_by_season[season]["n_plays"],
                "consumed_weeks": consumed_by_season[season]["weeks"],
                "leaked_rows": consumed_by_season[season]["leaked_rows"],
                "week_gap_max_wk_lt_min_wk_plus_1": week_gaps[season],
                "pbp_sha256": pbp_meta[season]["sha256"],
            }
            for season in (2016, 2017)
        },
        "play_filter": "play_type IN ('pass','run'); season_type=REG; week IN 1..7 of that season",
        "per_target": "window = team T1 rows with week <= rating_week; all those kickoffs < target",
        "cross_season_t2": "FORBIDDEN — rolling_5g run on per-season T1 only",
        "result": "PASS",
    }
    (PACKET / "LEAKAGE_AUDIT.json").write_text(
        json.dumps(leakage, indent=2) + "\n", encoding="utf-8"
    )

    (PACKET / "EXCLUSIONS.json").write_text(
        json.dumps(
            {
                "rule": existing["exclusion_rule"],
                "n_source": existing["n_source"],
                "n_excluded_missing_retained": existing["n_excluded_missing_retained"],
                "n_eligible": 55,
                "exclusions": exclusions,
                "substituted": False,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    (PACKET / "T1_TRANSFORM.json").write_text(
        json.dumps(
            {
                "contract_t1": "nfl_dp_team_situational_weekly columns cited in b41f4b43 §4",
                "producer": "services/model-service/data_platform_nfl/ingest.py offense/defense CTEs",
                "producer_sha256": w2.INGEST_SHA256,
                "reused_from": "data/ops/nfl-hist-bt-stage1b-w2-t4893u/build_recon_t4893u.py",
                "builder_sha8": "7e77c57f",
                "functions_reused": [
                    "t1_from_plays",
                    "rolling_5g",
                    "lookup_t2",
                    "synthetic_t1_selfcheck",
                    "team_strength_from_record",
                    "rest_days_et",
                ],
                "synthetic_selfcheck": selfcheck,
                "season_generalization": (
                    "PBP path + T1 week filter parameterized to 2016/2017 W1–W7. "
                    "No T1/T4 formula change."
                ),
                "identity_remap_2016_extra": {
                    "LAC": "SD",
                    "class": "identity join only",
                    "rationale": (
                        "2016 games.csv 4fe1cdd7 uses SD; restage PBP 95eba04e uses LAC. "
                        "Same class as W2 LA→LAR / WAS→WSH / LV→OAK."
                    ),
                },
                "epa_retrofit_caveat": coverage["epa_retrofit_caveat"],
                "labels": ["RETRO_FIT", "DEV_RESEARCH"],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    # --- W2 14 parity vs 708513db ---
    if not W2_RECON.is_file():
        raise SystemExit(f"sealed W2 RECON missing at {W2_RECON}")
    w2_digest = sha256_file(W2_RECON)
    if w2_digest != existing["recon_parity_refs"]["w2_content_sha256"]:
        raise SystemExit(
            f"W2 RECON content {w2_digest} != pin 708513db — refuse filename-tip seal"
        )
    sealed_cells = {}
    with W2_RECON.open(newline="") as fh:
        for row in csv.DictReader(fh):
            sealed_cells[(row["game_id"], row["field"])] = row
    rebuilt_w2 = [
        r
        for r in matrix
        if r["season"] == 2017
        and r["week"] == 2
        and r["game_id"] in existing["slices"]["2017_W2_PARITY"]["game_ids_sorted"]
    ]
    compare_fields = list(INDEX_FIELDS) + list(EPA_SUCCESS_FIELDS)
    comparisons = []
    fails = []
    for rec_row in rebuilt_w2:
        field = rec_row["field"]
        if field not in compare_fields:
            continue
        key = (rec_row["game_id"], field)
        sealed = sealed_cells.get(key)
        if sealed is None:
            fails.append({"game_id": rec_row["game_id"], "field": field, "reason": "missing in sealed RECON"})
            continue
        tol = TOL_INDEX if field in INDEX_FIELDS else TOL_EPA
        family = "index" if field in INDEX_FIELDS else "epa_success_5g"
        if rec_row["status"] != sealed["status"]:
            fails.append(
                {
                    "game_id": rec_row["game_id"],
                    "field": field,
                    "reason": f"status {rec_row['status']} != sealed {sealed['status']}",
                }
            )
            continue
        if rec_row["status"] != "DERIVED_PREGAME":
            comparisons.append(
                {
                    "game_id": rec_row["game_id"],
                    "field": field,
                    "family": family,
                    "status": rec_row["status"],
                    "abs_delta": None,
                    "tol": tol,
                    "pass": True,
                }
            )
            continue
        try:
            a = float(rec_row["reconstructed_value"])
            b = float(sealed["reconstructed_value"])
        except (TypeError, ValueError) as exc:
            fails.append(
                {
                    "game_id": rec_row["game_id"],
                    "field": field,
                    "reason": f"non-float compare {exc}",
                }
            )
            continue
        delta = abs(a - b)
        ok = delta < tol
        comparisons.append(
            {
                "game_id": rec_row["game_id"],
                "field": field,
                "family": family,
                "rebuilt": a,
                "sealed": b,
                "abs_delta": delta,
                "tol": tol,
                "pass": ok,
            }
        )
        if not ok:
            fails.append(
                {
                    "game_id": rec_row["game_id"],
                    "field": field,
                    "abs_delta": delta,
                    "tol": tol,
                    "rebuilt": a,
                    "sealed": b,
                }
            )

    n_index = sum(1 for c in comparisons if c["family"] == "index")
    n_epa = sum(1 for c in comparisons if c["family"] == "epa_success_5g")
    n_index_pass = sum(1 for c in comparisons if c["family"] == "index" and c["pass"])
    n_epa_pass = sum(
        1 for c in comparisons if c["family"] == "epa_success_5g" and c["pass"]
    )
    max_index = max(
        (c["abs_delta"] or 0.0 for c in comparisons if c["family"] == "index"),
        default=0.0,
    )
    max_epa = max(
        (c["abs_delta"] or 0.0 for c in comparisons if c["family"] == "epa_success_5g"),
        default=0.0,
    )

    # games.csv index vs rebuilt for W7–W8 / 2016 W8
    games_by_id = {r["game_id"]: r for r in all_games}
    games_index_comp = []
    games_index_fail = []
    csv_map = {
        "offense_index_home": "record_offense_index_home",
        "offense_index_away": "record_offense_index_away",
        "defense_index_home": "record_defense_index_home",
        "defense_index_away": "record_defense_index_away",
    }
    for rec_row in matrix:
        if rec_row["field"] not in INDEX_FIELDS:
            continue
        if rec_row["game_id"] in existing["slices"]["2017_W2_PARITY"]["game_ids_sorted"]:
            continue
        grow = games_by_id.get(rec_row["game_id"])
        if grow is None:
            continue
        raw = grow.get(csv_map[rec_row["field"]], "")
        if raw in ("", None):
            continue
        try:
            csv_v = float(raw)
            reb_v = float(rec_row["reconstructed_value"])
        except (TypeError, ValueError):
            continue
        if not math.isfinite(csv_v):
            continue
        delta = abs(reb_v - csv_v)
        ok = delta < TOL_INDEX
        item = {
            "game_id": rec_row["game_id"],
            "field": rec_row["field"],
            "abs_delta": delta,
            "pass": ok,
        }
        games_index_comp.append(item)
        if not ok:
            games_index_fail.append(item)

    parity = {
        "tolerances_source": "STAGE_B_GAME_SELECTION_t4923u.md / SELECTION_HASH_SEAL.json",
        "tolerances_locked": {
            "index_abs_delta": TOL_INDEX,
            "epa_success_5g_abs_delta": TOL_EPA,
            "post_hoc_change": False,
        },
        "w2_recon_content_sha256": w2_digest,
        "w2_recon_content_sha8": "708513db",
        "w2_games": 14,
        "n_index_compared": n_index,
        "n_index_pass": n_index_pass,
        "n_epa_success_compared": n_epa,
        "n_epa_success_pass": n_epa_pass,
        "max_abs_delta_index": max_index,
        "max_abs_delta_epa_success": max_epa,
        "w2_parity_pass": not fails and n_index == 14 * 4 and n_epa == 14 * 10,
        "fails": fails,
        "games_csv_index_w7w8_2016w8": {
            "n_compared": len(games_index_comp),
            "n_pass": sum(1 for x in games_index_comp if x["pass"]),
            "n_fail": len(games_index_fail),
            "fails": games_index_fail[:20],
            "note": "4fe1cdd7 index vs rebuilt T5; |Δ|<1e-6 when csv finite",
        },
        "cdff0115": (
            "Cited pin only; W3–W6 games are not in this sample; no field compare."
        ),
    }
    (PACKET / "PARITY.json").write_text(json.dumps(parity, indent=2) + "\n", encoding="utf-8")

    (PACKET / "SAMPLE_MANIFEST.json").write_text(
        json.dumps(
            {
                "artifact": "nfl-hist-stage-b-t4923u",
                "labels": ["RETRO_FIT", "DEV_RESEARCH"],
                "cert": 0,
                "scoring": False,
                "model_fit": False,
                "stage_c_authorized": False,
                "n_eligible": 55,
                "n_missing_retained": 2,
                "selection_hash_eligible_combined": existing[
                    "selection_hash_eligible_combined"
                ],
                "games": games_out,
                "pbp": pbp_meta,
                "holdout_2024_25": "untouched",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "phase": "REBUILT",
                "n_eligible": 55,
                "n_complete_27_of_27": len(complete_games),
                "n_partial": len(partial_games),
                "t2_exact_week_misses": len(t2_misses),
                "w2_parity_pass": parity["w2_parity_pass"],
                "n_index_pass": n_index_pass,
                "n_epa_success_pass": n_epa_pass,
                "max_abs_delta_index": max_index,
                "max_abs_delta_epa_success": max_epa,
                "fails": len(fails),
                **coverage["status_counts"],
            },
            indent=2,
        )
    )
    if fails:
        raise SystemExit(f"W2 parity FAIL n={len(fails)}")


if __name__ == "__main__":
    sys.exit(main())
