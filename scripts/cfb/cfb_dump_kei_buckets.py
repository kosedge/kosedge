#!/usr/bin/env python3
"""CFB KEI vs close/open by spread bucket — Chapter 0 measurement only.

Sources:
  - Bundled KEI: apps/web/lib/data/cfb-kei-w0-w1-2026.json
  - Official slate scores: apps/web/lib/data/cfb-official-slate-2026.json
  - W0 closes: Odds API historical (preferred) else data/ops/book/cfb-2026-08-29.json
  - W1 open/current: live Odds API (no close yet)

Does NOT edit apply_cfb_kei, power, WP, shock, or invent closes.

Usage:
  ODDS_API_KEY=… python3 scripts/cfb/cfb_dump_kei_buckets.py --json \\
    > data/ops/cfb-kei-bucket-20260831.json
  python3 scripts/cfb/cfb_dump_kei_buckets.py --assert-canaries
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO = Path(__file__).resolve().parents[2]
KEI_PATH = REPO / "apps/web/lib/data/cfb-kei-w0-w1-2026.json"
SLATE_PATH = REPO / "apps/web/lib/data/cfb-official-slate-2026.json"
BOOK_PATH = REPO / "data/ops/book/cfb-2026-08-29.json"

SPORT_KEY = "americanfootball_ncaaf"
ALLOWED_BOOKS = [
    "draftkings",
    "fanduel",
    "betmgm",
    "betrivers",
    "hardrockbet",
    "fanatics",
    "bet365",
    "circa",
    "betr",
]

# Brief table — not product trust band
BUCKETS = (
    ("pick", 0.0, 3.0),
    ("short", 3.0, 7.0),
    ("mid", 7.0, 14.0),
    ("long", 14.0, 21.0),
    ("cupcake", 21.0, 999.0),
)

ALIASES = {
    "umass": "massachusetts",
    "umass minutemen": "massachusetts minutemen",
    "massachusetts": "massachusetts",
    "massachusetts minutemen": "massachusetts minutemen",
    "mass": "massachusetts",
    "hawaii": "hawaii",
    "hawai'i": "hawaii",
    "haw": "hawaii",
    "san jose": "san jose",
    "sjsu": "san jose",
    "miami oh": "miami-ohio",
    "miami ohio": "miami-ohio",
    "miami oh redhawks": "miami-ohio redhawks",
    "miami hurricanes": "miami-florida hurricanes",
    "mia": "miami-florida",
    "rut": "rutgers",
}


def fold(raw: str) -> str:
    s = unicodedata.normalize("NFKD", str(raw or ""))
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    s = s.replace("'", "").replace("`", "").replace("ʻ", "")
    s = re.sub(r"[^a-z0-9@\s-]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def alias_token(s: str) -> str:
    f = fold(s)
    if f in ALIASES:
        return ALIASES[f]
    words = f.split()
    if len(words) >= 2:
        two = f"{words[0]} {words[1]}"
        if two in ALIASES:
            rest = " ".join(words[2:])
            return f"{ALIASES[two]} {rest}".strip()
    if words and words[0] in ALIASES:
        rest = " ".join(words[1:])
        return f"{ALIASES[words[0]]} {rest}".strip()
    return f


def match_keys(game: str) -> List[str]:
    n = fold(game)
    n = re.sub(r"\s*@\s*", " @ ", n)
    parts = n.split(" @ ")
    if len(parts) != 2:
        return [n] if n else []
    away, home = alias_token(parts[0]), alias_token(parts[1])

    def take(s: str, words: int) -> str:
        return " ".join(s.split()[:words])

    keys = [
        f"{away} @ {home}",
        f"{take(away, 2)} @ {take(home, 2)}",
        f"{take(away, 1)} @ {take(home, 1)}",
    ]
    return list(dict.fromkeys(k for k in keys if "@" in k))


def bucket_for(abs_spread: Optional[float]) -> str:
    if abs_spread is None:
        return "unknown"
    a = abs(float(abs_spread))
    for name, lo, hi in BUCKETS:
        if lo <= a < hi or (name == "cupcake" and a >= lo):
            return name
    return "unknown"


def family_for(abs_spread: Optional[float]) -> str:
    """Reading label: A cupcake / mid / pick / other."""
    if abs_spread is None:
        return "other"
    a = abs(float(abs_spread))
    if a >= 21:
        return "A"
    if a <= 3:
        return "pick"
    if 3 < a <= 14:
        return "mid"
    return "other"


def http_json(url: str) -> Tuple[Any, Optional[str]]:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "KosEdgeCFB/1.0 (+https://www.kosedge.com)",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            return json.loads(resp.read().decode("utf-8")), None
    except Exception as exc:  # noqa: BLE001
        return None, str(exc)


def home_spread_from_event(ev: Dict[str, Any]) -> Optional[float]:
    home = ev.get("home_team")
    points: List[float] = []
    for b in ev.get("bookmakers") or []:
        if str(b.get("key") or "").lower() not in ALLOWED_BOOKS:
            continue
        m = next(
            (x for x in (b.get("markets") or []) if x.get("key") == "spreads"),
            None,
        )
        if not m:
            continue
        home_o = next(
            (o for o in (m.get("outcomes") or []) if o.get("name") == home),
            None,
        )
        if home_o is not None and home_o.get("point") is not None:
            points.append(float(home_o["point"]))
    if not points:
        return None
    # Consensus = median of book home points
    points.sort()
    mid = len(points) // 2
    if len(points) % 2:
        return points[mid]
    return (points[mid - 1] + points[mid]) / 2.0


def normalize_iso_z(raw: str) -> str:
    """Odds historical requires full seconds: 2026-08-29T16:00:00Z (not …T16:00Z)."""
    s = str(raw or "").strip()
    if not s:
        return s
    if s.endswith("Z"):
        body = s[:-1]
        if body.count(":") == 1:
            return body + ":00Z"
        return s
    return s


def fetch_historical_closes(
    api_key: str, kickoffs: List[str]
) -> Tuple[Dict[str, Dict[str, Any]], Optional[str]]:
    """Map match_keys → {close_h, source_ts} from Odds historical near each kick."""
    out: Dict[str, Dict[str, Any]] = {}
    err: Optional[str] = None
    seen_dates: Dict[str, bool] = {}
    for k in kickoffs:
        date_param = normalize_iso_z(k)
        if not date_param or date_param in seen_dates:
            continue
        seen_dates[date_param] = True
        qs = urllib.parse.urlencode(
            {
                "apiKey": api_key,
                "regions": "us,us2",
                "markets": "spreads,totals",
                "oddsFormat": "american",
                "bookmakers": ",".join(ALLOWED_BOOKS),
                "date": date_param,
            }
        )
        url = (
            f"https://api.the-odds-api.com/v4/historical/sports/"
            f"{SPORT_KEY}/odds?{qs}"
        )
        payload, e = http_json(url)
        if e:
            err = e
            continue
        events = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(events, list):
            continue
        ts = payload.get("timestamp") if isinstance(payload, dict) else None
        for ev in events:
            label = f"{ev.get('away_team')} @ {ev.get('home_team')}"
            close_h = home_spread_from_event(ev)
            if close_h is None:
                continue
            for key in match_keys(label):
                out.setdefault(
                    key,
                    {
                        "close_h": close_h,
                        "source": "odds_api_historical",
                        "snapshot_ts": ts,
                        "label": label,
                    },
                )
    return out, err


def fetch_live_odds(
    api_key: str,
) -> Tuple[Dict[str, Dict[str, Any]], Optional[str]]:
    qs = urllib.parse.urlencode(
        {
            "apiKey": api_key,
            "regions": "us,us2",
            "markets": "spreads,totals",
            "oddsFormat": "american",
            "bookmakers": ",".join(ALLOWED_BOOKS),
        }
    )
    url = f"https://api.the-odds-api.com/v4/sports/{SPORT_KEY}/odds?{qs}"
    payload, e = http_json(url)
    if e:
        return {}, e
    if not isinstance(payload, list):
        return {}, f"unexpected payload {type(payload)}"
    out: Dict[str, Dict[str, Any]] = {}
    for ev in payload:
        label = f"{ev.get('away_team')} @ {ev.get('home_team')}"
        open_h = home_spread_from_event(ev)
        if open_h is None:
            continue
        for key in match_keys(label):
            out.setdefault(
                key,
                {
                    "open_h": open_h,
                    "current_h": open_h,
                    "source": "odds_api_live",
                    "label": label,
                },
            )
    return out, None


def load_desk_book() -> Dict[str, Dict[str, Any]]:
    if not BOOK_PATH.exists():
        return {}
    book = json.loads(BOOK_PATH.read_text(encoding="utf-8"))
    out: Dict[str, Dict[str, Any]] = {}
    for g in book.get("games") or []:
        away = str(g.get("away") or "").replace("fcs:", "").replace("FCS:", "")
        home = str(g.get("home") or "").replace("fcs:", "").replace("FCS:", "")
        pair = f"{away}@{home}"
        mkt = g.get("market_spread_home")
        if mkt is None:
            continue
        payload = {
            "close_h": float(mkt),
            "source": "desk_book_snapshot_2026-08-29",
            "posted_at": book.get("posted_at"),
            "pair": pair,
            "not_official_odds_api_close": True,
        }
        out[pair] = payload
        for key in match_keys(f"{away} @ {home}"):
            out.setdefault(key, payload)
    return out


def load_slate_scores() -> Dict[str, Dict[str, Any]]:
    slate = json.loads(SLATE_PATH.read_text(encoding="utf-8"))
    out: Dict[str, Dict[str, Any]] = {}
    for g in slate.get("games") or []:
        away = str(g.get("away") or "").replace("fcs:", "").replace("FCS:", "")
        home = str(g.get("home") or "").replace("fcs:", "").replace("FCS:", "")
        pair = f"{away.upper()}@{home.upper()}"
        away_s, home_s = g.get("away_score"), g.get("home_score")
        margin = None
        if away_s is not None and home_s is not None:
            margin = float(home_s) - float(away_s)
        out[pair] = {
            "away_score": away_s,
            "home_score": home_s,
            "result_margin_home": margin,
            "status": g.get("status"),
            "week": g.get("week"),
        }
    return out


def cover(spread_home: Optional[float], margin_home: Optional[float]) -> Optional[str]:
    """Did home cover the home-signed spread?"""
    if spread_home is None or margin_home is None:
        return None
    # Home covers if margin_home + spread_home > 0 (favorite negative spread)
    edge = margin_home + float(spread_home)
    if abs(edge) < 1e-9:
        return "push"
    return "home" if edge > 0 else "away"


def assert_canaries(kei: Dict[str, Any]) -> int:
    ball = tcu = None
    for g in kei.get("games") or []:
        if g.get("week") == 1 and g.get("away") == "BALL" and g.get("home") == "OSU":
            ball = (g.get("kei") or {}).get("kei_spread_home")
        if g.get("week") == 0 and g.get("away") == "UNC" and g.get("home") == "TCU":
            tcu = (g.get("kei") or {}).get("kei_spread_home")
    ok = True
    if ball != -42.2:
        print(f"FAIL: BALL@OSU KEI expected -42.2 got {ball!r}", file=sys.stderr)
        ok = False
    else:
        print("OK: BALL@OSU kei_spread_home == -42.2")
    if tcu is None or abs(float(tcu) - (-20.39)) > 0.05:
        print(f"FAIL: UNC@TCU KEI expected ≈ -20.39 got {tcu!r}", file=sys.stderr)
        ok = False
    else:
        print(f"OK: UNC@TCU kei_spread_home == {tcu}")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--assert-canaries", action="store_true")
    ap.add_argument(
        "--desk-book-only",
        action="store_true",
        help="Skip Odds historical; use desk book for W0 closes",
    )
    args = ap.parse_args()

    kei = json.loads(KEI_PATH.read_text(encoding="utf-8"))
    if args.assert_canaries:
        return assert_canaries(kei)

    api_key = (
        os.environ.get("ODDS_API_KEY")
        or os.environ.get("ODDS_API_KEY_BACKUP")
        or ""
    ).strip()

    desk = load_desk_book()
    scores = load_slate_scores()

    # Collect W0 kickoffs for historical
    w0_kickoffs: List[str] = []
    for g in kei.get("games") or []:
        if g.get("week") == 0 and g.get("fbs_vs_fbs") and (g.get("kei") or {}).get(
            "kei_spread_home"
        ) is not None:
            kick = str(g.get("kickoff") or "")
            if kick:
                w0_kickoffs.append(kick)

    hist: Dict[str, Dict[str, Any]] = {}
    hist_err: Optional[str] = None
    if api_key and not args.desk_book_only:
        hist, hist_err = fetch_historical_closes(api_key, w0_kickoffs)

    live: Dict[str, Dict[str, Any]] = {}
    live_err: Optional[str] = None
    if api_key:
        live, live_err = fetch_live_odds(api_key)

    rows: List[Dict[str, Any]] = []
    for g in kei.get("games") or []:
        week = g.get("week")
        if week not in (0, 1):
            continue
        if not g.get("fbs_vs_fbs"):
            continue
        kei_obj = g.get("kei") or {}
        kei_h = kei_obj.get("kei_spread_home")
        if kei_h is None:
            continue
        away = str(g.get("away") or "").replace("fcs:", "").replace("FCS:", "").upper()
        home = str(g.get("home") or "").replace("fcs:", "").replace("FCS:", "").upper()
        pair = f"{away}@{home}"
        label = f"{g.get('away_name') or away} @ {g.get('home_name') or home}"
        keys = match_keys(label) + match_keys(f"{away} @ {home}") + [pair]

        close_h = None
        close_source = None
        open_h = None
        current_h = None

        if week == 0:
            # Prefer historical
            hit = None
            for k in keys:
                if k in hist:
                    hit = hist[k]
                    break
            if hit:
                close_h = hit.get("close_h")
                close_source = hit.get("source")
            else:
                for k in keys:
                    if k in desk:
                        close_h = desk[k].get("close_h")
                        close_source = desk[k].get("source")
                        break
        else:
            for k in keys:
                if k in live:
                    open_h = live[k].get("open_h")
                    current_h = live[k].get("current_h")
                    break

        # Anchor spread for bucket: close if present else KEI
        anchor = close_h if close_h is not None else (
            current_h if current_h is not None else float(kei_h)
        )
        bkt = bucket_for(anchor)
        fam = family_for(anchor)

        residual = None
        if close_h is not None:
            residual = round(float(kei_h) - float(close_h), 2)
        elif current_h is not None:
            residual = round(float(kei_h) - float(current_h), 2)

        sc = scores.get(pair) or {}
        margin = sc.get("result_margin_home")
        cover_kei = cover(float(kei_h), margin) if week == 0 else None
        cover_close = cover(float(close_h), margin) if week == 0 and close_h is not None else None

        rows.append(
            {
                "pair": pair,
                "week": week,
                "game": label,
                "kickoff": g.get("kickoff"),
                "family": fam,
                "bucket": bkt,
                "kei_spread_home": float(kei_h),
                "kei_total": kei_obj.get("kei_total"),
                "open_h": open_h,
                "current_h": current_h,
                "close_h": close_h,
                "close_source": close_source,
                "residual_kei_minus_close": residual,
                "result_margin_home": margin,
                "cover_kei": cover_kei,
                "cover_close": cover_close,
            }
        )

    # Bucket summaries (W0 with close only)
    w0_closed = [r for r in rows if r["week"] == 0 and r["close_h"] is not None]
    by_bucket: Dict[str, Dict[str, Any]] = {}
    for bname, _, _ in BUCKETS:
        subset = [r for r in w0_closed if r["bucket"] == bname]
        residuals = [r["residual_kei_minus_close"] for r in subset if r["residual_kei_minus_close"] is not None]
        by_bucket[bname] = {
            "n": len(subset),
            "mean_residual": round(sum(residuals) / len(residuals), 3) if residuals else None,
            "pairs": [r["pair"] for r in subset],
            "residuals": residuals,
        }

    mid_res = by_bucket.get("mid", {}).get("mean_residual")
    cup_res = by_bucket.get("cupcake", {}).get("mean_residual")
    # Also long often holds cupcake-direction games (FSU)
    long_res = by_bucket.get("long", {}).get("mean_residual")

    summary = {
        "kei_as_of": kei.get("as_of"),
        "engine_version": kei.get("engine_version"),
        "n_rows": len(rows),
        "n_w0": sum(1 for r in rows if r["week"] == 0),
        "n_w1": sum(1 for r in rows if r["week"] == 1),
        "n_w0_with_close": len(w0_closed),
        "historical_error": hist_err,
        "live_error": live_err,
        "desk_book_path": str(BOOK_PATH.relative_to(REPO)),
        "by_bucket_w0": by_bucket,
        "mid_vs_cupcake_sign": {
            "mid_mean": mid_res,
            "cupcake_mean": cup_res,
            "long_mean": long_res,
            "same_sign": (
                mid_res is not None
                and cup_res is not None
                and (mid_res == 0 or cup_res == 0 or (mid_res > 0) == (cup_res > 0))
            )
            if mid_res is not None and cup_res is not None
            else None,
            "note": (
                "residual = KEI_home − close_home. "
                "Negative ⇒ KEI longer favorite than close; "
                "positive ⇒ KEI shorter than close (cupcake-direction)."
            ),
        },
        "canaries": {
            "BALL@OSU": next(
                (r for r in rows if r["pair"] == "BALL@OSU"), None
            ),
            "UNC@TCU": next(
                (r for r in rows if r["pair"] == "UNC@TCU"), None
            ),
            "HAW@STAN": next(
                (r for r in rows if r["pair"] == "HAW@STAN"), None
            ),
        },
        "thresholds_untouched": {
            "ABSURD_VS_KEI": 12,
            "LEAN": 2.5,
            "PLAY": 4.0,
        },
    }

    payload = {"summary": summary, "rows": rows}
    if args.json:
        print(json.dumps(payload, indent=2))
        return 0

    print("# CFB KEI bucket dump")
    print(f"- engine `{summary['engine_version']}` as_of={summary['kei_as_of']}")
    print(f"- W0={summary['n_w0']} (with close {summary['n_w0_with_close']}) W1={summary['n_w1']}")
    print(f"- mid mean residual={mid_res} cupcake mean={cup_res} long mean={long_res}")
    print(f"- same_sign mid vs cupcake={summary['mid_vs_cupcake_sign']['same_sign']}")
    print()
    print("| week | bucket | family | pair | kei_h | close/cur | residual | margin |")
    print("|---:|---|---|---|---:|---:|---:|---:|")
    for r in sorted(rows, key=lambda x: (x["week"], x["bucket"], x["pair"])):
        mkt = r["close_h"] if r["close_h"] is not None else r["current_h"]
        print(
            f"| {r['week']} | {r['bucket']} | {r['family']} | {r['pair']} | "
            f"{r['kei_spread_home']} | {mkt} | {r['residual_kei_minus_close']} | "
            f"{r['result_margin_home']} |"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
