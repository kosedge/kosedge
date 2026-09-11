#!/usr/bin/env python3
"""Joined residual audit — KEI/model vs market. Measure only.

Does not retune KEI, pull into the odds lake, or flip PLAY. One optional
Odds API read for the current priced slate (same endpoint as
cfb_dump_edgeboard.py). Prefer --odds-json to reuse a snapshot.

Usage:
  python3 scripts/cfb/cfb_joined_residual_audit.py \\
    --kei apps/web/lib/data/cfb-kei-w0-w1-2026.json \\
    --before /tmp/kei-before.json \\
    --odds-json data/ops/cfb-w2-odds-join-20260911.json \\
    --weeks 2 --json
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "cfb"))

from cfb_dump_edgeboard import (  # noqa: E402
    away_book_to_home,
    fetch_odds,
    match_keys,
    pick_spread_open_best,
    pick_total_open_best,
    trust_cfb_market,
)

POWER_PATH = REPO / "services/model-service/src/services/cfb_season_engine/data/cfb_power_sot_2026.json"
P0 = (
    "MIZZ",
    "ARST",
    "CSU",
    "ECU",
    "JVST",
    "NEV",
    "ODU",
    "TOL",
    "UAB",
    "UNM",
    "UNT",
)
FOCUS = (("MIZZ", "KU"), ("RUT", "BC"))


def _num(v: Any) -> Optional[float]:
    if v is None or v == "" or v == "—":
        return None
    try:
        n = float(v)
    except (TypeError, ValueError):
        return None
    return None if n != n else n


def _sign(v: Optional[float]) -> Optional[int]:
    n = _num(v)
    if n is None or abs(n) < 1e-9:
        return 0
    return 1 if n > 0 else -1


def load_kei(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def index_games(pack: Dict[str, Any]) -> Dict[Tuple[str, str, int], Dict[str, Any]]:
    out: Dict[Tuple[str, str, int], Dict[str, Any]] = {}
    for g in pack.get("games") or []:
        home = str(g.get("home") or "").upper()
        away = str(g.get("away") or "").upper()
        week = int(g.get("week") or -1)
        out[(away, home, week)] = g
    return out


def slim_from_espn(path: Path) -> Dict[str, Any]:
    """Scoreboard snapshot (measure only). Home-signed spread + over/under."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    rows = raw.get("rows") or raw.get("events") or []
    by_key: Dict[str, Dict[str, Any]] = {}
    slim_rows = []
    for row in rows:
        label = row.get("label") or (
            f"{row.get('away_name')} @ {row.get('home_name')}"
        )
        spread_home = _num(row.get("spread_home") if "spread_home" in row else row.get("spread"))
        total = _num(row.get("over_under") or row.get("total"))
        payload = {
            "label": label,
            "open_away": None if spread_home is None else -spread_home,
            "best_away": None if spread_home is None else -spread_home,
            "n_books": 1,
            "best_book": row.get("provider") or "espn_scoreboard",
            "open_total": total,
            "best_total": total,
            "commence": row.get("commence"),
            "open_spread_home": spread_home,
            "best_spread_home": spread_home,
            "source": "espn_scoreboard",
        }
        slim_rows.append(payload)
        for k in match_keys(label):
            by_key.setdefault(k, payload)
    return {
        "n_events": len(slim_rows),
        "source": "espn_scoreboard",
        "rows": slim_rows,
        "by_key": by_key,
    }


def slim_odds(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    rows = []
    by_key: Dict[str, Dict[str, Any]] = {}
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
            "open_spread_home": away_book_to_home(open_a),
            "best_spread_home": away_book_to_home(best_a),
        }
        rows.append(payload)
        for k in match_keys(label):
            by_key.setdefault(k, payload)
    return {"n_events": len(events), "rows": rows, "by_key": by_key}


def attach_odds(
    game: Dict[str, Any], odds_index: Dict[str, Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    away = str(game.get("away") or "")
    home = str(game.get("home") or "")
    label = f"{game.get('away_name') or away} @ {game.get('home_name') or home}"
    for k in match_keys(label) + match_keys(f"{away} @ {home}"):
        if k in odds_index:
            return odds_index[k]
    return None


def residuals_for_pack(
    pack: Dict[str, Any],
    odds_index: Dict[str, Dict[str, Any]],
    weeks: Sequence[int],
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    week_set = set(weeks)
    for g in pack.get("games") or []:
        if int(g.get("week") or -1) not in week_set:
            continue
        if not g.get("fbs_vs_fbs"):
            continue
        kei = g.get("kei") or {}
        kei_sp = _num(kei.get("kei_spread_home") if kei.get("kei_spread_home") is not None else g.get("model_spread_home"))
        model_sp = _num(g.get("model_spread_home") or kei.get("model_spread_home"))
        kei_tot = _num(kei.get("kei_total") if kei.get("kei_total") is not None else g.get("model_total"))
        model_tot = _num(g.get("model_total") or kei.get("model_total"))
        odds = attach_odds(g, odds_index)
        if not odds:
            rows.append(
                {
                    "week": g.get("week"),
                    "away": g.get("away"),
                    "home": g.get("home"),
                    "pair": f"{g.get('away')}@{g.get('home')}",
                    "joined": False,
                    "kei_spread_home": kei_sp,
                    "model_spread_home": model_sp,
                    "kei_total": kei_tot,
                    "model_total": model_tot,
                }
            )
            continue
        mkt_sp = _num(odds.get("best_spread_home"))
        if mkt_sp is None:
            mkt_sp = _num(odds.get("open_spread_home"))
        mkt_tot = _num(odds.get("best_total"))
        if mkt_tot is None:
            mkt_tot = _num(odds.get("open_total"))
        trust = trust_cfb_market(
            kei_sp,
            odds.get("best_spread_home"),
            odds.get("open_spread_home"),
            odds.get("n_books"),
        )
        sp_res = (
            None
            if kei_sp is None or mkt_sp is None
            else round(kei_sp - mkt_sp, 3)
        )
        tot_res = (
            None
            if kei_tot is None or mkt_tot is None
            else round(kei_tot - mkt_tot, 3)
        )
        rows.append(
            {
                "week": g.get("week"),
                "away": g.get("away"),
                "home": g.get("home"),
                "pair": f"{g.get('away')}@{g.get('home')}",
                "joined": True,
                "trusted": bool(trust.get("trusted")),
                "trust_reason": trust.get("reason"),
                "kei_spread_home": kei_sp,
                "model_spread_home": model_sp,
                "market_spread_home": mkt_sp,
                "spread_residual": sp_res,
                "favorite_flip_vs_market": bool(
                    kei_sp is not None
                    and mkt_sp is not None
                    and _sign(kei_sp) != 0
                    and _sign(mkt_sp) != 0
                    and _sign(kei_sp) != _sign(mkt_sp)
                ),
                "kei_total": kei_tot,
                "model_total": model_tot,
                "market_total": mkt_tot,
                "total_residual": tot_res,
                "n_books": odds.get("n_books"),
            }
        )
    return rows


def _mae(vals: List[float]) -> Optional[float]:
    if not vals:
        return None
    return round(sum(abs(v) for v in vals) / len(vals), 3)


def _median(vals: List[float]) -> Optional[float]:
    if not vals:
        return None
    return round(float(statistics.median(vals)), 3)


def summarize(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    joined = [r for r in rows if r.get("joined") and r.get("spread_residual") is not None]
    tot_joined = [r for r in rows if r.get("joined") and r.get("total_residual") is not None]
    sp = [float(r["spread_residual"]) for r in joined]
    tot = [float(r["total_residual"]) for r in tot_joined]
    gaps = [abs(v) for v in sp]
    flips = [r for r in joined if r.get("favorite_flip_vs_market")]
    team_abs: Dict[str, List[float]] = defaultdict(list)
    for r in joined:
        team_abs[str(r["away"])].append(abs(float(r["spread_residual"])))
        team_abs[str(r["home"])].append(abs(float(r["spread_residual"])))
    outliers = sorted(
        (
            {
                "team": t,
                "n": len(vs),
                "mean_abs_spread_residual": round(sum(vs) / len(vs), 3),
            }
            for t, vs in team_abs.items()
        ),
        key=lambda x: -x["mean_abs_spread_residual"],
    )[:12]
    return {
        "n_fbs_games": len(rows),
        "n_joined_spread": len(joined),
        "n_joined_total": len(tot_joined),
        "n_unjoined": sum(1 for r in rows if not r.get("joined")),
        "spread_mae": _mae(sp),
        "total_mae": _mae(tot),
        "median_spread_residual": _median(sp),
        "median_total_residual": _median(tot),
        "mean_total_residual": round(sum(tot) / len(tot), 3) if tot else None,
        "favorite_flips_vs_market": len(flips),
        "gap_ge_7": sum(1 for g in gaps if g >= 7),
        "gap_ge_10": sum(1 for g in gaps if g >= 10),
        "gap_ge_14": sum(1 for g in gaps if g >= 14),
        "gap_ge_20": sum(1 for g in gaps if g >= 20),
        "team_outliers": outliers,
        "flip_pairs": [r["pair"] for r in flips],
    }


def power_null_census(path: Path) -> Dict[str, Any]:
    pack = json.loads(path.read_text(encoding="utf-8"))
    nulls = []
    independent_p0 = []
    for row in pack.get("teams") or []:
        code = str(row.get("team") or "").upper()
        p = _num(row.get("power_index"))
        off = _num(row.get("offense_index"))
        deff = _num(row.get("defense_index"))
        if p is None or off is None or deff is None:
            nulls.append(code)
        if code in P0 and str(row.get("conference") or "") == "Independent":
            independent_p0.append(code)
    return {
        "n_teams": len(pack.get("teams") or []),
        "null_power_count": len(nulls),
        "null_power_codes": nulls,
        "p0_independent_leftover": independent_p0,
        "p0_null": [c for c in nulls if c in P0],
        "power_as_of": pack.get("power_as_of") or pack.get("as_of"),
    }


def focus_pair(
    pack: Dict[str, Any], away: str, home: str
) -> Optional[Dict[str, Any]]:
    for g in pack.get("games") or []:
        if str(g.get("away") or "").upper() == away and str(g.get("home") or "").upper() == home:
            kei = g.get("kei") or {}
            return {
                "week": g.get("week"),
                "pair": f"{away}@{home}",
                "kei_version": pack.get("kei_version"),
                "as_of": pack.get("as_of"),
                "model_spread_home": g.get("model_spread_home"),
                "kei_spread_home": kei.get("kei_spread_home"),
                "model_total": g.get("model_total"),
                "kei_total": kei.get("kei_total"),
                "tag": kei.get("tag"),
            }
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--kei",
        default=str(REPO / "apps/web/lib/data/cfb-kei-w0-w1-2026.json"),
    )
    ap.add_argument("--before", help="Pre-repair KEI pack for before/after")
    ap.add_argument("--odds-json", help="Reuse a slim odds snapshot")
    ap.add_argument("--espn-json", help="ESPN scoreboard snapshot (measure only)")
    ap.add_argument("--write-odds-json", help="Persist slim odds after one fetch")
    ap.add_argument("--weeks", default="2", help="Comma weeks, e.g. 2 or 1,2")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    weeks = [int(x) for x in str(args.weeks).split(",") if x.strip() != ""]
    after = load_kei(Path(args.kei))
    before = load_kei(Path(args.before)) if args.before else None

    if args.espn_json:
        slim = slim_from_espn(Path(args.espn_json))
        if args.write_odds_json:
            Path(args.write_odds_json).write_text(
                json.dumps(slim, indent=2), encoding="utf-8"
            )
        odds_index = slim["by_key"]
        odds_meta = {"source": "espn_scoreboard", "n_events": slim["n_events"]}
    elif args.odds_json and Path(args.odds_json).exists():
        odds_pack = json.loads(Path(args.odds_json).read_text(encoding="utf-8"))
        odds_index = odds_pack.get("by_key") or {}
        odds_meta = {"source": args.odds_json, "n_events": odds_pack.get("n_events")}
    else:
        key = (
            os.environ.get("ODDS_API_KEY")
            or os.environ.get("ODDS_API_KEY_BACKUP")
            or ""
        ).strip()
        if not key:
            print("ODDS_API_KEY not set and no --odds-json", file=sys.stderr)
            return 2
        events, err = fetch_odds(key)
        if err:
            print(f"odds feed error: {err}", file=sys.stderr)
            return 3
        slim = slim_odds(events)
        if args.write_odds_json:
            Path(args.write_odds_json).write_text(
                json.dumps(slim, indent=2), encoding="utf-8"
            )
        odds_index = slim["by_key"]
        odds_meta = {"source": "live_odds_api", "n_events": slim["n_events"]}

    after_rows = residuals_for_pack(after, odds_index, weeks)
    report: Dict[str, Any] = {
        "weeks": weeks,
        "after_stamps": {
            "kei_version": after.get("kei_version"),
            "as_of": after.get("as_of"),
            "generated_at": after.get("generated_at"),
            "engine_version": after.get("engine_version"),
        },
        "odds": odds_meta,
        "after": summarize(after_rows),
        "focus": {},
        "power": power_null_census(POWER_PATH),
        "kill_switch": "CFB_EDGE_BOARD_PUBLIC_ENABLED must stay false",
    }
    if before:
        before_rows = residuals_for_pack(before, odds_index, weeks)
        report["before_stamps"] = {
            "kei_version": before.get("kei_version"),
            "as_of": before.get("as_of"),
            "generated_at": before.get("generated_at"),
        }
        report["before"] = summarize(before_rows)
        before_idx = {(r["away"], r["home"]): r for r in before_rows}
        after_idx = {(r["away"], r["home"]): r for r in after_rows}
        repair_flips = []
        for key, ar in after_idx.items():
            br = before_idx.get(key)
            if not br:
                continue
            if _sign(br.get("kei_spread_home")) != _sign(ar.get("kei_spread_home")):
                if _sign(br.get("kei_spread_home")) and _sign(ar.get("kei_spread_home")):
                    repair_flips.append(
                        {
                            "pair": ar["pair"],
                            "before": br.get("kei_spread_home"),
                            "after": ar.get("kei_spread_home"),
                        }
                    )
        report["favorite_flips_before_vs_after"] = repair_flips

    for away, home in FOCUS:
        report["focus"][f"{away}@{home}"] = {
            "after": focus_pair(after, away, home),
            "before": focus_pair(before, away, home) if before else None,
        }

    if args.json:
        print(json.dumps(report, indent=2))
        return 0

    a = report["after"]
    print(f"weeks={weeks} kei={after.get('kei_version')} as_of={after.get('as_of')}")
    print(
        f"joined spread n={a['n_joined_spread']}  MAE={a['spread_mae']}  "
        f"median residual={a['median_spread_residual']}"
    )
    print(
        f"joined total  n={a['n_joined_total']}  MAE={a['total_mae']}  "
        f"median residual={a['median_total_residual']}  "
        f"mean residual={a['mean_total_residual']}"
    )
    print(
        f"favorite flips vs market={a['favorite_flips_vs_market']}  "
        f"|gap|≥7/{a['gap_ge_7']} ≥10/{a['gap_ge_10']} ≥14/{a['gap_ge_14']} ≥20/{a['gap_ge_20']}"
    )
    print(
        f"null power={report['power']['null_power_count']}  "
        f"P0 leftover Independent={report['power']['p0_independent_leftover']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
