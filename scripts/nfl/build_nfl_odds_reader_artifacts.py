#!/usr/bin/env python3
"""RO inventory + cutoff-join manifest for NFL 2020–2023. No writes to sources."""

from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))

from src.services.nfl_odds_reader import (  # noqa: E402
    HD_LAKE,
    HD_NFLVERSE,
    HD_OC_CSV,
    HD_RAW_HIST,
    HD_SQLITE,
    PERMITTED_SEASONS,
    SEASON_WINDOW_END,
    SEASON_WINDOW_START,
    classify_market,
    games_from_quotes,
    hd_mounted,
    iter_jsonl_quotes,
    iter_open_close_csv_quotes,
    join_quotes_at_cutoff,
    jsonl_path_for_season,
    load_nflverse_games,
    require_hd,
    resolve_team_identity,
)


def _git(*args: str) -> str:
    try:
        return subprocess.check_output(["git", "-C", str(ROOT), *args], text=True).strip()
    except subprocess.CalledProcessError:
        return ""


def inventory_jsonl() -> dict:
    by: list[dict] = []
    capture: dict[int, dict[str, str]] = {}
    game_dates: dict[int, dict[str, str]] = {}
    games: dict[int, set[tuple[str, str, str]]] = defaultdict(set)
    for season in sorted(PERMITTED_SEASONS):
        path = jsonl_path_for_season(season)
        if not path.is_file():
            continue
        n = 0
        books: Counter[str] = Counter()
        markets: Counter[str] = Counter()
        classes: Counter[str] = Counter()
        caps: list[str] = []
        days: list[str] = []
        for row in iter_jsonl_quotes(seasons=[season]):
            n += 1
            books[str(row.get("book") or "")] += 1
            market = str(row.get("market") or "")
            markets[market] += 1
            classes[classify_market(market)] += 1
            if row.get("captured_at"):
                caps.append(str(row["captured_at"]))
            if row.get("game_date"):
                days.append(str(row["game_date"])[:10])
            home = resolve_team_identity(str(row.get("home") or ""))
            away = resolve_team_identity(str(row.get("away") or ""))
            if home.status == "resolved" and away.status == "resolved":
                games[season].add((str(row.get("game_date") or "")[:10], home.abbr, away.abbr))
        by.append(
            {
                "season": season,
                "path": str(path),
                "bytes": path.stat().st_size,
                "rows": n,
                "distinct_games": len(games[season]),
                "by_book": dict(books),
                "by_market": dict(markets),
                "by_market_class": dict(classes),
                "capture_time_min": min(caps) if caps else None,
                "capture_time_max": max(caps) if caps else None,
                "game_date_min": min(days) if days else None,
                "game_date_max": max(days) if days else None,
            }
        )
        if caps:
            capture[season] = {"min": min(caps), "max": max(caps)}
        if days:
            game_dates[season] = {"min": min(days), "max": max(days)}
    return {
        "store": "clean_jsonl_2020_2023",
        "note": "2024–26 JSONL files were not opened.",
        "rows": sum(item["rows"] for item in by),
        "distinct_games": sum(item["distinct_games"] for item in by),
        "by_season": by,
        "capture_time_ranges": capture,
        "game_date_ranges": game_dates,
    }


def inventory_nflverse_games() -> dict:
    games = load_nflverse_games()
    by_season: dict[int, int] = Counter(int(g["season"]) for g in games)
    return {
        "store": "nflverse_pbp_csv_2020_2023",
        "note": "Distinct game_id from existing PBP CSVs. start_time has no timezone and is not used as a cutoff.",
        "distinct_games": len(games),
        "by_season": dict(sorted(by_season.items())),
        "paths": [str(HD_NFLVERSE / f"play_by_play_{s}.csv") for s in sorted(PERMITTED_SEASONS)],
    }


def inventory_sqlite_requests() -> dict:
    if not HD_SQLITE.is_file():
        return {"store": "gapfill_sqlite_requests", "status": "missing"}
    conn = sqlite3.connect(f"file:{HD_SQLITE}?mode=ro", uri=True, timeout=60)
    rows = conn.execute(
        """
        SELECT kind, snapshot_kind, COUNT(*) AS n,
               MIN(date_param) AS min_date, MAX(date_param) AS max_date
        FROM requests
        WHERE sport_key = 'americanfootball_nfl'
          AND date_param >= ?
          AND date_param < ?
        GROUP BY kind, snapshot_kind
        ORDER BY kind, snapshot_kind
        """,
        (SEASON_WINDOW_START, SEASON_WINDOW_END),
    ).fetchall()
    conn.close()
    return {
        "store": "gapfill_sqlite_requests",
        "path": str(HD_SQLITE),
        "bytes": HD_SQLITE.stat().st_size,
        "window": [SEASON_WINDOW_START, SEASON_WINDOW_END],
        "note": "Request ledger only (not a deduplicated line total). Old harvest counts may overlap.",
        "by_kind_snapshot": [
            {
                "kind": kind,
                "snapshot_kind": snap,
                "n": n,
                "date_param_min": min_d,
                "date_param_max": max_d,
            }
            for kind, snap, n, min_d, max_d in rows
        ],
    }


def inventory_raw_historical() -> dict:
    by = []
    for season in sorted(PERMITTED_SEASONS):
        path = HD_RAW_HIST / str(season)
        n = 0
        if path.is_dir():
            n = sum(1 for p in path.rglob("*") if p.is_file())
        by.append({"season": season, "path": str(path), "files": n})
    return {
        "store": "raw_americanfootball_nfl_historical",
        "note": "File counts only for 2020–2023 directories. 2024–26 dirs were not listed for content.",
        "by_season": by,
    }


def inventory_lake_index() -> dict:
    """Cite 2020–2023 keys from lake inventory.json without opening later parquets."""
    path = HD_LAKE / "inventory.json"
    if not path.is_file():
        return {"store": "lake_inventory_json", "status": "missing"}
    payload = json.loads(path.read_text(encoding="utf-8"))
    by_season = {
        key: value
        for key, value in (payload.get("by_season") or {}).items()
        if str(key) in {"2020", "2021", "2022", "2023"}
    }
    return {
        "store": "lake_inventory_json_2020_2023_keys_only",
        "path": str(path),
        "as_of": payload.get("as_of"),
        "source": payload.get("source"),
        "by_season_rows": by_season,
        "in_scope_row_sum": sum(int(v) for v in by_season.values()),
        "note": (
            "Full lake inventory.json also lists later seasons; those parquet files "
            "were not opened. These are export snapshot counts, not a current "
            "deduplicated sqlite total. Old harvest counts may overlap."
        ),
    }


def join_jsonl_with_explicit_game_cutoff() -> dict:
    """Join clean JSONL to quote-derived games.

    JSONL rows have no kickoff. Coverage uses an explicit per-game cutoff equal
    to that game's latest in-file captured_at so the join is deterministic and
    does not invent a later close from another store. Rows after that cutoff
    cannot exist inside the same game group; the useful exclusion signal is
    identity / market / missing fields. A second join against open/close CSV
    uses commence_time as the forecast cutoff.
    """
    quotes = list(iter_jsonl_quotes())
    games = games_from_quotes(quotes)
    # Attach explicit per-game cutoff = max captured_at in that game (in-file).
    by_key: dict[tuple[str, str, str], list[str]] = defaultdict(list)
    for row in quotes:
        home = resolve_team_identity(str(row.get("home") or ""))
        away = resolve_team_identity(str(row.get("away") or ""))
        if home.status != "resolved" or away.status != "resolved":
            continue
        if row.get("captured_at"):
            by_key[(str(row.get("game_date") or "")[:10], home.abbr, away.abbr)].append(
                str(row["captured_at"])
            )
    for game in games:
        key = (game["game_date"], game["home_team"], game["away_team"])
        stamps = by_key.get(key) or []
        game["forecast_cutoff"] = max(stamps) if stamps else None
    result = join_quotes_at_cutoff(quotes, games, None)
    return {
        "mode": "jsonl_self_join_explicit_max_captured_cutoff",
        "note": (
            "Cutoff is the max captured_at already on that game in the JSONL. "
            "This does not substitute a later/closing quote from another file."
        ),
        "quotes_in": len(quotes),
        "games_in": len(games),
        "eligible_n": len(result.eligible),
        "excluded_n": len(result.excluded),
        "identical_duplicate_n": result.identical_duplicate_n,
        "reason_tallies": result.reason_tallies,
        "latest_per_book_market_n": len(result.latest_per_book_market),
    }


def inventory_and_join_csv() -> tuple[dict, dict]:
    """One RO stream of 2020–2023 open/close CSV: inventory + commence cutoff join."""
    from src.services.nfl_odds_reader import classify_market as _class

    quotes: list[dict] = []
    by_season: dict[int, dict] = {}
    games: dict[int, set[tuple[str, str, str]]] = defaultdict(set)
    class_total: Counter[str] = Counter()
    snap_total: Counter[str] = Counter()

    for row in iter_open_close_csv_quotes():
        season = int(row["season"]) if row.get("season") is not None else None
        if season is None:
            continue
        bucket = by_season.setdefault(
            season,
            {
                "season": season,
                "rows": 0,
                "by_book": Counter(),
                "by_market": Counter(),
                "by_market_class": Counter(),
                "by_snapshot_kind": Counter(),
                "capture_time_min": None,
                "capture_time_max": None,
                "game_date_min": None,
                "game_date_max": None,
            },
        )
        bucket["rows"] += 1
        bucket["by_book"][str(row.get("book") or "")] += 1
        market = str(row.get("market") or "")
        bucket["by_market"][market] += 1
        mclass = _class(market)
        bucket["by_market_class"][mclass] += 1
        class_total[mclass] += 1
        kind = str(row.get("snapshot_kind") or "")
        bucket["by_snapshot_kind"][kind] += 1
        snap_total[kind] += 1
        cap = str(row.get("captured_at") or "")
        if cap:
            if bucket["capture_time_min"] is None or cap < bucket["capture_time_min"]:
                bucket["capture_time_min"] = cap
            if bucket["capture_time_max"] is None or cap > bucket["capture_time_max"]:
                bucket["capture_time_max"] = cap
        day = str(row.get("game_date") or "")[:10]
        if day:
            if bucket["game_date_min"] is None or day < bucket["game_date_min"]:
                bucket["game_date_min"] = day
            if bucket["game_date_max"] is None or day > bucket["game_date_max"]:
                bucket["game_date_max"] = day
        home = resolve_team_identity(str(row.get("home") or ""))
        away = resolve_team_identity(str(row.get("away") or ""))
        if home.status == "resolved" and away.status == "resolved":
            games[season].add((day, home.abbr, away.abbr))
        if mclass == "mainline":
            quotes.append(row)

    by_season_out = []
    for season, bucket in sorted(by_season.items()):
        by_season_out.append(
            {
                "season": season,
                "rows": bucket["rows"],
                "distinct_games": len(games[season]),
                "by_book": dict(bucket["by_book"]),
                "by_market": dict(bucket["by_market"]),
                "by_market_class": dict(bucket["by_market_class"]),
                "by_snapshot_kind": dict(bucket["by_snapshot_kind"]),
                "capture_time_min": bucket["capture_time_min"],
                "capture_time_max": bucket["capture_time_max"],
                "game_date_min": bucket["game_date_min"],
                "game_date_max": bucket["game_date_max"],
            }
        )

    inventory = {
        "store": "open_close_csv_2020_2023",
        "path": str(HD_OC_CSV),
        "bytes": HD_OC_CSV.stat().st_size if HD_OC_CSV.is_file() else None,
        "note": (
            "Flattened outcome rows. Mainline vs props/periods counted separately. "
            "Capture-time ranges are not game dates. Not a sqlite dedupe total."
        ),
        "rows": sum(item["rows"] for item in by_season_out),
        "distinct_games": sum(item["distinct_games"] for item in by_season_out),
        "by_market_class": dict(class_total),
        "by_snapshot_kind": dict(snap_total),
        "by_season": by_season_out,
    }

    game_rows = games_from_quotes(quotes)
    for game in game_rows:
        game["forecast_cutoff"] = game.get("kickoff")
    result = join_quotes_at_cutoff(quotes, game_rows, None)
    join = {
        "mode": "open_close_csv_mainline_commence_as_forecast_cutoff",
        "note": (
            "Full 2020–2023 CSV stream. Join uses mainline rows only. "
            "Each game's explicit forecast_cutoff is Odds API commence_time. "
            "Quotes with captured_at > commence_time are post_cutoff and are not "
            "replaced by a later close."
        ),
        "truncated": False,
        "quotes_in": len(quotes),
        "games_in": len(game_rows),
        "eligible_n": len(result.eligible),
        "excluded_n": len(result.excluded),
        "identical_duplicate_n": result.identical_duplicate_n,
        "reason_tallies": result.reason_tallies,
        "latest_per_book_market_n": len(result.latest_per_book_market),
    }
    return inventory, join


def main() -> int:
    require_hd()
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    code_pin = {
        "branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
        "commit": _git("rev-parse", "HEAD"),
        "base": "origin/restore-working-ui",
        "base_commit": _git("merge-base", "HEAD", "origin/restore-working-ui"),
        "reader": "services/model-service/src/services/nfl_odds_reader.py",
        "tests": "services/model-service/tests/test_nfl_odds_reader.py",
    }
    source_pins = {
        "kosedge_data_mounted": hd_mounted(),
        "sqlite": {
            "path": str(HD_SQLITE),
            "bytes": HD_SQLITE.stat().st_size if HD_SQLITE.is_file() else None,
        },
        "jsonl_2020_2023": [
            {
                "season": season,
                "path": str(jsonl_path_for_season(season)),
                "bytes": jsonl_path_for_season(season).stat().st_size
                if jsonl_path_for_season(season).is_file()
                else None,
            }
            for season in sorted(PERMITTED_SEASONS)
        ],
        "open_close_csv": {
            "path": str(HD_OC_CSV),
            "bytes": HD_OC_CSV.stat().st_size if HD_OC_CSV.is_file() else None,
        },
        "forbidden": [
            "Did not open clean/odds/nfl/snapshots-2024|2025|2026 JSONL",
            "Did not open lake snapshots-2024|2025|2026.parquet",
            "Did not treat 2026 nflverse/odds archive as a live feed",
        ],
    }

    jsonl_inv = inventory_jsonl()
    nflverse_inv = inventory_nflverse_games()
    requests_inv = inventory_sqlite_requests()
    raw_inv = inventory_raw_historical()
    lake_inv = inventory_lake_index()
    csv_inv, csv_join = inventory_and_join_csv()
    jsonl_join = join_jsonl_with_explicit_game_cutoff()

    inventory = {
        "generated_at_utc": generated,
        "season_bound": sorted(PERMITTED_SEASONS),
        "overlap_warning": (
            "Old harvest / lake / jsonl / csv / sqlite counts may overlap. "
            "Do not add them into a current deduplicated total."
        ),
        "code_pin": code_pin,
        "source_pins": source_pins,
        "stores": [jsonl_inv, csv_inv, nflverse_inv, requests_inv, raw_inv, lake_inv],
    }
    manifest = {
        "generated_at_utc": generated,
        "code_pin": code_pin,
        "source_pins": source_pins,
        "joins": [jsonl_join, csv_join],
        "exclusion_contract": [
            "missing_cutoff",
            "unresolvable_timestamp",
            "post_cutoff",
            "ambiguous_identity",
            "unknown_team",
            "incompatible_market",
            "market_line_mismatch",
            "missing_value",
            "duplicate_conflict",
            "season_out_of_bounds",
            "no_game_match",
        ],
        "cutoff_rule": "source timestamp <= explicit forecast_cutoff; never substitute a later/closing quote",
        "sign_convention": "odds_api_spread_home_negative_when_home_favored",
    }

    ops = ROOT / "data" / "ops"
    ops.mkdir(parents=True, exist_ok=True)
    inv_json = ops / "nfl-odds-reader-2020-2023-inventory.json"
    man_json = ops / "nfl-odds-reader-2020-2023-join-manifest.json"
    inv_md = ops / "nfl-odds-reader-2020-2023-inventory.md"
    inv_json.write_text(json.dumps(inventory, indent=2) + "\n", encoding="utf-8")
    man_json.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# NFL odds reader inventory — 2020–2023 only",
        "",
        f"Generated: `{generated}`",
        f"Code pin: `{code_pin['commit']}` on `{code_pin['branch']}`",
        "",
        "Read-only. CERT=0. No merge. Paid Odds paused. 2024–25 contents not opened.",
        "",
        inventory["overlap_warning"],
        "",
        "## Stores",
        "",
    ]
    for store in inventory["stores"]:
        lines.append(f"### {store.get('store')}")
        lines.append("")
        lines.append("```json")
        lines.append(json.dumps(store, indent=2))
        lines.append("```")
        lines.append("")
    lines.extend(
        [
            "## Join summary",
            "",
            "```json",
            json.dumps(manifest["joins"], indent=2),
            "```",
            "",
        ]
    )
    inv_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"inventory": str(inv_json), "manifest": str(man_json), "md": str(inv_md)}, indent=2))
    print("JSONL", jsonl_inv["rows"], "rows", jsonl_inv["distinct_games"], "games")
    print("CSV join", csv_join["eligible_n"], "eligible", csv_join["reason_tallies"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
