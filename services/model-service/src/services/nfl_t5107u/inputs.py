"""Prepare hashed 2020–23 schedule/results from the owned nflverse PBP archive.

Opens only permitted seasons (2020–2023). Never invents efficiency/index
formulas or Stage C fields. 2024–26 files are refused.
"""

from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

PERMITTED_SEASONS = (2020, 2021, 2022, 2023)
SEALED_SEASONS = (2024, 2025, 2026)
DEFAULT_ARCHIVE = Path("/Volumes/KosEdgeData/nflverse/archive/pbp/2026-11-01")
DEFAULT_OUT = Path("data/ops/nfl-forecast-builder-t5107u/inputs")
PUBLISHER_SHA_2023 = "4aeca98ebe6357c5f1a13165533007964605d1f17bd54561937769b952c67613"
GAMES_SHA256 = "4fe1cdd7f2eb616103ee6107e6a5cb0d5280f8006be420b606af0995351abef8"
OUTCOMES_SHA256 = "50bda875daa8bf1aadd56dd0a3bc19f1bb52dafe42b6a9c921a5816c7d7dc081"
QUOTE_MANIFEST_SHA256 = "6a1c1b378b91abd5e2ed185649536468192147057a2ea535a23e8ae5b14e6984"
QUOTE_MANIFEST_PATH = "data/ops/nfl-odds-reader-2020-2023-join-manifest.json"
SOURCE_SHA = {
    2020: "a7700b519197ec563aabf24ce7791896d8803f67cb73a45fcad0e8ae7db7245f",
    2021: "35f5d0b49905daa7d63ace9710346c48c7eb32ce0b8686629491954308013354",
    2022: "8aeb0e505d43950e09fec35a241a4e62720422454cdd3ac8f98c95650d54ab54",
    2023: PUBLISHER_SHA_2023,
}
EXTRACT_FIELDS = (
    "game_id",
    "season",
    "week",
    "season_type",
    "home",
    "away",
    "home_score",
    "away_score",
    "game_date",
    "start_time_raw",
    "rest_days_home",
    "rest_days_away",
)
# Efficiency / index fields are contract-required for IF produce-μ and are
# not derived here. Owner + dependent field are recorded as MISSING.
EFFICIENCY_FIELDS = (
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


class InputRefuse(ValueError):
    """Fail-closed input prep."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _parse_game_date(raw: str) -> date | None:
    text = str(raw or "").strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def extract_reg_games(path: Path, *, season: int) -> list[dict[str, Any]]:
    if season in SEALED_SEASONS:
        raise InputRefuse(f"refusing sealed season {season}")
    if season not in PERMITTED_SEASONS:
        raise InputRefuse(f"season {season} is not in the permitted 2020–23 window")
    if not path.is_file():
        raise InputRefuse(f"PBP missing: {path}")
    games: dict[str, dict[str, Any]] = {}
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        required = {
            "game_id",
            "season",
            "week",
            "season_type",
            "home_team",
            "away_team",
            "home_score",
            "away_score",
            "game_date",
            "start_time",
        }
        missing_cols = required - set(reader.fieldnames or [])
        if missing_cols:
            raise InputRefuse(f"{path.name} missing columns {sorted(missing_cols)}")
        for row in reader:
            if str(row.get("season_type") or "").upper() != "REG":
                continue
            try:
                row_season = int(row["season"])
            except (TypeError, ValueError) as exc:
                raise InputRefuse(f"non-integer season in {path.name}") from exc
            if row_season != season:
                raise InputRefuse(f"{path.name} contains season {row_season} != {season}")
            if row_season in SEALED_SEASONS:
                raise InputRefuse(f"sealed season leaked from {path.name}")
            gid = str(row.get("game_id") or "").strip()
            if not gid or gid in games:
                continue
            games[gid] = {
                "game_id": gid,
                "season": row_season,
                "week": int(row.get("week") or 0),
                "season_type": "REG",
                "home": str(row.get("home_team") or "").strip(),
                "away": str(row.get("away_team") or "").strip(),
                "home_score": row.get("home_score"),
                "away_score": row.get("away_score"),
                "game_date": str(row.get("game_date") or "").strip(),
                "start_time_raw": str(row.get("start_time") or "").strip(),
                "rest_days_home": "",
                "rest_days_away": "",
            }
    if not games:
        raise InputRefuse(f"no REG games extracted from {path.name}")
    return list(games.values())


def attach_rest_days(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Prior-game rest from game_date only (no invented kickoff TZ)."""
    by_team: dict[str, list[dict[str, Any]]] = defaultdict(list)
    out = [dict(row) for row in rows]
    for row in sorted(out, key=lambda r: (r["game_date"], r["game_id"])):
        gd = _parse_game_date(str(row["game_date"]))
        for side in ("home", "away"):
            team = str(row[side])
            prev = by_team[team][-1] if by_team[team] else None
            if gd is None or prev is None:
                row[f"rest_days_{side}"] = ""
            else:
                prev_d = _parse_game_date(str(prev["game_date"]))
                row[f"rest_days_{side}"] = "" if prev_d is None else str((gd - prev_d).days)
            by_team[team].append(row)
    return out


def _write_csv(path: Path, rows: list[Mapping[str, Any]]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(EXTRACT_FIELDS), extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in EXTRACT_FIELDS})
    return sha256_file(path)


def prepare_local_inputs(
    *,
    archive: Path | None = None,
    dest: Path | None = None,
) -> dict[str, Any]:
    root = Path(archive) if archive else DEFAULT_ARCHIVE
    out = Path(dest) if dest else DEFAULT_OUT
    if not root.is_dir():
        raise InputRefuse(f"archive not mounted: {root}")
    for season in SEALED_SEASONS:
        sealed = root / f"play_by_play_{season}.csv"
        if sealed.is_file():
            # Presence is fine; opening is not.
            pass
    extracted: list[dict[str, Any]] = []
    source_rows: list[dict[str, Any]] = []
    for season in PERMITTED_SEASONS:
        csv_path = root / f"play_by_play_{season}.csv"
        games = extract_reg_games(csv_path, season=season)
        extracted.extend(games)
        source_rows.append(
            {
                "season": season,
                "path": str(csv_path),
                "status": "available",
                "publisher_sha256": SOURCE_SHA[season],
                "n_reg_games": len(games),
            }
        )
    extracted = attach_rest_days(extracted)
    extracted.sort(key=lambda r: (int(r["season"]), int(r["week"]), r["game_id"]))
    all_path = out / "schedule_results_2020_2023.csv"
    y2023_path = out / "schedule_results_2023.csv"
    all_sha = _write_csv(all_path, extracted)
    rows_2023 = [r for r in extracted if int(r["season"]) == 2023]
    y2023_sha = _write_csv(y2023_path, rows_2023)

    bindings = {
        "schema_version": "nfl-t5108u-input-bindings-v1",
        "label": "RESEARCH_CONSUMED_RETRO",
        "cert_candidate": 0,
        "design_seal_is_forecast_freeze": False,
        "archive": str(root),
        "permitted_seasons": list(PERMITTED_SEASONS),
        "sealed_seasons_not_opened": list(SEALED_SEASONS),
        "prepared": [
            {
                "name": "schedule_results_2020_2023",
                "path": str(all_path),
                "status": "hashed",
                "sha256": all_sha,
                "n": len(extracted),
                "owner": "t5108u / owned nflverse PBP 2026-11-01 archive",
                "dependent_field": "game identity / scores / game_date / rest_days",
            },
            {
                "name": "schedule_results_2023",
                "path": str(y2023_path),
                "status": "hashed",
                "sha256": y2023_sha,
                "n": len(rows_2023),
                "owner": "t5108u / play_by_play_2023.csv (publisher 4aeca98e)",
                "dependent_field": "2023 REG scores + schedule (Q2 as-of / EVAL outcomes)",
            },
        ],
        "sources": source_rows,
        "availability": input_availability_table(all_sha, y2023_sha),
        "notes": [
            "Schedule/results only. No Stage C. No invented efficiency/index formulas.",
            "start_time in PBP is naive (e.g. '9/10/23, 13:02:43'); kickoff_utc is MISSING TZ.",
            "Design seal e5bb682d is not a forecast freeze.",
        ],
        "prepared_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    digest = sha256_bytes(
        json.dumps(bindings, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    )
    bindings["bindings_sha256"] = digest
    dest_json = out / "INPUT_BINDINGS.json"
    dest_json.write_text(json.dumps(bindings, indent=2) + "\n", encoding="utf-8")
    bindings["_path"] = str(dest_json)
    return bindings


def input_availability_table(all_sha: str = "", y2023_sha: str = "") -> list[dict[str, Any]]:
    return [
        {
            "input": "nflverse PBP archive 2020–23",
            "status": "available",
            "sha256_or_pin": "see SOURCE_SHA / MANIFEST.md",
            "owner": "owned archive /Volumes/KosEdgeData/nflverse/archive/pbp/2026-11-01/",
            "dependent_field": "schedule / scores extract",
        },
        {
            "input": "prepared schedule_results_2020_2023.csv",
            "status": "hashed" if all_sha else "available",
            "sha256_or_pin": all_sha,
            "owner": "t5108u inputs.py",
            "dependent_field": "game_id, season, week, home, away, scores, game_date, rest_days",
        },
        {
            "input": "prepared schedule_results_2023.csv",
            "status": "hashed" if y2023_sha else "available",
            "sha256_or_pin": y2023_sha,
            "owner": "t5108u inputs.py / 4aeca98e publisher",
            "dependent_field": "2023 REG outcomes + in-season Q2 as-of scores",
        },
        {
            "input": "games.csv 4fe1cdd7 kickoff_utc",
            "status": "hashed",
            "sha256_or_pin": GAMES_SHA256,
            "owner": "Q2 / t4422u games.csv (pin sidecar 8155fd194; Alex 69710b9c verified UTC Z for 2020–23)",
            "dependent_field": "kickoff_utc (NOT missing; explicit UTC Z for 2020–23; KO−60 cutoff)",
        },
        {
            "input": "outcomes extract 50bda875",
            "status": "hashed",
            "sha256_or_pin": OUTCOMES_SHA256,
            "owner": "Q2 outcomes_2013_2022_score_only.csv (stops 2022; pin sidecar 8155fd194)",
            "dependent_field": "pre-2023 scored history; 2023 REG scores from PBP extract 253e178b",
        },
        {
            "input": "quote/odds join manifest 2020–23",
            "status": "hashed",
            "sha256_or_pin": QUOTE_MANIFEST_SHA256,
            "owner": "t5105u reader join manifest",
            "dependent_field": QUOTE_MANIFEST_PATH,
        },
        {
            "input": "PBP start_time raw (not used for kickoff_utc)",
            "status": "available",
            "sha256_or_pin": "",
            "owner": "nflverse start_time is naive; kickoff_utc comes from games.csv 4fe1cdd7 (UTC Z)",
            "dependent_field": "start_time_raw only — kickoff_utc is bound from games.csv",
        },
        {
            "input": "b41f4b43 hist inputs / efficiency+index 5g",
            "status": "MISSING",
            "sha256_or_pin": "b41f4b43",
            "owner": "t4873u / paper §2 — do not invent formulas",
            "dependent_field": ",".join(EFFICIENCY_FIELDS),
        },
        {
            "input": "RECON_MATRIX_2020_2023_REG",
            "status": "MISSING",
            "sha256_or_pin": "b56be146 / 7be71acff (2017 only)",
            "owner": "IF recon matrix owner",
            "dependent_field": ",".join(EFFICIENCY_FIELDS),
        },
        {
            "input": "archived IF mus 2020–23 @ 6ca03716",
            "status": "MISSING",
            "sha256_or_pin": "6ca03716",
            "owner": "IF archive / 19c6a4607 consume lineage",
            "dependent_field": "if_margin_mu (archived)",
        },
        {
            "input": "frozen IF tree 6ca03716",
            "status": "available",
            "sha256_or_pin": "52d9e909 simulator / a0051cc4 framework",
            "owner": "git tip 6ca03716fe52930332d5ffba302c312a651980cc",
            "dependent_field": "produce-μ reconstruction",
        },
        {
            "input": "Stage C / scored columns",
            "status": "FORBIDDEN",
            "sha256_or_pin": "1ee90fac",
            "owner": "held — not a missing-to-invent source",
            "dependent_field": "none (refused)",
        },
    ]
