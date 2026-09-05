#!/usr/bin/env python3
"""Ingest ESPN NCAAM scoreboard → packaged official schedule JSON (Option A).

Usage (from repo root):
  python scripts/ncaam/ingest_espn_official_schedule.py --season 2022-23
  python scripts/ncaam/ingest_espn_official_schedule.py --season 2023-24 \\
      --end-date 2024-01-28

Rules:
  - Real ESPN events only (never invent games / tips).
  - B7 map via apps/web ncaam identity — fail-closed (omit unmapped).
  - slate_complete stays false unless explicitly forced after honest densify
    (default: false; this script never auto-stamps true).
  - odds_event_id stub is always null (no invented Odds↔ESPN links).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO = Path(__file__).resolve().parents[2]
WEB_SRC = REPO / "apps" / "web" / "src"
if str(WEB_SRC) not in sys.path:
    sys.path.insert(0, str(WEB_SRC))

from ncaam_espn_schedule_map import map_espn_event_sides  # noqa: E402

ESPN_SCOREBOARD = (
    "https://site.web.api.espn.com/apis/site/v2/sports/basketball/"
    "mens-college-basketball/scoreboard"
)
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
OUT_DIR = (
    REPO
    / "services"
    / "model-service"
    / "src"
    / "services"
    / "ncaam_schedule"
    / "data"
)

# Academic season → inclusive tip window (regular season emphasis).
SEASON_WINDOWS = {
    "2022-23": (date(2022, 11, 1), date(2023, 4, 10)),
    "2023-24": (date(2023, 11, 1), date(2024, 4, 10)),
    # 2024-25 sealed-holdout candidate window (tip dates inclusive).
    "2024-25": (date(2024, 11, 4), date(2025, 4, 8)),
}


def _http_get_json(url: str, *, timeout: float = 25.0, retries: int = 4) -> Dict[str, Any]:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "Referer": "https://www.espn.com/mens-college-basketball/scoreboard",
        },
    )
    last_exc: Exception | None = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            last_exc = exc
            # Back off on rate-limit / forbid; ESPN sometimes 403s burst traffic.
            if exc.code in (403, 429, 500, 502, 503) and attempt + 1 < retries:
                time.sleep(0.8 * (2**attempt))
                continue
            raise
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_exc = exc
            if attempt + 1 < retries:
                time.sleep(0.5 * (2**attempt))
                continue
            raise
    assert last_exc is not None
    raise last_exc

def fetch_scoreboard_day(day: date) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    params = urllib.parse.urlencode(
        {
            "dates": day.strftime("%Y%m%d"),
            "groups": "50",
            "limit": "500",
        }
    )
    url = f"{ESPN_SCOREBOARD}?{params}"
    try:
        payload = _http_get_json(url)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        return [], f"{day.isoformat()}: {exc}"
    events = payload.get("events") or []
    if not isinstance(events, list):
        return [], f"{day.isoformat()}: events not a list"
    return events, None


def _status_label(event: Dict[str, Any]) -> str:
    st = (event.get("status") or {}).get("type") or {}
    if st.get("completed") or str(st.get("state") or "").lower() == "post":
        return "final"
    state = str(st.get("state") or "").lower()
    if state == "in":
        return "in"
    if state == "pre":
        return "scheduled"
    name = str(st.get("name") or "").lower()
    if "final" in name:
        return "final"
    return state or "unknown"


def parse_event(event: Dict[str, Any], *, season_key: str, season_end_year: int) -> Dict[str, Any]:
    comps = (event.get("competitions") or [{}])[0] or {}
    competitors = comps.get("competitors") or []
    home = next(
        (c for c in competitors if str(c.get("homeAway") or "").lower() == "home"),
        None,
    )
    away = next(
        (c for c in competitors if str(c.get("homeAway") or "").lower() == "away"),
        None,
    )
    tip = str(event.get("date") or comps.get("date") or comps.get("startDate") or "")
    espn_gid = str(event.get("id") or comps.get("id") or "").strip()
    venue = comps.get("venue") or {}
    address = venue.get("address") or {}
    home_team = (home or {}).get("team") or {}
    away_team = (away or {}).get("team") or {}
    mapped = (
        map_espn_event_sides(home_team, away_team)
        if home and away
        else {
            "ok": False,
            "home": None,
            "away": None,
            "home_name": "",
            "away_name": "",
            "home_espn_id": "",
            "away_espn_id": "",
            "reason": "missing_side",
            "home_matched_alias": None,
            "away_matched_alias": None,
        }
    )
    home_score = _score((home or {}).get("score"))
    away_score = _score((away or {}).get("score"))
    season_meta = event.get("season") or {}
    season_type = "regular"
    stype = season_meta.get("type")
    if stype == 3:
        season_type = "postseason"
    elif stype == 1:
        season_type = "preseason"
    return {
        "espn_game_id": espn_gid,
        "tipoff": tip.replace("+00:00", "Z") if tip.endswith("+00:00") else tip,
        "date": tip[:10] if tip else "",
        "home_team_raw": home_team,
        "away_team_raw": away_team,
        # Preserve null when ESPN omits the field (unknown ≠ False).
        "neutral_site": (
            None if "neutralSite" not in comps else bool(comps.get("neutralSite"))
        ),
        "conference_game": bool(comps.get("conferenceCompetition")),
        "venue": str(venue.get("fullName") or ""),
        "venue_city": str(address.get("city") or ""),
        "venue_state": str(address.get("state") or ""),
        "home_score": home_score,
        "away_score": away_score,
        "status": _status_label(event),
        "season_type": season_type,
        "espn_season_year": season_meta.get("year"),
        "mapped": mapped,
        "season": season_key,
        "season_end_year": season_end_year,
    }


def _score(raw: Any) -> Optional[float]:
    if raw is None or raw == "":
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def build_mapped_game(parsed: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    mapped = parsed["mapped"]
    if not mapped.get("ok"):
        return None
    espn_gid = parsed["espn_game_id"]
    if not espn_gid:
        return None
    return {
        "game_id": espn_gid,
        "source_game_id": espn_gid,
        "espn_game_id": espn_gid,
        "season": parsed["season"],
        "season_end_year": parsed["season_end_year"],
        "tipoff": parsed["tipoff"],
        "kickoff": parsed["tipoff"],  # CFB-field alias for shared tooling
        "date": parsed["date"],
        "home": mapped["home"],
        "away": mapped["away"],
        "home_name": mapped["home_name"],
        "away_name": mapped["away_name"],
        "home_espn_id": mapped["home_espn_id"],
        "away_espn_id": mapped["away_espn_id"],
        "home_matched_alias": mapped.get("home_matched_alias"),
        "away_matched_alias": mapped.get("away_matched_alias"),
        "neutral_site": parsed["neutral_site"],
        "conference_game": parsed["conference_game"],
        "season_type": parsed["season_type"],
        "venue": parsed["venue"],
        "venue_city": parsed["venue_city"],
        "venue_state": parsed["venue_state"],
        "home_score": parsed["home_score"],
        "away_score": parsed["away_score"],
        "status": parsed["status"],
        "map_status": "b7_both",
        # Future E hybrid stub — do not invent Odds↔ESPN links.
        "odds_event_id": None,
    }


def ingest_window(
    *,
    season_key: str,
    start: date,
    end: date,
    delay_s: float = 0.2,
    archive_raw_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    season_end_year = int(season_key.split("-")[0]) + 1
    games: List[Dict[str, Any]] = []
    seen: set[str] = set()
    fetch_errors: List[str] = []
    unmapped_sample: List[Dict[str, Any]] = []
    espn_events = 0
    mapped_both = 0
    omit_unmapped = 0
    omit_dup = 0
    miss_names: Dict[str, int] = {}
    raw_receipts: List[Dict[str, Any]] = []

    if archive_raw_dir is not None:
        archive_raw_dir.mkdir(parents=True, exist_ok=True)

    day = start
    while day <= end:
        events, err = fetch_scoreboard_day(day)
        if archive_raw_dir is not None:
            import hashlib

            envelope = {
                "day": day.isoformat(),
                "endpoint": ESPN_SCOREBOARD,
                "captured_at_utc": datetime.now(timezone.utc).isoformat(),
                "schema_version": "espn-scoreboard-raw-v1",
                "error": err,
                "payload": {"events": events} if not err else None,
            }
            raw_bytes = json.dumps(
                envelope, sort_keys=True, separators=(",", ":")
            ).encode("utf-8")
            raw_path = archive_raw_dir / f"espn_scoreboard_{day.isoformat()}.json"
            raw_path.write_bytes(raw_bytes)
            digest = hashlib.sha256(raw_bytes).hexdigest()
            (archive_raw_dir / f"espn_scoreboard_{day.isoformat()}.sha256").write_text(
                digest + "\n", encoding="utf-8"
            )
            raw_receipts.append(
                {
                    "day": day.isoformat(),
                    "path": raw_path.name,
                    "sha256": digest,
                    "n_events": len(events),
                    "error": err,
                }
            )
        if err:
            fetch_errors.append(err)
        for event in events:
            espn_events += 1
            parsed = parse_event(
                event, season_key=season_key, season_end_year=season_end_year
            )
            mapped_row = build_mapped_game(parsed)
            if mapped_row is None:
                omit_unmapped += 1
                m = parsed["mapped"]
                if not m.get("home"):
                    raw = str(m.get("home_name") or "").strip()
                    if raw:
                        miss_names[raw] = miss_names.get(raw, 0) + 1
                if not m.get("away"):
                    raw = str(m.get("away_name") or "").strip()
                    if raw:
                        miss_names[raw] = miss_names.get(raw, 0) + 1
                if len(unmapped_sample) < 40:
                    unmapped_sample.append(
                        {
                            "espn_game_id": parsed["espn_game_id"],
                            "tipoff": parsed["tipoff"],
                            "home_name": m.get("home_name"),
                            "away_name": m.get("away_name"),
                            "home": m.get("home"),
                            "away": m.get("away"),
                            "reason": m.get("reason"),
                        }
                    )
                continue
            gid = mapped_row["game_id"]
            if gid in seen:
                omit_dup += 1
                continue
            seen.add(gid)
            mapped_both += 1
            games.append(mapped_row)
        day += timedelta(days=1)
        if delay_s > 0:
            time.sleep(delay_s)

    games.sort(key=lambda g: (g.get("tipoff") or "", g.get("game_id") or ""))
    miss_rate = (omit_unmapped / espn_events) if espn_events else 0.0
    as_of = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    top_misses = sorted(miss_names.items(), key=lambda kv: (-kv[1], kv[0]))[:40]

    # Miami FL / OH receipt check on mapped pack
    miami_fl = sum(
        1 for g in games if g["home"] == "miami fl" or g["away"] == "miami fl"
    )
    miami_oh = sum(
        1 for g in games if g["home"] == "miami oh" or g["away"] == "miami oh"
    )

    blob = {
        "sport": "ncaam",
        "season": season_key,
        "season_end_year": season_end_year,
        "as_of": as_of,
        "official": True,
        "source": "espn_scoreboard_public",
        "source_detail": {
            "endpoint": ESPN_SCOREBOARD,
            "groups": 50,
            "limit": 500,
            "window_start": start.isoformat(),
            "window_end": end.isoformat(),
        },
        "fidelity": "espn_receipt_b7_mapped_subset",
        "slate_complete": False,
        "slate_complete_note": (
            "Fail-closed B7 map of ESPN scoreboard. Thin/mapped subset ≠ complete D1 slate. "
            "Do not stamp slate_complete=true without an honest densified full join."
        ),
        "lab_join_note": (
            "Lab interim joins still use Odds event_id (D). This pack exposes ESPN game_id "
            "+ odds_event_id=null stubs for future E hybrid — no invented Odds↔ESPN links."
        ),
        "crosswalk": {
            "odds_event_id_field": "odds_event_id",
            "populated": False,
            "policy": "evidence_only_never_invent",
        },
        "n_games": len(games),
        "map_stats": {
            "espn_events": espn_events,
            "mapped_both_sides": mapped_both,
            "omit_unmapped_or_ambiguous": omit_unmapped,
            "omit_duplicate_game_id": omit_dup,
            "map_miss_rate": round(miss_rate, 4),
            "miami_fl_mapped_games": miami_fl,
            "miami_oh_mapped_games": miami_oh,
            "miami_fl_ne_miami_oh": True,
        },
        "fetch_errors": fetch_errors,
        "top_unmapped_names": [
            {"name": n, "count": c} for n, c in top_misses
        ],
        "unmapped_sample": unmapped_sample,
        "raw_day_receipts": raw_receipts,
        "games": games,
        "notes": [
            "Option A Schedule SoT — ESPN public scoreboard.",
            "Identity: apps/web/lib/ncaam/aliases.json via ncaam_identity (fail-closed).",
            "Bare miami omitted — Miami FL ≠ Miami OH.",
            "No Edge Board populate / PLAY / props / Odds densify in this package.",
            "metadata_class=HISTORICAL_STATIC_RECONSTRUCTION for post-tip venue/static fields.",
        ],
        "metadata_class": "HISTORICAL_STATIC_RECONSTRUCTION",
    }
    return blob


def out_path_for_season(season_key: str) -> Path:
    safe = season_key.replace("-", "_")
    return OUT_DIR / f"ncaam_official_schedule_{safe}.json"


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--season",
        default="2022-23",
        choices=sorted(SEASON_WINDOWS.keys()),
        help="Academic season key",
    )
    parser.add_argument(
        "--start-date",
        default=None,
        help="Override window start YYYY-MM-DD",
    )
    parser.add_argument(
        "--end-date",
        default=None,
        help="Override window end YYYY-MM-DD",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.15,
        help="Polite per-day delay seconds",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="Output JSON path (default: model-service ncaam_schedule/data)",
    )
    parser.add_argument(
        "--archive-raw",
        default=None,
        help="Directory for immutable per-day ESPN raw envelopes + sha256 sidecars",
    )
    args = parser.parse_args(argv)

    start, end = SEASON_WINDOWS[args.season]
    if args.start_date:
        start = date.fromisoformat(args.start_date)
    if args.end_date:
        end = date.fromisoformat(args.end_date)
    if end < start:
        print("end-date before start-date", file=sys.stderr)
        return 2

    archive = Path(args.archive_raw) if args.archive_raw else None
    print(f"Ingesting ESPN NCAAM {args.season} ({start} → {end})…")
    blob = ingest_window(
        season_key=args.season,
        start=start,
        end=end,
        delay_s=args.delay,
        archive_raw_dir=archive,
    )
    out = Path(args.out) if args.out else out_path_for_season(args.season)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(blob, indent=2) + "\n", encoding="utf-8")
    stats = blob["map_stats"]
    print(
        f"Wrote {out} — espn_events={stats['espn_events']} "
        f"mapped={stats['mapped_both_sides']} "
        f"miss_rate={stats['map_miss_rate']:.1%} "
        f"miami_fl={stats['miami_fl_mapped_games']} "
        f"miami_oh={stats['miami_oh_mapped_games']} "
        f"slate_complete={blob['slate_complete']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
