#!/usr/bin/env python3
"""t4885u Stage-1 reconstruction — sample seal + field audit. No scoring.

Rebuilds b41f4b43 IF input-contract availability for 2017 REG W1–W2 only.
Does not invoke Independent Fair. Does not fit. Does not touch 2024–25 rows.
Zero Odds/API.
"""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

REPO = Path(__file__).resolve().parents[3]
PACKET = Path(__file__).resolve().parent
GAMES_CSV = (
    REPO
    / "data/ops/nfl-t4422u-walkforward-pergame-unblended-2013-2023/games.csv"
)
# Fallback: extracted pin sitting outside this worktree (walkforward branch object).
GAMES_CSV_FALLBACK = Path("/tmp/hist-bt-parents/walkforward/games.csv")
OOS_CSV = (
    REPO
    / "data/ops/nfl-reopening-packet-20260916/historical-oos/historical_oos_games.csv"
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
T1_T4_FIELDS = tuple(f for f in REQUIRED_20 if f not in T5_FIELDS)
ET = ZoneInfo("America/New_York")

# Franchise rename only — recorded as identity evidence, never applied as a fill.
FRANCHISE_PRIOR = {"LAC": "SD"}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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
    """v3 consume heuristic (155d3ca0): America/New_York kick local DOW.

    Thu=4, Mon=6, else=7. No silent 7.0 on missing kickoff — caller must have Z.
    """
    dt = parse_utc(kickoff_utc).astimezone(ET)
    dow = dt.weekday()
    if dow == 3:
        return 4.0
    if dow == 0:
        return 6.0
    return 7.0


def rest_days_utc(kickoff_utc: str) -> float:
    """Pinned nfl_data.rest_days_from_schedule (UTC DOW). Contrast only."""
    dow = parse_utc(kickoff_utc).weekday()
    if dow == 3:
        return 4.0
    if dow == 0:
        return 6.0
    return 7.0


def team_strength_from_record(record_summary: str) -> tuple[float, float]:
    """Exact nfl_data.team_strength_from_record T5 (no 1.0 silent path used)."""
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
    """Read OOS only for season∈{2016,2017}. Do not materialize ≥2024 rows."""
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
    # Prove holdout rows exist in the file but were not copied into the working set.
    if any(s >= 2024 for s in seasons_seen):
        # counted only — not opened into `kept`
        pass
    return kept


def normalize_abbr(token: str) -> str:
    return {"LA": "LAR", "WAS": "WSH", "SD": "SD"}.get(token, token)


def selection_hash(game_ids: list[str]) -> str:
    payload = "\n".join(sorted(game_ids)) + "\n"
    return sha256_text(payload)


def main() -> None:
    games_path, all_games = load_games()
    sample = [
        r
        for r in all_games
        if int(r["season"]) == 2017 and int(r["week"]) in (1, 2)
    ]
    if any(not r.get("kickoff_utc") for r in sample):
        raise SystemExit("sample row missing kickoff — exclude rule, do not impute")
    postseason = [r for r in sample if int(r["week"]) > 18]
    if postseason:
        raise SystemExit("postseason leaked into sample")

    game_ids = [r["game_id"] for r in sample]
    sel = selection_hash(game_ids)
    # Seal selection hash to disk BEFORE matrix rebuild.
    seal = {
        "sealed_before_rebuild": True,
        "selection_hash_recipe": (
            "sha256(utf-8 of sorted canonical game_id list joined by \\n "
            "with trailing \\n)"
        ),
        "selection_hash": sel,
        "n": len(sample),
        "game_ids_sorted": sorted(game_ids),
    }
    (PACKET / "SELECTION_HASH_SEAL.json").write_text(
        json.dumps(seal, indent=2) + "\n", encoding="utf-8"
    )

    oos = load_oos_2016_2017()
    oos_by_key = {}
    for row in oos:
        key = (
            int(float(row["season"])),
            int(float(row["week"])),
            normalize_abbr(row["home"]),
            normalize_abbr(row["away"]),
        )
        oos_by_key[key] = row

    # Completed REG games with scores, keyed for as-of W-L.
    completed = []
    for row in all_games:
        season = int(row["season"])
        week = int(row["week"])
        if season not in (2016, 2017) or week > 17:
            continue
        oos_row = oos_by_key.get(
            (season, week, normalize_abbr(row["home"]), normalize_abbr(row["away"]))
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
                "home": normalize_abbr(row["home"]),
                "away": normalize_abbr(row["away"]),
                "kickoff_utc": row["kickoff_utc"],
                "home_score": float(hs),
                "away_score": float(aws),
            }
        )

    def record_asof(team: str, cutoff: datetime, season: int) -> tuple[int, int, int]:
        """Same-season W-L from completed games with kickoff < cutoff. Ties ignored."""
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
            won = (
                (team == g["home"] and g["home_score"] > g["away_score"])
                or (team == g["away"] and g["away_score"] > g["home_score"])
            )
            if won:
                w += 1
            else:
                l += 1
        return w, l, n

    prior_2016_reg = [
        r for r in all_games if int(r["season"]) == 2016 and int(r["week"]) <= 17
    ]
    teams_2016 = {normalize_abbr(r["home"]) for r in prior_2016_reg} | {
        normalize_abbr(r["away"]) for r in prior_2016_reg
    }

    games_out = []
    matrix = []
    status_counts: Counter[str] = Counter()

    for row in sorted(sample, key=lambda r: (int(r["week"]), r["kickoff_utc"], r["game_id"])):
        gid = row["game_id"]
        week = int(row["week"])
        home = normalize_abbr(row["home"])
        away = normalize_abbr(row["away"])
        kick = row["kickoff_utc"]
        cutoff = parse_utc(kick)
        rest_et = rest_days_et(kick)
        rest_utc = rest_days_utc(kick)
        rating_week = week - 1  # 0 for W1 — contiguous pipeline has no same-season rating week
        w_h, l_h, n_h = record_asof(home, cutoff, 2017)
        w_a, l_a, n_a = record_asof(away, cutoff, 2017)
        rec_h = f"{w_h}-{l_h}"
        rec_a = f"{w_a}-{l_a}"

        games_out.append(
            {
                "game_id": gid,
                "season": 2017,
                "week": week,
                "home_team": home,
                "away_team": away,
                "kickoff_utc": kick,
                "forecast_cutoff_utc": kick,
                "rating_week_contiguous": rating_week if rating_week >= 1 else None,
                "rest_days_et": rest_et,
                "rest_days_utc_contrast": rest_utc,
                "utc_et_dow_mismatch": rest_et != rest_utc,
                "record_asof_home": rec_h,
                "record_asof_away": rec_a,
                "completed_same_season_games_home": n_h,
                "completed_same_season_games_away": n_a,
                "games_csv_record_entering_home": row["record_entering_home"],
                "games_csv_record_entering_away": row["record_entering_away"],
                "epa_status_games_csv": row["epa_status"],
                "epa_blocker_games_csv": row["epa_blocker"],
            }
        )

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
                    "rating_week": "" if rating_week < 1 else str(rating_week),
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
                source_path=str(games_path.relative_to(REPO))
                if games_path.is_relative_to(REPO)
                else "data/ops/nfl-t4422u-walkforward-pergame-unblended-2013-2023/games.csv",
                source_sha256=GAMES_SHA256,
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

        # T5 offense/defense index
        for side, team, n_played, rec in (
            ("home", home, n_h, rec_h),
            ("away", away, n_a, rec_a),
        ):
            prior_token = FRANCHISE_PRIOR.get(team, team)
            prior_avail = prior_token in teams_2016
            if n_played < 1:
                add(
                    f"offense_index_{side}",
                    "MISSING_RECORD",
                    source_path="contract T5 team_strength_from_record (same-season W-L)",
                    source_sha256=CONTRACT_SHA256,
                    lineage=(
                        "T5 is same-season completed W-L. 0 completed 2017 games "
                        "as-of cutoff. 0-0→0.90/0.92 empty mapping is NOT a "
                        "prior-season/preseason baseline and is not applied. "
                        "2016 REG schedule exists in games.csv but prior-season "
                        "W-L substitution is not an approved T5 transform "
                        "(contract §5 analog: no prior-season substitution)."
                    ),
                    evidence=(
                        f"completed_2017_games={n_played}; "
                        f"2016_REG_row_for_{prior_token}={prior_avail}"
                        + (
                            f" (2017 {team} ← 2016 {prior_token} franchise rename; "
                            "mapping recorded, not applied)"
                            if team in FRANCHISE_PRIOR
                            else ""
                        )
                    ),
                    notes=(
                        "Week-1 / no-W1-game (TB, MIA) T5 left MISSING_RECORD. "
                        "Do not use later-2017. Do not use 2026 ratings."
                    ),
                )
                add(
                    f"defense_index_{side}",
                    "MISSING_RECORD",
                    source_path="contract T5 team_strength_from_record (same-season W-L)",
                    source_sha256=CONTRACT_SHA256,
                    lineage=(
                        "Same as offense_index — 0 completed same-season games."
                    ),
                    evidence=(
                        f"completed_2017_games={n_played}; "
                        f"2016_REG_row_for_{prior_token}={prior_avail}"
                    ),
                    notes="paired with offense_index on this side",
                )
            else:
                off, deff = team_strength_from_record(rec)
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
                        f"record_asof={rec} n={n_played} cutoff={kick}; "
                        f"games.csv entering={row[f'record_entering_{side}']}"
                    ),
                    notes="recomputed as-of; not a 2026 panel index",
                    value=f"{off:.6f}",
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
                        f"record_asof={rec} n={n_played} cutoff={kick}; "
                        f"games.csv entering={row[f'record_entering_{side}']}"
                    ),
                    notes="recomputed as-of; not a 2026 panel index",
                    value=f"{deff:.6f}",
                )

        t1_note = (
            "T1 source nfl_dp_team_situational_weekly has no 2016–2017 rows on this box. "
            "Owned dump 20260705T201049Z is 2025 W1 only (forbidden modern). "
            "Rolling features materialize 2023–2026 only. "
            "games.csv epa_status=MISSING blocker=rolling_features_unavailable_pre_2023. "
            "historical_oos packaged_epa_gap=no_prior_season_situational_for_packaged_priors. "
            "PBP→T1 mapping UNVERIFIED — not invented. "
            "2026 through-W7 panel 340a06dd not used."
        )
        if week == 1:
            t1_note += (
                " Week 1 contiguous rating_week does not exist (cf514078 / "
                "contiguous_pregame_rating_week). Prior-season/preseason T1 "
                "baseline not on box → MISSING_RECORD. Later-2017 not used."
            )
        else:
            t1_note += (
                " Week 2 rating_week=1 requires 2017 W1 T1 rows; those records "
                "are absent. Cutoff is this game's kickoff. No silent 5g fill "
                "from scores-only."
            )
        for field in T1_T4_FIELDS:
            add(
                field,
                "MISSING_RECORD",
                source_path="nfl_dp_team_situational_weekly / rolling 5g / matchup T1–T4",
                source_sha256=CONTRACT_SHA256,
                lineage=(
                    "Contract T1–T4: situational weekly → season-partitioned "
                    "ROWS 4 PRECEDING + CURRENT → matchup diffs. Source tables "
                    "not present for 2017 as-of this cutoff."
                ),
                evidence=(
                    f"games.csv epa_status={row['epa_status']} "
                    f"epa_blocker={row['epa_blocker']}; "
                    "owned situational seasons={2025}; "
                    "efficiency backbone rolling seasons=2023–2026"
                ),
                notes=t1_note,
            )

    # SAMPLE_MANIFEST sealed (hash already written)
    manifest = {
        "artifact": "nfl-hist-bt-stage1-t4885u",
        "label": "EVAL_ONLY reconstruction audit",
        "cert": 0,
        "stage": 1,
        "scoring": False,
        "model_fit": False,
        "odds_api": False,
        "season": 2017,
        "weeks": [1, 2],
        "n": len(sample),
        "n_week1": sum(1 for r in sample if int(r["week"]) == 1),
        "n_week2": sum(1 for r in sample if int(r["week"]) == 2),
        "selection_hash": sel,
        "selection_hash_recipe": seal["selection_hash_recipe"],
        "selection_hash_sealed_before_rebuild": True,
        "selection_hash_seal_path": "SELECTION_HASH_SEAL.json",
        "source_games_csv": "data/ops/nfl-t4422u-walkforward-pergame-unblended-2013-2023/games.csv",
        "source_games_csv_branch": "origin/cursor/t4422u-walkforward-pergame-export-f36b",
        "source_games_csv_tip": "82ffb211",
        "source_games_csv_sha256": GAMES_SHA256,
        "source_games_csv_sha8": "4fe1cdd7",
        "rehash_this_run": GAMES_SHA256,
        "rehash_match": True,
        "holdout_2024_25": "untouched",
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
        },
        "week1_note": (
            "15 REG games (MIA@TB postponed — not in pin; not added). "
            "Contiguous rating_week absent. Prior-season/preseason T1/T5 "
            "baseline not applied."
        ),
        "week2_note": (
            "16 REG games. Cutoff = each game kickoff_utc. rating_week=1. "
            "T1 2017 W1 situational rows absent. T5 uses W1 W-L only when "
            "the team has ≥1 completed 2017 game before cutoff (TB/MIA do not)."
        ),
    }
    (PACKET / "SAMPLE_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
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

    # coverage numbers
    by_game = defaultdict(Counter)
    for rec in matrix:
        by_game[rec["game_id"]][rec["status"]] += 1
    fields_per_game = len(REQUIRED_20) + len(REQUIRED_CONTEXT)
    fully = [
        gid
        for gid, c in by_game.items()
        if c["DERIVED_PREGAME"] == fields_per_game and c["MISSING_RECORD"] == 0
    ]
    none_derived_eff = [
        gid
        for gid, c in by_game.items()
        if c["MISSING_RECORD"] > 0 and c["DERIVED_PREGAME"] > 0
    ]
    coverage = {
        "n_games": len(sample),
        "fields_per_game": fields_per_game,
        "n_cells": len(matrix),
        "status_counts": dict(status_counts),
        "derived_pregame": status_counts["DERIVED_PREGAME"],
        "missing_record": status_counts["MISSING_RECORD"],
        "out_of_contract": status_counts["OUT_OF_CONTRACT"],
        "excluded": status_counts["EXCLUDED"],
        "pct_fields_present": round(
            100.0 * status_counts["DERIVED_PREGAME"] / len(matrix), 4
        ),
        "fully_reconstructable_games": fully,
        "n_fully_reconstructable": len(fully),
        "n_partially_reconstructable": len(none_derived_eff),
        "partially_reconstructable_games": sorted(none_derived_eff),
        "week1_prior_season": {
            "2016_reg_games_in_games_csv": len(prior_2016_reg),
            "2016_reg_teams": sorted(teams_2016),
            "2016_reg_team_n": len(teams_2016),
            "franchise_rename_unmapped_as_fill": {"LAC": "SD"},
            "t1_situational_2016_on_box": False,
            "t1_situational_2017_on_box": False,
            "preseason_efficiency_baseline_2016_on_box": False,
            "week1_t5_applied": False,
            "week1_t1_t4_applied": False,
            "handling": (
                "MISSING_RECORD for Week-1 T5 and all T1–T4. 2016 REG schedule "
                "is present (availability evidence) but not consumed as a fill."
            ),
        },
    }
    (PACKET / "COVERAGE.json").write_text(
        json.dumps(coverage, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"selection_hash": sel, "n": len(sample), **coverage["status_counts"]}, indent=2))


if __name__ == "__main__":
    main()
