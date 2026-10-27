#!/usr/bin/env python3
"""t4422u P3 — walk-forward per-game unblended engine export (2013–2023).

Research prep only. Does not open holdout, does not change frozen tests,
does not write production publish paths, does not fit candidates, does not
burn Odds API, does not enable IFB / injury / personnel overlays, and does
not invent HFA or sites.

Extends the existing calibration-audit / historical-OOS schedule spine:
  data/ops/nfl-reopening-packet-20260916/historical-oos/historical_oos_games.csv

RECORD path: walk-forward same-season W-L updated AFTER each game (identical
rule to backtest_record_vs_epa_signal.py). Strength indices use the exact
nfl_data.team_strength_from_record formula (copied here to avoid the
requests import). Engine call is simulate_nfl_game with market lines omitted
(unblended).

EPA path: not rematerialized. Trailing EPA rolling features are warehouse-
only (nfl_dp_team_rolling_features_weekly, present 2023–2026). This tip has
DATABASE_URL unset. Repo OOS already filed 2023 trailing *decompose*
spread/total (no win probs). Those decompose means are copied through as
repo-available EPA point estimates; epa_home_win_prob is MISSING.

Usage:
  python3 data/ops/nfl-team-simulator-calibration-audit/export_walkforward_pergame_2013_2023.py
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.request import urlopen
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[3]
MS_SRC = ROOT / "services" / "model-service"
sys.path.insert(0, str(MS_SRC))

from src.services.nfl_handicapping_framework import (  # noqa: E402
    NFL_HANDICAPPING_FRAMEWORK_VERSION,
    get_nfl_handicapping_config,
)
from src.services.nfl_simulator import (  # noqa: E402
    DEFAULT_NFL_MODEL_VERSION,
    NflGameInputs,
    simulate_nfl_game,
)

START_SEASON = 2013
END_SEASON = 2023  # inclusive; holdout 2024+ is NOT opened
SIMULATIONS_PER_GAME = 4000  # engine default; stable win-prob grain
EXPORT_ID = "t4422u-walkforward-pergame-unblended-2013-2023"
SEED_NAMESPACE = "t4422u-unblended-record"
NFLVERSE_GAMES_URL = "https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv"
# Clock / identity only — do not persist nflverse closes into this artifact (MS-9).
NFLVERSE_KEEP_COLS = (
    "game_id",
    "season",
    "game_type",
    "week",
    "gameday",
    "weekday",
    "gametime",
    "away_team",
    "home_team",
    "location",
    "old_game_id",
    "stadium",
)

OOS_SCHEDULE = (
    ROOT
    / "data"
    / "ops"
    / "nfl-reopening-packet-20260916"
    / "historical-oos"
    / "historical_oos_games.csv"
)
OUT_DIR = ROOT / "data" / "ops" / "nfl-t4422u-walkforward-pergame-unblended-2013-2023"

# Existing product alias (nfl_epa_authority.normalize_nfl_abbr). Used only to
# join nflverse game_id / clocks. Does not rewrite exported home/away labels.
_ABBR_TO_PRODUCT = {"LA": "LAR", "WAS": "WSH"}


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _write_sha256_sidecar(path: Path) -> Path:
    digest = _sha256_file(path)
    sidecar = path.with_name(path.name + ".sha256")
    sidecar.write_text(digest + "\n", encoding="utf-8")
    return sidecar


def _git_sha() -> str:
    try:
        return (
            subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                cwd=ROOT,
                stderr=subprocess.DEVNULL,
            )
            .decode()
            .strip()
        )
    except Exception:
        return "UNKNOWN"


def _git_sha_short() -> str:
    sha = _git_sha()
    return sha[:12] if sha != "UNKNOWN" else sha


def normalize_join_abbr(raw: str) -> str:
    team = str(raw or "").strip().upper()
    return _ABBR_TO_PRODUCT.get(team, team)


def team_strength_from_record(record_summary: Optional[str]) -> Tuple[float, float]:
    """Exact copy of src.services.nfl_data.team_strength_from_record."""
    if not record_summary or "-" not in record_summary:
        return 1.0, 1.0
    try:
        wins, losses = record_summary.split("-", 1)
        w = max(0.0, float(wins))
        l = max(0.0, float(losses))
        games = max(1.0, w + l)
        win_pct = w / games
    except Exception:
        return 1.0, 1.0
    offense = 0.90 + (0.22 * win_pct)
    defense = 0.92 + (0.20 * win_pct)
    return max(0.82, min(1.18, offense)), max(0.82, min(1.20, defense))


def _stable_seed(game_id: str) -> int:
    digest = hashlib.sha256(f"{game_id}|{SEED_NAMESPACE}".encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big") % (2**31)


def _kickoff_utc(gameday: str, gametime: str) -> Optional[str]:
    """nflverse gametime is Eastern even for London/Mexico (09:30 = 9:30 ET).

    Convert America/New_York → UTC. Do not invent a site-specific timezone.
    """
    if not gameday or not gametime:
        return None
    try:
        local = datetime.strptime(f"{gameday} {gametime}", "%Y-%m-%d %H:%M")
        aware = local.replace(tzinfo=ZoneInfo("America/New_York"))
        return aware.astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        return None


def _download_nflverse_games(dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    raw = Path("/tmp/nflverse-games-raw.csv")
    raw.parent.mkdir(parents=True, exist_ok=True)
    with urlopen(NFLVERSE_GAMES_URL, timeout=60) as resp:
        raw.write_bytes(resp.read())
    with raw.open(newline="", encoding="utf-8") as fh, dest.open(
        "w", newline="", encoding="utf-8"
    ) as out:
        reader = csv.DictReader(fh)
        writer = csv.DictWriter(out, fieldnames=list(NFLVERSE_KEEP_COLS), extrasaction="ignore")
        writer.writeheader()
        for row in reader:
            season = str(row.get("season") or "")
            try:
                year = int(season)
            except ValueError:
                continue
            if year < START_SEASON or year > END_SEASON:
                continue
            writer.writerow({k: row.get(k, "") for k in NFLVERSE_KEEP_COLS})
    return dest


def _load_nflverse_index(path: Path) -> Dict[Tuple[str, str, str, str], Dict[str, str]]:
    out: Dict[Tuple[str, str, str, str], Dict[str, str]] = {}
    with path.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            season = str(row.get("season") or "")
            if not season:
                continue
            try:
                year = int(season)
            except ValueError:
                continue
            if year < START_SEASON or year > END_SEASON:
                continue
            key = (
                season,
                str(row.get("week") or ""),
                normalize_join_abbr(str(row.get("home_team") or "")),
                normalize_join_abbr(str(row.get("away_team") or "")),
            )
            out[key] = row
    return out


def _epa_fields(oos: Dict[str, str]) -> Dict[str, str]:
    trailing_spread = (oos.get("trailing_spread") or "").strip()
    trailing_total = (oos.get("trailing_total") or "").strip()
    gap = (oos.get("trailing_epa_gap") or "").strip()
    season = int(oos["season"])
    if trailing_spread and trailing_total:
        return {
            "epa_trailing_spread_home": trailing_spread,
            "epa_trailing_total": trailing_total,
            "epa_home_win_prob": "",
            "epa_away_win_prob": "",
            "epa_status": "repo_decompose_only",
            "epa_blocker": (
                "2023 trailing EPA decompose means copied from "
                "historical_oos_games.csv (locked 2026-09-16 OOS). "
                "simulate_nfl_game EPA win probs MISSING: "
                "nfl_dp_team_rolling_features_weekly not mounted "
                "(DATABASE_URL unset); do not invert spread/total into indices."
            ),
        }
    blocker = gap or (
        "trailing_epa_pre_2023: nfl_dp_team_rolling_features_weekly only "
        "2023–2026; packaged priors cannot be built for test seasons ≤2023 "
        "(no prior-season situational in warehouse)."
        if season < 2023
        else "EPA rolling features unavailable on this tip (DATABASE_URL unset)."
    )
    return {
        "epa_trailing_spread_home": "",
        "epa_trailing_total": "",
        "epa_home_win_prob": "",
        "epa_away_win_prob": "",
        "epa_status": "MISSING",
        "epa_blocker": blocker,
    }


def _load_oos_rows() -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    with OOS_SCHEDULE.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            season = int(row["season"])
            if START_SEASON <= season <= END_SEASON:
                rows.append(row)
    rows.sort(
        key=lambda r: (
            int(r["season"]),
            str(r.get("game_date") or ""),
            int(r["week"]),
            str(r.get("key") or ""),
        )
    )
    return rows


FIELDNAMES = [
    "season",
    "week",
    "game_id",
    "home",
    "away",
    "kickoff_utc",
    "nflverse_gameday",
    "nflverse_gametime",
    "nflverse_location",
    "nflverse_join",
    "record_entering_home",
    "record_entering_away",
    "record_offense_index_home",
    "record_offense_index_away",
    "record_defense_index_home",
    "record_defense_index_away",
    "record_pred_margin_home",
    "record_spread_home",
    "record_total",
    "record_decomp_pred_margin_home",
    "record_decomp_spread_home",
    "record_decomp_total",
    "home_win_prob",
    "away_win_prob",
    "cover_prob",
    "over_prob",
    "epa_trailing_spread_home",
    "epa_trailing_total",
    "epa_home_win_prob",
    "epa_away_win_prob",
    "epa_status",
    "epa_blocker",
    "market_blend_applied",
    "injury_overlay",
    "ifb_overlay",
    "personnel_overlay",
    "rest_days_home",
    "rest_days_away",
    "simulations",
    "seed",
    "model_version",
    "framework_version",
    "pit_schedule_path",
    "pit_schedule_sha256",
    "pit_record_rule",
]


def main() -> None:
    if os.environ.get("NFL_WEEKLY_PROPS_LIVE"):
        # Export does not touch props; keep the env visible in the manifest only.
        pass

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    nflverse_path = OUT_DIR / "nflverse_games_2013_2023_join.csv"
    print(f"Downloading nflverse games.csv → {nflverse_path}")
    _download_nflverse_games(nflverse_path)
    nflverse_sha = _sha256_file(nflverse_path)
    _write_sha256_sidecar(nflverse_path)
    nflverse_idx = _load_nflverse_index(nflverse_path)
    print(f"  nflverse join keys={len(nflverse_idx)} sha256={nflverse_sha}")

    oos_rows = _load_oos_rows()
    oos_sha = _sha256_file(OOS_SCHEDULE)
    print(f"OOS schedule rows {START_SEASON}-{END_SEASON}: {len(oos_rows)}")

    cfg = get_nfl_handicapping_config()
    priors = cfg.get("priors") or {}
    tip = _git_sha()
    tip_short = _git_sha_short()

    record: Dict[Tuple[int, str], List[int]] = defaultdict(lambda: [0, 0])
    out_rows: List[Dict[str, Any]] = []
    join_hits = 0
    kickoff_hits = 0
    by_season: Dict[int, int] = defaultdict(int)
    epa_by_status: Dict[str, int] = defaultdict(int)

    for i, oos in enumerate(oos_rows, start=1):
        season = int(oos["season"])
        week = int(oos["week"])
        home = str(oos["home"])
        away = str(oos["away"])
        join_key = (
            str(season),
            str(week),
            normalize_join_abbr(home),
            normalize_join_abbr(away),
        )
        nv = nflverse_idx.get(join_key)
        if nv:
            join_hits += 1
            game_id = str(nv.get("game_id") or "")
            gameday = str(nv.get("gameday") or "")
            gametime = str(nv.get("gametime") or "")
            location = str(nv.get("location") or "")
            kickoff = _kickoff_utc(gameday, gametime)
            join_flag = "ok"
        else:
            game_id = f"{season}_{week:02d}_{away}_{home}"
            gameday = str(oos.get("game_date") or "")
            gametime = ""
            location = ""
            kickoff = None
            join_flag = "MISSING"

        if kickoff:
            kickoff_hits += 1

        home_wl = record[(season, home)]
        away_wl = record[(season, away)]
        home_rec = f"{home_wl[0]}-{home_wl[1]}"
        away_rec = f"{away_wl[0]}-{away_wl[1]}"
        rec_off_home, rec_def_home = team_strength_from_record(home_rec)
        rec_off_away, rec_def_away = team_strength_from_record(away_rec)
        seed = _stable_seed(game_id or f"{season}|{week}|{away}|{home}")

        inputs = NflGameInputs(
            game_id=game_id or f"{season}_{week:02d}_{away}_{home}",
            home_team=home,
            away_team=away,
            offense_index_home=rec_off_home,
            offense_index_away=rec_off_away,
            defense_index_home=rec_def_home,
            defense_index_away=rec_def_away,
            rest_days_home=7.0,
            rest_days_away=7.0,
            matchup_season=season,
            matchup_week=week,
            matchup_game_id=game_id or None,
            matchup_home_team=home,
            matchup_away_team=away,
        )
        projection = simulate_nfl_game(
            inputs,
            simulations=SIMULATIONS_PER_GAME,
            seed=seed,
            apply_linear_totals_calibration=True,
            totals_calibration=None,
            market_spread_home=None,
            market_total=None,
        )
        markets = projection["markets"]
        decomp = projection["decomposition"]
        blend = (projection.get("diagnostics") or {}).get("market_blend") or {}
        if blend.get("spread_applied") or blend.get("total_applied"):
            raise RuntimeError(f"market blend leaked on {game_id}")

        decomp_margin = float(decomp["predicted_margin"])
        decomp_total = float(decomp["predicted_total"])
        mc_spread = float(markets["spread_home"])
        mc_total = float(markets["total_mean"])
        epa = _epa_fields(oos)

        out_rows.append(
            {
                "season": season,
                "week": week,
                "game_id": game_id,
                "home": home,
                "away": away,
                "kickoff_utc": kickoff or "",
                "nflverse_gameday": gameday,
                "nflverse_gametime": gametime,
                "nflverse_location": location,
                "nflverse_join": join_flag,
                "record_entering_home": home_rec,
                "record_entering_away": away_rec,
                "record_offense_index_home": f"{rec_off_home:.6f}",
                "record_offense_index_away": f"{rec_off_away:.6f}",
                "record_defense_index_home": f"{rec_def_home:.6f}",
                "record_defense_index_away": f"{rec_def_away:.6f}",
                "record_pred_margin_home": f"{-mc_spread:.4f}",
                "record_spread_home": f"{mc_spread:.4f}",
                "record_total": f"{mc_total:.4f}",
                "record_decomp_pred_margin_home": f"{decomp_margin:.4f}",
                "record_decomp_spread_home": f"{-decomp_margin:.4f}",
                "record_decomp_total": f"{decomp_total:.4f}",
                "home_win_prob": f"{float(markets['home_win_prob']):.4f}",
                "away_win_prob": f"{float(markets['away_win_prob']):.4f}",
                "cover_prob": "",
                "over_prob": "",
                **epa,
                "market_blend_applied": "false",
                "injury_overlay": "false",
                "ifb_overlay": "false",
                "personnel_overlay": "false",
                "rest_days_home": "7.0",
                "rest_days_away": "7.0",
                "simulations": SIMULATIONS_PER_GAME,
                "seed": seed,
                "model_version": DEFAULT_NFL_MODEL_VERSION,
                "framework_version": NFL_HANDICAPPING_FRAMEWORK_VERSION,
                "pit_schedule_path": str(OOS_SCHEDULE.relative_to(ROOT)),
                "pit_schedule_sha256": oos_sha,
                "pit_record_rule": "walkforward_wl_after_game_same_season",
            }
        )
        by_season[season] += 1
        epa_by_status[epa["epa_status"]] += 1

        try:
            hs = float(oos["home_score"])
            aws = float(oos["away_score"])
        except (TypeError, ValueError):
            hs = aws = None
        if hs is not None and aws is not None:
            if hs > aws:
                home_wl[0] += 1
                away_wl[1] += 1
            elif aws > hs:
                away_wl[0] += 1
                home_wl[1] += 1

        if i % 400 == 0 or i == len(oos_rows):
            print(f"  ...{i}/{len(oos_rows)} games")

    games_path = OUT_DIR / "games.csv"
    with games_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDNAMES, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(out_rows)
    games_sha = _sha256_file(games_path)
    _write_sha256_sidecar(games_path)

    missing = {
        "artifact": EXPORT_ID,
        "authority": {
            "DECISION_RYAN_t4422u": "sha8 dbb35c04",
            "ALEX_PREDICTIVE_BASELINE_STATUS_t4422u_v1": "sha8 7f16f829",
            "IMV_gates_packet_t4422u": "sha8 7af96335",
            "note": "Authority filings not in this worktree; cited as given. Research prep only — adopt IMV gates before graded results.",
        },
        "probability_columns": {
            "home_win_prob": {
                "status": "PRESENT",
                "source": "simulate_nfl_game markets.home_win_prob (RECORD walk-forward, unblended)",
                "n": len(out_rows),
            },
            "away_win_prob": {
                "status": "PRESENT",
                "source": "simulate_nfl_game markets.away_win_prob (RECORD walk-forward, unblended)",
                "n": len(out_rows),
            },
            "cover_prob": {
                "status": "MISSING",
                "blocker": (
                    "nfl_simulator.simulate_nfl_game does not emit cover probability. "
                    "Cover would require a market spread line; this export is unblended "
                    "and does not pass market_spread_home (MS-9 nflverse close is Alex-side)."
                ),
            },
            "over_prob": {
                "status": "MISSING",
                "blocker": (
                    "nfl_simulator.simulate_nfl_game does not emit over probability. "
                    "Over would require a market total; this export is unblended and "
                    "does not pass market_total."
                ),
            },
            "epa_home_win_prob": {
                "status": "MISSING",
                "blocker": (
                    "Cannot call simulate_nfl_game on EPA indices for ≤2023 on this tip. "
                    "Code path: scripts/nfl/historical_market_backtest.py and "
                    "data/ops/nfl-team-simulator-calibration-audit/backtest_record_vs_epa_signal.py "
                    "LEFT JOIN nfl_dp_team_rolling_features_weekly. Data: that table is "
                    "warehouse-only (present 2023–2026 per HISTORICAL_OOS_DIAGNOSTIC). "
                    "DATABASE_URL unset; Railway MCP unauthenticated. Do not fabricate "
                    "EPA win probs from decompose spread/total."
                ),
                "repo_decompose_only_n": epa_by_status.get("repo_decompose_only", 0),
            },
        },
        "kickoff_utc": {
            "status": "PRESENT_WHEN_NFLVERSE_JOINED",
            "n_present": kickoff_hits,
            "n_missing": len(out_rows) - kickoff_hits,
            "convention": (
                "nflverse gameday+gametime interpreted as America/New_York "
                "(nflverse stores ET even for London 09:30). Neutral-site rows "
                "keep the same ET convention; no site-specific timezone invented."
            ),
        },
        "true_close_clv": {
            "status": "OUT_OF_SCOPE",
            "blocker": (
                "Owned odds lake / true-close JSONL not mounted (DATABASE_URL unset; "
                "no HD drive). Market columns intentionally omitted (MS-9 nflverse "
                "close is Alex-side diagnostic). No Odds API spend."
            ),
        },
        "epa_trailing_pre_2023": {
            "status": "MISSING",
            "blocker": (
                "nfl_dp_team_rolling_features_weekly only 2023–2026 "
                "(HISTORICAL_OOS_DIAGNOSTIC coverage.data_insufficient)."
            ),
        },
        "epa_packaged_le_2023": {
            "status": "MISSING",
            "blocker": (
                "nfl_dp_team_situational_weekly source=nflverse only present 2023–2025; "
                "cannot build season-start packaged priors for seasons before 2024."
            ),
        },
        "ifb_overlay": {
            "status": "OFF",
            "blocker": "No IFB overlay module on this tip; no IFB inputs passed.",
        },
    }
    missing_path = OUT_DIR / "MISSING.json"
    missing_path.write_text(json.dumps(missing, indent=2) + "\n", encoding="utf-8")
    _write_sha256_sidecar(missing_path)

    manifest = {
        "artifact": EXPORT_ID,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "git_sha": tip,
        "git_sha12": tip_short,
        "seasons": [START_SEASON, END_SEASON],
        "holdout_opened": False,
        "n_games": len(out_rows),
        "n_by_season": {str(k): by_season[k] for k in sorted(by_season)},
        "nflverse_join_hits": join_hits,
        "kickoff_utc_n": kickoff_hits,
        "epa_status_counts": dict(epa_by_status),
        "simulations_per_game": SIMULATIONS_PER_GAME,
        "seed_namespace": SEED_NAMESPACE,
        "engine": {
            "function": "src.services.nfl_simulator.simulate_nfl_game",
            "model_version": DEFAULT_NFL_MODEL_VERSION,
            "framework_version": NFL_HANDICAPPING_FRAMEWORK_VERSION,
            "home_field_points": priors.get("home_field_points"),
            "base_total_points": priors.get("base_total_points"),
            "base_score_stdev": priors.get("base_score_stdev"),
            "market_blend": False,
            "injury_overlay": False,
            "ifb_overlay": False,
            "personnel_overlay": False,
            "rest_days": 7.0,
            "totals_linear_cal": "identity (no historical-fit dict passed)",
        },
        "python": sys.version.split()[0],
        "inputs": {
            "oos_schedule": str(OOS_SCHEDULE.relative_to(ROOT)),
            "oos_schedule_sha256": oos_sha,
            "nflverse_games_url": NFLVERSE_GAMES_URL,
            "nflverse_games_sha256": nflverse_sha,
        },
        "outputs": {
            "games_csv": str(games_path.relative_to(ROOT)),
            "games_csv_sha256": games_sha,
        },
        "constraints": {
            "nfl_no_go": True,
            "coming_soon": True,
            "no_merge_deploy_spend": True,
            "no_holdout": True,
            "no_protected_results": True,
            "no_candidate_fitting": True,
            "no_frozen_test_changes": True,
        },
        "command": (
            "python3 data/ops/nfl-team-simulator-calibration-audit/"
            "export_walkforward_pergame_2013_2023.py"
        ),
    }
    manifest_path = OUT_DIR / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    _write_sha256_sidecar(manifest_path)

    readme = _readme(manifest, missing, games_sha)
    readme_path = OUT_DIR / "README.md"
    readme_path.write_text(readme, encoding="utf-8")
    _write_sha256_sidecar(readme_path)

    print(f"Wrote {games_path} n={len(out_rows)} sha256={games_sha}")
    print(f"by_season={dict(sorted(by_season.items()))}")
    print(f"nflverse_join={join_hits}/{len(out_rows)} kickoff_utc={kickoff_hits}")
    print(f"epa_status={dict(epa_by_status)}")


def _readme(manifest: Dict[str, Any], missing: Dict[str, Any], games_sha: str) -> str:
    by_season_lines = "\n".join(
        f"| {season} | {n} |"
        for season, n in manifest["n_by_season"].items()
    )
    eng = manifest["engine"]
    return f"""# t4422u — walk-forward per-game unblended engine export (2013–2023)

Research prep for Alex baseline. **Not a CLEAR. Not graded results.**  
NFL board **NO-GO**. Coming soon **ON**. No merge / deploy / spend.

Authority cited (filings not in this worktree):  
`DECISION_RYAN_t4422u` sha8 `dbb35c04` ·  
`ALEX_PREDICTIVE_BASELINE_STATUS_t4422u_v1.md` sha8 `7f16f829` ·  
IMV gates packet t4422u sha8 `7af96335` (adopt before graded results).

## Reproduce

```bash
python3 data/ops/nfl-team-simulator-calibration-audit/export_walkforward_pergame_2013_2023.py
```

| Pin | Value |
| --- | --- |
| Command | `{manifest["command"]}` |
| Git tip at generation | `{manifest["git_sha"]}` (`{manifest["git_sha12"]}`) |
| Python | `{manifest["python"]}` |
| Engine | `{eng["function"]}` |
| `model_version` | `{eng["model_version"]}` |
| `framework_version` | `{eng["framework_version"]}` |
| HFA (engine prior, not invented) | `{eng["home_field_points"]}` |
| Base total (engine prior) | `{eng["base_total_points"]}` |
| Simulations / game | `{manifest["simulations_per_game"]}` |
| Seed | sha256(`game_id\\|t4422u-unblended-record`)[:4] → int31 |
| IFB overlays | **OFF** (no IFB module on this tip; no inputs passed) |
| Injury overlays | **OFF** |
| Personnel overlays | **OFF** |
| Market blend | **OFF** (`market_spread_home` / `market_total` omitted) |
| Market columns | **not in this file** (nflverse close is Alex-side MS-9) |
| Holdout 2024+ | **not opened** |
| Rest days | `7.0` / `7.0` (same hardcoded rest as `historical_market_backtest.py` / record-vs-EPA audit; do not invent rest from incomplete clocks) |

## PIT inputs

1. Schedule / scores spine: `{manifest["inputs"]["oos_schedule"]}`  
   sha256 `{manifest["inputs"]["oos_schedule_sha256"]}`  
   Already-filed 2013–2026 completed games from the 2026-09-16 historical OOS packet (Railway `nfl_dp_schedules` read at that time). This export **filters to 2013–2023 inclusive**.
2. nflverse `games.csv` (free; no Odds spend) for `game_id` + gameday/gametime:  
   `{manifest["inputs"]["nflverse_games_url"]}`  
   sha256 `{manifest["inputs"]["nflverse_games_sha256"]}`  
   Join key = `(season, week, normalize_join_abbr(home), normalize_join_abbr(away))` using the existing product alias `LA→LAR`, `WAS→WSH` (`nfl_epa_authority.normalize_nfl_abbr`). Exported `home`/`away` stay as the OOS labels (WSH/LAR).
3. RECORD strength: walk-forward same-season W-L, updated **after** the game, ties ignored (same rule as `backtest_record_vs_epa_signal.py`). Indices = `team_strength_from_record` (`0.90+0.22*win_pct` / `0.92+0.20*win_pct`, clamped).

## Probability columns

| Column | Status | Notes |
| --- | --- | --- |
| `home_win_prob` / `away_win_prob` | **PRESENT** | RECORD unblended Monte Carlo (`simulate_nfl_game`) |
| `cover_prob` | **MISSING** | Engine does not emit cover; would need a market spread |
| `over_prob` | **MISSING** | Engine does not emit over; would need a market total |
| `epa_home_win_prob` / `epa_away_win_prob` | **MISSING** | See `MISSING.json` — rolling-feature table not mounted |
| `epa_trailing_spread_home` / `epa_trailing_total` | repo decompose only, 2023 | Copied from historical OOS; **not** engine win probs |

Point estimates: use `record_decomp_*` for the stable unblended RECORD mean (matches filed OOS `record_spread` / `record_total` on 0–0 week-1: −1.05 / 44.8435). `record_pred_margin_home` / `record_spread_home` / `record_total` are Monte Carlo means (simulation grain).

Sign: `*_spread_home` negative = home favored. `*_pred_margin_home` positive = home favored (home − away).

## Row counts by season

| Season | n |
| --- | ---: |
{by_season_lines}
| **Total** | **{manifest["n_games"]}** |

nflverse join hits: {manifest["nflverse_join_hits"]} / {manifest["n_games"]}.  
`kickoff_utc` present: {manifest["kickoff_utc_n"]}.

## Sealed files

| File | Role |
| --- | --- |
| `games.csv` | one row per game 2013–2023 |
| `games.csv.sha256` | `{games_sha}` |
| `manifest.json` | machine pins |
| `MISSING.json` | blockers (do not fabricate) |
| `nflverse_games_2013_2023_join.csv` | join input copy |

## True-close / CLV

**Out of scope.** Owned odds lake / true-close JSONL not mounted (`DATABASE_URL` unset). Market columns omitted on purpose.

## Non-actions honored

- No holdout open (2024+ rows not exported)
- No frozen-test edits
- No HFA / site invention (engine priors + nflverse ET clock convention only)
- No production publish path edits
- No candidate fitting / remat / overlay unlock
"""


if __name__ == "__main__":
    main()
