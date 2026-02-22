#!/usr/bin/env python3
"""
Capture SportsData.io API data for future models.

Two modes:
  Replay: Uses a replay session key (from Replay Dashboard). Fetches metadata then all endpoints.
  Production: Uses your main API key (SPORTSDATA_API_KEY or SPORTSDATA_REPLAY_KEY in .env.local)
    with api.sportsdata.io. Pass --season/--week/--date or rely on package_defaults in config.
    Historical data is available via the same endpoints with past dates/seasons.

Saves to data/raw/sportsdata_replay/{league}/{package}/ (same dir for both modes).

Usage (from repo root or apps/web):
  # Production (your key, historical by season/week/date):
  python apps/web/scripts/capture_sportsdata_replay.py --production --league nfl --package nfl_2023_week1
  python apps/web/scripts/capture_sportsdata_replay.py --production --league nfl --season 2023reg --week 1 --package nfl_2023_week1

  # Replay (replay session key from Dashboard):
  python apps/web/scripts/capture_sportsdata_replay.py --league nfl --package nfl_2023_week1

Config: data/raw/sportsdata_replay_endpoints.json.
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

import requests

_WEB = Path(__file__).resolve().parent.parent
REPLAY_BASE = "https://replay.sportsdata.io"
PRODUCTION_BASE = "https://api.sportsdata.io"
METADATA_PATH = "/api/metadata"
CONFIG_PATH = _WEB / "data" / "raw" / "sportsdata_replay_endpoints.json"
OUT_ROOT = _WEB / "data" / "raw" / "sportsdata_replay"


def _load_dotenv() -> None:
    """Load SPORTSDATA_REPLAY_KEY and SPORTSDATA_API_KEY from .env.local / .env if not set."""
    wanted = {"SPORTSDATA_REPLAY_KEY", "SPORTSDATA_API_KEY"}
    if all(os.environ.get(k) for k in wanted):
        return
    for name in (".env.local", ".env"):
        p = _WEB / name
        if not p.is_file():
            continue
        with open(p, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                k = k.strip()
                if k in wanted:
                    os.environ[k] = v.strip().strip('"').strip("'")
                    wanted.discard(k)
                    if not wanted:
                        return


def load_config(config_path: Path | None = None) -> dict:
    path = config_path or CONFIG_PATH
    if not path.exists():
        print(f"Config not found: {path}. Create it from sportsdata_replay_endpoints.json.")
        return {}
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    data.pop("_comment", None)
    return data


def fetch_metadata(key: str) -> dict:
    """Fetch replay context (current date/time in replay). Returns {} on 400 (key may be production or replay not started)."""
    url = f"{REPLAY_BASE}{METADATA_PATH}"
    r = requests.get(url, params={"key": key}, timeout=15)
    if r.status_code != 200:
        if r.status_code == 400:
            print("  Metadata 400: use a Replay key from Dashboard (Start a Replay → copy key). Using package_defaults.")
        return {}
    return r.json()


def build_substitutions(metadata: dict, defaults: dict, league: str) -> dict:
    """Build {placeholder: value} for path substitution. Prefer metadata, fallback to package_defaults."""
    subs = {}
    defaults = (defaults or {}).get(league) or {}
    # Date: metadata often has CurrentDate, Date, or similar (EST)
    for k in ("CurrentDate", "Date", "CurrentDateTime", "date"):
        if isinstance(metadata.get(k), str) and len(metadata[k]) >= 10:
            subs["date"] = metadata[k][:10]
            break
    if "date" not in subs and defaults.get("date"):
        subs["date"] = defaults["date"]
    if "date" not in subs:
        subs["date"] = "2024-01-15"
    for key in ("season", "week"):
        subs[key] = str(metadata.get(key) or metadata.get(key.capitalize()) or defaults.get(key) or "")
    if not subs.get("season") and defaults.get("season"):
        subs["season"] = defaults["season"]
    if not subs.get("week") and defaults.get("week"):
        subs["week"] = defaults["week"]
    return subs


def build_substitutions_production(
    defaults: dict, league: str, season: str | None = None, week: str | None = None, date: str | None = None
) -> dict:
    """Build substitutions from package_defaults + optional CLI overrides (production API has no metadata)."""
    league_defaults = (defaults or {}).get(league) or {}
    subs = {
        "season": season or league_defaults.get("season") or "",
        "week": week or league_defaults.get("week") or "",
        "date": date or league_defaults.get("date") or "2024-01-15",
    }
    subs["season"] = str(subs["season"])
    subs["week"] = str(subs["week"])
    if len(subs["date"]) < 10:
        subs["date"] = "2024-01-15"
    return subs


def substitute_path(path: str, subs: dict) -> str:
    for k, v in subs.items():
        path = path.replace("{" + k + "}", str(v))
    return path


def extract_game_ids(data: object) -> list[int]:
    """Extract game IDs from a scores/games response. Tries common field names."""
    ids = []
    if isinstance(data, list):
        for item in data:
            ids.extend(extract_game_ids(item))
    elif isinstance(data, dict):
        for key in ("GlobalGameID", "GameID", "ScoreID", "GameKey", "game_id"):
            if key in data and data[key] is not None:
                try:
                    ids.append(int(data[key]))
                except (TypeError, ValueError):
                    pass
        for v in data.values():
            ids.extend(extract_game_ids(v))
    return list(dict.fromkeys(ids))


def capture_league(
    key: str,
    league: str,
    package: str,
    config: dict,
    base_url: str = REPLAY_BASE,
    subs_override: dict | None = None,
) -> int:
    endpoints = config.get(league)
    if not endpoints:
        print(f"No endpoints configured for league={league}. Add to {CONFIG_PATH}")
        return 0
    defaults = config.get("package_defaults") or {}
    if subs_override is not None:
        subs = subs_override
    else:
        metadata = fetch_metadata(key)
        subs = build_substitutions(metadata or {}, defaults, league)
    out_dir = OUT_ROOT / league / package
    out_dir.mkdir(parents=True, exist_ok=True)

    by_segment = [e for e in endpoints if not e.get("needs_gameid")]
    by_game = [e for e in endpoints if e.get("needs_gameid")]
    saved = 0

    # 1) Season / week / date level (no gameid)
    for spec in by_segment:
        path_tpl = spec.get("path") or spec.get("path_template", "")
        slug = spec.get("slug", "endpoint")
        path = substitute_path(path_tpl, subs)
        if "{" in path:
            print(f"  Skip {slug}: unresolved placeholders in {path}")
            continue
        url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"
        try:
            r = requests.get(url, params={"key": key}, timeout=30)
            if r.status_code != 200:
                print(f"  [{spec.get('segment', '?')}] {slug}: HTTP {r.status_code}")
                continue
            data = r.json()
            out_file = out_dir / f"{slug}.json"
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            print(f"  Saved {out_file.relative_to(OUT_ROOT)}")
            saved += 1
            # If this response can supply game IDs for by-game endpoints, collect them
            if spec.get("game_list_source") and by_game:
                gids = extract_game_ids(data)
                if gids:
                    subs["_game_ids"] = gids
        except Exception as e:
            print(f"  [{spec.get('segment', '?')}] {slug}: {e}")
        time.sleep(0.3)

    # 2) Game level: play-by-play, pitch-by-pitch, box score, etc. (per gameid)
    game_ids = subs.get("_game_ids") or []
    if not game_ids and by_game:
        print("  No game IDs found from week/date feeds; skip game-level endpoints or check game_list_source.")
    for gameid in game_ids:
        game_dir = out_dir / "by_game" / str(gameid)
        game_dir.mkdir(parents=True, exist_ok=True)
        subs["gameid"] = gameid
        for spec in by_game:
            path_tpl = spec.get("path") or spec.get("path_template", "")
            slug = spec.get("slug", "endpoint")
            path = substitute_path(path_tpl, subs)
            if "{" in path:
                continue
            url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"
            try:
                r = requests.get(url, params={"key": key}, timeout=30)
                if r.status_code != 200:
                    continue
                out_file = game_dir / f"{slug}.json"
                with open(out_file, "w", encoding="utf-8") as f:
                    json.dump(r.json(), f, indent=2)
                saved += 1
            except Exception:
                pass
            time.sleep(0.2)
        if game_ids and (game_ids.index(gameid) + 1) % 10 == 0:
            print(f"  Games: {game_ids.index(gameid) + 1}/{len(game_ids)}")
    if game_ids and by_game:
        print(f"  Saved by_game/ ({len(by_game)} endpoints x {len(game_ids)} games)")
    return saved


def main() -> int:
    # When run via pnpm run capture:replay -- --league nfl ..., argv has a leading '--'; strip it
    if len(sys.argv) > 1 and sys.argv[1] == "--":
        sys.argv = [sys.argv[0]] + sys.argv[2:]
    ap = argparse.ArgumentParser(
        description="Capture SportsData.io API data (Replay or Production historical)."
    )
    ap.add_argument("--league", "-l", help="League to capture (nfl, nba, ncaab, mlb, nhl, ncaaf, wnba)")
    ap.add_argument("--package", "-p", default="default", help="Package name for output folder")
    ap.add_argument("--all", action="store_true", help="Run all leagues in config")
    ap.add_argument("--config", default=None, help="Override config JSON path")
    ap.add_argument(
        "--production",
        action="store_true",
        help="Use production API (api.sportsdata.io) with your key; pass --season/--week/--date or use package_defaults.",
    )
    ap.add_argument("--season", help="Season (e.g. 2023reg, 2023) for --production")
    ap.add_argument("--week", help="Week (e.g. 1) for --production")
    ap.add_argument("--date", help="Date YYYY-MM-DD for --production")
    args = ap.parse_args()

    _load_dotenv()
    production = args.production
    if production:
        key = (
            os.environ.get("SPORTSDATA_API_KEY")
            or os.environ.get("SPORTSDATA_REPLAY_KEY")
            or ""
        ).strip()
        if not key:
            print("Set SPORTSDATA_API_KEY or SPORTSDATA_REPLAY_KEY in .env.local for production capture.")
            return 1
    else:
        key = (os.environ.get("SPORTSDATA_REPLAY_KEY") or "").strip()
        if not key:
            print("Set SPORTSDATA_REPLAY_KEY in .env.local or env (replay key from Replay Dashboard).")
            return 1

    config_path = Path(args.config) if args.config else CONFIG_PATH
    config = load_config(config_path)
    if not config:
        return 1

    # Leagues that have endpoint lists (exclude package_defaults and _comment)
    all_leagues = [k for k in config if k not in ("package_defaults", "_comment") and isinstance(config.get(k), list)]
    if args.all:
        leagues = all_leagues
    elif args.league:
        if args.league not in config or not isinstance(config.get(args.league), list):
            print(f"Unknown or missing league: {args.league}. Options: {all_leagues}")
            return 1
        leagues = [args.league]
    else:
        print("Use --league LEAGUE or --all.")
        return 1

    package = os.environ.get("REPLAY_PACKAGE_NAME") or args.package
    base_url = PRODUCTION_BASE if production else REPLAY_BASE
    defaults = config.get("package_defaults") or {}
    total = 0
    for league in leagues:
        if league == "package_defaults":
            continue
        print(f"League: {league} package={package}" + (" (production)" if production else ""))
        if production:
            subs = build_substitutions_production(
                defaults, league,
                season=args.season, week=args.week, date=args.date,
            )
            total += capture_league(key, league, package, config, base_url=base_url, subs_override=subs)
        else:
            total += capture_league(key, league, package, config, base_url=base_url)
    print(f"Saved {total} responses under {OUT_ROOT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
