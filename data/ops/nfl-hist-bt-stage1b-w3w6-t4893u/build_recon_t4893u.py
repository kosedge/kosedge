#!/usr/bin/env python3
"""t4893u Stage-1b reconstruction — 2017 REG W3–W6 (eligible N=60).

Reuses T1–T4 transforms from the sealed W2 builder
(data/ops/nfl-hist-bt-stage1b-w2-t4893u/build_recon_t4893u.py).
Does not invent new pressure/RZ/T4 signs/rest_days/T5 formulas.

Reconstructs contract b41f4b43 T1–T4 from owned nflverse PBP 2017
parquet pin 84eacd96. Does not invoke Independent Fair.
Does not fit, score, tune, call Odds, or touch 2024–25 rows.

Seal order (mandatory):
  1) determine eligible game_ids from games.csv + OOS as-of counts ONLY
  2) write / verify SELECTION_HASH_SEAL.json
  3) then open PBP and write RECON_MATRIX / other rebuild artifacts
"""

from __future__ import annotations

import csv
import importlib.util
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

PACKET = Path(__file__).resolve().parent
W2_BUILDER = PACKET.parent / "nfl-hist-bt-stage1b-w2-t4893u" / "build_recon_t4893u.py"
SEAL_MOD = PACKET / "seal_selection_t4893u.py"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot load {name} at {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_w2():
    return _load_module("w2_recon_t4893u", W2_BUILDER)


def _finite(value: float | None) -> bool:
    return value is not None and isinstance(value, (int, float)) and math.isfinite(float(value))


def _fmt(value: float, digits: int = 8) -> str:
    return f"{float(value):.{digits}f}"


def _window_game_ids(t1, team: str, rating_week: int) -> list[str]:
    """Game ids on that team's T1 rows with week <= rating_week (played weeks only)."""
    hit = t1[(t1["team"] == team) & (t1["week"] <= rating_week)]
    ids: list[str] = []
    for raw in hit["source_game_ids"].tolist():
        ids.extend(str(raw).split("|"))
    return sorted({i for i in ids if i and i != "nan"})


def main() -> None:
    w2 = _load_w2()
    sealmod = _load_module("seal_selection_t4893u", SEAL_MOD)

    # --- SEAL (must succeed before PBP open) ---
    games_path, all_games = sealmod.load_games()
    oos = sealmod.load_oos_2016_2017()
    completed = sealmod.build_completed(all_games, oos)
    by_week, combined_ids, combined_hash = sealmod.eligible_for_weeks(
        all_games, completed
    )
    expected_seal = sealmod.build_seal(by_week, combined_ids, combined_hash)
    seal_path = PACKET / "SELECTION_HASH_SEAL.json"
    if not seal_path.exists():
        raise SystemExit(
            "SELECTION_HASH_SEAL.json missing — run seal_selection_t4893u.py first"
        )
    existing = json.loads(seal_path.read_text(encoding="utf-8"))
    for key in (
        "selection_hash_combined",
        "game_ids_sorted_combined",
        "n_eligible",
        "n_excluded",
        "n_source",
        "per_week",
        "selection_hash_recipe",
        "exclusion_rule",
    ):
        if existing.get(key) != expected_seal.get(key):
            raise SystemExit(f"seal mismatch on {key} — abort, do not rebuild")
    if combined_hash != existing["selection_hash_combined"]:
        raise SystemExit("combined selection_hash drift — abort")
    print(
        json.dumps(
            {
                "phase": "SEAL_VERIFIED",
                "selection_hash_combined": combined_hash,
                "n_eligible": existing["n_eligible"],
            },
            indent=2,
        )
    )

    source_rows = []
    exclusions = []
    for week in sealmod.WEEKS:
        source_rows.extend(by_week[week]["source_rows"])
        exclusions.extend(by_week[week]["exclusions"])
    if len(source_rows) != 60:
        raise SystemExit(f"eligible N target 60, got {len(source_rows)}")
    if exclusions:
        raise SystemExit(f"unexpected exclusions after seal: {exclusions}")

    # --- rebuild after seal ---
    if not w2.PBP_PATH.is_file():
        raise SystemExit(f"PBP missing at {w2.PBP_PATH}")
    pbp_digest = w2.sha256_file(w2.PBP_PATH)
    if pbp_digest != w2.PBP_SHA256:
        raise SystemExit(f"PBP sha256 {pbp_digest} != pin {w2.PBP_SHA256}")

    selfcheck = w2.synthetic_t1_selfcheck()

    import pandas as pd

    pbp_cols = [
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
    pbp = pd.read_parquet(w2.PBP_PATH, columns=pbp_cols)
    if int(pbp["season"].dropna().astype(int).nunique()) != 1 or int(pbp["season"].iloc[0]) != 2017:
        raise SystemExit("PBP season != 2017 only")

    kickoff_by_gid = {
        r["game_id"]: r["kickoff_utc"]
        for r in all_games
        if int(r["season"]) == 2017 and int(r["week"]) <= 6
    }
    prior_games = [
        r
        for r in all_games
        if int(r["season"]) == 2017 and int(r["week"]) <= 5
    ]
    prior_ids = {r["game_id"] for r in prior_games}
    # Week gaps (same structure as W2's max_W1 < min_W2). A global
    # max(W1–W5) < min(W3) cannot hold — W5 is after W3. Per-target
    # consumption is week <= rating_week = target_week-1.
    week_kick_bounds = {}
    for wk in range(1, 7):
        rows = [
            r
            for r in all_games
            if int(r["season"]) == 2017 and int(r["week"]) == wk
        ]
        kicks = [w2.parse_utc(r["kickoff_utc"]) for r in rows]
        week_kick_bounds[wk] = (min(kicks), max(kicks))
    for wk in range(1, 6):
        if not (week_kick_bounds[wk][1] < week_kick_bounds[wk + 1][0]):
            raise SystemExit(
                f"as-of fail: latest W{wk} {week_kick_bounds[wk][1].isoformat()} "
                f"not < earliest W{wk+1} {week_kick_bounds[wk+1][0].isoformat()}"
            )
    min_target = week_kick_bounds[3][0]

    plays = pbp[
        (pbp["season"] == 2017)
        & (pbp["season_type"] == "REG")
        & (pbp["week"].isin([1, 2, 3, 4, 5]))
        & pbp["week"].notna()
        & pbp["posteam"].notna()
        & pbp["play_type"].isin(["pass", "run"])
        & pbp["game_id"].isin(prior_ids)
    ].copy()
    if plays.empty:
        raise SystemExit("no W1–W5 REG pass/run plays after filter")

    leaked = []
    consumed_game_ids = sorted(plays["game_id"].dropna().unique().tolist())
    for gid in consumed_game_ids:
        kick = kickoff_by_gid.get(gid)
        if kick is None:
            leaked.append(
                {
                    "game_id": gid,
                    "reason": "consumed PBP game_id not in games.csv 2017 W1–W5",
                }
            )
    # Global T1 includes W3–W5 because W4–W6 rating weeks need them.
    # Per-target audit consumes only week <= rating_week. Forbid W6 in T1.
    w6_in_consumed = [g for g in consumed_game_ids if "_06_" in g]
    if w6_in_consumed:
        leaked.append({"reason": "W6 game_id in consumed T1 set", "game_ids": w6_in_consumed})
    if leaked:
        raise SystemExit(f"leakage test failed: {leaked}")

    t1 = w2.t1_from_plays(plays)
    # W1=30 (no TB/MIA), W2–W4=32, W5=28 byes ATL/DEN/NO/WSH → 30+32*3+28 = 154
    if len(t1) != 154:
        raise SystemExit(f"expected 154 W1–W5 T1 team-rows, got {len(t1)}")
    w1_teams = set(t1.loc[t1["week"] == 1, "team"])
    if w1_teams & {"TB", "MIA"}:
        raise SystemExit("T1 W1 includes TB/MIA — those teams had no 2017 W1 game")
    if len(w1_teams) != 30:
        raise SystemExit(f"expected 30 W1 T1 teams, got {len(w1_teams)}")

    t2 = w2.rolling_5g(t1)

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
        "offensive_dropbacks",
        "offensive_pressures_allowed",
        "defensive_dropbacks_faced",
        "defensive_pressures_generated",
        "source_game_ids",
        "games_in_window_5",
    ]
    t1.to_csv(PACKET / "t1_team_week_2017_w1w5.csv", index=False, columns=t1_out_cols)

    games_out = []
    matrix = []
    status_counts: Counter[str] = Counter()
    complete_games = []
    partial_games = []
    t2_misses = []

    t1_lineage = (
        "T1=nfl_dp_team_situational_weekly port of ingest.py offense/defense CTEs "
        f"@sha256 {w2.INGEST_SHA256[:8]}… from owned PBP 2017 pin 84eacd96. "
        "play_type IN ('pass','run') — kneels/spikes/no_play/penalties excluded. "
        "T2=season-partitioned ROWS BETWEEN 4 PRECEDING AND CURRENT ROW "
        "(same function as W2 builder rolling_5g). "
        "T3 home/away = T2 at rating_week=target_week-1 (cf514078; never target-week CURRENT ROW). "
        "Exact week lookup (W2 lookup_t2). No last-played-week fill if rating_week is a bye. "
        "T4 diffs per contract §4 / ingest matchup SQL. "
        "nflverse EPA/success are retro-scored by a later EP model — metric-definition "
        "look-ahead, not W3–W6 outcome leakage."
    )

    for rec in source_rows:
        gid = rec["game_id"]
        home = rec["home_team"]
        away = rec["away_team"]
        kick = rec["kickoff_utc"]
        week = int(rec["week"])
        rating_week = int(rec["rating_week_contiguous"])
        rest_et = rec["rest_days_et"]
        rest_utc = rec["rest_days_utc_contrast"]
        h = w2.lookup_t2(t2, home, rating_week)
        a = w2.lookup_t2(t2, away, rating_week)
        if h is None:
            t2_misses.append(
                {
                    "game_id": gid,
                    "side": "home",
                    "team": home,
                    "rating_week": rating_week,
                    "reason": "no T2 row at exact rating_week (W2 lookup_t2); no last-played fill",
                }
            )
        if a is None:
            t2_misses.append(
                {
                    "game_id": gid,
                    "side": "away",
                    "team": away,
                    "rating_week": rating_week,
                    "reason": "no T2 row at exact rating_week (W2 lookup_t2); no last-played fill",
                }
            )

        # Per-target leakage: every consumed prior-week game for each available side
        # has kickoff < this target. Window = that team's T1 weeks <= rating_week.
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

        def add(
            field: str,
            status: str,
            *,
            source_path: str,
            source_sha256: str,
            lineage: str,
            evidence: str,
            notes: str,
            value: str = "",
            exclusion_reason: str = "",
        ) -> None:
            matrix.append(
                {
                    "game_id": gid,
                    "season": 2017,
                    "week": week,
                    "home_team": home,
                    "away_team": away,
                    "field": field,
                    "status": status,
                    "reconstructed_value": value,
                    "source_path": source_path,
                    "source_sha256": source_sha256,
                    "source_sha8": source_sha256[:8],
                    "pregame_cutoff_utc": kick,
                    "rating_week": str(rating_week),
                    "derivation_lineage": lineage,
                    "availability_evidence": evidence,
                    "exclusion_reason": exclusion_reason,
                    "notes": notes,
                }
            )
            status_counts[status] += 1

        identity = {
            "game_id": gid,
            "home_team": home,
            "away_team": away,
            "matchup_season": "2017",
            "matchup_week": str(week),
        }
        for field, value in identity.items():
            add(
                field,
                "DERIVED_PREGAME",
                source_path="data/ops/nfl-t4422u-walkforward-pergame-unblended-2013-2023/games.csv",
                source_sha256=w2.GAMES_SHA256,
                lineage="sample identity from sealed games.csv pin 4fe1cdd7; kickoff known pregame",
                evidence=f"row present season=2017 week={week} game_id={gid}",
                notes="canonical game_id from walkforward export; not invented",
                value=value,
            )

        for side in ("home", "away"):
            add(
                f"rest_days_{side}",
                "DERIVED_PREGAME",
                source_path="services/model-service/src/services/nfl_offline_if_eval_w8.py:rest_days_from_schedule (ET) @155d3ca0; contract §3 rest_days_from_schedule",
                source_sha256=w2.NFL_DATA_SHA256,
                lineage=(
                    "ET DOW heuristic as in v3 IF consume (Thu=4, Mon=6, else=7) "
                    "from target kickoff_utc. Same value both sides. "
                    "Not team-specific days-since-last-game. "
                    "Silent 7.0-on-missing-kickoff path not used (Z present). "
                    "Same heuristic as W2 packet."
                ),
                evidence=f"kickoff_utc={kick} rest_et={rest_et} rest_utc_contrast={rest_utc}",
                notes=(
                    f"utc_et_dow_mismatch={rest_et != rest_utc}; "
                    "games.csv rest_days_* hardcoded 7.0 NOT used"
                ),
                value=str(rest_et),
            )

        for side, team, n_played, rec_wl in (
            ("home", home, rec["completed_same_season_games_home"], rec["record_asof_home"]),
            ("away", away, rec["completed_same_season_games_away"], rec["record_asof_away"]),
        ):
            off_i, def_i = w2.team_strength_from_record(rec_wl)
            add(
                f"offense_index_{side}",
                "DERIVED_PREGAME",
                source_path=(
                    "data/ops/nfl-reopening-packet-20260916/historical-oos/"
                    "historical_oos_games.csv + games.csv kickoff join; "
                    "T5 team_strength_from_record"
                ),
                source_sha256=w2.OOS_SHA256,
                lineage=(
                    "T5: win_pct from same-season completed REG games with "
                    "kickoff < target kickoff (ties ignored); "
                    "off=clamp(0.90+0.22*wp, 0.82, 1.18)"
                ),
                evidence=(
                    f"record_asof={rec_wl} n={n_played} cutoff={kick}; "
                    f"games.csv entering={rec[f'games_csv_record_entering_{side}']}"
                ),
                notes="recomputed as-of; not a 2026 panel index",
                value=_fmt(off_i, 6),
            )
            add(
                f"defense_index_{side}",
                "DERIVED_PREGAME",
                source_path=(
                    "data/ops/nfl-reopening-packet-20260916/historical-oos/"
                    "historical_oos_games.csv + games.csv kickoff join; "
                    "T5 team_strength_from_record"
                ),
                source_sha256=w2.OOS_SHA256,
                lineage=(
                    "T5: def=clamp(0.92+0.20*wp, 0.82, 1.20) from same record"
                ),
                evidence=(
                    f"record_asof={rec_wl} n={n_played} cutoff={kick}; "
                    f"games.csv entering={rec[f'games_csv_record_entering_{side}']}"
                ),
                notes="recomputed as-of; not a 2026 panel index",
                value=_fmt(def_i, 6),
            )

        def _side_metrics(row: dict | None) -> dict[str, float | None]:
            if row is None:
                return {
                    "off": None,
                    "def": None,
                    "pr": None,
                    "so": None,
                    "sd": None,
                    "pg": None,
                    "pa": None,
                    "rz": None,
                }
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

        # Contract T3 signs (ingest matchup SQL) — same as W2:
        # diff_off = h.off - a.off
        # diff_def_allowed = a.def_allowed - h.def_allowed
        # diff_pressure_generated = h - a
        # diff_pressure_allowed = a - h
        # diff_rz = h - a
        # T4 success = mean( (h_so-a_so), (a_sd-h_sd) ) — both terms required
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
            parts.append(f"pbp_sha8=84eacd96 cutoff={kick}")
            return "; ".join(parts)

        for field, val in {**side_values, **diff_values}.items():
            if not _finite(val):
                add(
                    field,
                    "MISSING_RECORD",
                    source_path=str(w2.PBP_PATH),
                    source_sha256=w2.PBP_SHA256,
                    lineage=t1_lineage,
                    evidence=(
                        f"non-finite or unavailable T1/T2 value for {field}; "
                        + _t2_evidence()
                    ),
                    notes=(
                        "fail-closed; no default; no last-played-week T2 fill "
                        "(W2 lookup_t2 is exact rating_week)"
                    ),
                    exclusion_reason=(
                        "T2 row absent at exact rating_week or non-finite metric"
                    ),
                )
                continue
            add(
                field,
                "DERIVED_PREGAME",
                source_path=str(w2.PBP_PATH),
                source_sha256=w2.PBP_SHA256,
                lineage=t1_lineage,
                evidence=_t2_evidence(),
                notes=(
                    "pressure=(sack OR qb_hit)/play_type='pass' per T1 SQL; "
                    "RZ=plays with yardline_100<=20 (not drive-trips). "
                    "EPA retro-fit caveat labeled. Same T1–T4 as W2."
                ),
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

    fields_per_game = len(w2.REQUIRED_20) + len(w2.REQUIRED_CONTEXT)
    if len(matrix) != 60 * fields_per_game:
        raise SystemExit(f"matrix cells {len(matrix)} != 60*27")

    manifest = {
        "artifact": "nfl-hist-bt-stage1b-w3w6-t4893u",
        "label": "EVAL_ONLY reconstruction audit — 2017 REG W3–W6",
        "cert": 0,
        "stage": "1b",
        "scoring": False,
        "model_fit": False,
        "odds_api": False,
        "season": 2017,
        "weeks": [3, 4, 5, 6],
        "n_source": 60,
        "n_excluded": len(exclusions),
        "n": len(source_rows),
        "n_eligible": 60,
        "selection_hash_combined": combined_hash,
        "selection_hash_per_week": {
            str(w): by_week[w]["selection_hash"] for w in sealmod.WEEKS
        },
        "selection_hash_recipe": existing["selection_hash_recipe"],
        "selection_hash_sealed_before_rebuild": True,
        "selection_hash_sealed_before_pbp_open": True,
        "selection_hash_seal_path": "SELECTION_HASH_SEAL.json",
        "selection_hash_seal_commit": "32f9a3ec",
        "source_games_csv": "data/ops/nfl-t4422u-walkforward-pergame-unblended-2013-2023/games.csv",
        "source_games_csv_branch": "origin/cursor/t4422u-walkforward-pergame-export-f36b",
        "source_games_csv_tip": "82ffb211",
        "source_games_csv_sha256": w2.GAMES_SHA256,
        "source_games_csv_sha8": "4fe1cdd7",
        "rehash_this_run": w2.GAMES_SHA256,
        "rehash_match": True,
        "pbp_path": str(w2.PBP_PATH),
        "pbp_sha256": w2.PBP_SHA256,
        "pbp_sha8": "84eacd96",
        "pbp_rehash_this_run": pbp_digest,
        "pbp_rehash_match": pbp_digest == w2.PBP_SHA256,
        "pbp_bytes": w2.PBP_PATH.stat().st_size,
        "holdout_2024_25": "untouched",
        "exclusions": exclusions,
        "t2_exact_week_misses": t2_misses,
        "games": games_out,
        "w2_lineage": sealmod.W2_LINEAGE,
        "pins": {
            "contract_sha8": "b41f4b43",
            "contract_sha256": w2.CONTRACT_SHA256,
            "contract_path": (
                "data/ops/nfl-efficiency-2026-w1-w8-t4770u/"
                "ALEX_E1_EFFICIENCY_CONTRACT_t4770u_v2.md"
            ),
            "contract_branch": "origin/cursor/hift1-efficiency-recovery-f693",
            "pass_contract_sha8": "1a53bbd3",
            "pass_contract_sha256": w2.PASS_CONTRACT_SHA256,
            "pass_contract_path": (
                "data/ops/nfl-efficiency-2026-w1-w8-t4770u/"
                "IMV_GRADE_t4770u_E1_EFFICIENCY_CONTRACT_v2.txt"
            ),
            "as_of_sha8": "cf514078",
            "as_of_status": "PASS_ASOF_BOUNDARY",
            "as_of_tip": "1010b86f",
            "as_of_module": "services/model-service/src/services/nfl_pregame_asof.py",
            "as_of_module_sha256": w2.ASOF_MODULE_SHA256,
            "as_of_module_sha8": "7dc6afea",
            "source_only_sha8": "52d9e909",
            "source_only_sha256": w2.SOURCE_PIN_SHA256,
            "source_only_commit": "1b39f4e9",
            "t1_ingest_sha256": w2.INGEST_SHA256,
            "t1_ingest_sha8": w2.INGEST_SHA256[:8],
            "pbp_sha256": w2.PBP_SHA256,
            "pbp_sha8": "84eacd96",
            "w2_builder": "data/ops/nfl-hist-bt-stage1b-w2-t4893u/build_recon_t4893u.py",
        },
        "week_note": (
            "60 REG source games W3–W6 (16+16+14+14). Eligible 60 after "
            "0-prior rule (no exclusions). Cutoff = each game kickoff_utc. "
            "rating_week = target_week-1. T1 from 2017 REG W1–W5 PBP "
            "(play_type pass/run). T2 exact-week lookup (W2 method); "
            "W5-bye sides at W6 rating_week=5 stay MISSING (no last-played fill)."
        ),
    }
    (PACKET / "SAMPLE_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    (PACKET / "EXCLUSIONS.json").write_text(
        json.dumps(
            {
                "rule": existing["exclusion_rule"],
                "n_source": 60,
                "n_source_by_week": {str(w): by_week[w]["n_source"] for w in sealmod.WEEKS},
                "n_excluded": len(exclusions),
                "n_eligible": 60,
                "exclusions": exclusions,
                "note": (
                    "No W3–W6 game had a 0-completed-same-season side. "
                    "W1 Irma TB/MIA completed W2 before W3."
                ),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

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

    by_field = defaultdict(Counter)
    by_week_cov = defaultdict(lambda: {"complete": [], "partial": []})
    for rec_row in matrix:
        by_field[rec_row["field"]][rec_row["status"]] += 1
    for gid in complete_games:
        rec = next(r for r in source_rows if r["game_id"] == gid)
        by_week_cov[rec["week"]]["complete"].append(gid)
    for part in partial_games:
        by_week_cov[part["week"]]["partial"].append(part["game_id"])

    coverage = {
        "n_source": 60,
        "n_source_by_week": {str(w): by_week[w]["n_source"] for w in sealmod.WEEKS},
        "n_excluded": len(exclusions),
        "excluded_game_ids": [e["game_id"] for e in exclusions],
        "n_games": len(source_rows),
        "n_eligible": 60,
        "fields_per_game": fields_per_game,
        "n_cells": len(matrix),
        "status_counts": dict(status_counts),
        "derived_pregame": status_counts["DERIVED_PREGAME"],
        "missing_record": status_counts.get("MISSING_RECORD", 0),
        "out_of_contract": status_counts.get("OUT_OF_CONTRACT", 0),
        "excluded_cells": status_counts.get("EXCLUDED", 0),
        "pct_fields_present": round(
            100.0 * status_counts["DERIVED_PREGAME"] / len(matrix), 4
        ),
        "complete_eligible_games_27_of_27": sorted(complete_games),
        "n_complete_eligible": len(complete_games),
        "partial_eligible_games": partial_games,
        "n_partial_eligible": len(partial_games),
        "by_week": {
            str(w): {
                "n_source": by_week[w]["n_source"],
                "n_eligible": by_week[w]["n_eligible"],
                "n_complete": len(by_week_cov[w]["complete"]),
                "n_partial": len(by_week_cov[w]["partial"]),
                "complete_game_ids": sorted(by_week_cov[w]["complete"]),
                "partial_game_ids": sorted(by_week_cov[w]["partial"]),
            }
            for w in sealmod.WEEKS
        },
        "by_field": {k: dict(v) for k, v in sorted(by_field.items())},
        "t1_w1w5_teams_w1": int(t1.loc[t1["week"] == 1, "team"].nunique()),
        "t1_w1w5_rows": int(len(t1)),
        "t2_exact_week_misses": t2_misses,
        "pressure_rz_status": "DERIVED_PREGAME via T1 SQL as written (not a substitute) when T2 row present; MISSING_RECORD if exact rating_week T2 absent",
        "epa_retrofit_caveat": (
            "nflverse epa/success are retro-scored by a later-fitted EP model. "
            "Metric-definition look-ahead; not consumption of target-week outcomes."
        ),
        "w2_lineage_tip": "440314e4",
        "w2_lineage_alex_sha8": "91e2d7db",
    }
    (PACKET / "COVERAGE.json").write_text(
        json.dumps(coverage, indent=2) + "\n", encoding="utf-8"
    )

    week_counts = Counter(int(g.split("_")[1]) for g in consumed_game_ids)
    leakage = {
        "rule": "no consumed play/game with kickoff >= target kickoff; T1 weeks strictly < target week",
        "consumed_pbp_game_ids": consumed_game_ids,
        "n_consumed_games": len(consumed_game_ids),
        "n_consumed_plays": int(len(plays)),
        "consumed_weeks": sorted(int(x) for x in plays["week"].dropna().unique().tolist()),
        "consumed_week_game_counts": {str(k): int(v) for k, v in sorted(week_counts.items())},
        "max_consumed_kickoff_utc": max(kickoff_by_gid[g] for g in consumed_game_ids),
        "min_eligible_target_kickoff_utc": min(r["kickoff_utc"] for r in source_rows),
        "week_gap_max_wk_lt_min_wk_plus_1": {
            str(wk): True for wk in range(1, 6)
        },
        "note_global_max_w5_after_min_w3": (
            "T1 frame includes W3–W5 for later targets. "
            "Per-target window is week <= rating_week; week gaps hold."
        ),
        "w6_plays_consumed": 0,
        "season_types_consumed": ["REG"],
        "leaked_rows": leaked,
        "play_filter": "play_type IN ('pass','run'); season_type=REG; week IN (1,2,3,4,5)",
        "per_target": "window = team T1 rows with week <= rating_week; all those kickoffs < target",
        "result": "PASS",
    }
    (PACKET / "LEAKAGE_AUDIT.json").write_text(
        json.dumps(leakage, indent=2) + "\n", encoding="utf-8"
    )

    t1_verify = {
        "contract_t1": "nfl_dp_team_situational_weekly columns cited in b41f4b43 §4",
        "producer": "services/model-service/data_platform_nfl/ingest.py offense/defense CTEs",
        "producer_sha256": w2.INGEST_SHA256,
        "producer_sha8": w2.INGEST_SHA256[:8],
        "reused_from": "data/ops/nfl-hist-bt-stage1b-w2-t4893u/build_recon_t4893u.py",
        "functions_reused": [
            "t1_from_plays",
            "rolling_5g",
            "lookup_t2",
            "synthetic_t1_selfcheck",
            "team_strength_from_record",
            "rest_days_et",
        ],
        "numeric_2023_plus_gate": (
            "NOT POSSIBLE on this box: 2023 PBP not owned (pin unused); "
            "2025 situational dump is 2025 W1 only and 2025 PBP is not owned. "
            "No 2024–25 rows opened for values. Same residual as W2."
        ),
        "gate_used": "SQL-to-pandas code-review port + synthetic fixture (abs_tol 1e-12) via W2 builder",
        "synthetic_selfcheck": selfcheck,
        "pressure_definition": {
            "contract": "T1 column pressure_rate_allowed/generated from ingest.py",
            "sql": "(sack OR qb_hit) among play_type='pass' / count play_type='pass'",
            "qb_dropback_used_as_denominator": False,
            "hurries_required": False,
            "matched": True,
            "status": "DERIVED_PREGAME when T2 present",
            "escalation": None,
        },
        "red_zone_definition": {
            "contract": "T1 column red_zone_td_rate from ingest.py",
            "sql": "(yardline_100<=20 AND touchdown) / (yardline_100<=20) on pass/run plays",
            "trips_definition_used": False,
            "plain_english_trips_paraphrase": (
                "T1T4_PLAIN_ENGLISH_DEFS says 'RZ trips ending in TD'. "
                "Contract-cited T1 SQL is play-based, not drive-trip-based. "
                "Using trips would be a substitute → refused. Play-based SQL used."
            ),
            "matched": True,
            "status": "DERIVED_PREGAME when T2 present",
            "escalation": (
                "NOTE only: plain-English 'trips' ≠ T1 SQL plays. "
                "Reconstructed as written (SQL). Not a contract change."
            ),
        },
        "play_filter": "play_type IN ('pass','run') — excludes qb_kneel, qb_spike, no_play, special teams",
        "team_identity_remap": {
            "LA": "LAR",
            "WAS": "WSH",
            "LV": "OAK",
            "note": (
                "2017 PBP uses later nflverse codes LA/WAS/LV; games.csv pin uses "
                "LAR/WSH/OAK. Identity join only."
            ),
        },
        "min_periods": (
            "T2 window = last ≤5 PLAYED games. rating_week = target_week-1. "
            "W2 lookup_t2 is exact week. W5 byes (ATL/DEN/NO/WSH) have no T2 "
            "row at week=5 → W6 sides MISSING_RECORD (no last-played fill)."
        ),
        "epa_retrofit_caveat": coverage["epa_retrofit_caveat"],
    }
    (PACKET / "T1_TRANSFORM.json").write_text(
        json.dumps(t1_verify, indent=2) + "\n", encoding="utf-8"
    )

    print(
        json.dumps(
            {
                "phase": "REBUILT",
                "selection_hash_combined": combined_hash,
                "n_eligible": 60,
                "n_complete_27_of_27": len(complete_games),
                "n_partial": len(partial_games),
                "t2_exact_week_misses": len(t2_misses),
                **coverage["status_counts"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    sys.exit(main())
