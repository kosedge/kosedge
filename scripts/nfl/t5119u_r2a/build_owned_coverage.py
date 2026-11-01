#!/usr/bin/env python3
"""t5119u R2-A — outcome-blind owned NFL odds coverage.

Read-only sources. No scoring. No EVAL claim. No new pulls.
Does not touch t5116u ONE_RUN / ONE_EXEC_RESULT.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import sqlite3
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import median
from typing import Any, Dict, Iterable, Iterator, List, Mapping, Optional, Sequence, Tuple

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))

from nfl_odds_reader import (  # noqa: E402
    PERMITTED_SEASONS,
    canonical_market,
    classify_market,
    iter_jsonl_quotes,
    iter_open_close_csv_quotes,
    join_quotes_at_cutoff,
    normalize_quote_timestamp,
    resolve_team_identity,
    season_from_commence,
    timestamp_to_iso,
)

WORK = ROOT / ".cos-work" / "t5119u_r2"
PINS = WORK / "pins"
EXTRACTS = WORK / "extracts"
RECEIPTS = WORK / "receipts"
OUT = ROOT / "data" / "ops" / "nfl-t5119u-r2-owned-coverage"
OPS_ADDENDUM = ROOT / "ops" / "CURSOR_ADDENDUM_t5119u_R2A_COVERAGE_v1.md"

HD_SQLITE = Path("/Volumes/KosEdgeData/clean/odds/gapfill/odds_gapfill.sqlite")
HD_CSV = Path("/Volumes/KosEdgeData/clean/odds/americanfootball_nfl/open_close/lines.csv")
HD_JSONL = {
    2020: Path("/Volumes/KosEdgeData/clean/odds/nfl/snapshots-2020-20260806.jsonl"),
    2021: Path("/Volumes/KosEdgeData/clean/odds/nfl/snapshots-2021-20260806.jsonl"),
    2022: Path("/Volumes/KosEdgeData/clean/odds/nfl/snapshots-2022-20260806.jsonl"),
    2023: Path("/Volumes/KosEdgeData/clean/odds/nfl/snapshots-2023-20260806.jsonl"),
}
HD_LAKE = {
    2020: Path("/Volumes/KosEdgeData/clean/odds/nfl/lake/snapshots-2020.parquet"),
    2021: Path("/Volumes/KosEdgeData/clean/odds/nfl/lake/snapshots-2021.parquet"),
    2022: Path("/Volumes/KosEdgeData/clean/odds/nfl/lake/snapshots-2022.parquet"),
    2023: Path("/Volumes/KosEdgeData/clean/odds/nfl/lake/snapshots-2023.parquet"),
}
HD_LAKE_INV = Path("/Volumes/KosEdgeData/clean/odds/nfl/lake/inventory.json")
HD_RAW = Path("/Volumes/KosEdgeData/raw/odds/americanfootball_nfl/historical")

EVAL_SHA = "fac21ebed92b6ef91e27095026751f088440dbd81e47ca368d256c580b58d7f0"
DEV_SHA = "92b915850b6094c4fa73923eeeb86763b91368007b8d5977d97e6770f40e6c49"
WC_SHA = "f81d381e0553a82a87a86b5e1a980cc2792be2e12f73203e48aa1435199d0722"
GAMES_SHA = "4fe1cdd7f2eb616103ee6107e6a5cb0d5280f8006be420b606af0995351abef8"
QUOTE_MANIFEST_SHA = "6a1c1b378b91abd5e2ed185649536468192147057a2ea535a23e8ae5b14e6984"

CUTOFF_MINUTES = 60
MAX_QUOTE_AGE_HOURS = 24
BOOKS = frozenset({"draftkings", "fanduel"})
DECLARED_REG = {2020: 256, 2021: 272, 2022: 271, 2023: 272}
PARSER_ID = "nfl-t5119u-r2a-owned-coverage-v1"

# silence unused import if join path is only used in replay
_ = join_quotes_at_cutoff


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(8 * 1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_json(obj: Any) -> str:
    return sha256_bytes(json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8"))


def write_json(path: Path, obj: Any) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(obj, indent=2, default=str) + "\n"
    path.write_text(body, encoding="utf-8")
    return sha256_bytes(body.encode("utf-8"))


def cohort_sha(game_ids: Sequence[str]) -> str:
    return sha256_json({"game_ids": list(game_ids)})


def load_pins() -> Tuple[dict, List[dict], dict]:
    cohorts = json.loads((PINS / "COHORT_IDENTITIES_t5119u.json").read_text())
    games = json.loads((PINS / "GAMES_2020_2023_IDENTITY.json").read_text())["games"]
    live_eval = cohort_sha(cohorts["eval"]["game_ids"])
    live_dev = cohort_sha(cohorts["dev_reg"]["game_ids"])
    live_wc = cohort_sha(cohorts["non_reg_wildcard"]["game_ids"])
    if live_eval != EVAL_SHA:
        raise SystemExit(f"EVAL identity pin mismatch {live_eval} != {EVAL_SHA}")
    if live_dev != DEV_SHA:
        raise SystemExit(f"DEV identity pin mismatch {live_dev} != {DEV_SHA}")
    if live_wc != WC_SHA:
        raise SystemExit(f"WC identity pin mismatch {live_wc} != {WC_SHA}")
    if len(cohorts["eval"]["game_ids"]) != 449:
        raise SystemExit("EVAL n != 449")
    if len(cohorts["dev_reg"]["game_ids"]) != 437:
        raise SystemExit("DEV n != 437")
    if len(cohorts["non_reg_wildcard"]["game_ids"]) != 6:
        raise SystemExit("WC n != 6")
    by_id = {g["game_id"]: g for g in games}
    return cohorts, games, by_id


def resolve_abbr(name: str) -> Tuple[str, str]:
    ident = resolve_team_identity(name)
    return ident.abbr, ident.status


def kickoff_cutoff(kickoff_utc: str) -> Tuple[Optional[datetime], Optional[datetime], Optional[str]]:
    ko = normalize_quote_timestamp(kickoff_utc, source_timezone=None)
    if ko is None:
        return None, None, "kickoff_utc missing TZ or unparseable"
    return ko, ko - timedelta(minutes=CUTOFF_MINUTES), None


def build_game_indexes(games: Sequence[Mapping[str, Any]]) -> dict:
    by_id = {}
    by_gameday: Dict[Tuple[str, str, str], List[dict]] = defaultdict(list)
    by_kickoff: Dict[Tuple[str, str, datetime], List[dict]] = defaultdict(list)
    refused_kickoff = []
    for raw in games:
        home_abbr, home_st = resolve_abbr(str(raw["home"]))
        away_abbr, away_st = resolve_abbr(str(raw["away"]))
        ko, cutoff, err = kickoff_cutoff(str(raw.get("kickoff_utc") or ""))
        row = dict(raw)
        row["home_abbr"] = home_abbr
        row["away_abbr"] = away_abbr
        row["home_status"] = home_st
        row["away_status"] = away_st
        row["kickoff_dt"] = ko
        row["cutoff_dt"] = cutoff
        row["identity_error"] = err
        if home_st != "resolved" or away_st != "resolved":
            row["identity_error"] = f"team {home_st}/{away_st} home={raw['home']!r} away={raw['away']!r}"
        if ko is None:
            refused_kickoff.append(row["game_id"])
        by_id[row["game_id"]] = row
        gameday = str(row.get("nflverse_gameday") or "")[:10]
        if home_st == "resolved" and away_st == "resolved" and gameday:
            by_gameday[(gameday, home_abbr, away_abbr)].append(row)
        if home_st == "resolved" and away_st == "resolved" and ko is not None:
            by_kickoff[(home_abbr, away_abbr, ko)].append(row)
    return {
        "by_id": by_id,
        "by_gameday": by_gameday,
        "by_kickoff": by_kickoff,
        "refused_kickoff": refused_kickoff,
    }


def match_jsonl_game(row: Mapping[str, Any], idx: dict) -> Tuple[Optional[dict], str, str]:
    home_abbr, home_st = resolve_abbr(str(row.get("home") or row.get("home_team") or ""))
    away_abbr, away_st = resolve_abbr(str(row.get("away") or row.get("away_team") or ""))
    if home_st == "ambiguous" or away_st == "ambiguous":
        return None, "ambiguous_identity", f"home={row.get('home')!r} away={row.get('away')!r}"
    if home_st != "resolved" or away_st != "resolved":
        return None, "unknown_team", f"home={row.get('home')!r} away={row.get('away')!r}"
    day = str(row.get("game_date") or "")[:10]
    if not day:
        return None, "ambiguous_identity", "jsonl missing game_date; no commence_time on this store"
    hits = idx["by_gameday"].get((day, home_abbr, away_abbr), [])
    if not hits:
        return None, "no_game_match", f"jsonl gameday {day} {home_abbr} vs {away_abbr}"
    if len(hits) > 1:
        return None, "ambiguous_identity", f"jsonl gameday {day} {home_abbr} vs {away_abbr} n={len(hits)}"
    return hits[0], "", ""


def match_commence_game(row: Mapping[str, Any], idx: dict) -> Tuple[Optional[dict], str, str]:
    home_abbr, home_st = resolve_abbr(str(row.get("home_team") or row.get("home") or ""))
    away_abbr, away_st = resolve_abbr(str(row.get("away_team") or row.get("away") or ""))
    if home_st == "ambiguous" or away_st == "ambiguous":
        return None, "ambiguous_identity", f"home={row.get('home_team')!r} away={row.get('away_team')!r}"
    if home_st != "resolved" or away_st != "resolved":
        return None, "unknown_team", f"home={row.get('home_team')!r} away={row.get('away_team')!r}"
    commence = normalize_quote_timestamp(row.get("commence_time"))
    if commence is None:
        return None, "unresolvable_timestamp", f"commence_time={row.get('commence_time')!r}"
    hits = idx["by_kickoff"].get((home_abbr, away_abbr, commence), [])
    if not hits:
        return None, "no_game_match", (
            f"commence {timestamp_to_iso(commence)} {home_abbr} vs {away_abbr} "
            "!= any kickoff_utc (exact; no undocumented slack)"
        )
    if len(hits) > 1:
        return None, "ambiguous_identity", f"commence exact hits {len(hits)}"
    return hits[0], "", ""


def observation_dt(row: Mapping[str, Any]) -> Tuple[Optional[datetime], str]:
    raw = row.get("captured_at") or row.get("snapshot_ts")
    dt = normalize_quote_timestamp(raw)
    if dt is None:
        return None, f"observation unparseable or missing TZ: {raw!r}"
    return dt, ""


def file_meta(path: Path) -> dict:
    if not path.is_file():
        return {"path": str(path), "exists": False}
    st = path.stat()
    return {
        "path": str(path),
        "exists": True,
        "bytes": st.st_size,
        "mtime_utc": datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "mtime_is_not_observation": True,
    }


def inventory_sources(csv_lake_hashes: Optional[dict] = None) -> dict:
    jsonl_hashes = json.loads((RECEIPTS / "SOURCE_HASHES_JSONL.json").read_text())
    jsonl_by_path = {r["path"]: r for r in jsonl_hashes}
    extra = {}
    extra_path = RECEIPTS / "SOURCE_HASHES_CSV_LAKE.json"
    if extra_path.is_file():
        extra = {r["path"]: r for r in json.loads(extra_path.read_text())}
    if csv_lake_hashes:
        extra.update(csv_lake_hashes)

    jsonl = []
    for season, path in HD_JSONL.items():
        rec = file_meta(path)
        rec["season_filename"] = season
        rec["filename_season_is_not_game_season"] = True
        rec.update({k: jsonl_by_path.get(str(path), {}).get(k) for k in ("sha256",)})
        rec["used_in_t5116u_6a1c1b37_load"] = season in (2022, 2023)
        jsonl.append(rec)

    raw = {}
    for season in (2020, 2021, 2022, 2023):
        d = HD_RAW / str(season)
        files = sorted(p.name for p in d.iterdir() if p.is_file()) if d.is_dir() else []
        raw[str(season)] = {"path": str(d), "n_files": len(files), "sample": files[:8]}

    sqlite_extract = EXTRACTS / "gapfill_nfl_2020_2023_dkfd_mainline.jsonl"
    return {
        "generated_at_utc": utc_now(),
        "volume": "/Volumes/KosEdgeData",
        "originals_modified": False,
        "new_pulls": False,
        "protected_2024_26_opened": False,
        "stores": {
            "jsonl_2020_2023": jsonl,
            "open_close_csv": {
                **file_meta(HD_CSV),
                "sha256": (extra.get(str(HD_CSV)) or {}).get("sha256"),
                "used_in_t5116u_6a1c1b37_load": True,
                "schema": "sport_key,event_id,commence_time,home_team,away_team,snapshot_kind,snapshot_ts,book,market,outcome,price,point",
            },
            "gapfill_sqlite": {
                **file_meta(HD_SQLITE),
                "tables": ["lines", "requests"],
                "used_in_t5116u_6a1c1b37_load": False,
                "extract_path": str(sqlite_extract),
                "note": "13GB original left untouched; coverage uses 2020-23 NFL DK/FD mainline extract only",
            },
            "lake_parquet_2020_2023": [
                {
                    **file_meta(path),
                    "season": season,
                    "sha256": (extra.get(str(path)) or {}).get("sha256"),
                    "used_in_t5116u_6a1c1b37_load": False,
                    "2024_26_parquet_opened": False,
                }
                for season, path in HD_LAKE.items()
            ],
            "lake_inventory_json": {
                **file_meta(HD_LAKE_INV),
                "sha256": (extra.get(str(HD_LAKE_INV)) or {}).get("sha256"),
                "note": "contains later-season count keys; those parquet files were not opened",
            },
            "raw_historical_2020_2023": raw,
        },
        "forbidden": [
            "Did not open clean/odds/nfl/snapshots-2024|2025|2026 JSONL",
            "Did not open lake snapshots-2024|2025|2026.parquet",
            "Did not open raw/odds/.../historical/2024|2025|2026 file contents",
        ],
    }


def load_cli_sqlite_csv() -> Optional[Path]:
    """Return completed CLI dump path, or None if still writing / absent."""
    done = EXTRACTS / "SQLITE_CLI.DONE"
    path = EXTRACTS / "gapfill_nfl_2020_2023_dkfd_mainline.csv"
    if not done.is_file() or not path.is_file() or path.stat().st_size < 64:
        return None
    with path.open("rb") as fh:
        head = fh.readline()
        if b"event_id" not in head:
            return None
        rest = fh.read(16)
        if not rest:
            return None
    return path


def iter_cli_sqlite_csv(path: Path) -> Iterator[dict]:
    with path.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            row["book"] = str(row.get("book") or "").strip().lower()
            row["source"] = str(HD_SQLITE)
            row["provenance"] = "odds_gapfill_sqlite"
            row["captured_at"] = row.get("snapshot_ts")
            yield row


def extract_sqlite_from_cli_or_scan(*, skip_scan: bool) -> dict:
    dest = EXTRACTS / "gapfill_nfl_2020_2023_dkfd_mainline.jsonl"
    targeted = RECEIPTS / "SQLITE_EXTRACT_TARGETED.json"
    if dest.is_file() and targeted.is_file():
        rec = json.loads(targeted.read_text(encoding="utf-8"))
        live = sha256_file(dest)
        if rec.get("sha256") == live and rec.get("rows"):
            print(json.dumps({"phase": "sqlite_reuse_targeted_jsonl", "rows": rec.get("rows"), "sha256": live}), flush=True)
            write_json(RECEIPTS / "SQLITE_EXTRACT.json", rec)
            return rec
    cli = load_cli_sqlite_csv()
    if cli is not None:
        print(json.dumps({"phase": "sqlite_from_cli_csv", "path": str(cli)}), flush=True)
        n = 0
        kept = 0
        by_season = Counter()
        by_book = Counter()
        by_market = Counter()
        events: Dict[str, dict] = {}
        h = hashlib.sha256()
        EXTRACTS.mkdir(parents=True, exist_ok=True)
        with dest.open("w", encoding="utf-8") as out:
            for row in iter_cli_sqlite_csv(cli):
                n += 1
                season = season_from_commence(row.get("commence_time"))
                if season not in PERMITTED_SEASONS:
                    continue
                row["season"] = season
                line = json.dumps(row, separators=(",", ":"), default=str)
                out.write(line + "\n")
                h.update((line + "\n").encode("utf-8"))
                kept += 1
                by_season[season] += 1
                by_book[row["book"]] += 1
                by_market[str(row.get("market") or "")] += 1
                eid = str(row.get("event_id") or "")
                if eid and eid not in events:
                    events[eid] = {
                        "event_id": eid,
                        "commence_time": row.get("commence_time"),
                        "home_team": row.get("home_team"),
                        "away_team": row.get("away_team"),
                        "season": season,
                    }
        rec = {
            "path": str(dest),
            "source": str(cli),
            "source_sha256": sha256_file(cli),
            "source_bytes": cli.stat().st_size,
            "rows": kept,
            "filter_hits": n,
            "sha256": h.hexdigest(),
            "bytes": dest.stat().st_size if dest.is_file() else 0,
            "by_season": dict(by_season),
            "by_book": dict(by_book),
            "by_market": dict(by_market),
            "distinct_event_ids": len(events),
            "original_sqlite_modified": False,
            "extracted_at_utc": utc_now(),
            "method": "cli_csv",
        }
        write_json(RECEIPTS / "SQLITE_EXTRACT.json", rec)
        return rec
    if skip_scan:
        rec = {
            "path": str(dest),
            "rows": 0,
            "sha256": None,
            "skipped": True,
            "reason": "sqlite CLI dump not finished; skip_scan=1",
            "original_sqlite_modified": False,
            "extracted_at_utc": utc_now(),
            "method": "skipped",
        }
        write_json(RECEIPTS / "SQLITE_EXTRACT.json", rec)
        return rec
    return extract_sqlite_scan()


def extract_sqlite_scan() -> dict:
    dest = EXTRACTS / "gapfill_nfl_2020_2023_dkfd_mainline.jsonl"
    EXTRACTS.mkdir(parents=True, exist_ok=True)
    events_dest = EXTRACTS / "gapfill_nfl_2020_2023_events.jsonl"
    conn = sqlite3.connect(f"file:{HD_SQLITE}?mode=ro", uri=True, timeout=120)
    conn.row_factory = sqlite3.Row
    sql = """
        SELECT sport_key, event_id, commence_time, home_team, away_team,
               snapshot_kind, snapshot_ts, book, market, outcome, price, point
        FROM lines
        WHERE sport_key = 'americanfootball_nfl'
          AND commence_time >= '2020-03-01'
          AND commence_time < '2024-03-01'
          AND lower(book) IN ('draftkings', 'fanduel')
          AND market IN ('h2h', 'spreads', 'totals')
    """
    n = 0
    kept = 0
    by_season = Counter()
    by_book = Counter()
    by_market = Counter()
    events: Dict[str, dict] = {}
    h = hashlib.sha256()
    with dest.open("w", encoding="utf-8") as out:
        for raw in conn.execute(sql):
            n += 1
            row = dict(raw)
            season = season_from_commence(row.get("commence_time"))
            if season not in PERMITTED_SEASONS:
                continue
            row["season"] = season
            row["book"] = str(row.get("book") or "").strip().lower()
            row["provenance"] = "odds_gapfill_sqlite"
            line = json.dumps(row, separators=(",", ":"), default=str)
            out.write(line + "\n")
            h.update((line + "\n").encode("utf-8"))
            kept += 1
            by_season[season] += 1
            by_book[row["book"]] += 1
            by_market[str(row.get("market") or "")] += 1
            eid = str(row.get("event_id") or "")
            if eid and eid not in events:
                events[eid] = {
                    "event_id": eid,
                    "commence_time": row.get("commence_time"),
                    "home_team": row.get("home_team"),
                    "away_team": row.get("away_team"),
                    "season": season,
                }
            if kept % 50000 == 0:
                print(json.dumps({"phase": "sqlite_extract", "kept": kept, "scanned_matching_filter": n}), flush=True)
    conn.close()
    with events_dest.open("w", encoding="utf-8") as fh:
        for ev in events.values():
            fh.write(json.dumps(ev, separators=(",", ":")) + "\n")
    rec = {
        "path": str(dest),
        "rows": kept,
        "filter_hits": n,
        "sha256": h.hexdigest(),
        "bytes": dest.stat().st_size if dest.is_file() else 0,
        "by_season": dict(by_season),
        "by_book": dict(by_book),
        "by_market": dict(by_market),
        "distinct_event_ids": len(events),
        "events_path": str(events_dest),
        "events_sha256": sha256_file(events_dest) if events_dest.is_file() else None,
        "original_sqlite_modified": False,
        "extracted_at_utc": utc_now(),
    }
    write_json(RECEIPTS / "SQLITE_EXTRACT.json", rec)
    return rec


def iter_sqlite_extract() -> Iterator[dict]:
    path = EXTRACTS / "gapfill_nfl_2020_2023_dkfd_mainline.jsonl"
    if not path.is_file():
        return
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                yield json.loads(line)


def normalize_flat_group(rows: Sequence[Mapping[str, Any]], game: Mapping[str, Any]) -> Tuple[Optional[dict], str]:
    """Collapse flattened outcome rows for one book/market/timestamp into a home-oriented quote."""
    if not rows:
        return None, "missing_value"
    market = canonical_market(rows[0].get("market"))
    home_abbr = game["home_abbr"]
    away_abbr = game["away_abbr"]
    home_side = []
    away_side = []
    over_side = []
    under_side = []
    unknown = []
    for row in rows:
        outcome = str(row.get("outcome") or "").strip()
        ident = resolve_team_identity(outcome)
        token = outcome.lower()
        if market in {"spread", "moneyline"}:
            if ident.status == "resolved" and ident.abbr == home_abbr:
                home_side.append(row)
            elif ident.status == "resolved" and ident.abbr == away_abbr:
                away_side.append(row)
            elif ident.status == "ambiguous":
                return None, "ambiguous_identity"
            else:
                unknown.append(row)
        elif market == "total":
            if token.startswith("over"):
                over_side.append(row)
            elif token.startswith("under"):
                under_side.append(row)
            else:
                unknown.append(row)
        else:
            return None, "incompatible_market"
    if unknown:
        return None, "unknown_team"
    if market == "spread":
        if len(home_side) != 1:
            return None, "sign_unresolved_home_side" if not home_side else "duplicate_conflict"
        home_point = home_side[0].get("point")
        if home_point in (None, ""):
            return None, "market_line_mismatch"
        try:
            spread_home = float(home_point)
        except (TypeError, ValueError):
            return None, "market_line_mismatch"
        if away_side:
            try:
                away_point = float(away_side[0].get("point"))
            except (TypeError, ValueError):
                return None, "market_line_mismatch"
            if abs(spread_home + away_point) > 1e-9:
                return None, "sign_conflict_home_plus_away_nonzero"
        return {
            "market": "spread",
            "spread_home": spread_home,
            "price_home": home_side[0].get("price"),
            "price_away": away_side[0].get("price") if away_side else None,
            "line": spread_home,
        }, ""
    if market == "moneyline":
        if len(home_side) != 1 or len(away_side) != 1:
            return None, "missing_ml_pair"
        return {
            "market": "moneyline",
            "price_home": home_side[0].get("price"),
            "price_away": away_side[0].get("price"),
            "line": None,
        }, ""
    if market == "total":
        if len(over_side) != 1:
            return None, "market_line_mismatch"
        try:
            total = float(over_side[0].get("point"))
        except (TypeError, ValueError):
            return None, "market_line_mismatch"
        return {
            "market": "total",
            "total_points": total,
            "over_price": over_side[0].get("price"),
            "under_price": under_side[0].get("price") if under_side else None,
            "line": total,
        }, ""
    return None, "incompatible_market"


def consider_quote(
    *,
    game: Mapping[str, Any],
    captured: datetime,
    book: str,
    market: str,
    line: Any,
    price: Any,
    extra: Mapping[str, Any],
    source: str,
    provenance: str,
    snapshot_kind: str,
    event_id: str,
) -> Tuple[Optional[dict], str, str]:
    if book not in BOOKS:
        return None, "book_not_benchmark", book
    if market not in {"spread", "moneyline", "total"}:
        return None, "incompatible_market", market
    cutoff = game.get("cutoff_dt")
    if cutoff is None:
        return None, "missing_cutoff", game.get("game_id") or ""
    if captured > cutoff:
        return None, "post_cutoff", f"{timestamp_to_iso(captured)} > {timestamp_to_iso(cutoff)}"
    age_h = (cutoff - captured).total_seconds() / 3600.0
    if age_h > MAX_QUOTE_AGE_HOURS:
        return None, "quote_too_old", f"age_h={age_h:.3f}"
    if game.get("season") not in PERMITTED_SEASONS:
        return None, "season_out_of_bounds", str(game.get("season"))
    rec = {
        "game_id": game["game_id"],
        "season": int(game["season"]),
        "week": int(game["week"]),
        "home_abbr": game["home_abbr"],
        "away_abbr": game["away_abbr"],
        "kickoff_utc": game["kickoff_utc"],
        "cutoff_utc": timestamp_to_iso(cutoff),
        "captured_at": timestamp_to_iso(captured),
        "age_hours": round(age_h, 6),
        "book": book,
        "market": market,
        "line": None if line is None else float(line),
        "spread_home": extra.get("spread_home"),
        "price_home": extra.get("price_home"),
        "price_away": extra.get("price_away"),
        "total_points": extra.get("total_points"),
        "source": source,
        "provenance": provenance,
        "snapshot_kind": snapshot_kind,
        "event_id": event_id,
        "observation_is_not_file_mtime": True,
    }
    return rec, "", ""


def fingerprint(q: Mapping[str, Any]) -> Tuple[Any, ...]:
    return (
        q.get("game_id"),
        q.get("book"),
        q.get("market"),
        q.get("captured_at"),
        q.get("spread_home"),
        q.get("price_home"),
        q.get("price_away"),
        q.get("total_points"),
        q.get("line"),
    )


def conflict_key(q: Mapping[str, Any]) -> Tuple[Any, ...]:
    return (q.get("game_id"), q.get("book"), q.get("market"), q.get("captured_at"))


def collapse(quotes: Sequence[Mapping[str, Any]]) -> Tuple[List[dict], int, List[dict]]:
    by_conflict: Dict[Tuple[Any, ...], List[dict]] = defaultdict(list)
    for q in quotes:
        by_conflict[conflict_key(q)].append(dict(q))
    kept: List[dict] = []
    identical = 0
    refused: List[dict] = []
    for key, group in by_conflict.items():
        fps = {fingerprint(q) for q in group}
        if len(fps) > 1:
            refused.append(
                {
                    "reason": "duplicate_conflict",
                    "game_id": key[0],
                    "book": key[1],
                    "market": key[2],
                    "captured_at": key[3],
                    "n": len(group),
                    "sources": sorted({str(q.get("provenance")) for q in group}),
                }
            )
            continue
        kept.append(group[0])
        identical += len(group) - 1
    latest: Dict[Tuple[str, str, str], dict] = {}
    for q in kept:
        slot = (str(q["game_id"]), str(q["book"]), str(q["market"]))
        prev = latest.get(slot)
        if prev is None or q["captured_at"] > prev["captured_at"]:
            latest[slot] = q
    return list(latest.values()), identical, refused


def ingest_jsonl(idx: dict, seasons: Iterable[int]) -> Tuple[List[dict], Counter]:
    reasons: Counter = Counter()
    out: List[dict] = []
    for row in iter_jsonl_quotes(seasons=seasons):
        game, reason, detail = match_jsonl_game(row, idx)
        if reason:
            reasons[reason] += 1
            continue
        captured, err = observation_dt(row)
        if captured is None:
            reasons["unresolvable_timestamp"] += 1
            continue
        book = str(row.get("book") or "").strip().lower()
        market = canonical_market(row.get("market"))
        extra = {
            "spread_home": row.get("spread_home"),
            "price_home": row.get("price_home"),
            "price_away": row.get("price_away"),
            "total_points": row.get("total_points"),
        }
        line = extra["spread_home"] if market == "spread" else extra["total_points"] if market == "total" else None
        rec, reason, _detail = consider_quote(
            game=game,
            captured=captured,
            book=book,
            market=market,
            line=line,
            price=row.get("price_home"),
            extra=extra,
            source=str(row.get("source") or HD_JSONL.get(int(game["season"]), "")),
            provenance=str(row.get("provenance") or "clean_jsonl"),
            snapshot_kind=str(row.get("snapshot_kind") or "enterprise_snapshot"),
            event_id=str(row.get("event_id") or ""),
        )
        if reason:
            reasons[reason] += 1
            continue
        out.append(rec)
        reasons["kept"] += 1
    return out, reasons


def ingest_flat(rows: Iterable[Mapping[str, Any]], idx: dict, default_source: str) -> Tuple[List[dict], Counter]:
    """Group flattened CSV/sqlite rows, then match + sign-resolve."""
    reasons: Counter = Counter()
    grouped: Dict[Tuple[Any, ...], List[dict]] = defaultdict(list)
    n = 0
    for row in rows:
        n += 1
        if n % 100000 == 0:
            print(json.dumps({"phase": "flat_group", "n": n, "source": default_source}), flush=True)
        book = str(row.get("book") or "").strip().lower()
        if book not in BOOKS:
            reasons["book_not_benchmark"] += 1
            continue
        if classify_market(row.get("market")) != "mainline":
            reasons["incompatible_market"] += 1
            continue
        grouped[
            (
                str(row.get("event_id") or ""),
                str(row.get("commence_time") or ""),
                str(row.get("home_team") or ""),
                str(row.get("away_team") or ""),
                book,
                canonical_market(row.get("market")),
                str(row.get("snapshot_ts") or row.get("captured_at") or ""),
                str(row.get("snapshot_kind") or ""),
                str(row.get("source") or default_source),
                str(row.get("provenance") or default_source),
            )
        ].append(dict(row))
    out: List[dict] = []
    for key, group in grouped.items():
        game, reason, detail = match_commence_game(group[0], idx)
        if reason:
            reasons[reason] += 1
            continue
        captured, err = observation_dt(group[0])
        if captured is None:
            reasons["unresolvable_timestamp"] += 1
            continue
        norm, nreason = normalize_flat_group(group, game)
        if nreason:
            reasons[nreason] += 1
            continue
        rec, reason, _detail = consider_quote(
            game=game,
            captured=captured,
            book=key[4],
            market=key[5],
            line=norm.get("line"),
            price=norm.get("price_home"),
            extra=norm,
            source=key[8],
            provenance=key[9],
            snapshot_kind=key[7],
            event_id=key[0],
        )
        if reason:
            reasons[reason] += 1
            continue
        out.append(rec)
        reasons["kept"] += 1
    return out, reasons


def coverage_from_latest(latest: Sequence[Mapping[str, Any]], target_ids: Sequence[str]) -> dict:
    by_game: Dict[str, List[dict]] = defaultdict(list)
    for q in latest:
        by_game[str(q["game_id"])].append(dict(q))
    matched = []
    missing = []
    for gid in target_ids:
        qs = by_game.get(gid, [])
        spreads = [q for q in qs if q["market"] == "spread" and q.get("spread_home") is not None]
        books = sorted({q["book"] for q in spreads})
        sources = sorted({q["provenance"] for q in qs})
        if spreads:
            matched.append(
                {
                    "game_id": gid,
                    "books": books,
                    "n_spread_quotes": len(spreads),
                    "median_spread_home": float(median([float(q["spread_home"]) for q in spreads])),
                    "sources": sources,
                }
            )
        else:
            missing.append({"game_id": gid, "had_any_quote": bool(qs), "sources": sources, "markets": sorted({q["market"] for q in qs})})
    return {
        "matched_n": len(matched),
        "missing_n": len(missing),
        "matched_game_ids": [r["game_id"] for r in matched],
        "missing_game_ids": [r["game_id"] for r in missing],
        "matched": matched,
        "missing": missing,
    }


def replay_t5116u(idx: dict, eval_ids: Sequence[str]) -> dict:
    """Replay the spent look's source subset + reader join. Outcome-blind. Does not write ONE_RUN."""
    quotes = list(iter_jsonl_quotes(seasons=(2022, 2023)))
    quotes.extend(list(iter_open_close_csv_quotes(seasons=(2022, 2023))))
    games = []
    for gid in eval_ids:
        g = idx["by_id"][gid]
        if g.get("cutoff_dt") is None:
            raise SystemExit(f"EVAL game missing kickoff TZ: {gid}")
        games.append(
            {
                "game_id": gid,
                "season": g["season"],
                "week": g["week"],
                "home": g["home"],
                "away": g["away"],
                "home_team": g["home"],
                "away_team": g["away"],
                "kickoff": g["kickoff_utc"],
                "kickoff_utc": g["kickoff_utc"],
                "game_date": g.get("nflverse_gameday") or "",
                "forecast_cutoff": timestamp_to_iso(g["cutoff_dt"]),
            }
        )
    join = join_quotes_at_cutoff(quotes, games, None, per_game_cutoff_key="forecast_cutoff")
    eligible = []
    extra_reasons: Counter = Counter()
    for quote in join.latest_per_book_market:
        captured = normalize_quote_timestamp(quote.captured_at, source_timezone="UTC")
        cutoff = next(g["cutoff_dt"] for g in [idx["by_id"][quote.game_id]])
        if captured is None:
            extra_reasons["unresolvable_timestamp"] += 1
            continue
        age_h = (cutoff - captured).total_seconds() / 3600.0
        if age_h > MAX_QUOTE_AGE_HOURS:
            extra_reasons["quote_too_old"] += 1
            continue
        if quote.book not in BOOKS:
            extra_reasons["book_not_benchmark"] += 1
            continue
        extra_reasons["kept_latest"] += 1
        eligible.append(quote)
    by_game: Dict[str, list] = defaultdict(list)
    for q in eligible:
        by_game[q.game_id].append(q)
    matched = []
    missing_reasons = {}
    for gid in eval_ids:
        qs = by_game.get(gid, [])
        spreads = [q for q in qs if q.market == "spread" and (q.spread_home is not None or q.line is not None)]
        if spreads:
            matched.append(gid)
        else:
            missing_reasons[gid] = {
                "had_latest_quotes": bool(qs),
                "markets": sorted({q.market for q in qs}),
                "books": sorted({q.book for q in qs}),
            }
    by_season = Counter(int(gid.split("_")[0]) for gid in matched)
    return {
        "label": "t5116u_source_subset_replay_outcome_blind",
        "not_a_second_look": True,
        "one_run_untouched": True,
        "sources": ["jsonl_2022_2023", "open_close_csv_2022_2023"],
        "sqlite_included": False,
        "quotes_in": len(quotes),
        "join_eligible_n": len(join.eligible),
        "join_excluded_n": len(join.excluded),
        "join_identical_duplicate_n": join.identical_duplicate_n,
        "join_reason_tallies": dict(join.reason_tallies),
        "post_join_filter_tallies": dict(extra_reasons),
        "margin_eligible_n": len(matched),
        "margin_eligible_by_season": {str(k): int(by_season[k]) for k in (2022, 2023)},
        "matched_game_ids": matched,
        "missing_game_ids": [gid for gid in eval_ids if gid not in set(matched)],
        "missing_detail": missing_reasons,
        "spent_declared_n": 132,
        "spent_declared_by_season": {"2022": 47, "2023": 85},
        "reproduced_spent_132": len(matched) == 132
        and by_season[2022] == 47
        and by_season[2023] == 85,
    }


def per_season_vs_declared(matched_ids: Sequence[str]) -> dict:
    by = Counter(int(gid.split("_")[0]) for gid in matched_ids)
    out = {}
    for season, declared in DECLARED_REG.items():
        qn = int(by.get(season, 0))
        excluded = declared - qn
        rate = excluded / declared if declared else None
        out[str(season)] = {
            "declared_pbp_reg": declared,
            "quote_eligible_n": qn,
            "excluded_n": excluded,
            "exclusion_rate": rate,
            "hold_gt_30pct": bool(rate is not None and rate > 0.30),
        }
    return out


def write_r2b_consume(*, ready: bool, reason: str, manifest_name: str, quotes_name: str, extra: dict) -> str:
    body = {
        "schema": "nfl-t5119u-r2b-consume-v1",
        "cert_candidate": 0,
        "eval_claim": False,
        "g5_loosened": False,
        "time_rule_loosened": False,
        "book_rule_loosened": False,
        "market_e2e": "READY_FOR_R2B_DEV_E2E" if ready else "NOT_READY",
        "reason": reason,
        "coverage_manifest": f"data/ops/nfl-t5119u-r2-owned-coverage/{manifest_name}",
        "admissible_quotes": f"data/ops/nfl-t5119u-r2-owned-coverage/{quotes_name}",
        "rules": {
            "books": sorted(BOOKS),
            "cutoff_minutes_before_kickoff": CUTOFF_MINUTES,
            "max_quote_age_hours": MAX_QUOTE_AGE_HOURS,
            "observation": "captured_at / snapshot_ts with explicit offset or Z — not file mtime / import / close label",
            "dedupe": "identical fingerprint collapse; conflict refuses",
        },
        "staged_at_utc": utc_now(),
        **extra,
    }
    return write_json(OUT / "R2B_CONSUME.json", body)


def main() -> int:
    skip_sqlite_scan = "--skip-sqlite-scan" in sys.argv
    print(json.dumps({"phase": "start", "at": utc_now(), "skip_sqlite_scan": skip_sqlite_scan}), flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    EXTRACTS.mkdir(parents=True, exist_ok=True)
    RECEIPTS.mkdir(parents=True, exist_ok=True)

    extra_hashes = {}
    extra_path = RECEIPTS / "SOURCE_HASHES_CSV_LAKE.json"
    if extra_path.is_file():
        extra_hashes = {r["path"]: r for r in json.loads(extra_path.read_text())}
    else:
        print(json.dumps({"phase": "hash_csv_lake"}), flush=True)
        recs = []
        for path in [HD_CSV, HD_LAKE_INV, *HD_LAKE.values()]:
            if not path.is_file():
                continue
            rec = {**file_meta(path), "sha256": sha256_file(path)}
            recs.append(rec)
            extra_hashes[str(path)] = rec
            print(json.dumps({"hashed": str(path), "sha256": rec["sha256"]}), flush=True)
        write_json(extra_path, recs)

    cohorts, games, _ = load_pins()
    idx = build_game_indexes(games)
    eval_ids = list(cohorts["eval"]["game_ids"])
    dev_ids = list(cohorts["dev_reg"]["game_ids"])
    wc_ids = list(cohorts["non_reg_wildcard"]["game_ids"])

    print(json.dumps({"phase": "ingest_jsonl"}), flush=True)
    jsonl_quotes, jsonl_reasons = ingest_jsonl(idx, (2020, 2021, 2022, 2023))
    print(json.dumps({"phase": "ingest_csv"}), flush=True)
    csv_quotes, csv_reasons = ingest_flat(iter_open_close_csv_quotes(seasons=(2020, 2021, 2022, 2023)), idx, str(HD_CSV))
    print(json.dumps({"phase": "sqlite_extract"}), flush=True)
    sqlite_extract = extract_sqlite_from_cli_or_scan(skip_scan=skip_sqlite_scan)
    print(json.dumps({"phase": "ingest_sqlite", "extract": {k: sqlite_extract.get(k) for k in ("rows", "skipped", "method")}}), flush=True)
    sql_quotes, sql_reasons = ingest_flat(iter_sqlite_extract(), idx, str(HD_SQLITE))

    by_store = {
        "jsonl": jsonl_quotes,
        "open_close_csv": csv_quotes,
        "gapfill_sqlite": sql_quotes,
    }
    all_quotes = jsonl_quotes + csv_quotes + sql_quotes
    latest, identical_n, conflicts = collapse(all_quotes)

    print(json.dumps({"phase": "t5116u_replay"}), flush=True)
    replay = replay_t5116u(idx, eval_ids)

    r2_eval = coverage_from_latest(latest, eval_ids)
    r2_dev = coverage_from_latest(latest, dev_ids)
    r2_wc = coverage_from_latest(latest, wc_ids)

    # per-source coverage (after that store's own collapse)
    per_source_eval = {}
    for name, qs in by_store.items():
        src_latest, _, src_conflicts = collapse(qs)
        cov = coverage_from_latest(src_latest, eval_ids)
        per_source_eval[name] = {
            "quotes_kept_pre_collapse": len(qs),
            "latest_n": len(src_latest),
            "conflicts_n": len(src_conflicts),
            "eval_matched_n": cov["matched_n"],
            "eval_missing_n": cov["missing_n"],
            "eval_matched_game_ids": cov["matched_game_ids"],
            "eval_missing_game_ids": cov["missing_game_ids"],
            "eval_matched_by_season": dict(Counter(int(g.split("_")[0]) for g in cov["matched_game_ids"])),
        }

    # t5116u missing reasons vs EVAL, using R2 identity on the same two stores
    t5116_subset, _, _ = collapse(jsonl_quotes + csv_quotes)
    # restrict to quotes whose provenance is the two t5116u stores and seasons 2022-23 games
    t5116_latest = [q for q in t5116_subset if int(q["season"]) in (2022, 2023)]
    t5116_r2path = coverage_from_latest(t5116_latest, eval_ids)

    missing_vs_eval = []
    replay_missing = set(replay["missing_game_ids"])
    r2_missing = set(r2_eval["missing_game_ids"])
    for gid in eval_ids:
        season = int(gid.split("_")[0])
        in_replay = gid not in replay_missing
        in_r2 = gid not in r2_missing
        src_hit = [name for name, rec in per_source_eval.items() if gid in rec["eval_matched_game_ids"]]
        if in_replay:
            reason = "matched_on_t5116u_replay"
        elif src_hit:
            reason = "missing_from_t5116u_source_subset_or_join_but_present_on_owned_store:" + ",".join(src_hit)
        else:
            reason = "no_admissible_dk_fd_spread_after_identity_cutoff_age"
        missing_vs_eval.append(
            {
                "game_id": gid,
                "season": season,
                "in_t5116u_replay_132_path": in_replay,
                "in_r2_union_coverage": in_r2,
                "stores_with_admissible_spread": src_hit,
                "reason": reason,
            }
        )

    exclusion_rows = [r for r in missing_vs_eval if not r["in_t5116u_replay_132_path"]]
    excl_2022 = [r["game_id"] for r in exclusion_rows if r["season"] == 2022]
    excl_2023 = [r["game_id"] for r in exclusion_rows if r["season"] == 2023]

    parser = {
        "parser_id": PARSER_ID,
        "reader_path": "scripts/nfl/t5119u_r2a/nfl_odds_reader.py",
        "reader_sha256": sha256_file(HERE / "nfl_odds_reader.py"),
        "builder_path": "scripts/nfl/t5119u_r2a/build_owned_coverage.py",
        "builder_sha256": sha256_file(Path(__file__)),
        "selection_books": sorted(BOOKS),
        "cutoff_minutes_before_kickoff": CUTOFF_MINUTES,
        "max_quote_age_hours": MAX_QUOTE_AGE_HOURS,
        "commence_vs_kickoff": "exact_datetime_utc",
        "jsonl_identity": "nflverse_gameday + resolved home/away abbr",
        "sign": "odds_api_spread_home_negative_when_home_favored; flattened home outcome required",
        "performance_selection": False,
        "outcome_scoring": False,
    }

    inventory = inventory_sources(extra_hashes)
    inventory["stores"]["gapfill_sqlite"]["extract"] = sqlite_extract

    extract_hashes = {
        "jsonl": [{k: r.get(k) for k in ("path", "bytes", "sha256")} for r in inventory["stores"]["jsonl_2020_2023"]],
        "open_close_csv": {
            "path": str(HD_CSV),
            "bytes": inventory["stores"]["open_close_csv"].get("bytes"),
            "sha256": inventory["stores"]["open_close_csv"].get("sha256"),
        },
        "gapfill_sqlite_original_bytes": inventory["stores"]["gapfill_sqlite"].get("bytes"),
        "gapfill_sqlite_extract": sqlite_extract,
        "lake_2020_2023": inventory["stores"]["lake_parquet_2020_2023"],
        "reader_sha256": parser["reader_sha256"],
        "builder_sha256": parser["builder_sha256"],
    }

    rule = {
        "schema": "nfl-t5119u-r2a-source-selection-dedupe-v1",
        "books": sorted(BOOKS),
        "all_admissible_dk_fd": True,
        "performance_selected": False,
        "stores_in": ["clean_jsonl_2020_2023", "open_close_csv_2020_2023", "gapfill_sqlite_2020_2023_extract"],
        "markets": ["spread", "moneyline", "total"],
        "cutoff": "captured_at <= kickoff_utc - 60 minutes",
        "max_age_hours": 24,
        "duplicate_collapse": "identical fingerprint keeps one; conflicting fingerprint refuses",
        "latest_slot": "(game_id, book, market) latest captured_at still <= cutoff",
        "unresolved_conflict": "refuse",
        "undocumented_tz_sign_identity": "refuse",
    }

    identity_rule = {
        "schema": "nfl-t5119u-r2a-identity-v1",
        "games_csv_sha256": GAMES_SHA,
        "kickoff_field": "kickoff_utc (explicit Z)",
        "refused_as_kickoff": ["schedule_results.start_time_raw", "pbp.start_time", "file mtime", "import time"],
        "jsonl": "unique (nflverse_gameday, home_abbr, away_abbr)",
        "csv_sqlite": "unique (home_abbr, away_abbr, commence_time == kickoff_utc)",
        "no_slack_minutes": True,
        "observation": "captured_at / snapshot_ts with explicit offset or Z",
        "eval_sha256": EVAL_SHA,
        "dev_sha256": DEV_SHA,
        "wc_sha256": WC_SHA,
        "games_missing_kickoff_tz": idx["refused_kickoff"],
    }

    exclusion = {
        "schema": "nfl-t5119u-r2a-t5116u-exclusion-v1",
        "spent_look_untouched": True,
        "spent_quote_eligible_n": 132,
        "replay": {
            "n": replay["margin_eligible_n"],
            "by_season": replay["margin_eligible_by_season"],
            "reproduced_spent_132": replay["reproduced_spent_132"],
            "matched_game_ids": replay["matched_game_ids"],
            "missing_game_ids": replay["missing_game_ids"],
            "join_reason_tallies": replay["join_reason_tallies"],
            "post_join_filter_tallies": replay["post_join_filter_tallies"],
        },
        "vs_eval_449": {
            "eval_n": 449,
            "eval_sha256": EVAL_SHA,
            "replay_matched_n": replay["margin_eligible_n"],
            "replay_missing_n": len(replay["missing_game_ids"]),
            "replay_matched_2022": replay["margin_eligible_by_season"].get("2022"),
            "replay_matched_2023": replay["margin_eligible_by_season"].get("2023"),
            "replay_missing_2022": excl_2022,
            "replay_missing_2023": excl_2023,
        },
        "vs_declared_dens": per_season_vs_declared(replay["matched_game_ids"]),
        "why_t5116u_omitted_owned_sqlite": "run_nfl_eval_one_exec_t5116u.load_quotes used JSONL+CSV 2022-23 only",
        "r2_union_vs_eval": {
            "matched_n": r2_eval["matched_n"],
            "missing_n": r2_eval["missing_n"],
            "matched_by_season": dict(Counter(int(g.split("_")[0]) for g in r2_eval["matched_game_ids"])),
        },
        "per_source_eval": {k: {kk: vv for kk, vv in v.items() if kk not in {"eval_matched_game_ids", "eval_missing_game_ids"}} | {
            "eval_matched_game_ids": v["eval_matched_game_ids"],
            "eval_missing_game_ids": v["eval_missing_game_ids"],
        } for k, v in per_source_eval.items()},
        "per_game": missing_vs_eval,
        "r2_documented_sign_path_on_t5116u_stores": {
            "matched_n": t5116_r2path["matched_n"],
            "matched_game_ids": t5116_r2path["matched_game_ids"],
            "missing_game_ids": t5116_r2path["missing_game_ids"],
        },
    }

    manifest = {
        "schema": "nfl-t5119u-r2a-coverage-manifest-v1",
        "sealed_before_outcome_scoring": True,
        "eval_claim": False,
        "cert_candidate": 0,
        "label": "R2_OWNED_COVERAGE_OUTCOME_BLIND",
        "parser": parser,
        "source_selection_dedupe": rule,
        "identity": identity_rule,
        "extract_hashes": {
            "jsonl": extract_hashes["jsonl"],
            "open_close_csv_sha256": extract_hashes["open_close_csv"].get("sha256"),
            "sqlite_extract_sha256": sqlite_extract.get("sha256"),
            "sqlite_extract_rows": sqlite_extract.get("rows"),
            "reader_sha256": parser["reader_sha256"],
            "builder_sha256": parser["builder_sha256"],
        },
        "ingest_reason_tallies": {
            "jsonl": dict(jsonl_reasons),
            "open_close_csv": dict(csv_reasons),
            "gapfill_sqlite": dict(sql_reasons),
        },
        "collapse": {
            "input_n": len(all_quotes),
            "latest_n": len(latest),
            "identical_duplicate_n": identical_n,
            "conflict_n": len(conflicts),
        },
        "eval": {
            "n": 449,
            "cohort_sha256": EVAL_SHA,
            "r2_matched_n": r2_eval["matched_n"],
            "r2_missing_n": r2_eval["missing_n"],
            "r2_matched_game_ids": r2_eval["matched_game_ids"],
            "r2_missing_game_ids": r2_eval["missing_game_ids"],
            "r2_vs_declared": per_season_vs_declared(r2_eval["matched_game_ids"]),
        },
        "dev_reg": {
            "n": 437,
            "cohort_sha256": DEV_SHA,
            "r2_matched_n": r2_dev["matched_n"],
            "r2_missing_n": r2_dev["missing_n"],
            "r2_matched_game_ids": r2_dev["matched_game_ids"],
            "r2_missing_game_ids": r2_dev["missing_game_ids"],
        },
        "non_reg_wildcard": {
            "n": 6,
            "cohort_sha256": WC_SHA,
            "r2_matched_n": r2_wc["matched_n"],
            "r2_missing_n": r2_wc["missing_n"],
            "r2_matched_game_ids": r2_wc["matched_game_ids"],
            "r2_missing_game_ids": r2_wc["missing_game_ids"],
        },
        "t5116u_replay_n": replay["margin_eligible_n"],
        "t5116u_replay_reproduced_132": replay["reproduced_spent_132"],
        "sealed_at_utc": utc_now(),
    }
    manifest["manifest_sha256"] = sha256_json({k: v for k, v in manifest.items() if k != "manifest_sha256"})

    hashes = {
        "SOURCE_INVENTORY.json": write_json(OUT / "SOURCE_INVENTORY.json", inventory),
        "IDENTITY_RULE.json": write_json(OUT / "IDENTITY_RULE.json", identity_rule),
        "SOURCE_SELECTION_DEDUPE_RULE.json": write_json(OUT / "SOURCE_SELECTION_DEDUPE_RULE.json", rule),
        "PARSER_VERSION.json": write_json(OUT / "PARSER_VERSION.json", parser),
        "EXTRACT_HASHES.json": write_json(OUT / "EXTRACT_HASHES.json", extract_hashes),
        "T5116U_EXCLUSION_REPORT.json": write_json(OUT / "T5116U_EXCLUSION_REPORT.json", exclusion),
        "T5116U_REPLAY.json": write_json(OUT / "T5116U_REPLAY.json", replay),
        "EVAL_MATCHED_GAME_IDS.json": write_json(OUT / "EVAL_MATCHED_GAME_IDS.json", r2_eval["matched_game_ids"]),
        "EVAL_MISSING_GAME_IDS.json": write_json(OUT / "EVAL_MISSING_GAME_IDS.json", r2_eval["missing_game_ids"]),
        "DEV_MATCHED_GAME_IDS.json": write_json(OUT / "DEV_MATCHED_GAME_IDS.json", r2_dev["matched_game_ids"]),
        "DEV_MISSING_GAME_IDS.json": write_json(OUT / "DEV_MISSING_GAME_IDS.json", r2_dev["missing_game_ids"]),
        "WC_MATCHED_GAME_IDS.json": write_json(OUT / "WC_MATCHED_GAME_IDS.json", r2_wc["matched_game_ids"]),
        "WC_MISSING_GAME_IDS.json": write_json(OUT / "WC_MISSING_GAME_IDS.json", r2_wc["missing_game_ids"]),
        "DUPLICATE_CONFLICTS.json": write_json(OUT / "DUPLICATE_CONFLICTS.json", conflicts),
        "COVERAGE_MANIFEST.json": write_json(OUT / "COVERAGE_MANIFEST.json", manifest),
    }
    quotes_path = OUT / "ADMISSIBLE_QUOTES.jsonl"
    qh = hashlib.sha256()
    with quotes_path.open("w", encoding="utf-8") as fh:
        for q in sorted(latest, key=lambda r: (str(r["game_id"]), str(r["book"]), str(r["market"]), str(r["captured_at"]))):
            line = json.dumps(q, separators=(",", ":"), default=str)
            fh.write(line + "\n")
            qh.update((line + "\n").encode("utf-8"))
    hashes["ADMISSIBLE_QUOTES.jsonl"] = qh.hexdigest()
    sqlite_ready = bool(sqlite_extract.get("rows")) and not sqlite_extract.get("skipped")
    ready = sqlite_ready
    hashes["R2B_CONSUME.json"] = write_r2b_consume(
        ready=ready,
        reason=(
            "sealed admissible DK/FD extract + coverage manifest; sqlite included; conflicts refused not loosened"
            if ready
            else "sqlite 2020-23 DK/FD extract not sealed yet — market E2E stays NOT_READY"
        ),
        manifest_name="COVERAGE_MANIFEST.json",
        quotes_name="ADMISSIBLE_QUOTES.jsonl",
        extra={
            "admissible_quotes_n": len(latest),
            "admissible_quotes_sha256": qh.hexdigest(),
            "coverage_manifest_sha256": hashes["COVERAGE_MANIFEST.json"],
            "sqlite_extract": {k: sqlite_extract.get(k) for k in ("rows", "sha256", "skipped", "method")},
            "t5116u_replay_n": replay["margin_eligible_n"],
            "eval_r2_matched_n": r2_eval["matched_n"],
            "dev_r2_matched_n": r2_dev["matched_n"],
            "authority_amend": "t5125u ad000a52",
        },
    )
    write_json(OUT / "ARTIFACT_SHA256.json", hashes)

    print(
        json.dumps(
            {
                "phase": "sealed",
                "eval_r2": r2_eval["matched_n"],
                "dev_r2": r2_dev["matched_n"],
                "wc_r2": r2_wc["matched_n"],
                "t5116u_replay": replay["margin_eligible_n"],
                "reproduced_132": replay["reproduced_spent_132"],
                "sqlite_rows": sqlite_extract.get("rows"),
                "conflicts": len(conflicts),
                "out": str(OUT),
            },
            indent=2,
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
