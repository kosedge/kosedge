#!/usr/bin/env python3
"""Dump CFB Week 1 Edge Board rows — mirrors web loaders (measure only).

Sources (same as /edge-board/cfb):
  - Bundled KEI: apps/web/lib/data/cfb-kei-w0-w1-2026.json
  - Official slate: apps/web/lib/data/cfb-official-slate-2026.json
  - Odds: The Odds API americanfootball_ncaaf (apps/web/lib/odds-api.ts)
  - Trusted market: apps/web/lib/cfb-trusted-market.ts (verbatim thresholds)

Does NOT call apply_cfb_kei, retune power/WP, or invent books.

Usage:
  ODDS_API_KEY=… python3 scripts/cfb/cfb_dump_edgeboard.py
  ODDS_API_KEY=… python3 scripts/cfb/cfb_dump_edgeboard.py --json > data/ops/cfb-week1-book-dump.json
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

# From apps/web/lib/cfb-trusted-market.ts
CFB_PLAY_EDGE_PTS = 4.0
CFB_LEAN_EDGE_PTS = 2.5
CFB_OUTLIER_VS_OPEN_PTS = 3.5
CFB_ABSURD_VS_KEI_PTS = 12.0
CFB_SINGLE_BOOK_ABSURD_PTS = 8.0
# Totals PLAY sit — mirror CFB_TOTALS_PLAY_ELIGIBLE (docs/CFB_TOTALS_PLAY_SIT.md).
CFB_TOTALS_PLAY_ELIGIBLE = False
# Spread PLAY sit — mirror CFB_SPREAD_PLAY_ELIGIBLE (docs/CFB_SPREAD_PLAY_SIT.md).
CFB_SPREAD_PLAY_ELIGIBLE = False

# From apps/web/lib/odds-api.ts
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

FAMILY_A = {
    "BALL@OSU",
    "TXST@TEX",
    "ECU@ALA",
    "UTEP@OU",
    "MOST@TAMU",
    "UNT@IU",
    "FIU@USF",
}
FAMILY_B = {
    "BOISE@ORE",
    "MIA@STAN",
    "CLEM@LSU",
    "WIS@ND",
    "LOU@MISS",
    "SMU@FSU",
    "WSU@WASH",
}

ALIASES = {
    "hawaii": "hawaii",
    "hawai'i": "hawaii",
    "haw": "hawaii",
    "san jose": "san jose",
    "sjsu": "san jose",
    # Massachusetts / UMass
    "umass": "massachusetts",
    "umass minutemen": "massachusetts minutemen",
    "massachusetts": "massachusetts",
    "massachusetts minutemen": "massachusetts minutemen",
    "mass": "massachusetts",
    # Miami FL vs Miami OH (distinct first tokens)
    "miami oh": "miami-ohio",
    "miami ohio": "miami-ohio",
    "miami oh redhawks": "miami-ohio redhawks",
    "miami ohio redhawks": "miami-ohio redhawks",
    "m-oh": "miami-ohio",
    "moh": "miami-ohio",
    "miami fl": "miami-florida",
    "miami florida": "miami-florida",
    "miami hurricanes": "miami-florida hurricanes",
    "miami florida hurricanes": "miami-florida hurricanes",
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
    if not f:
        return f
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
    n = fold(game).replace(" @ ", " @ ")
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


def num(v: Any) -> Optional[float]:
    if v is None or v == "" or v == "—":
        return None
    m = re.sub(r"[^+\-\d.]", "", str(v))
    try:
        n = float(m)
    except ValueError:
        return None
    return n if n == n else None


def trust_cfb_market(
    kei: Any, best: Any, open_: Any, book_count: Optional[int] = None
) -> Dict[str, Any]:
    """Port of trustCfbMarket. best/open must already be **home-signed**."""
    k = num(kei)
    b = num(best)
    o = num(open_)
    books = book_count
    if books is None:
        books = 2 if (b is not None and o is not None and b != o) else 1

    if k is None:
        return {"trusted": False, "market": None, "reason": "no_kei"}
    if b is None and o is None:
        return {"trusted": False, "market": None, "reason": "no_market"}

    candidate = b if b is not None else o
    reason = "best"
    if b is not None and o is not None and abs(b - o) >= CFB_OUTLIER_VS_OPEN_PTS:
        candidate = o
        reason = "best_outlier_vs_open"
    if candidate is None:
        return {"trusted": False, "market": None, "reason": "no_candidate"}

    gap = abs(candidate - k)
    if gap >= CFB_ABSURD_VS_KEI_PTS:
        return {"trusted": False, "market": None, "reason": "absurd_vs_kei"}
    if books < 2 and gap >= CFB_SINGLE_BOOK_ABSURD_PTS:
        return {"trusted": False, "market": None, "reason": "single_book_outlier"}
    return {"trusted": True, "market": candidate, "reason": reason}


def away_book_to_home(away_signed: Any) -> Optional[float]:
    """Mirror cfbAwayBookToHome — Odds away point → home."""
    n = num(away_signed)
    return None if n is None else -n


def cfb_edge_tag(abs_edge: Optional[float], market: str = "spread") -> str:
    """Mirror apps/web/lib/cfb-trusted-market.ts cfbEdgeTag."""
    if abs_edge is None:
        return "PASS"
    e = abs(float(abs_edge))
    if e >= CFB_PLAY_EDGE_PTS:
        if market == "total" and not CFB_TOTALS_PLAY_ELIGIBLE:
            return "PASS"
        if market == "spread" and not CFB_SPREAD_PLAY_ELIGIBLE:
            return "PASS"
        return "PLAY"
    if e >= CFB_LEAN_EDGE_PTS:
        return "LEAN"
    return "PASS"


def fetch_odds(api_key: str) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    books = ",".join(ALLOWED_BOOKS)
    qs = urllib.parse.urlencode(
        {
            "regions": "us,us2",
            "markets": "spreads,totals",
            "oddsFormat": "american",
            "bookmakers": books,
            "apiKey": api_key,
        }
    )
    url = f"https://api.the-odds-api.com/v4/sports/{SPORT_KEY}/odds?{qs}"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "KosEdgeCFB/1.0 (+https://www.kosedge.com)",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=40) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        if isinstance(payload, list):
            return payload, None
        return [], str(payload)
    except Exception as exc:  # noqa: BLE001
        return [], str(exc)


def pick_spread_open_best(
    event: Dict[str, Any],
) -> Tuple[Optional[float], Optional[float], int, Optional[str]]:
    """Mirror odds-api.ts: open = preference-ordered first book away line; best = best away point."""
    away = event.get("away_team")
    home = event.get("home_team")
    entries: List[Tuple[str, float, Optional[float]]] = []
    for b in event.get("bookmakers") or []:
        key = str(b.get("key") or "").lower()
        if key not in ALLOWED_BOOKS:
            continue
        m = next(
            (x for x in (b.get("markets") or []) if x.get("key") == "spreads"),
            None,
        )
        if not m:
            continue
        away_o = next(
            (o for o in (m.get("outcomes") or []) if o.get("name") == away), None
        )
        if away_o is None or away_o.get("point") is None:
            continue
        entries.append((key, float(away_o["point"]), away_o.get("price")))
    if not entries:
        return None, None, 0, None
    # preference order for open
    entries.sort(key=lambda e: ALLOWED_BOOKS.index(e[0]) if e[0] in ALLOWED_BOOKS else 99)
    open_pt = entries[0][1]
    # best away = highest point (more points for away = better for away bettor), juice tiebreak skipped simply
    best = max(entries, key=lambda e: (e[1], e[2] if e[2] is not None else -9999))
    return open_pt, best[1], len({e[0] for e in entries}), best[0]


def pick_total_open_best(
    event: Dict[str, Any],
) -> Tuple[Optional[float], Optional[float]]:
    entries: List[Tuple[str, float]] = []
    for b in event.get("bookmakers") or []:
        key = str(b.get("key") or "").lower()
        if key not in ALLOWED_BOOKS:
            continue
        m = next(
            (x for x in (b.get("markets") or []) if x.get("key") == "totals"),
            None,
        )
        if not m:
            continue
        over = next(
            (o for o in (m.get("outcomes") or []) if str(o.get("name")).lower() == "over"),
            None,
        )
        if over is None or over.get("point") is None:
            continue
        entries.append((key, float(over["point"])))
    if not entries:
        return None, None
    entries.sort(key=lambda e: ALLOWED_BOOKS.index(e[0]) if e[0] in ALLOWED_BOOKS else 99)
    open_pt = entries[0][1]
    best_pt = max(e[1] for e in entries)  # higher total over line as board pickBestTotal
    return open_pt, best_pt


def family_for(pair: str) -> str:
    if pair in FAMILY_A:
        return "A"
    if pair in FAMILY_B:
        return "B"
    return "other"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true", help="Emit full JSON")
    ap.add_argument("--markdown", action="store_true", help="Emit markdown table (default)")
    ap.add_argument(
        "--assert-canary",
        action="store_true",
        help="Assert BALL@OSU bundled KEI is still -42.2 (no Odds call)",
    )
    args = ap.parse_args()

    if args.assert_canary:
        kei = json.loads(KEI_PATH.read_text())
        hit = None
        for g in kei.get("games") or []:
            if g.get("away") == "BALL" and g.get("home") == "OSU" and g.get("week") == 1:
                hit = (g.get("kei") or {}).get("kei_spread_home")
                break
        if hit != -42.2:
            print(f"FAIL: BALL@OSU KEI expected -42.2, got {hit!r}", file=sys.stderr)
            return 1
        print("OK: BALL@OSU kei_spread_home == -42.2")
        return 0
    if not args.json and not args.markdown:
        args.markdown = True

    kei = json.loads(KEI_PATH.read_text(encoding="utf-8"))
    slate = json.loads(SLATE_PATH.read_text(encoding="utf-8"))

    api_key = (
        os.environ.get("ODDS_API_KEY")
        or os.environ.get("ODDS_API_KEY_BACKUP")
        or ""
    ).strip()
    events: List[Dict[str, Any]] = []
    feed_err: Optional[str] = None
    if api_key:
        events, feed_err = fetch_odds(api_key)
    else:
        feed_err = "ODDS_API_KEY not set"

    # Index odds by match keys
    odds_by_key: Dict[str, Dict[str, Any]] = {}
    for ev in events:
        label = f"{ev.get('away_team')} @ {ev.get('home_team')}"
        open_a, best_a, nbooks, best_book = pick_spread_open_best(ev)
        open_t, best_t = pick_total_open_best(ev)
        payload = {
            "label": label,
            "open_away": open_a,
            "best_away": best_a,
            "n_books": nbooks,
            "best_book": best_book,
            "open_total": open_t,
            "best_total": best_t,
            "commence": ev.get("commence_time"),
        }
        for k in match_keys(label):
            odds_by_key.setdefault(k, payload)

    rows: List[Dict[str, Any]] = []
    fcs_null = 0
    for g in kei.get("games") or []:
        if g.get("week") != 1:
            continue
        if not g.get("fbs_vs_fbs"):
            if (g.get("kei") or {}).get("kei_spread_home") is None:
                fcs_null += 1
            continue
        kei_obj = g.get("kei") or {}
        kei_home = kei_obj.get("kei_spread_home")
        if kei_home is None:
            continue
        away = str(g.get("away") or "").replace("fcs:", "").replace("FCS:", "").upper()
        home = str(g.get("home") or "").replace("fcs:", "").replace("FCS:", "").upper()
        pair = f"{away}@{home}"
        label = f"{g.get('away_name') or away} @ {g.get('home_name') or home}"
        odds = None
        for k in match_keys(label) + match_keys(f"{away} @ {home}"):
            if k in odds_by_key:
                odds = odds_by_key[k]
                break

        if odds is None and feed_err:
            trusted_reason = "no_feed"
            verdict = {"trusted": False, "market": None, "reason": "no_feed"}
            open_away = best_away = None
            open_home = best_home = None
            open_tot = best_tot = None
            n_books = 0
        elif odds is None:
            trusted_reason = "no_market"
            verdict = {"trusted": False, "market": None, "reason": "no_market"}
            open_away = best_away = None
            open_home = best_home = None
            open_tot = best_tot = None
            n_books = 0
        else:
            open_away = odds["open_away"]
            best_away = odds["best_away"]
            open_tot = odds["open_total"]
            best_tot = odds["best_total"]
            n_books = odds["n_books"]
            # Board stores Open/Best away-signed; KEI home. Convert at trust boundary
            # (cfbAwayBookToHome / applyCfbTrustedMarketToRows).
            open_home = away_book_to_home(open_away)
            best_home = away_book_to_home(best_away)
            verdict = trust_cfb_market(
                kei=kei_home,
                best=best_home,
                open_=open_home,
                book_count=n_books,
            )
            trusted_reason = verdict["reason"]

        # Trusted market candidate is home-signed after boundary convert.
        # Feed Current (best_home) always paints; trustedBest only when trusted.
        best_home_trusted = None
        if verdict["trusted"] and verdict["market"] is not None:
            best_home_trusted = float(verdict["market"])
        current_h = best_home if best_home is not None else open_home
        painted_without_trust = bool(
            current_h is not None and not verdict["trusted"]
        )
        trust_label = None
        if not verdict["trusted"]:
            if trusted_reason in ("no_market", "no_kei", "no_candidate", "no_feed"):
                trust_label = "no book"
            else:
                trust_label = "untrusted"

        edge_line = None
        if best_home_trusted is not None:
            edge_line = round(float(kei_home) - best_home_trusted, 2)
        tag_line = cfb_edge_tag(
            abs(edge_line) if edge_line is not None else None, "spread"
        )

        kei_tot = kei_obj.get("kei_total")
        # Totals trust gate (same as applyCfbTrustedMarketToRows / flat-rows).
        tot_books = 2 if (open_tot is not None and best_tot is not None) else 1
        tot_verdict = (
            trust_cfb_market(kei_tot, best_tot, open_tot, tot_books)
            if kei_tot is not None
            else {"trusted": False, "market": None, "reason": "no_kei"}
        )
        edge_ou = None
        if (
            tot_verdict.get("trusted")
            and kei_tot is not None
            and best_tot is not None
        ):
            edge_ou = round(float(kei_tot) - float(best_tot), 2)
        tag_ou = cfb_edge_tag(
            abs(edge_ou) if edge_ou is not None else None, "total"
        )

        fire = "NO"
        if (
            CFB_SPREAD_PLAY_ELIGIBLE
            and verdict["trusted"]
            and edge_line is not None
            and abs(edge_line) >= CFB_PLAY_EDGE_PTS
        ):
            fire = "CANDIDATE_ONLY"

        # Measurement: legacy raw gap (home KEI vs away Open) vs same-side gap.
        board_raw_gap = None
        if open_away is not None:
            board_raw_gap = round(abs(float(kei_home) - float(open_away)), 2)
        same_side_gap = None
        if open_home is not None:
            same_side_gap = round(abs(float(kei_home) - float(open_home)), 2)
        # After home-sign fix, sign_mismatch_clear should be 0 (trust uses same-side).
        sign_mismatch_clear = (
            trusted_reason == "absurd_vs_kei"
            and same_side_gap is not None
            and same_side_gap < CFB_ABSURD_VS_KEI_PTS
        )

        rows.append(
            {
                "game_id": g.get("game_id"),
                "pair": pair,
                "game": label,
                "kickoff": g.get("kickoff"),
                "family": family_for(pair),
                "kei_spread_home": kei_home,
                "kei_total": kei_tot,
                "open_spread_away": open_away,
                "open_h": open_home,
                "open_spread_home": open_home,
                "best_spread_away_raw": best_away,
                "current_h": current_h,
                "best_spread_home_trusted": best_home_trusted,
                "painted_without_trust": painted_without_trust,
                "trust_label": trust_label,
                "open_total": open_tot,
                "best_total": best_tot,
                "n_books": n_books,
                "trusted": bool(verdict["trusted"]),
                "trusted_reason": trusted_reason,
                "board_raw_gap_kei_vs_open_away": board_raw_gap,
                "same_side_gap_kei_vs_open_home": same_side_gap,
                "sign_mismatch_clear": sign_mismatch_clear,
                "edge_line": edge_line,
                "edge_ou": edge_ou,
                "tag_line": tag_line,
                "tag_ou": tag_ou,
                "fire": fire,
            }
        )

    # Totals: trust gate + PLAY sit (mirror web cfbEdgeTag market=total).

    summary = {
        "slate_as_of": slate.get("as_of"),
        "slate_version": slate.get("slate_version"),
        "kei_as_of": kei.get("as_of"),
        "engine_version": kei.get("engine_version"),
        "odds_sport_key": SPORT_KEY,
        "odds_events": len(events),
        "feed_error": feed_err,
        "n_w1_fbs_with_kei": len(rows),
        "n_w1_fcs_null_kei": fcs_null,
        "n_trusted": sum(1 for r in rows if r["trusted"]),
        "n_kei_no_trusted_best": sum(1 for r in rows if not r["trusted"]),
        "by_reason": {},
        "n_play_candidate": sum(1 for r in rows if r["fire"] == "CANDIDATE_ONLY"),
        "n_sign_mismatch_clear": sum(1 for r in rows if r.get("sign_mismatch_clear")),
        "thresholds": {
            "LEAN": CFB_LEAN_EDGE_PTS,
            "PLAY": CFB_PLAY_EDGE_PTS,
            "ABSURD_VS_KEI": CFB_ABSURD_VS_KEI_PTS,
            "SINGLE_BOOK": CFB_SINGLE_BOOK_ABSURD_PTS,
            "TOTALS_PLAY_ELIGIBLE": CFB_TOTALS_PLAY_ELIGIBLE,
            "SPREAD_PLAY_ELIGIBLE": CFB_SPREAD_PLAY_ELIGIBLE,
        },
        "note_sign": (
            "Board Open/Best remain away-signed in odds cache. "
            "trustCfbMarket receives home via away_book_to_home / cfbAwayBookToHome. "
            "Band unchanged (ABSURD=12). KEI untouched. "
            "Totals PLAY sat (CFB_TOTALS_PLAY_ELIGIBLE=false); "
            "Spread PLAY sat (CFB_SPREAD_PLAY_ELIGIBLE=false); LEAN ≥2.5 still fires."
        ),
    }
    for r in rows:
        summary["by_reason"][r["trusted_reason"]] = (
            summary["by_reason"].get(r["trusted_reason"], 0) + 1
        )

    payload = {"summary": summary, "rows": rows}

    if args.json:
        print(json.dumps(payload, indent=2))
        return 0

    # Markdown table for audit
    print(f"# CFB Week 1 book dump (live loaders mirror)")
    print()
    print(f"- slate `as_of`={summary['slate_as_of']} · KEI `as_of`={summary['kei_as_of']}")
    print(f"- engine `{summary['engine_version']}`")
    print(f"- odds events={summary['odds_events']} feed_error={summary['feed_error']!r}")
    print(
        f"- W1 FBS+KEI={summary['n_w1_fbs_with_kei']} trusted={summary['n_trusted']} "
        f"no_trusted_best={summary['n_kei_no_trusted_best']} FCS null KEI={summary['n_w1_fcs_null_kei']}"
    )
    print(f"- reasons: {summary['by_reason']}")
    print(f"- PLAY candidates (|edge|≥4 + trusted): {summary['n_play_candidate']}")
    print()
    print(
        "| family | pair | kei_h | open_h | best_h_trusted | reason | edge | tag | fire |"
    )
    print("|---|---|---:|---:|---:|---|---:|---|---|")
    # Family A/B first, then others
    order = {"A": 0, "B": 1, "other": 2}
    for r in sorted(rows, key=lambda x: (order.get(x["family"], 9), x["pair"])):
        def fmt(v: Any) -> str:
            if v is None:
                return "—"
            if isinstance(v, float):
                return f"{v:.2f}".rstrip("0").rstrip(".")
            return str(v)

        print(
            f"| {r['family']} | {r['pair']} | {fmt(r['kei_spread_home'])} | "
            f"{fmt(r['open_spread_home'])} | {fmt(r['best_spread_home_trusted'])} | "
            f"{r['trusted_reason']} | {fmt(r['edge_line'])} | {r['tag_line']} | {r['fire']} |"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
