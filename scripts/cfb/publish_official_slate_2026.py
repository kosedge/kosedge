#!/usr/bin/env python3
"""Publish the in-house KosEdge CFB official slate (W0/W1).

Primary: packaged ESPN team-schedule SoT (cfb_official_schedule_2026.json).
Fact-check: The Odds API NCAAF events (matchup + commence_time).

Rules:
  agree same day, kickoff within 3h → accept (ESPN time/venue/neutral)
  same matchup, kickoff/date conflict → needs_review, keep ESPN, list in ops
  only-in-primary → include as unconfirmed_secondary
  only-in-secondary → do not add; list in ops
  never invent games

Refresh:
  python scripts/cfb/publish_official_slate_2026.py
  ODDS_API_KEY=... python scripts/cfb/publish_official_slate_2026.py
"""

from __future__ import annotations

import json
import os
import re
import sys
import unicodedata
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO = Path(__file__).resolve().parents[2]
ESPN_PATH = (
    REPO
    / "services/model-service/src/services/cfb_season_engine/data/cfb_official_schedule_2026.json"
)
UNIVERSE_PATH = (
    REPO
    / "services/model-service/src/services/cfb_season_engine/data/cfb_fbs_universe_2026.json"
)
NAMES_PATH = REPO / "apps/web/lib/data/cfb-team-names-2026.json"
WEB_OUT = REPO / "apps/web/lib/data/cfb-official-slate-2026.json"
MS_OUT = (
    REPO
    / "services/model-service/src/services/cfb_season_engine/data/cfb_official_slate_2026.json"
)
RAW_DIR = REPO / "data/cfb/raw"
OPS_PATH = REPO / "data/ops/cfb-official-slate-20260817.md"

SLATE_VERSION = "cfb-official-slate-v2-dual-20260817"
PRIMARY_SOURCE = "espn_team_schedule_public"
FACTCHECK_SOURCE = "the_odds_api_ncaaf_events"
KICKOFF_TOLERANCE_SEC = 3 * 3600
WEEKS = (0, 1)
AS_OF = datetime.now(timezone.utc).strftime("%Y-%m-%d")

ALIASES = {
    "north carolina": "UNC",
    "nc state": "NCSU",
    "ole miss": "MISS",
    "miami fl": "MIA",
    "miami (fl)": "MIA",
    "miami": "MIA",
    "miami oh": "M-OH",
    "miami (oh)": "M-OH",
    "uconn": "CONN",
    "connecticut": "CONN",
    "southern miss": "USM",
    "southern mississippi": "USM",
    "texas a&m": "TAMU",
    "texas a m": "TAMU",
    "hawaii": "HAW",
    "san jose state": "SJSU",
    "app state": "APP",
    "appalachian state": "APP",
    "louisiana": "UL",
    "ul lafayette": "UL",
    "utsa": "UTSA",
    "tcu": "TCU",
    "usc": "USC",
    "ucla": "UCLA",
    "lsu": "LSU",
    "byu": "BYU",
    "ucf": "UCF",
    "usf": "USF",
    "unlv": "UNLV",
    "ohio state": "OSU",
    "penn state": "PSU",
    "florida state": "FSU",
    "notre dame": "ND",
    "jacksonville state": "JVST",
    "north dakota state": "NDSU",
    "sacramento state": "SAC",
    "new mexico state": "NMSU",
    "boston college": "BC",
    "georgia tech": "GT",
    "virginia tech": "VT",
    "texas tech": "TTU",
    "texas state": "TXST",
    "ole miss rebels": "MISS",
    "umass": "MASS",
    "umass minutemen": "MASS",
    "massachusetts": "MASS",
    "sam houston": "SHSU",
    "sam houston state": "SHSU",
    "sam houston state bearkats": "SHSU",
    "southern mississippi golden eagles": "USM",
}


def fold(raw: str) -> str:
    s = unicodedata.normalize("NFKD", str(raw or ""))
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    s = s.replace("'", "").replace("`", "").replace("ʻ", "")
    s = re.sub(r"[^a-z0-9\s-]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def bare(code: str) -> str:
    return str(code or "").replace("fcs:", "").replace("FCS:", "").upper()


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_name_index() -> Dict[str, str]:
    raw: Dict[str, List[str]] = {}

    def add(key: str, code: str) -> None:
        f = fold(key)
        if not f:
            return
        raw.setdefault(f, [])
        if code not in raw[f]:
            raw[f].append(code)

    uni = load_json(UNIVERSE_PATH)
    for bucket in ("teams", "transitioning"):
        for code, row in (uni.get(bucket) or {}).items():
            add(code, code)
            add(str(row.get("display_name") or ""), code)
            parts = fold(str(row.get("display_name") or "")).split()
            if len(parts) >= 2:
                add(" ".join(parts[:-1]), code)
    if NAMES_PATH.is_file():
        for code, name in (load_json(NAMES_PATH).get("teams") or {}).items():
            add(code, code)
            add(str(name), code)
    for alias, code in ALIASES.items():
        add(alias, code)
    return {k: v[0] for k, v in raw.items() if len(v) == 1}


def match_name(index: Dict[str, str], name: str) -> Optional[str]:
    return index.get(fold(name))


def parse_iso(raw: Optional[str]) -> Optional[datetime]:
    if not raw:
        return None
    text = str(raw).replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def pair_key(away: str, home: str) -> Tuple[str, str]:
    return (bare(away), bare(home))


def fetch_odds_events(api_key: str) -> List[Dict[str, Any]]:
    url = (
        "https://api.the-odds-api.com/v4/sports/americanfootball_ncaaf/events?"
        + urllib.parse.urlencode({"apiKey": api_key})
    )
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "KosEdgeCFB/1.0 (+https://www.kosedge.com)",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=25) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    return payload if isinstance(payload, list) else []


def conference_for(universe: Dict[str, Any], code: str) -> Optional[str]:
    teams = universe.get("teams") or {}
    row = teams.get(bare(code)) or {}
    conf = row.get("conference")
    return str(conf) if conf else None


def main() -> int:
    espn = load_json(ESPN_PATH)
    universe = load_json(UNIVERSE_PATH)
    index = build_name_index()
    primary = []
    for g in espn.get("games") or []:
        if not isinstance(g, dict):
            continue
        try:
            week = int(g.get("week"))
        except (TypeError, ValueError):
            continue
        if week in WEEKS:
            primary.append(g)

    api_key = (
        os.environ.get("ODDS_API_KEY")
        or os.environ.get("ODDS_API_KEY_BACKUP")
        or ""
    ).strip()
    events: List[Dict[str, Any]] = []
    factcheck_error: Optional[str] = None
    if api_key:
        try:
            events = fetch_odds_events(api_key)
        except Exception as exc:  # noqa: BLE001 — publish still writes primary
            factcheck_error = str(exc)
    else:
        factcheck_error = "ODDS_API_KEY not set"

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    (RAW_DIR / "odds_api_ncaaf_events_2026.json").write_text(
        json.dumps(
            {
                "as_of": AS_OF,
                "source": FACTCHECK_SOURCE,
                "n": len(events),
                "error": factcheck_error,
                "events": events,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    secondary: Dict[Tuple[str, str], Dict[str, Any]] = {}
    unmatched_names: List[str] = []
    for ev in events:
        home = match_name(index, str(ev.get("home_team") or ""))
        away = match_name(index, str(ev.get("away_team") or ""))
        if not home or not away:
            unmatched_names.append(
                f"{ev.get('away_team')} @ {ev.get('home_team')}"
            )
            continue
        secondary[pair_key(away, home)] = {
            "home": home,
            "away": away,
            "kickoff": ev.get("commence_time"),
            "home_name": ev.get("home_team"),
            "away_name": ev.get("away_team"),
        }

    published: List[Dict[str, Any]] = []
    conflicts: List[Dict[str, Any]] = []
    only_primary: List[str] = []
    agreed = 0
    for raw in primary:
        home = str(raw.get("home") or "")
        away = str(raw.get("away") or "")
        key = pair_key(away, home)
        espn_ko = parse_iso(str(raw.get("kickoff") or raw.get("date") or ""))
        sec = secondary.get(key)
        status = "unconfirmed_secondary"
        fact = "unconfirmed"
        if sec:
            sec_ko = parse_iso(str(sec.get("kickoff") or ""))
            same_day = bool(
                espn_ko
                and sec_ko
                and espn_ko.date() == sec_ko.date()
            )
            delta = (
                abs((espn_ko - sec_ko).total_seconds())
                if espn_ko and sec_ko
                else None
            )
            if same_day and delta is not None and delta <= KICKOFF_TOLERANCE_SEC:
                status = "accepted"
                fact = "agree"
                agreed += 1
            else:
                status = "needs_review"
                fact = "conflict"
                conflicts.append(
                    {
                        "away": away,
                        "home": home,
                        "week": raw.get("week"),
                        "espn_kickoff": raw.get("kickoff"),
                        "odds_kickoff": sec.get("kickoff"),
                        "same_day": same_day,
                        "delta_hours": (
                            round(delta / 3600, 2) if delta is not None else None
                        ),
                    }
                )
        else:
            only_primary.append(f"{away} @ {home} (W{raw.get('week')})")

        published.append(
            {
                "week": int(raw.get("week")),
                "game_id": raw.get("game_id") or raw.get("espn_game_id"),
                "home": home,
                "away": away,
                "home_name": raw.get("home_name"),
                "away_name": raw.get("away_name"),
                "kickoff": raw.get("kickoff") or raw.get("date"),
                "neutral_site": bool(raw.get("neutral_site")),
                "venue": raw.get("venue"),
                "network": raw.get("network"),
                "conference": conference_for(universe, home),
                "conference_game": bool(raw.get("conference_game")),
                "fcs_home": bool(raw.get("fcs_home")),
                "fcs_away": bool(raw.get("fcs_away")),
                "fbs_vs_fbs": (not raw.get("fcs_home")) and (not raw.get("fcs_away")),
                "status": status,
                "factcheck": fact,
            }
        )

    used_keys = {pair_key(g["away"], g["home"]) for g in published}
    only_secondary = [
        f"{row['away']} @ {row['home']} ({row.get('kickoff')})"
        for key, row in sorted(secondary.items())
        if key not in used_keys
    ]

    w0 = [g for g in published if g["week"] == 0]
    w1 = [g for g in published if g["week"] == 1]
    artifact = {
        "slate_version": SLATE_VERSION,
        "season": 2026,
        "as_of": AS_OF,
        "official": True,
        "slate_complete": True,
        "source": "kosedge_official_slate",
        "primary_source": PRIMARY_SOURCE,
        "factcheck_source": FACTCHECK_SOURCE,
        "primary_as_of": espn.get("as_of"),
        "used_in_spread": False,
        "kei": False,
        "weeks": list(WEEKS),
        "n_games": len(published),
        "n_fbs_vs_fbs": sum(1 for g in published if g["fbs_vs_fbs"]),
        "n_w0": len(w0),
        "n_w1": len(w1),
        "n_w0_fbs_vs_fbs": sum(1 for g in w0 if g["fbs_vs_fbs"]),
        "n_w1_fbs_vs_fbs": sum(1 for g in w1 if g["fbs_vs_fbs"]),
        "factcheck": {
            "primary_w0": len(w0),
            "primary_w1": len(w1),
            "secondary_events": len(events),
            "secondary_matched_names": len(secondary),
            "agreed": agreed,
            "conflicts": conflicts,
            "only_primary": only_primary,
            "only_secondary": only_secondary,
            "unmatched_secondary_names": unmatched_names,
            "error": factcheck_error,
            "kickoff_tolerance_hours": 3,
            "rule": (
                "ESPN is primary. Odds API confirms matchup + day/time. "
                "Conflicts keep ESPN and flag needs_review. "
                "Only-secondary rows are not added."
            ),
        },
        "games": published,
    }

    text = json.dumps(artifact, indent=2) + "\n"
    WEB_OUT.write_text(text, encoding="utf-8")
    MS_OUT.write_text(text, encoding="utf-8")

    ops = f"""# CFB Official Slate — in-house dual-source

**Date:** {AS_OF}
**Slate version:** `{SLATE_VERSION}`
**Desk SoT:** `apps/web/lib/data/cfb-official-slate-2026.json` (copy in model-service)

## Sources

| Role | Source | Notes |
|------|--------|--------|
| Primary | ESPN public team schedule (`{PRIMARY_SOURCE}`) | Packaged `{espn.get("as_of")}` · 889-game season file · not live-scraped this pass |
| Fact-check | The Odds API NCAAF events | Structured `/v4/sports/americanfootball_ncaaf/events` · already in stack |
| Tried / not used | CFBD `/games` | 401 without `CFBD_API_KEY` |
| Tried / not used | NCAA.com scoreboard JSON | 404 for 2026 week paths |
| Tried / not used | SportsDataverse 2026 parquet | Not a live 2026 schedule publish |
| Tried / not used | Wikipedia season page | Featured kickoffs only, not full FBS |

## Counts

| Week | Primary ESPN | Fact-check matched | Published | FBS–FBS |
|------|-------------:|-------------------:|----------:|--------:|
| 0 | {len(w0)} | {sum(1 for g in w0 if g["factcheck"]=="agree")} | {len(w0)} | {sum(1 for g in w0 if g["fbs_vs_fbs"])} |
| 1 | {len(w1)} | {sum(1 for g in w1 if g["factcheck"]=="agree")} | {len(w1)} | {sum(1 for g in w1 if g["fbs_vs_fbs"])} |
| **Total** | **{len(published)}** | **{agreed}** | **{len(published)}** | **{sum(1 for g in published if g["fbs_vs_fbs"])}** |

Secondary events pulled: {len(events)} · name-matched: {len(secondary)}
Fact-check error: {factcheck_error or "none"}

## Conflicts (needs_review, ESPN time kept)

{json.dumps(conflicts, indent=2) if conflicts else "_None._"}

## Only in primary (published as `unconfirmed_secondary`)

{chr(10).join(f"- {row}" for row in only_primary) or "_None._"}

## Only in secondary (not added)

{chr(10).join(f"- {row}" for row in only_secondary[:40]) or "_None._"}
{"" if len(only_secondary) <= 40 else f"- … +{len(only_secondary)-40} more (later weeks / unmatched desk weeks)"}

## Refresh

```bash
ODDS_API_KEY=… python scripts/cfb/publish_official_slate_2026.py
```

Re-run weekly (or when ESPN kickoffs move). Primary refresh still comes from the packaged ESPN season file; replace that file first if the team-schedule ingest is re-run.

## Doctrine

KosEdge slate is desk SoT. Sources are inputs. Sim / KEI math is unchanged.
"""
    OPS_PATH.write_text(ops, encoding="utf-8")

    print(f"published {len(published)} games → {WEB_OUT.relative_to(REPO)}")
    print(f"agreed {agreed} conflicts {len(conflicts)} only_primary {len(only_primary)} only_secondary {len(only_secondary)}")
    print(f"ops {OPS_PATH.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
