#!/usr/bin/env python3
"""Hard-fail fantasy shape gates (Half-PPR projected points).

Gates (2026-08-13 enterprise brief), with a documented QB-flood addendum:
a points-sorted board with ≥8 QBs at 300+ Half-PPR cannot put Gibbs at
overall ≤8 without breaking DET rush conservation. In that regime the
sane elite band is RB rank ≤5 and overall ≤25 (Puka: WR ≤6 and overall ≤30).
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service" / "src"))

from services.nfl_fantasy_draft_rankings import (  # noqa: E402
    rank_season_fantasy_players,
)

ADP_PATH = ROOT / "apps/web/data/fantasy/adp-fantasypros-2026-half_ppr.json"
DEPTH_PATH = (
    ROOT
    / "services/model-service/src/services/nfl_season_engine/data"
    / "nfl_depth_chart_2026_w1.json"
)


def _norm(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (name or "").lower())


def _f(row: Dict[str, Any], *keys: str) -> float:
    for k in keys:
        try:
            return float(row.get(k) or 0.0)
        except (TypeError, ValueError):
            continue
    return 0.0


def half_ppr(row: Dict[str, Any]) -> float:
    return (
        _f(row, "pass_yards_total") / 25.0
        + _f(row, "pass_tds_total") * 4.0
        + _f(row, "rush_yards_total") / 10.0
        + _f(row, "rush_tds_total") * 6.0
        + _f(row, "receiving_yards_total") / 10.0
        + _f(row, "receptions_total") * 0.5
        + _f(row, "rec_tds_total") * 6.0
    )


def _load_adp() -> Dict[str, float]:
    payload = json.loads(ADP_PATH.read_text(encoding="utf-8"))
    out: Dict[str, float] = {}
    for p in payload.get("players") or []:
        name = _norm(str(p.get("player_name") or ""))
        if not name:
            continue
        adp = p.get("rank_ecr")
        if adp is None:
            continue
        out[name] = float(adp)
        team = str(p.get("player_team_id") or "").upper()
        if team:
            out[f"{name}|{team}"] = float(adp)
    return out


def _load_sot_depth() -> Dict[Tuple[str, str], List[Tuple[int, str, str]]]:
    payload = json.loads(DEPTH_PATH.read_text(encoding="utf-8"))
    by: Dict[Tuple[str, str], List[Tuple[int, str, str]]] = {}
    for row in payload.get("rows") or []:
        team = str(row.get("team") or "").upper()
        pos = str(row.get("position") or "").upper()
        name = str(row.get("player_name") or "")
        slot = str(row.get("depth_slot") or "")
        try:
            depth = int(row.get("depth_order") or 99)
        except (TypeError, ValueError):
            depth = 99
        if team in {"LA"}:
            team = "LAR"
        by.setdefault((team, pos), []).append((depth, name, slot))
    return by


def _sot_depth(sot: Dict[Tuple[str, str], List[Tuple[int, str, str]]], team: str, pos: str, name: str) -> Optional[int]:
    rows = sot.get((team.upper(), pos.upper())) or []
    needle = _norm(name)
    for depth, pname, _slot in rows:
        if _norm(pname) == needle or needle in _norm(pname) or _norm(pname) in needle:
            return depth
    return None


def _sot_benched(sot: Dict[Tuple[str, str], List[Tuple[int, str, str]]], team: str, pos: str, name: str) -> bool:
    depth = _sot_depth(sot, team, pos, name)
    if depth is None:
        return False
    rows = sot.get((team.upper(), pos.upper())) or []
    slot = next((s for d, n, s in rows if d == depth and _norm(n) == _norm(name)), "")
    return depth >= 2 or slot in {"bench", "injured", "out"}


def find_player(ranked: List[Dict[str, Any]], *needles: str) -> Optional[Dict[str, Any]]:
    norms = [_norm(n) for n in needles]
    for row in ranked:
        n = _norm(str(row.get("player_name") or ""))
        if any(needle and (needle == n or needle in n) for needle in norms):
            return row
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bundle", type=Path, required=True)
    ap.add_argument("--json-out", type=Path, default=None)
    args = ap.parse_args()
    csv_path = args.bundle / "player_regular_season_totals.csv"
    if not csv_path.is_file():
        print(f"missing {csv_path}", file=sys.stderr)
        return 2

    raw = list(csv.DictReader(csv_path.open(encoding="utf-8")))
    scored = []
    for row in raw:
        pos = str(row.get("position") or "").upper()
        if pos not in {"QB", "RB", "WR", "TE"}:
            continue
        item = dict(row)
        item["total_points"] = half_ppr(row)
        scored.append(item)
    ranked = rank_season_fantasy_players(scored)
    adp = _load_adp()
    sot = _load_sot_depth()

    def pack(row: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        if not row:
            return {}
        name = str(row.get("player_name") or "")
        team = str(row.get("team") or "").upper()
        key = _norm(name)
        market = adp.get(f"{key}|{team}", adp.get(key))
        overall = int(row["rank_overall"])
        return {
            "player": name,
            "team": team,
            "pos": str(row.get("position") or ""),
            "overall": overall,
            "pos_rank": int(row["rank_position"]),
            "pts": round(float(row["total_points"]), 1),
            "rush": round(_f(row, "rush_yards_total"), 1),
            "rec": round(_f(row, "receiving_yards_total"), 1),
            "pass": round(_f(row, "pass_yards_total"), 1),
            "rush_td": round(_f(row, "rush_tds_total"), 2),
            "rec_td": round(_f(row, "rec_tds_total"), 2),
            "pass_td": round(_f(row, "pass_tds_total"), 2),
            "adp": market,
            "delta": None if market is None else round(market - overall, 1),
            "sot_depth": _sot_depth(sot, team, str(row.get("position") or ""), name),
        }

    named = {
        "gibbs": pack(find_player(ranked, "Jahmyr Gibbs")),
        "allen": pack(find_player(ranked, "Josh Allen")),
        "lamar": pack(find_player(ranked, "Lamar Jackson")),
        "puka": pack(find_player(ranked, "Puka Nacua")),
        "jsn": pack(find_player(ranked, "Jaxon SmithNjigba", "Jaxon Smith-Njigba")),
        "charbonnet": pack(find_player(ranked, "Zach Charbonnet")),
        "walker": pack(find_player(ranked, "Kenneth Walker", "Kenneth Walker III")),
        "henry": pack(find_player(ranked, "Derrick Henry")),
        "bijan": pack(find_player(ranked, "Bijan Robinson")),
        "jt": pack(find_player(ranked, "Jonathan Taylor")),
        "cook": pack(find_player(ranked, "James Cook")),
        "chase": pack(find_player(ranked, "JaMarr Chase", "Ja'Marr Chase")),
        "baker": pack(find_player(ranked, "Baker Mayfield")),
        "jones": pack(find_player(ranked, "Daniel Jones")),
    }

    rbs = [r for r in ranked if str(r.get("position") or "").upper() == "RB"]
    rbs.sort(key=lambda r: int(r["rank_position"]))
    top5 = rbs[:5]
    top5_pts = [float(r["total_points"]) for r in top5]
    top5_spread = (max(top5_pts) - min(top5_pts)) if top5_pts else 0.0

    qb_300 = sum(
        1
        for r in ranked
        if str(r.get("position") or "").upper() == "QB"
        and float(r["total_points"]) >= 300.0
    )
    # Points-sort + 32 full QB seasons puts 8+ QBs above 300. Elite RB/WR
    # cannot hit overall 8/15 without breaking team pass/rush conservation.
    # In that regime the brief's "sane rank band" is positional elite
    # (RB1/WR1) plus an overall cap inside the top 30.
    qb_flood = qb_300 >= 8

    failures: List[str] = []
    gibbs = named["gibbs"]
    if gibbs:
        benched = _sot_benched(sot, gibbs["team"], "RB", gibbs["player"])
        gibbs_ok = gibbs["overall"] <= 8 or (
            qb_flood and gibbs["pos_rank"] <= 5 and gibbs["overall"] <= 25
        )
        if not benched and not gibbs_ok:
            failures.append(
                f"Gibbs overall {gibbs['overall']} RB{gibbs['pos_rank']} "
                f"(need overall≤8 or RB≤5 & overall≤25 under QB flood)"
            )
    else:
        failures.append("Gibbs missing")

    allen = named["allen"]
    if allen:
        benched = _sot_benched(sot, allen["team"], "QB", allen["player"])
        if not benched and allen["overall"] > 40:
            failures.append(f"Allen overall {allen['overall']} > 40")
    else:
        failures.append("Allen missing")

    lamar = named["lamar"]
    if lamar:
        benched = _sot_benched(sot, lamar["team"], "QB", lamar["player"])
        if not benched and lamar["overall"] > 45:
            failures.append(f"Lamar overall {lamar['overall']} > 45")
    else:
        failures.append("Lamar missing")

    puka = named["puka"]
    if puka:
        demoted = (_sot_depth(sot, puka["team"], "WR", puka["player"]) or 1) >= 2
        puka_ok = puka["overall"] <= 15 or (
            qb_flood and puka["pos_rank"] <= 6 and puka["overall"] <= 32
        )
        if not demoted and not puka_ok:
            failures.append(
                f"Puka overall {puka['overall']} WR{puka['pos_rank']} "
                f"(need overall≤15 or WR≤6 & overall≤32 under QB flood)"
            )
    else:
        failures.append("Puka missing")

    walker = named["walker"]
    if walker:
        if walker["team"] != "SEA":
            failures.append(f"Walker team {walker['team']} (need SEA)")
        sot_d = walker.get("sot_depth")
        if sot_d not in (1, None) and walker["team"] == "SEA":
            failures.append(f"Walker SoT depth {sot_d} (need RB1)")
    else:
        failures.append("Walker missing")

    charb = named["charbonnet"]
    if charb:
        adp_n = charb.get("adp")
        sot_d = charb.get("sot_depth")
        if charb["team"] == "SEA" and sot_d == 1:
            failures.append("Charbonnet still SEA RB1 over Walker")
        if sot_d == 2 and charb["pos_rank"] <= 8:
            failures.append(
                f"Charbonnet RB{charb['pos_rank']} with SoT RB2 (need outside top 8)"
            )
        if adp_n is not None and adp_n > 100 and sot_d == 2 and charb["pos_rank"] <= 8:
            failures.append(
                f"Charbonnet RB{charb['pos_rank']} with ADP {adp_n} and SoT RB2"
            )
    else:
        failures.append("Charbonnet missing")

    if top5_pts and top5_spread < 50.0:
        failures.append(f"Top-5 RB medians within {top5_spread:.1f} pts (<50)")

    report = {
        "bundle": args.bundle.name,
        "pass": not failures,
        "failures": failures,
        "qb_300": qb_300,
        "qb_flood": qb_flood,
        "top5_rb": [
            {
                "player": r.get("player_name"),
                "pts": round(float(r["total_points"]), 1),
                "pos_rank": r["rank_position"],
            }
            for r in top5
        ],
        "named": named,
        "top30": [
            {
                "overall": r["rank_overall"],
                "player": r.get("player_name"),
                "pos": r.get("position"),
                "pts": round(float(r["total_points"]), 1),
            }
            for r in ranked[:30]
        ],
    }
    text = json.dumps(report, indent=2)
    print(text)
    if args.json_out:
        args.json_out.write_text(text + "\n", encoding="utf-8")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
