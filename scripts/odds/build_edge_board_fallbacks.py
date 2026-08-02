#!/usr/bin/env python3
"""Convert Odds API raw event dumps → edge_board_fallback_*.json."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
OUT = Path(__file__).resolve().parents[2] / "apps/web/data/processed"
BOOK_DISPLAY = {
    "draftkings": "DraftKings",
    "fanduel": "FanDuel",
    "betmgm": "BetMGM",
    "betrivers": "BetRivers",
    "hardrockbet": "Hard Rock Bet",
    "fanatics": "Fanatics",
    "bet365": "Bet365",
    "circa": "Circa",
    "betr": "Betr",
}
ALLOWED = list(BOOK_DISPLAY)


def fmt_juice(price):
    if price is None:
        return None
    n = int(round(price))
    return f"+{n}" if n > 0 else str(n)


def fmt_dt(iso: str) -> str:
    d = datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(ET)
    return d.strftime("%m/%d %-I:%M %p ET")


def pick_best_spread(entries):
    if not entries:
        return None
    return sorted(
        entries, key=lambda e: (e["point"], e.get("juiceAway") or ""), reverse=True
    )[0]


def pick_best_total(entries):
    if not entries:
        return None
    return sorted(
        entries, key=lambda e: (e["point"], e.get("juiceOver") or ""), reverse=True
    )[0]


def pick_best_moneyline(entries):
    if not entries:
        return None
    return sorted(entries, key=lambda e: e["awayPrice"], reverse=True)[0]


def events_to_rows(events, sport: str):
    rows = []
    events = sorted(events, key=lambda e: e.get("commence_time", ""))
    for ev in events:
        game = f"{ev['away_team']} @ {ev['home_team']}"
        time = fmt_dt(ev["commence_time"])
        books = [b for b in (ev.get("bookmakers") or []) if b.get("key") in ALLOWED]
        books.sort(key=lambda b: ALLOWED.index(b["key"]) if b["key"] in ALLOWED else 99)

        if sport == "mlb":
            ml_entries = []
            for b in books:
                m = next(
                    (x for x in (b.get("markets") or []) if x.get("key") == "h2h"),
                    None,
                )
                if not m:
                    continue
                away = next(
                    (
                        o
                        for o in m.get("outcomes") or []
                        if o.get("name") == ev["away_team"]
                    ),
                    None,
                )
                home = next(
                    (
                        o
                        for o in m.get("outcomes") or []
                        if o.get("name") == ev["home_team"]
                    ),
                    None,
                )
                if not away or away.get("price") is None or not home or home.get("price") is None:
                    continue
                ml_entries.append(
                    {
                        "book": b["key"],
                        "away": fmt_juice(away.get("price")),
                        "home": fmt_juice(home.get("price")),
                        "awayPrice": away["price"],
                        "homePrice": home["price"],
                    }
                )
            open_m = ml_entries[0] if ml_entries else None
            best_m = pick_best_moneyline(ml_entries)
            rows.append(
                {
                    "id": f"{ev['id']}-moneyline",
                    "game": game,
                    "time": time,
                    "commenceTime": ev["commence_time"],
                    "market": "Moneyline",
                    "open": open_m["away"] if open_m else None,
                    "best": (best_m or open_m or {}).get("away"),
                    "book": BOOK_DISPLAY.get((best_m or {}).get("book", ""))
                    if best_m
                    else None,
                    "bookKey": (best_m or {}).get("book"),
                    "openJuice": open_m.get("away") if open_m else None,
                    "openJuiceHome": open_m.get("home") if open_m else None,
                    "bestJuice": (best_m or open_m or {}).get("away"),
                    "bestJuiceHome": (best_m or open_m or {}).get("home"),
                }
            )
        else:
            spread_entries = []
            for b in books:
                m = next(
                    (x for x in (b.get("markets") or []) if x.get("key") == "spreads"),
                    None,
                )
                if not m:
                    continue
                away = next(
                    (
                        o
                        for o in m.get("outcomes") or []
                        if o.get("name") == ev["away_team"]
                    ),
                    None,
                )
                home = next(
                    (
                        o
                        for o in m.get("outcomes") or []
                        if o.get("name") == ev["home_team"]
                    ),
                    None,
                )
                if not away or away.get("point") is None:
                    continue
                pt = away["point"]
                line = f"+{pt}" if pt > 0 else str(pt)
                spread_entries.append(
                    {
                        "book": b["key"],
                        "line": line,
                        "point": pt,
                        "juiceAway": fmt_juice(away.get("price")),
                        "juiceHome": fmt_juice(home.get("price") if home else None),
                    }
                )
            open_s = spread_entries[0] if spread_entries else None
            best_s = pick_best_spread(spread_entries)
            rows.append(
                {
                    "id": f"{ev['id']}-spread",
                    "game": game,
                    "time": time,
                    "commenceTime": ev["commence_time"],
                    "market": "Spread",
                    "open": open_s["line"] if open_s else None,
                    "best": (best_s or open_s or {}).get("line"),
                    "book": BOOK_DISPLAY.get((best_s or {}).get("book", ""))
                    if best_s
                    else None,
                    "bookKey": (best_s or {}).get("book"),
                    "openJuice": open_s.get("juiceAway") if open_s else None,
                    "openJuiceHome": open_s.get("juiceHome") if open_s else None,
                    "bestJuice": (best_s or open_s or {}).get("juiceAway"),
                    "bestJuiceHome": (best_s or open_s or {}).get("juiceHome"),
                }
            )

        total_entries = []
        for b in books:
            m = next(
                (x for x in (b.get("markets") or []) if x.get("key") == "totals"),
                None,
            )
            if not m:
                continue
            over = next(
                (o for o in m.get("outcomes") or [] if o.get("name") == "Over"), None
            )
            under = next(
                (o for o in m.get("outcomes") or [] if o.get("name") == "Under"), None
            )
            point = (
                over.get("point")
                if over
                else (m.get("outcomes") or [{}])[0].get("point")
            )
            if point is None:
                continue
            total_entries.append(
                {
                    "book": b["key"],
                    "line": str(point),
                    "point": point,
                    "juiceOver": fmt_juice(over.get("price") if over else None),
                    "juiceUnder": fmt_juice(under.get("price") if under else None),
                }
            )
        open_t = total_entries[0] if total_entries else None
        best_t = pick_best_total(total_entries)
        rows.append(
            {
                "id": f"{ev['id']}-total",
                "game": game,
                "time": time,
                "commenceTime": ev["commence_time"],
                "market": "Total",
                "open": open_t["line"] if open_t else None,
                "best": (best_t or open_t or {}).get("line"),
                "book": BOOK_DISPLAY.get((best_t or {}).get("book", ""))
                if best_t
                else None,
                "bookKey": (best_t or {}).get("book"),
                "openJuice": open_t.get("juiceOver") if open_t else None,
                "openJuiceHome": open_t.get("juiceUnder") if open_t else None,
                "bestJuice": (best_t or open_t or {}).get("juiceOver"),
                "bestJuiceHome": (best_t or open_t or {}).get("juiceUnder"),
            }
        )
    return [r for r in rows if r.get("open") or r.get("best")]


def main() -> int:
    captured = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for sport in ("wnba", "mlb", "nhl", "cfb", "nba", "ncaam"):
        raw_path = OUT / f"odds_raw_{sport}.json"
        if not raw_path.exists():
            print("skip missing", raw_path.name)
            continue
        data = json.loads(raw_path.read_text())
        events = data.get("events") or []
        rows = events_to_rows(events, sport)
        payload = {
            "sport": sport,
            "source": "odds-api-live-pull",
            "capturedAt": captured,
            "eventCount": len(events),
            "rows": rows,
        }
        if sport == "nba" and not rows:
            payload["note"] = (
                "Odds API basketball_nba returned 0 events (offseason / no posted board)."
            )
        out = OUT / f"edge_board_fallback_{sport}.json"
        out.write_text(json.dumps(payload, indent=2) + "\n")
        print(f"{sport}: events={len(events)} rows={len(rows)} -> {out.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
