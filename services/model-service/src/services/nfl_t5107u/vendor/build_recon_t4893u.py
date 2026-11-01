#!/usr/bin/env python3
"""t4893u Stage-1b reconstruction — 2017 REG W2 first (eligible N=14).

Reconstructs contract b41f4b43 T1–T4 (and keeps T5/context) from the owned
nflverse PBP 2017 parquet pin 84eacd96. Does not invoke Independent Fair.
Does not fit, score, tune, call Odds, or touch 2024–25 rows.

Seal order (mandatory):
  1) determine eligible game_ids from games.csv + OOS as-of counts ONLY
  2) write SELECTION_HASH_SEAL.json
  3) then open PBP and write RECON_MATRIX / other rebuild artifacts
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

REPO = Path(__file__).resolve().parents[3]
PACKET = Path(__file__).resolve().parent

GAMES_CSV = (
    REPO / "data/ops/nfl-t4422u-walkforward-pergame-unblended-2013-2023/games.csv"
)
GAMES_CSV_FALLBACK = Path("/tmp/t4893u_refs/games.csv")
OOS_CSV = (
    REPO
    / "data/ops/nfl-reopening-packet-20260916/historical-oos/historical_oos_games.csv"
)
PBP_PATH = Path(
    "/workspace/data/raw/nfl/pbp/t4696u_s1_restage/play_by_play_2017.parquet"
)

GAMES_SHA256 = "4fe1cdd7f2eb616103ee6107e6a5cb0d5280f8006be420b606af0995351abef8"
OOS_SHA256 = "1ee90facf7d44dfd19758cbf89d5518417cbc1fba6faec4e76fb33d8532adaed"
CONTRACT_SHA256 = "b41f4b43e1367bd5658c743475b9b84535c65395630a0b06c804f8b3552b81f4"
PASS_CONTRACT_SHA256 = (
    "1a53bbd33f32fec8d25a102f2abea7b975a92fbd55edbaaaafe020055c25b9f8"
)
ASOF_MODULE_SHA256 = (
    "7dc6afea2f13705b02683a5d16e53193adb7acd5441bde8494268fe850c50c98"
)
SOURCE_PIN_SHA256 = (
    "52d9e90927c9bc9d48314659d2735b9647974f20c2f15944855727e0cfd86385"
)
NFL_DATA_SHA256 = (
    "2989a556047fddae47ce8671dfb79eafc54c809a8e1e0b7ea06aaf0cce04a79b"
)
PBP_SHA256 = "84eacd963c1fdd45965f6222c62e9329a7f3412f029d92c1ac5e34a1bb4d3710"
INGEST_SHA256 = (
    "5fc97157c388452da60f687f886770d631e26e5405789bc76cefbbb86284ee4d"
)

# Pre-declared Irma exclusions (OWNER t4893u). Verified, not invented.
PREDECLARED_EXCLUSIONS = {
    "2017_02_CHI_TB": "TB home — 0 completed 2017 games as-of kickoff (Irma postpone)",
    "2017_02_MIA_LAC": "MIA away — 0 completed 2017 games as-of kickoff (Irma postpone)",
}

REQUIRED_20 = (
    "offense_index_home",
    "offense_index_away",
    "defense_index_home",
    "defense_index_away",
    "home_off_epa_5g",
    "away_off_epa_5g",
    "home_def_epa_allowed_5g",
    "away_def_epa_allowed_5g",
    "home_pass_rate_5g",
    "away_pass_rate_5g",
    "home_success_offense_5g",
    "away_success_offense_5g",
    "home_success_defense_allowed_5g",
    "away_success_defense_allowed_5g",
    "matchup_diff_off_epa_5g",
    "matchup_diff_def_epa_allowed_5g",
    "matchup_diff_success_rate_5g",
    "matchup_diff_pressure_generated_5g",
    "matchup_diff_pressure_allowed_5g",
    "matchup_diff_red_zone_td_rate_5g",
)
REQUIRED_CONTEXT = (
    "game_id",
    "home_team",
    "away_team",
    "matchup_season",
    "matchup_week",
    "rest_days_home",
    "rest_days_away",
)
T5_FIELDS = (
    "offense_index_home",
    "offense_index_away",
    "defense_index_home",
    "defense_index_away",
)
T1_SIDE_FIELDS = (
    "home_off_epa_5g",
    "away_off_epa_5g",
    "home_def_epa_allowed_5g",
    "away_def_epa_allowed_5g",
    "home_pass_rate_5g",
    "away_pass_rate_5g",
    "home_success_offense_5g",
    "away_success_offense_5g",
    "home_success_defense_allowed_5g",
    "away_success_defense_allowed_5g",
)
T4_DIFF_FIELDS = (
    "matchup_diff_off_epa_5g",
    "matchup_diff_def_epa_allowed_5g",
    "matchup_diff_success_rate_5g",
    "matchup_diff_pressure_generated_5g",
    "matchup_diff_pressure_allowed_5g",
    "matchup_diff_red_zone_td_rate_5g",
)
ET = ZoneInfo("America/New_York")

# Identity remaps only — join PBP / games.csv codes. Never a statistical fill.
PBP_TO_CANON = {"LA": "LAR", "WAS": "WSH", "LV": "OAK"}
GAMES_TO_CANON = {"LA": "LAR", "WAS": "WSH", "SD": "SD"}


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


def team_strength_from_record(record_summary: str) -> tuple[float, float]:
    if not record_summary or "-" not in record_summary:
        raise ValueError("malformed record would silent-default to 1.0 — reject")
    wins, losses = record_summary.split("-", 1)
    w = max(0.0, float(wins))
    l = max(0.0, float(losses))
    games = w + l
    if games <= 0:
        raise ValueError("0-0 empty record is not a completed-game T5 baseline")
    win_pct = w / games
    offense = 0.90 + (0.22 * win_pct)
    defense = 0.92 + (0.20 * win_pct)
    return max(0.82, min(1.18, offense)), max(0.82, min(1.20, defense))


def normalize_games_abbr(token: str) -> str:
    return GAMES_TO_CANON.get(token, token)


def normalize_pbp_abbr(token: str) -> str:
    if token is None or (isinstance(token, float) and math.isnan(token)):
        return ""
    return PBP_TO_CANON.get(str(token), str(token))


def selection_hash(game_ids: list[str]) -> str:
    payload = "\n".join(sorted(game_ids)) + "\n"
    return sha256_text(payload)


def _finite(value: float | None) -> bool:
    return value is not None and isinstance(value, (int, float)) and math.isfinite(float(value))


def _fmt(value: float, digits: int = 8) -> str:
    return f"{float(value):.{digits}f}"


def _truthy(series: pd.Series) -> pd.Series:
    return series.fillna(0).astype(float).eq(1.0)


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
    seasons_seen: Counter[int] = Counter()
    with OOS_CSV.open(newline="") as fh:
        for row in csv.DictReader(fh):
            season = int(float(row["season"]))
            seasons_seen[season] += 1
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


def t1_from_plays(plays: pd.DataFrame) -> pd.DataFrame:
    """Port of ingest.py nfl_dp_team_situational_weekly offense/defense CTEs.

    Filters already applied by caller: season_type REG, play_type in (pass, run),
    week/posteam present. Pressure = (sack OR qb_hit) / play_type='pass'.
    RZ TD rate = (yardline_100<=20 AND touchdown) / (yardline_100<=20).
    """
    if plays.empty:
        raise SystemExit("T1 input plays empty")

    work = plays.copy()
    is_pass = work["play_type"].eq("pass")
    work["is_pass"] = is_pass.astype(int)
    work["is_run"] = work["play_type"].eq("run").astype(int)
    work["sack_on_pass"] = (is_pass & _truthy(work["sack"])).astype(int)
    work["qbhit_on_pass"] = (is_pass & _truthy(work["qb_hit"])).astype(int)
    work["pressure_on_pass"] = (
        is_pass & (_truthy(work["sack"]) | _truthy(work["qb_hit"]))
    ).astype(int)
    work["rz"] = work["yardline_100"].le(20).fillna(False).astype(int)
    work["rz_td"] = (
        work["yardline_100"].le(20).fillna(False) & _truthy(work["touchdown"])
    ).astype(int)
    work["early"] = work["down"].isin([1.0, 2.0, 1, 2]).astype(int)
    work["early_pass"] = (
        work["down"].isin([1.0, 2.0, 1, 2]) & is_pass
    ).astype(int)
    work["third"] = work["down"].eq(3).astype(int)
    work["third_conv"] = (work["down"].eq(3) & _truthy(work["first_down"])).astype(int)
    work["fourth"] = work["down"].eq(4).astype(int)
    work["fourth_conv"] = (work["down"].eq(4) & _truthy(work["first_down"])).astype(int)
    work["success_num"] = work["success"].astype(float)
    work["epa_num"] = work["epa"].astype(float)
    work["team_canon"] = work["posteam"].map(normalize_pbp_abbr)
    work["def_canon"] = work["defteam"].map(normalize_pbp_abbr)

    off = (
        work.groupby(["season", "week", "team_canon"], dropna=True)
        .agg(
            games_played=("game_id", "nunique"),
            offensive_plays=("game_id", "size"),
            pass_plays=("is_pass", "sum"),
            run_plays=("is_run", "sum"),
            early_down_plays=("early", "sum"),
            early_down_pass_plays=("early_pass", "sum"),
            third_down_attempts=("third", "sum"),
            third_down_conversions=("third_conv", "sum"),
            fourth_down_attempts=("fourth", "sum"),
            fourth_down_conversions=("fourth_conv", "sum"),
            red_zone_plays=("rz", "sum"),
            red_zone_touchdowns=("rz_td", "sum"),
            sacks_allowed=("sack_on_pass", "sum"),
            qb_hits_allowed=("qbhit_on_pass", "sum"),
            offensive_pressures_allowed=("pressure_on_pass", "sum"),
            offensive_dropbacks=("is_pass", "sum"),
            success_rate_offense=("success_num", "mean"),
            epa_per_play_offense=("epa_num", "mean"),
            source_game_ids=("game_id", lambda s: "|".join(sorted(set(s)))),
        )
        .reset_index()
        .rename(columns={"team_canon": "team"})
    )

    dwork = work[work["def_canon"].ne("")].copy()
    deff = (
        dwork.groupby(["season", "week", "def_canon"], dropna=True)
        .agg(
            defensive_plays=("game_id", "size"),
            sacks_generated=("sack_on_pass", "sum"),
            qb_hits_generated=("qbhit_on_pass", "sum"),
            defensive_pressures_generated=("pressure_on_pass", "sum"),
            defensive_dropbacks_faced=("is_pass", "sum"),
            success_rate_defense_allowed=("success_num", "mean"),
            epa_per_play_defense_allowed=("epa_num", "mean"),
        )
        .reset_index()
        .rename(columns={"def_canon": "team"})
    )

    t1 = off.merge(deff, on=["season", "week", "team"], how="left")

    def rate(num: pd.Series, den: pd.Series) -> pd.Series:
        out = pd.Series([None] * len(num), index=num.index, dtype="float64")
        ok = den.fillna(0) > 0
        out.loc[ok] = num.loc[ok].astype(float) / den.loc[ok].astype(float)
        return out

    t1["pass_rate"] = rate(t1["pass_plays"], t1["offensive_plays"])
    t1["early_down_pass_rate"] = rate(t1["early_down_pass_plays"], t1["early_down_plays"])
    t1["third_down_conversion_rate"] = rate(
        t1["third_down_conversions"], t1["third_down_attempts"]
    )
    t1["fourth_down_conversion_rate"] = rate(
        t1["fourth_down_conversions"], t1["fourth_down_attempts"]
    )
    t1["red_zone_td_rate"] = rate(t1["red_zone_touchdowns"], t1["red_zone_plays"])
    t1["pressure_rate_allowed"] = rate(
        t1["offensive_pressures_allowed"], t1["offensive_dropbacks"]
    )
    t1["pressure_rate_generated"] = rate(
        t1["defensive_pressures_generated"], t1["defensive_dropbacks_faced"]
    )
    t1["games_in_window_5"] = t1["games_played"]
    return t1


def synthetic_t1_selfcheck() -> dict:
    """Tiny fixture: SQL-equivalent rates, no 2017 values."""
    def _play(posteam: str, defteam: str, **kw: object) -> dict:
        base = {
            "season": 2099,
            "week": 1,
            "game_id": "FIX_1",
            "posteam": posteam,
            "defteam": defteam,
            "sack": 0.0,
            "qb_hit": 0.0,
            "yardline_100": 50.0,
            "touchdown": 0.0,
            "down": 1.0,
            "first_down": 0.0,
            "success": 0.0,
            "epa": 0.0,
        }
        base.update(kw)
        return base

    rows = [
        # AAA vs BBB: pass sack+hit (pressure), not RZ
        _play("AAA", "BBB", play_type="pass", sack=1.0, qb_hit=1.0, success=0.0, epa=-1.0),
        # AAA vs BBB: RZ TD run
        _play(
            "AAA",
            "BBB",
            play_type="run",
            yardline_100=5.0,
            touchdown=1.0,
            down=2.0,
            first_down=1.0,
            success=1.0,
            epa=2.0,
        ),
        # BBB vs AAA: mirror so both teams have offense+defense rows (T1 is offense LEFT JOIN defense)
        _play("BBB", "AAA", play_type="pass", sack=1.0, qb_hit=1.0, success=0.0, epa=-1.0),
        _play(
            "BBB",
            "AAA",
            play_type="run",
            yardline_100=5.0,
            touchdown=1.0,
            down=2.0,
            first_down=1.0,
            success=1.0,
            epa=2.0,
        ),
    ]
    t1 = t1_from_plays(pd.DataFrame(rows))
    if len(t1) != 2:
        raise SystemExit(f"T1 synthetic expected 2 team rows, got {len(t1)}")
    row = t1[t1["team"] == "AAA"].iloc[0]
    checks = {
        "pass_rate": (row["pass_rate"], 0.5),
        "epa_per_play_offense": (row["epa_per_play_offense"], 0.5),
        "success_rate_offense": (row["success_rate_offense"], 0.5),
        "pressure_rate_allowed": (row["pressure_rate_allowed"], 1.0),
        "red_zone_td_rate": (row["red_zone_td_rate"], 1.0),
        "pressure_rate_generated": (row["pressure_rate_generated"], 1.0),
        "epa_per_play_defense_allowed": (row["epa_per_play_defense_allowed"], 0.5),
    }
    mismatches = {
        k: {"got": float(got), "expected": exp}
        for k, (got, exp) in checks.items()
        if not math.isclose(float(got), exp, rel_tol=0.0, abs_tol=1e-12)
    }
    if mismatches:
        raise SystemExit(f"T1 synthetic self-check failed: {mismatches}")
    return {"status": "pass", "n_checks": len(checks), "mismatches": {}}


def rolling_5g(t1: pd.DataFrame) -> pd.DataFrame:
    """T2: per-team ORDER BY week, ROWS BETWEEN 4 PRECEDING AND CURRENT ROW."""
    metric_cols = [
        "epa_per_play_offense",
        "epa_per_play_defense_allowed",
        "pass_rate",
        "success_rate_offense",
        "success_rate_defense_allowed",
        "pressure_rate_allowed",
        "pressure_rate_generated",
        "red_zone_td_rate",
    ]
    frames = []
    for team, grp in t1.sort_values(["team", "season", "week"]).groupby("team"):
        g = grp.copy()
        g["games_in_window_5"] = g["week"].rolling(window=5, min_periods=1).count().astype(int)
        for col in metric_cols:
            g[f"{col}_5g"] = g[col].rolling(window=5, min_periods=1).mean()
        frames.append(g)
    return pd.concat(frames, ignore_index=True)


def lookup_t2(t2: pd.DataFrame, team: str, rating_week: int) -> dict | None:
    hit = t2[(t2["team"] == team) & (t2["week"] == rating_week)]
    if hit.empty:
        return None
    if len(hit) != 1:
        raise SystemExit(f"non-unique T2 row team={team} week={rating_week}")
    return hit.iloc[0].to_dict()


def main() -> None:
    games_path, all_games = load_games()
    w2_source = [
        r
        for r in all_games
        if int(r["season"]) == 2017 and int(r["week"]) == 2
    ]
    if len(w2_source) != 16:
        raise SystemExit(f"expected 16 W2 REG games in games.csv, got {len(w2_source)}")
    if any(not r.get("kickoff_utc") for r in w2_source):
        raise SystemExit("W2 row missing kickoff — exclude rule, do not impute")

    oos = load_oos_2016_2017()
    completed = build_completed(all_games, oos)

    source_rows = []
    exclusions = []
    for row in sorted(w2_source, key=lambda r: (r["kickoff_utc"], r["game_id"])):
        gid = row["game_id"]
        home = normalize_games_abbr(row["home"])
        away = normalize_games_abbr(row["away"])
        kick = row["kickoff_utc"]
        cutoff = parse_utc(kick)
        w_h, l_h, n_h = record_asof(completed, home, cutoff, 2017)
        w_a, l_a, n_a = record_asof(completed, away, cutoff, 2017)
        rec = {
            "game_id": gid,
            "season": 2017,
            "week": 2,
            "home_team": home,
            "away_team": away,
            "kickoff_utc": kick,
            "forecast_cutoff_utc": kick,
            "rating_week_contiguous": 1,
            "rest_days_et": rest_days_et(kick),
            "rest_days_utc_contrast": rest_days_utc(kick),
            "utc_et_dow_mismatch": rest_days_et(kick) != rest_days_utc(kick),
            "record_asof_home": f"{w_h}-{l_h}",
            "record_asof_away": f"{w_a}-{l_a}",
            "completed_same_season_games_home": n_h,
            "completed_same_season_games_away": n_a,
            "games_csv_record_entering_home": row["record_entering_home"],
            "games_csv_record_entering_away": row["record_entering_away"],
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
                PREDECLARED_EXCLUSIONS.get(gid)
                or f"{' / '.join(zero_side)} — 0 completed 2017 games as-of kickoff"
            )
            exclusions.append(
                {
                    "game_id": gid,
                    "reason": reason,
                    "predeclared": gid in PREDECLARED_EXCLUSIONS,
                    "completed_same_season_games_home": n_h,
                    "completed_same_season_games_away": n_a,
                    "home_team": home,
                    "away_team": away,
                    "rule": (
                        "exclude any W2 game where either side has 0 completed "
                        "same-season games as-of kickoff; leave MISSING, no fills"
                    ),
                }
            )
            continue
        source_rows.append(rec)

    missing_predeclared = set(PREDECLARED_EXCLUSIONS) - {e["game_id"] for e in exclusions}
    extra_exclusions = [
        e for e in exclusions if e["game_id"] not in PREDECLARED_EXCLUSIONS
    ]
    if missing_predeclared:
        raise SystemExit(f"predeclared exclusion not triggered: {missing_predeclared}")
    if extra_exclusions:
        raise SystemExit(f"unexpected extra exclusions: {extra_exclusions}")
    if len(source_rows) != 14:
        raise SystemExit(f"eligible N target 14, got {len(source_rows)}")

    eligible_ids = [r["game_id"] for r in source_rows]
    sel = selection_hash(eligible_ids)
    seal = {
        "sealed_before_rebuild": True,
        "sealed_before_pbp_open": True,
        "selection_hash_recipe": (
            "sha256(utf-8 of sorted canonical game_id list joined by \\n "
            "with trailing \\n)"
        ),
        "selection_hash": sel,
        "n": len(eligible_ids),
        "season": 2017,
        "week": 2,
        "exclusion_rule": (
            "SAMPLE_MANIFEST W2 games (16) minus any game where either side "
            "has 0 completed same-season games as-of kickoff"
        ),
        "predeclared_exclusions": PREDECLARED_EXCLUSIONS,
        "game_ids_sorted": sorted(eligible_ids),
    }
    seal_path = PACKET / "SELECTION_HASH_SEAL.json"
    if seal_path.exists():
        existing = json.loads(seal_path.read_text(encoding="utf-8"))
        if existing.get("selection_hash") != sel:
            raise SystemExit(
                "SELECTION_HASH_SEAL.json already written with a different hash — abort"
            )
    else:
        seal_path.write_text(json.dumps(seal, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"phase": "SEALED", "selection_hash": sel, "n": 14}, indent=2))

    # --- rebuild after seal ---
    if not PBP_PATH.is_file():
        raise SystemExit(f"PBP missing at {PBP_PATH}")
    pbp_digest = sha256_file(PBP_PATH)
    if pbp_digest != PBP_SHA256:
        raise SystemExit(f"PBP sha256 {pbp_digest} != pin {PBP_SHA256}")

    selfcheck = synthetic_t1_selfcheck()

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
    pbp = pd.read_parquet(PBP_PATH, columns=pbp_cols)
    if int(pbp["season"].dropna().astype(int).nunique()) != 1 or int(pbp["season"].iloc[0]) != 2017:
        raise SystemExit("PBP season != 2017 only")

    kickoff_by_gid = {
        r["game_id"]: r["kickoff_utc"]
        for r in all_games
        if int(r["season"]) == 2017 and int(r["week"]) <= 2
    }
    w1_games = [
        r
        for r in all_games
        if int(r["season"]) == 2017 and int(r["week"]) == 1
    ]
    w1_ids = {r["game_id"] for r in w1_games}
    min_target = min(parse_utc(r["kickoff_utc"]) for r in source_rows)
    max_w1 = max(parse_utc(r["kickoff_utc"]) for r in w1_games)
    if not (max_w1 < min_target):
        raise SystemExit(
            f"as-of fail: latest W1 kickoff {max_w1.isoformat()} not < earliest W2 eligible {min_target.isoformat()}"
        )

    plays = pbp[
        (pbp["season"] == 2017)
        & (pbp["season_type"] == "REG")
        & (pbp["week"] == 1)
        & pbp["week"].notna()
        & pbp["posteam"].notna()
        & pbp["play_type"].isin(["pass", "run"])
        & pbp["game_id"].isin(w1_ids)
    ].copy()
    if plays.empty:
        raise SystemExit("no W1 REG pass/run plays after filter")

    leaked = []
    consumed_game_ids = sorted(plays["game_id"].dropna().unique().tolist())
    for gid in consumed_game_ids:
        kick = kickoff_by_gid.get(gid)
        if kick is None:
            leaked.append({"game_id": gid, "reason": "consumed PBP game_id not in games.csv 2017 W1"})
            continue
        if parse_utc(kick) >= min_target:
            leaked.append(
                {
                    "game_id": gid,
                    "reason": "consumed kickoff >= earliest eligible W2 kickoff",
                    "kickoff_utc": kick,
                }
            )
    w2_in_consumed = [g for g in consumed_game_ids if "_02_" in g]
    if w2_in_consumed:
        leaked.append({"reason": "W2 game_id in consumed set", "game_ids": w2_in_consumed})
    if leaked:
        raise SystemExit(f"leakage test failed: {leaked}")

    t1 = t1_from_plays(plays)
    if len(t1) != 30:
        raise SystemExit(f"expected 30 W1 T1 team-rows (32-2 Irma), got {len(t1)}")
    if set(t1["team"]) & {"TB", "MIA"}:
        raise SystemExit("T1 includes TB/MIA — those teams had no 2017 W1 game")

    t2 = rolling_5g(t1)
    # W1-only frame: T2 CURRENT ROW == T1. Confirm 1-game window.
    if not (t2["games_in_window_5"] == 1).all():
        raise SystemExit("T2 window != 1 on W1-only frame")

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
    ]
    t1.to_csv(PACKET / "t1_team_week_2017_w1.csv", index=False, columns=t1_out_cols)

    games_out = []
    matrix = []
    status_counts: Counter[str] = Counter()
    complete_games = []
    partial_games = []

    t1_lineage = (
        "T1=nfl_dp_team_situational_weekly port of ingest.py offense/defense CTEs "
        f"@sha256 {INGEST_SHA256[:8]}… from owned PBP 2017 pin 84eacd96. "
        "play_type IN ('pass','run') — kneels/spikes/no_play/penalties excluded. "
        "T2=season-partitioned ROWS BETWEEN 4 PRECEDING AND CURRENT ROW "
        "(W1-only frame ⇒ 1-game window). "
        "T3 home/away = T2 at rating_week=1 (cf514078; never week-2 CURRENT ROW). "
        "T4 diffs per contract §4 / ingest matchup SQL. "
        "nflverse EPA/success are retro-scored by a later EP model — metric-definition "
        "look-ahead, not W2+ outcome leakage."
    )

    for rec in source_rows:
        gid = rec["game_id"]
        home = rec["home_team"]
        away = rec["away_team"]
        kick = rec["kickoff_utc"]
        rest_et = rec["rest_days_et"]
        rest_utc = rec["rest_days_utc_contrast"]
        h = lookup_t2(t2, home, 1)
        a = lookup_t2(t2, away, 1)
        if h is None or a is None:
            raise SystemExit(f"T2 missing for eligible game {gid} home={home} away={away}")

        # Per-target leakage: every consumed W1 game kickoff < this target.
        for side_row in (h, a):
            for cgid in str(side_row["source_game_ids"]).split("|"):
                ck = kickoff_by_gid.get(cgid)
                if ck is None or parse_utc(ck) >= parse_utc(kick):
                    raise SystemExit(
                        f"per-target leakage {gid}: consumed {cgid} kickoff={ck}"
                    )

        games_out.append(dict(rec))

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
                    "week": 2,
                    "home_team": home,
                    "away_team": away,
                    "field": field,
                    "status": status,
                    "reconstructed_value": value,
                    "source_path": source_path,
                    "source_sha256": source_sha256,
                    "source_sha8": source_sha256[:8],
                    "pregame_cutoff_utc": kick,
                    "rating_week": "1",
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
            "matchup_week": "2",
        }
        for field, value in identity.items():
            add(
                field,
                "DERIVED_PREGAME",
                source_path="data/ops/nfl-t4422u-walkforward-pergame-unblended-2013-2023/games.csv",
                source_sha256=GAMES_SHA256,
                lineage="sample identity from sealed games.csv pin 4fe1cdd7; kickoff known pregame",
                evidence=f"row present season=2017 week=2 game_id={gid}",
                notes="canonical game_id from walkforward export; not invented",
                value=value,
            )

        for side in ("home", "away"):
            add(
                f"rest_days_{side}",
                "DERIVED_PREGAME",
                source_path="services/model-service/src/services/nfl_offline_if_eval_w8.py:rest_days_from_schedule (ET) @155d3ca0; contract §3 rest_days_from_schedule",
                source_sha256=NFL_DATA_SHA256,
                lineage=(
                    "ET DOW heuristic as in v3 IF consume (Thu=4, Mon=6, else=7) "
                    "from target kickoff_utc. Same value both sides. "
                    "Not team-specific days-since-last-game. "
                    "Silent 7.0-on-missing-kickoff path not used (Z present)."
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
            off_i, def_i = team_strength_from_record(rec_wl)
            add(
                f"offense_index_{side}",
                "DERIVED_PREGAME",
                source_path=(
                    "data/ops/nfl-reopening-packet-20260916/historical-oos/"
                    "historical_oos_games.csv + games.csv kickoff join; "
                    "T5 team_strength_from_record"
                ),
                source_sha256=OOS_SHA256,
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
                source_sha256=OOS_SHA256,
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

        h_off = float(h["epa_per_play_offense_5g"])
        a_off = float(a["epa_per_play_offense_5g"])
        h_def = float(h["epa_per_play_defense_allowed_5g"])
        a_def = float(a["epa_per_play_defense_allowed_5g"])
        h_pr = float(h["pass_rate_5g"])
        a_pr = float(a["pass_rate_5g"])
        h_so = float(h["success_rate_offense_5g"])
        a_so = float(a["success_rate_offense_5g"])
        h_sd = float(h["success_rate_defense_allowed_5g"])
        a_sd = float(a["success_rate_defense_allowed_5g"])
        h_pg = float(h["pressure_rate_generated_5g"])
        a_pg = float(a["pressure_rate_generated_5g"])
        h_pa = float(h["pressure_rate_allowed_5g"])
        a_pa = float(a["pressure_rate_allowed_5g"])
        h_rz = float(h["red_zone_td_rate_5g"])
        a_rz = float(a["red_zone_td_rate_5g"])

        # Contract T3 signs (ingest matchup SQL):
        # diff_off = h.off - a.off
        # diff_def_allowed = a.def_allowed - h.def_allowed
        # diff_pressure_generated = h - a
        # diff_pressure_allowed = a - h
        # diff_rz = h - a
        # T4 success = mean( (h_so-a_so), (a_sd-h_sd) ) — both terms required
        diff_off = h_off - a_off
        diff_def = a_def - h_def
        diff_pg = h_pg - a_pg
        diff_pa = a_pa - h_pa
        diff_rz = h_rz - a_rz
        diff_sr = ((h_so - a_so) + (a_sd - h_sd)) / 2.0

        side_values = {
            "home_off_epa_5g": h_off,
            "away_off_epa_5g": a_off,
            "home_def_epa_allowed_5g": h_def,
            "away_def_epa_allowed_5g": a_def,
            "home_pass_rate_5g": h_pr,
            "away_pass_rate_5g": a_pr,
            "home_success_offense_5g": h_so,
            "away_success_offense_5g": a_so,
            "home_success_defense_allowed_5g": h_sd,
            "away_success_defense_allowed_5g": a_sd,
        }
        diff_values = {
            "matchup_diff_off_epa_5g": diff_off,
            "matchup_diff_def_epa_allowed_5g": diff_def,
            "matchup_diff_success_rate_5g": diff_sr,
            "matchup_diff_pressure_generated_5g": diff_pg,
            "matchup_diff_pressure_allowed_5g": diff_pa,
            "matchup_diff_red_zone_td_rate_5g": diff_rz,
        }
        for field, val in {**side_values, **diff_values}.items():
            if not _finite(val):
                add(
                    field,
                    "MISSING_RECORD",
                    source_path=str(PBP_PATH),
                    source_sha256=PBP_SHA256,
                    lineage=t1_lineage,
                    evidence=f"non-finite T1/T2 value for {field}",
                    notes="fail-closed; no default",
                )
                continue
            add(
                field,
                "DERIVED_PREGAME",
                source_path=str(PBP_PATH),
                source_sha256=PBP_SHA256,
                lineage=t1_lineage,
                evidence=(
                    f"T2 rating_week=1 games_in_window_5 home={int(h['games_in_window_5'])} "
                    f"away={int(a['games_in_window_5'])}; "
                    f"consumed_w1={h['source_game_ids']}|{a['source_game_ids']}; "
                    f"pbp_sha8=84eacd96 cutoff={kick}"
                ),
                notes=(
                    "pressure=(sack OR qb_hit)/play_type='pass' per T1 SQL; "
                    "RZ=plays with yardline_100<=20 (not drive-trips). "
                    "EPA retro-fit caveat labeled."
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
            partial_games.append(gid)

    manifest = {
        "artifact": "nfl-hist-bt-stage1b-w2-t4893u",
        "label": "EVAL_ONLY reconstruction audit — 2017 REG W2 first",
        "cert": 0,
        "stage": "1b",
        "scoring": False,
        "model_fit": False,
        "odds_api": False,
        "season": 2017,
        "weeks": [2],
        "n_source_w2": 16,
        "n_excluded": len(exclusions),
        "n": len(source_rows),
        "n_eligible": 14,
        "selection_hash": sel,
        "selection_hash_recipe": seal["selection_hash_recipe"],
        "selection_hash_sealed_before_rebuild": True,
        "selection_hash_sealed_before_pbp_open": True,
        "selection_hash_seal_path": "SELECTION_HASH_SEAL.json",
        "source_games_csv": "data/ops/nfl-t4422u-walkforward-pergame-unblended-2013-2023/games.csv",
        "source_games_csv_branch": "origin/cursor/t4422u-walkforward-pergame-export-f36b",
        "source_games_csv_tip": "82ffb211",
        "source_games_csv_sha256": GAMES_SHA256,
        "source_games_csv_sha8": "4fe1cdd7",
        "rehash_this_run": GAMES_SHA256,
        "rehash_match": True,
        "pbp_path": str(PBP_PATH),
        "pbp_sha256": PBP_SHA256,
        "pbp_sha8": "84eacd96",
        "pbp_rehash_this_run": pbp_digest,
        "pbp_rehash_match": pbp_digest == PBP_SHA256,
        "pbp_bytes": PBP_PATH.stat().st_size,
        "holdout_2024_25": "untouched",
        "exclusions": exclusions,
        "games": games_out,
        "pins": {
            "contract_sha8": "b41f4b43",
            "contract_sha256": CONTRACT_SHA256,
            "contract_path": (
                "data/ops/nfl-efficiency-2026-w1-w8-t4770u/"
                "ALEX_E1_EFFICIENCY_CONTRACT_t4770u_v2.md"
            ),
            "contract_branch": "origin/cursor/hift1-efficiency-recovery-f693",
            "pass_contract_sha8": "1a53bbd3",
            "pass_contract_sha256": PASS_CONTRACT_SHA256,
            "pass_contract_path": (
                "data/ops/nfl-efficiency-2026-w1-w8-t4770u/"
                "IMV_GRADE_t4770u_E1_EFFICIENCY_CONTRACT_v2.txt"
            ),
            "as_of_sha8": "cf514078",
            "as_of_status": "PASS_ASOF_BOUNDARY",
            "as_of_tip": "1010b86f",
            "as_of_module": "services/model-service/src/services/nfl_pregame_asof.py",
            "as_of_module_sha256": ASOF_MODULE_SHA256,
            "as_of_module_sha8": "7dc6afea",
            "source_only_sha8": "52d9e909",
            "source_only_sha256": SOURCE_PIN_SHA256,
            "source_only_commit": "1b39f4e9",
            "t1_ingest_sha256": INGEST_SHA256,
            "t1_ingest_sha8": INGEST_SHA256[:8],
            "pbp_sha256": PBP_SHA256,
            "pbp_sha8": "84eacd96",
        },
        "week2_note": (
            "16 REG source games. Eligible 14 after Irma TB/MIA exclusions. "
            "Cutoff = each game kickoff_utc. rating_week=1. "
            "T1 built from 2017 REG W1 PBP only (play_type pass/run). "
            "T5 uses W1 W-L (both sides have ≥1 completed 2017 game)."
        ),
    }
    (PACKET / "SAMPLE_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    (PACKET / "EXCLUSIONS.json").write_text(
        json.dumps(
            {
                "rule": seal["exclusion_rule"],
                "n_source_w2": 16,
                "n_excluded": len(exclusions),
                "n_eligible": 14,
                "exclusions": exclusions,
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
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(matrix)

    fields_per_game = len(REQUIRED_20) + len(REQUIRED_CONTEXT)
    if len(matrix) != 14 * fields_per_game:
        raise SystemExit(f"matrix cells {len(matrix)} != 14*27")

    by_field = defaultdict(Counter)
    for rec_row in matrix:
        by_field[rec_row["field"]][rec_row["status"]] += 1

    coverage = {
        "n_source_w2": 16,
        "n_excluded": len(exclusions),
        "excluded_game_ids": [e["game_id"] for e in exclusions],
        "n_games": len(source_rows),
        "n_eligible": 14,
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
        "partial_eligible_games": sorted(partial_games),
        "n_partial_eligible": len(partial_games),
        "by_field": {k: dict(v) for k, v in sorted(by_field.items())},
        "t1_w1_teams": int(t1["team"].nunique()),
        "t1_w1_rows": int(len(t1)),
        "pressure_rz_status": "DERIVED_PREGAME via T1 SQL as written (not a substitute)",
        "epa_retrofit_caveat": (
            "nflverse epa/success are retro-scored by a later-fitted EP model. "
            "Metric-definition look-ahead; not consumption of W2+ outcomes."
        ),
    }
    (PACKET / "COVERAGE.json").write_text(
        json.dumps(coverage, indent=2) + "\n", encoding="utf-8"
    )

    leakage = {
        "rule": "no consumed play/game with kickoff >= target kickoff",
        "consumed_pbp_game_ids": consumed_game_ids,
        "n_consumed_games": len(consumed_game_ids),
        "n_consumed_plays": int(len(plays)),
        "max_consumed_kickoff_utc": max(kickoff_by_gid[g] for g in consumed_game_ids),
        "min_eligible_target_kickoff_utc": min(r["kickoff_utc"] for r in source_rows),
        "max_w1_kickoff_lt_min_w2": True,
        "w2_plays_consumed": 0,
        "season_types_consumed": ["REG"],
        "weeks_consumed": [1],
        "leaked_rows": leaked,
        "play_filter": "play_type IN ('pass','run'); season_type=REG; week=1",
        "result": "PASS",
    }
    (PACKET / "LEAKAGE_AUDIT.json").write_text(
        json.dumps(leakage, indent=2) + "\n", encoding="utf-8"
    )

    t1_verify = {
        "contract_t1": "nfl_dp_team_situational_weekly columns cited in b41f4b43 §4",
        "producer": "services/model-service/data_platform_nfl/ingest.py offense/defense CTEs",
        "producer_sha256": INGEST_SHA256,
        "producer_sha8": INGEST_SHA256[:8],
        "numeric_2023_plus_gate": (
            "NOT POSSIBLE on this box: 2023 PBP not owned (pin unused); "
            "2025 situational dump is 2025 W1 only and 2025 PBP is not owned. "
            "No 2024–25 rows opened for values."
        ),
        "gate_used": "SQL-to-pandas code-review port + synthetic fixture (abs_tol 1e-12)",
        "synthetic_selfcheck": selfcheck,
        "pressure_definition": {
            "contract": "T1 column pressure_rate_allowed/generated from ingest.py",
            "sql": "(sack OR qb_hit) among play_type='pass' / count play_type='pass'",
            "qb_dropback_used_as_denominator": False,
            "hurries_required": False,
            "matched": True,
            "status": "DERIVED_PREGAME",
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
            "status": "DERIVED_PREGAME",
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
            "T2 window = last ≤5 PLAYED games. W2 rating_week=1 ⇒ 1-game window accepted."
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
                "selection_hash": sel,
                "n_eligible": 14,
                "n_complete_27_of_27": len(complete_games),
                "n_partial": len(partial_games),
                **coverage["status_counts"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
