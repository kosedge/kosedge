#!/usr/bin/env python3
"""t4893u Stage-1b W3–W6 — SEAL ONLY.

Determines eligible 2017 REG W3–W6 game_ids from games.csv + OOS as-of
counts ONLY. Writes SELECTION_HASH_SEAL.json. Does not open PBP.
Does not import pandas / the W2 rebuild module (those pull PBP deps).

Transforms copied verbatim from
data/ops/nfl-hist-bt-stage1b-w2-t4893u/build_recon_t4893u.py:
  sha256_file, sha256_text, parse_utc, rest_days_et, rest_days_utc,
  normalize_games_abbr, selection_hash, load_games, load_oos_2016_2017,
  build_completed, record_asof.
No new selection transforms.
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
WEEKS = (3, 4, 5, 6)
EXPECTED_SOURCE = {3: 16, 4: 16, 5: 14, 6: 14}

W2_LINEAGE = {
    "eng_tip": "440314e43cba41311b10a54b9b11ecd1e7638653",
    "eng_tip_sha8": "440314e4",
    "alex_ro": "ALEX_RO_HIST_W2_t4893u_v1.md",
    "alex_ro_sha8": "91e2d7db",
    "grade": "PASS_RECON",
    "cos_accept": True,
    "pr": 669,
    "selection_hash": (
        "96a1317613d695fe027caf4a9230028480f64facfe460736702bd66328708640"
    ),
    "n_eligible": 14,
    "n_excluded": 2,
    "excluded_game_ids": ["2017_02_CHI_TB", "2017_02_MIA_LAC"],
    "packet": "data/ops/nfl-hist-bt-stage1b-w2-t4893u",
}


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


def eligible_for_weeks(all_games: list[dict], completed: list[dict]):
    by_week: dict[int, dict] = {}
    for week in WEEKS:
        source = [
            r
            for r in all_games
            if int(r["season"]) == 2017 and int(r["week"]) == week
        ]
        expect = EXPECTED_SOURCE[week]
        if len(source) != expect:
            raise SystemExit(
                f"expected {expect} 2017 REG W{week} games in games.csv, got {len(source)}"
            )
        if any(not r.get("kickoff_utc") for r in source):
            raise SystemExit(
                f"W{week} row missing kickoff — exclude rule, do not impute"
            )

        source_rows = []
        exclusions = []
        for row in sorted(source, key=lambda r: (r["kickoff_utc"], r["game_id"])):
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
                "epa_status_games_csv": row["epa_status"],
                "epa_blocker_games_csv": row["epa_blocker"],
            }
            if n_h < 1 or n_a < 1:
                zero_side = []
                if n_h < 1:
                    zero_side.append(f"{home} home")
                if n_a < 1:
                    zero_side.append(f"{away} away")
                exclusions.append(
                    {
                        "game_id": gid,
                        "reason": (
                            f"{' / '.join(zero_side)} — 0 completed 2017 games "
                            "as-of kickoff"
                        ),
                        "predeclared": False,
                        "completed_same_season_games_home": n_h,
                        "completed_same_season_games_away": n_a,
                        "home_team": home,
                        "away_team": away,
                        "week": week,
                        "rule": (
                            "exclude any game where either side has 0 completed "
                            "same-season games as-of kickoff; leave MISSING, no fills"
                        ),
                    }
                )
                continue
            source_rows.append(rec)

        by_week[week] = {
            "n_source": len(source),
            "n_excluded": len(exclusions),
            "n_eligible": len(source_rows),
            "exclusions": exclusions,
            "source_rows": source_rows,
            "game_ids_sorted": sorted(r["game_id"] for r in source_rows),
            "selection_hash": selection_hash([r["game_id"] for r in source_rows]),
        }

    combined_ids: list[str] = []
    for week in WEEKS:
        combined_ids.extend(by_week[week]["game_ids_sorted"])
    combined_hash = selection_hash(combined_ids)
    return by_week, combined_ids, combined_hash


def build_seal(by_week, combined_ids, combined_hash) -> dict:
    recipe = (
        "sha256(utf-8 of sorted canonical game_id list joined by \\n "
        "with trailing \\n)"
    )
    per_week = {}
    for week in WEEKS:
        blk = by_week[week]
        per_week[str(week)] = {
            "n_source": blk["n_source"],
            "n_excluded": blk["n_excluded"],
            "n_eligible": blk["n_eligible"],
            "selection_hash": blk["selection_hash"],
            "game_ids_sorted": blk["game_ids_sorted"],
            "excluded_game_ids": [e["game_id"] for e in blk["exclusions"]],
        }
    return {
        "sealed_before_rebuild": True,
        "sealed_before_pbp_open": True,
        "pbp_opened_at_seal": False,
        "selection_hash_recipe": recipe,
        "season": 2017,
        "weeks": list(WEEKS),
        "exclusion_rule": (
            "SAMPLE_MANIFEST W3–W6 games minus any game where either side "
            "has 0 completed same-season games as-of kickoff"
        ),
        "n_source": sum(by_week[w]["n_source"] for w in WEEKS),
        "n_excluded": sum(by_week[w]["n_excluded"] for w in WEEKS),
        "n_eligible": sum(by_week[w]["n_eligible"] for w in WEEKS),
        "selection_hash_combined": combined_hash,
        "game_ids_sorted_combined": sorted(combined_ids),
        "per_week": per_week,
        "w2_lineage": W2_LINEAGE,
        "method": (
            "Identical to W2 t4893u builder: games.csv 4fe1cdd7 + OOS 1ee90fac "
            "as-of counts only. No PBP. Hash recipe unchanged."
        ),
        "sealed_at_utc": datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
    }


def main() -> None:
    _games_path, all_games = load_games()
    oos = load_oos_2016_2017()
    completed = build_completed(all_games, oos)
    by_week, combined_ids, combined_hash = eligible_for_weeks(all_games, completed)
    seal = build_seal(by_week, combined_ids, combined_hash)
    seal_path = PACKET / "SELECTION_HASH_SEAL.json"
    if seal_path.exists():
        existing = json.loads(seal_path.read_text(encoding="utf-8"))
        keys = (
            "selection_hash_combined",
            "game_ids_sorted_combined",
            "n_eligible",
            "n_excluded",
            "n_source",
            "per_week",
            "selection_hash_recipe",
            "exclusion_rule",
        )
        for key in keys:
            if existing.get(key) != seal.get(key):
                raise SystemExit(
                    f"SELECTION_HASH_SEAL.json already written with different {key} — abort"
                )
        print(
            json.dumps(
                {
                    "phase": "SEAL_VERIFIED",
                    "selection_hash_combined": combined_hash,
                    "n_eligible": seal["n_eligible"],
                    "n_excluded": seal["n_excluded"],
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
                "selection_hash_combined": combined_hash,
                "n_eligible": seal["n_eligible"],
                "n_excluded": seal["n_excluded"],
                "per_week": {
                    w: {
                        "n": by_week[int(w)]["n_eligible"],
                        "hash": by_week[int(w)]["selection_hash"],
                        "n_excl": by_week[int(w)]["n_excluded"],
                    }
                    for w in seal["per_week"]
                },
                "pbp_opened": False,
                "path": str(seal_path),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    sys.exit(main())
