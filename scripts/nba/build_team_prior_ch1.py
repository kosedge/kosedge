#!/usr/bin/env python3
"""Rebuild NBA Ch1 team prior pack from Basketball-Reference 2025-26 tables.

stats.nba.com Advanced timed out in the Cloud Agent build env; data.nba.com
2025-26 RS scores were unpublished on CDN. BR Team Ratings + advanced Pace
carry the same ORtg/DRtg/net/pace concepts. Re-run when NBA Stats egress works
and prefer leaguedashteamstats MeasureType=Advanced as SoT.

Usage:
  python scripts/nba/build_team_prior_ch1.py
"""

from __future__ import annotations

import html as htmlmod
import json
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = (
    ROOT
    / "services/model-service/src/services/nba_season_engine/data"
    / "nba_team_prior_2025_26_carry_2026_27.json"
)

TEAM_MAP = {
    "Oklahoma City Thunder": "OKC",
    "San Antonio Spurs": "SAS",
    "Boston Celtics": "BOS",
    "Detroit Pistons": "DET",
    "New York Knicks": "NYK",
    "Houston Rockets": "HOU",
    "Denver Nuggets": "DEN",
    "Charlotte Hornets": "CHA",
    "Cleveland Cavaliers": "CLE",
    "Minnesota Timberwolves": "MIN",
    "Toronto Raptors": "TOR",
    "Atlanta Hawks": "ATL",
    "Miami Heat": "MIA",
    "Phoenix Suns": "PHX",
    "Los Angeles Lakers": "LAL",
    "Los Angeles Clippers": "LAC",
    "Orlando Magic": "ORL",
    "Portland Trail Blazers": "POR",
    "Philadelphia 76ers": "PHI",
    "Golden State Warriors": "GSW",
    "New Orleans Pelicans": "NOP",
    "Chicago Bulls": "CHI",
    "Dallas Mavericks": "DAL",
    "Memphis Grizzlies": "MEM",
    "Milwaukee Bucks": "MIL",
    "Indiana Pacers": "IND",
    "Utah Jazz": "UTA",
    "Sacramento Kings": "SAC",
    "Brooklyn Nets": "BKN",
    "Washington Wizards": "WAS",
}

S_SET = [0.70, 0.80, 0.85, 0.90]
CHOSEN = 0.85
UA = {"User-Agent": "Mozilla/5.0 (compatible; KosEdgeNbaCh1/1.0)"}


def _get(url: str) -> str:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read().decode("utf-8", "replace").replace("<!--", "").replace("-->", "")


def _cells(row: str) -> list[str]:
    return [
        htmlmod.unescape(re.sub(r"<[^>]+>", "", c)).strip()
        for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, flags=re.S | re.I)
    ]


def shrink(value: float, mean: float, s: float) -> float:
    return mean + s * (value - mean)


def main() -> None:
    ratings = _get("https://www.basketball-reference.com/leagues/NBA_2026_ratings.html")
    summary = _get("https://www.basketball-reference.com/leagues/NBA_2026.html")
    teams: dict[str, dict] = {}
    for row in re.findall(r"<tr[^>]*>.*?</tr>", ratings, flags=re.S | re.I):
        texts = _cells(row)
        name = next((t for t in texts if t in TEAM_MAP), None)
        if not name:
            continue
        i = texts.index(name)
        w, l = int(texts[i + 3]), int(texts[i + 4])
        code = TEAM_MAP[name]
        teams[code] = {
            "team": code,
            "team_name": name,
            "w": w,
            "l": l,
            "gp": w + l,
            "ortg_pre": float(texts[i + 7]),
            "drtg_pre": float(texts[i + 8]),
            "net_pre": float(texts[i + 9]),
        }

    table = re.search(
        r'<table[^>]*id="advanced-team"[^>]*>.*?</table>', summary, flags=re.S | re.I
    )
    if not table:
        raise SystemExit("advanced-team table missing")
    for row in re.findall(r"<tr[^>]*>.*?</tr>", table.group(0), flags=re.S | re.I):
        cells = _cells(row)
        if len(cells) < 14:
            continue
        raw = cells[1].rstrip("*")
        if raw not in TEAM_MAP:
            continue
        teams[TEAM_MAP[raw]]["pace_pre"] = float(cells[13])

    if len(teams) != 30 or any("pace_pre" not in t for t in teams.values()):
        raise SystemExit(f"expected 30 teams with pace; got {len(teams)}")

    def mean(key: str) -> float:
        return sum(t[key] for t in teams.values()) / 30.0

    lm_ortg, lm_drtg, lm_net, lm_pace = (
        mean("ortg_pre"),
        mean("drtg_pre"),
        mean("net_pre"),
        mean("pace_pre"),
    )

    paper = []
    for s in S_SET:
        ranked_pre = sorted(teams.values(), key=lambda t: -t["net_pre"])
        ranked_post = sorted(
            teams.values(), key=lambda t: -shrink(t["net_pre"], lm_net, s)
        )
        lottery = {t["team"] for t in sorted(teams.values(), key=lambda t: t["w"])[:8]}
        top5_post = [t["team"] for t in ranked_post[:5]]
        nets = [shrink(t["net_pre"], lm_net, s) for t in teams.values()]
        paper.append(
            {
                "s": s,
                "mean_net_post": round(sum(nets) / 30, 8),
                "net_sd_pre": round(
                    (sum((t["net_pre"] - lm_net) ** 2 for t in teams.values()) / 30) ** 0.5,
                    4,
                ),
                "net_sd_post": round(
                    (sum((n - sum(nets) / 30) ** 2 for n in nets) / 30) ** 0.5, 4
                ),
                "top5_pre": [t["team"] for t in ranked_pre[:5]],
                "top5_post": top5_post,
                "bot5_pre": [t["team"] for t in ranked_pre[-5:]],
                "bot5_post": [t["team"] for t in ranked_post[-5:]],
                "lottery_in_top5_post": [c for c in top5_post if c in lottery],
                "okc_net_post": round(shrink(teams["OKC"]["net_pre"], lm_net, s), 4),
                "was_net_post": round(shrink(teams["WAS"]["net_pre"], lm_net, s), 4),
            }
        )

    out_teams = {}
    for code, t in sorted(teams.items()):
        out_teams[code] = {
            **{k: t[k] for k in ("team", "team_name", "w", "l", "gp")},
            "ortg_pre": t["ortg_pre"],
            "drtg_pre": t["drtg_pre"],
            "net_pre": t["net_pre"],
            "pace_pre": t["pace_pre"],
            "ortg": round(shrink(t["ortg_pre"], lm_ortg, CHOSEN), 4),
            "drtg": round(shrink(t["drtg_pre"], lm_drtg, CHOSEN), 4),
            "net_rating": round(shrink(t["net_pre"], lm_net, CHOSEN), 4),
            "pace": round(shrink(t["pace_pre"], lm_pace, CHOSEN), 4),
            "carry_shrink": CHOSEN,
        }

    pack = {
        "engine_version": "nba-season-engine-v0.1",
        "as_of": "2026-09-01",
        "season": "2025-26",
        "carry_to_season": "2026-27",
        "source": (
            "basketball-reference.com/leagues/NBA_2026_ratings.html + advanced-team pace "
            "(stats.nba.com leaguedashteamstats Advanced timed out in build env; "
            "data.nba.com 2025-26 RS scores unpublished on CDN)"
        ),
        "source_note": (
            "Unadjusted ORtg/DRtg/NRtg from BR Team Ratings; Pace from BR advanced-team. "
            "Same concepts as NBA Stats Advanced. Ch1 shell only — Ch2 player×minutes rebases."
        ),
        "formula": "team_prime = league_mean + TEAM_CARRY_SHRINK * (team_2025_26 - league_mean)",
        "TEAM_CARRY_SHRINK": CHOSEN,
        "paper_sim_s_set": S_SET,
        "paper_sim": paper,
        "league_mean_pre": {
            "ortg": round(lm_ortg, 6),
            "drtg": round(lm_drtg, 6),
            "net_rating": round(lm_net, 8),
            "pace": round(lm_pace, 6),
        },
        "league_mean_post": {
            "ortg": round(sum(x["ortg"] for x in out_teams.values()) / 30, 6),
            "drtg": round(sum(x["drtg"] for x in out_teams.values()) / 30, 6),
            "net_rating": round(sum(x["net_rating"] for x in out_teams.values()) / 30, 8),
            "pace": round(sum(x["pace"] for x in out_teams.values()) / 30, 6),
        },
        "team_count": 30,
        "teams": out_teams,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(pack, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT} s={CHOSEN} teams={len(out_teams)}")


if __name__ == "__main__":
    main()
