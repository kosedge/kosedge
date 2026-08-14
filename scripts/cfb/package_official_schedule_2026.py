#!/usr/bin/env python3
"""Package the official 2026 FBS schedule from ESPN team schedules.

SoT: ESPN public team schedule API (seasontype=2 regular; 3 postseason if present).
Not CFBD (key required). Not the densified sample seed.

Usage:
  python scripts/cfb/package_official_schedule_2026.py
"""

from __future__ import annotations

import json
import sys
import time
import urllib.request
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))

from src.services.cfb_season_engine.conferences import conference_for  # noqa: E402
from src.services.cfb_season_engine.fbs_universe import (  # noqa: E402
    load_fbs_universe,
    official_fbs_codes,
)
from src.services.cfb_season_engine.official_schedule import (  # noqa: E402
    OFFICIAL_SCHEDULE_PATH,
    WAREHOUSE_COPY,
    coverage_report,
    resolve_side,
)

ESPN_TEAMS = (
    "https://site.web.api.espn.com/apis/site/v2/sports/football/college-football/"
    "teams?limit=1000"
)
ESPN_SCHED = (
    "https://site.web.api.espn.com/apis/site/v2/sports/football/college-football/"
    "teams/{espn_id}/schedule?season=2026&seasontype={stype}"
)
UA = {
    "User-Agent": "Mozilla/5.0 (compatible; KosEdgeCFB/0.12; +https://www.kosedge.com)",
    "Accept": "application/json",
    "Referer": "https://www.espn.com/",
}


def _get(url: str) -> Any:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=45) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _espn_directory() -> List[Dict[str, str]]:
    blob = _get(ESPN_TEAMS)
    rows = []
    for row in blob["sports"][0]["leagues"][0]["teams"]:
        t = row["team"]
        rows.append(
            {
                "id": str(t.get("id") or ""),
                "abbr": str(t.get("abbreviation") or "").upper(),
                "name": str(t.get("displayName") or ""),
            }
        )
    return rows


def _map_official_to_espn(directory: List[Dict[str, str]]) -> Dict[str, Dict[str, str]]:
    official = official_fbs_codes()
    book = load_fbs_universe()
    names = {
        code: str((book.get("teams") or {}).get(code, {}).get("display_name") or "")
        for code in official
    }
    out: Dict[str, Dict[str, str]] = {}
    for row in directory:
        code, fcs = resolve_side(row["abbr"], row["name"], official=official)
        if fcs or code not in official:
            continue
        prev = out.get(code)
        if prev is None or row["name"] == names.get(code):
            out[code] = row
    return out


def _week_from_event(event: Dict[str, Any]) -> int:
    week = event.get("week") or {}
    try:
        n = int(week.get("number") or 0)
    except (TypeError, ValueError):
        n = 0
    kickoff = str(event.get("date") or "")
    if kickoff[:10] and kickoff[:10] < "2026-09-01":
        return 0
    return n


def _ingest_events(
    events: List[Dict[str, Any]],
    *,
    official: Any,
    season_type: str,
) -> List[Dict[str, Any]]:
    rows = []
    for event in events or []:
        comps = event.get("competitions") or []
        if not comps:
            continue
        comp = comps[0]
        sides = {c.get("homeAway"): c for c in (comp.get("competitors") or [])}
        home_c, away_c = sides.get("home") or {}, sides.get("away") or {}
        home_t = home_c.get("team") or {}
        away_t = away_c.get("team") or {}
        home, home_fcs = resolve_side(
            str(home_t.get("abbreviation") or ""),
            str(home_t.get("displayName") or ""),
            official=official,
        )
        away, away_fcs = resolve_side(
            str(away_t.get("abbreviation") or ""),
            str(away_t.get("displayName") or ""),
            official=official,
        )
        if home == away:
            continue
        kickoff = str(event.get("date") or comp.get("date") or "")
        week = _week_from_event(event)
        gid = str(event.get("id") or comp.get("id") or "")
        if not gid:
            gid = f"2026_w{week}_{away}@{home}"
        conf = False
        if not home_fcs and not away_fcs:
            conf = conference_for(home) == conference_for(away) and conference_for(
                home
            ) != "Independent"
        rows.append(
            {
                "game_id": gid,
                "source_game_id": gid,
                "espn_game_id": gid,
                "season": 2026,
                "week": week,
                "kickoff": kickoff,
                "date": kickoff[:10],
                "home": home,
                "away": away,
                "home_name": str(home_t.get("displayName") or ""),
                "away_name": str(away_t.get("displayName") or ""),
                "neutral_site": bool(comp.get("neutralSite")),
                "conference_game": conf,
                "fcs_home": home_fcs,
                "fcs_away": away_fcs,
                "fbs_vs_fcs": home_fcs or away_fcs,
                "season_type": season_type,
                "venue": str((comp.get("venue") or {}).get("fullName") or ""),
            }
        )
    return rows


def main() -> int:
    official = official_fbs_codes()
    print("Loading ESPN team directory…", file=sys.stderr)
    directory = _espn_directory()
    mapped = _map_official_to_espn(directory)
    missing = sorted(official - set(mapped))
    print(f"Official FBS mapped to ESPN ids: {len(mapped)} / {len(official)}", file=sys.stderr)
    if missing:
        print(f"Unmapped official teams: {missing}", file=sys.stderr)

    by_id: Dict[str, Dict[str, Any]] = {}
    fetch_errors: List[str] = []
    for i, (code, meta) in enumerate(sorted(mapped.items()), start=1):
        for stype, label in ((2, "regular"), (3, "postseason")):
            url = ESPN_SCHED.format(espn_id=meta["id"], stype=stype)
            try:
                blob = _get(url)
            except Exception as exc:  # noqa: BLE001
                fetch_errors.append(f"{code}/{label}: {exc}")
                continue
            rows = _ingest_events(blob.get("events") or [], official=official, season_type=label)
            for row in rows:
                by_id[row["game_id"]] = row
            time.sleep(0.08)
        if i % 20 == 0:
            print(f"  fetched {i}/{len(mapped)} teams; {len(by_id)} unique games", file=sys.stderr)

    games = sorted(by_id.values(), key=lambda r: (r["week"], r["kickoff"], r["game_id"]))
    from src.services.cfb_season_engine.official_schedule import games_from_blob

    blob = {
        "season": 2026,
        "as_of": date.today().isoformat(),
        "official": True,
        "source": "espn_team_schedule_public",
        "source_detail": (
            "ESPN site.web.api team schedule, seasontype=2 regular + 3 postseason. "
            "One SoT. Not densified. Not CFBD."
        ),
        "fidelity": "official_espn_slate",
        "unmapped_official_teams": missing,
        "fetch_errors": fetch_errors[:20],
        "n_espn_ids": len(mapped),
        "games": games,
        "postseason_games": sum(1 for g in games if g.get("season_type") == "postseason"),
        "notes": [
            "Week 0 = kickoff date before 2026-09-01 (ESPN often labels these Week 1).",
            "FCS opponents kept and labeled fcs:* — not generic -25.",
            "CFP / bowls included only if ESPN postseason schedules returned events.",
            "used_in_spread stays false. Research only.",
        ],
    }
    cov = coverage_report(games_from_blob(blob), official=official)
    blob["coverage"] = cov
    blob["slate_complete"] = bool(cov.get("slate_complete"))
    blob["n_games"] = cov.get("n_games")

    OFFICIAL_SCHEDULE_PATH.parent.mkdir(parents=True, exist_ok=True)
    OFFICIAL_SCHEDULE_PATH.write_text(json.dumps(blob, indent=2) + "\n", encoding="utf-8")
    WAREHOUSE_COPY.parent.mkdir(parents=True, exist_ok=True)
    WAREHOUSE_COPY.write_text(json.dumps(blob, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "path": str(OFFICIAL_SCHEDULE_PATH),
                "n_games": blob["n_games"],
                "slate_complete": blob["slate_complete"],
                "by_week": cov.get("by_week"),
                "fcs_games": cov.get("fcs_games"),
                "missing_teams": cov.get("missing_teams"),
                "unmapped": missing,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
