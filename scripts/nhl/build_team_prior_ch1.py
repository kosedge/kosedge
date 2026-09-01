#!/usr/bin/env python3
"""Rebuild NHL Ch1 team prior pack from nhl_team_box_2025.json only.

Formula:
  team' = league_mean + s * (team_2025_26 − league_mean)

Paper-sim {0.70, 0.80, 0.85, 0.90}; chosen NHL_TEAM_CARRY_SHRINK = 0.85.
No board emit. No xG. No player tables.

Usage:
  python3 scripts/nhl/build_team_prior_ch1.py
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[2]
BOX = (
    ROOT
    / "services/model-service/src/services/nhl_season_engine/data"
    / "nhl_team_box_2025.json"
)
OUT = (
    ROOT
    / "services/model-service/src/services/nhl_season_engine/data"
    / "nhl_team_prior_2026.json"
)

EXPECTED_TEAMS = 32
S_SET = [0.70, 0.80, 0.85, 0.90]
CHOSEN = 0.85  # NHL_TEAM_CARRY_SHRINK — own constant; not NBA/WNBA


def shrink(value: float, mean: float, s: float) -> float:
    return mean + s * (value - mean)


def _utc_today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def main() -> None:
    raw = json.loads(BOX.read_text(encoding="utf-8"))
    rows_in: List[Dict[str, Any]] = list(raw.get("teams") or [])
    if len(rows_in) != EXPECTED_TEAMS:
        raise SystemExit(f"expected {EXPECTED_TEAMS} team box rows; got {len(rows_in)}")

    teams: Dict[str, Dict[str, Any]] = {}
    for row in rows_in:
        code = str(row.get("team") or "").upper()
        if not code:
            raise SystemExit(f"team box row missing team: {row}")
        gf = float(row["gf"])
        ga = float(row["ga"])
        teams[code] = {
            "team": code,
            "team_name": row.get("team_name"),
            "w": int(row.get("wins") or 0),
            "l": int(row.get("losses") or 0),
            "otl": int(row.get("ot_losses") or 0),
            "pts": int(row.get("points") or 0),
            "gp": int(row.get("games_played") or 0),
            "gf_pre": gf,
            "ga_pre": ga,
            "net_pre": gf - ga,
            "conference": row.get("conference"),
            "division": row.get("division"),
        }

    if len(teams) != EXPECTED_TEAMS:
        raise SystemExit(f"duplicate/missing abbrevs: {len(teams)}")

    n = float(EXPECTED_TEAMS)

    def mean(key: str) -> float:
        return sum(float(t[key]) for t in teams.values()) / n

    lm_gf, lm_ga, lm_net = mean("gf_pre"), mean("ga_pre"), mean("net_pre")

    # Worst ~1/3 by points treated as "lottery" for invert gate (10 of 32).
    lottery = {
        t["team"]
        for t in sorted(teams.values(), key=lambda t: (t["pts"], t["w"], -t["l"]))[:10]
    }

    paper = []
    for s in S_SET:
        ranked_pre = sorted(teams.values(), key=lambda t: -t["net_pre"])
        ranked_post = sorted(
            teams.values(), key=lambda t: -shrink(t["net_pre"], lm_net, s)
        )
        top5_post = [t["team"] for t in ranked_post[:5]]
        nets = [shrink(t["net_pre"], lm_net, s) for t in teams.values()]
        mean_net_post = sum(nets) / n
        paper.append(
            {
                "s": s,
                "mean_net_post": round(mean_net_post, 8),
                "net_sd_pre": round(
                    (sum((t["net_pre"] - lm_net) ** 2 for t in teams.values()) / n)
                    ** 0.5,
                    4,
                ),
                "net_sd_post": round(
                    (sum((x - mean_net_post) ** 2 for x in nets) / n) ** 0.5,
                    4,
                ),
                "top5_pre": [t["team"] for t in ranked_pre[:5]],
                "top5_post": top5_post,
                "bot5_pre": [t["team"] for t in ranked_pre[-5:]],
                "bot5_post": [t["team"] for t in ranked_post[-5:]],
                "lottery_in_top5_post": [c for c in top5_post if c in lottery],
                "col_net_post": round(shrink(teams["COL"]["net_pre"], lm_net, s), 4),
                "van_net_post": round(shrink(teams["VAN"]["net_pre"], lm_net, s), 4),
            }
        )

    out_teams: Dict[str, Dict[str, Any]] = {}
    for code, t in sorted(teams.items()):
        out_teams[code] = {
            "team": code,
            "team_name": t["team_name"],
            "w": t["w"],
            "l": t["l"],
            "otl": t["otl"],
            "pts": t["pts"],
            "gp": t["gp"],
            "conference": t["conference"],
            "division": t["division"],
            "gf_pre": t["gf_pre"],
            "ga_pre": t["ga_pre"],
            "net_pre": t["net_pre"],
            "gf": round(shrink(t["gf_pre"], lm_gf, CHOSEN), 4),
            "ga": round(shrink(t["ga_pre"], lm_ga, CHOSEN), 4),
            "net_rating": round(shrink(t["net_pre"], lm_net, CHOSEN), 4),
            "carry_shrink": CHOSEN,
        }

    post_nets = [row["net_rating"] for row in out_teams.values()]
    pack = {
        "engine_version": "nhl-season-engine-v0.1",
        "as_of": _utc_today(),
        "season": "2025-26",
        "carry_to_season": "2026-27",
        "source": "nhl_team_box_2025.json (official *.nhle.com standings via nhl_data fetcher)",
        "source_note": (
            "Ch1 shell shrinks 2025–26 RS GF/GA toward league mean for 2026–27. "
            "Reads nhl_team_box_2025.json only. No xG. No player tables. "
            "Does not emit KEI onto /edge-board/nhl (KEINHL stays blank)."
        ),
        "formula": (
            "team_prime = league_mean + NHL_TEAM_CARRY_SHRINK * "
            "(team_2025_26 - league_mean)"
        ),
        "NHL_TEAM_CARRY_SHRINK": CHOSEN,
        "paper_sim_s_set": S_SET,
        "paper_sim": paper,
        "league_mean_pre": {
            "gf": round(lm_gf, 6),
            "ga": round(lm_ga, 6),
            "net_rating": round(lm_net, 8),
        },
        "league_mean_post": {
            "gf": round(sum(r["gf"] for r in out_teams.values()) / n, 6),
            "ga": round(sum(r["ga"] for r in out_teams.values()) / n, 6),
            "net_rating": round(sum(post_nets) / n, 8),
        },
        "team_count": EXPECTED_TEAMS,
        "teams": out_teams,
        "does_not": [
            "write KEI onto /edge-board/nhl",
            "fill blank KEINHL",
            "xG from MoneyPuck/NST",
            "new player tables",
            "situation layer",
            "reuse NBA/WNBA TEAM_CARRY_SHRINK",
            "CFB/NFL",
            "TOI grid / goalie tandem (Ch2)",
        ],
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(pack, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT} teams={EXPECTED_TEAMS} s={CHOSEN}")
    chosen_sim = next(r for r in paper if r["s"] == CHOSEN)
    print(
        "mean_net_post",
        chosen_sim["mean_net_post"],
        "top5",
        chosen_sim["top5_post"],
        "bot5",
        chosen_sim["bot5_post"],
        "lottery_in_top5",
        chosen_sim["lottery_in_top5_post"],
    )


if __name__ == "__main__":
    main()
