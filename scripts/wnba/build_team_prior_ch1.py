#!/usr/bin/env python3
"""Rebuild WNBA Ch1 team prior pack from 2026 YTD advanced team ratings.

Intended SoT (Ch0 audit): stats.wnba.com leaguedashteamstats Advanced via
wnba_data.py. In this build env stats.wnba.com timed out and data.wnba.com
returned 403. Pack stamped from Basketball-Reference WNBA 2026 advanced-team
(ORtg / DRtg / NRtg / Pace) — same concepts. Re-run when WNBA Stats egress
works and prefer leaguedashteamstats MeasureType=Advanced as SoT.

Midseason shell: ~40 of 44 RS games in. Shrink YTD toward league mean.
2025 belongs on players in Ch2 — not this pack.
Expansion TOR/POR: YTD + shrink only (no invented 2025 row).

Usage:
  python scripts/wnba/build_team_prior_ch1.py
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
    / "services/model-service/src/services/wnba_season_engine/data"
    / "wnba_team_prior_2026.json"
)

# Canonical desk keys — matches wnba_data.WNBA_TEAM_ABBREV / WNBA_TEAM_DIRECTORY.
TEAM_MAP = {
    "Atlanta Dream": "ATL",
    "Chicago Sky": "CHI",
    "Connecticut Sun": "CON",
    "Dallas Wings": "DAL",
    "Golden State Valkyries": "GSV",
    "Indiana Fever": "IND",
    "Las Vegas Aces": "LAS",
    "Los Angeles Sparks": "LA",
    "Minnesota Lynx": "MIN",
    "New York Liberty": "NY",
    "Phoenix Mercury": "PHX",
    "Portland Fire": "POR",
    "Seattle Storm": "SEA",
    "Toronto Tempo": "TOR",
    "Washington Mystics": "WSH",
}

EXPECTED_TEAMS = 15
S_SET = [0.70, 0.80, 0.85, 0.90]
CHOSEN = 0.85  # WNBA_TEAM_CARRY_SHRINK — own constant; not NBA TEAM_CARRY_SHRINK
UA = {"User-Agent": "Mozilla/5.0 (compatible; KosEdgeWnbaCh1/1.0)"}


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
    html = _get("https://www.basketball-reference.com/wnba/years/2026.html")
    table = re.search(
        r'<table[^>]*id="advanced-team"[^>]*>.*?</table>', html, flags=re.S | re.I
    )
    if not table:
        raise SystemExit("advanced-team table missing")

    teams: dict[str, dict] = {}
    for row in re.findall(r"<tr[^>]*>.*?</tr>", table.group(0), flags=re.S | re.I):
        texts = _cells(row)
        name = None
        for t in texts:
            key = t.rstrip("*")
            if key in TEAM_MAP:
                name = key
                break
        if not name:
            continue
        i = next(idx for idx, t in enumerate(texts) if t.rstrip("*") == name)
        # Rk, Team, Age, W, L, PW, PL, MOV, SOS, SRS, ORtg, DRtg, NRtg, Pace
        code = TEAM_MAP[name]
        w, l = int(texts[i + 2]), int(texts[i + 3])
        teams[code] = {
            "team": code,
            "team_name": name,
            "w": w,
            "l": l,
            "gp": w + l,
            "ortg_pre": float(texts[i + 9]),
            "drtg_pre": float(texts[i + 10]),
            "net_pre": float(texts[i + 11].replace("+", "")),
            "pace_pre": float(texts[i + 12]),
            "expansion_ytd_only": code in {"TOR", "POR"},
        }

    if len(teams) != EXPECTED_TEAMS:
        raise SystemExit(f"expected {EXPECTED_TEAMS} teams; got {len(teams)}")
    missing = set(TEAM_MAP.values()) - set(teams)
    if missing:
        raise SystemExit(f"missing teams: {sorted(missing)}")

    n = float(EXPECTED_TEAMS)

    def mean(key: str) -> float:
        return sum(t[key] for t in teams.values()) / n

    lm_ortg, lm_drtg, lm_net, lm_pace = (
        mean("ortg_pre"),
        mean("drtg_pre"),
        mean("net_pre"),
        mean("pace_pre"),
    )

    # Worst ~1/3 by wins treated as "lottery" for invert gate (5 of 15).
    lottery = {t["team"] for t in sorted(teams.values(), key=lambda t: t["w"])[:5]}
    paper = []
    for s in S_SET:
        ranked_pre = sorted(teams.values(), key=lambda t: -t["net_pre"])
        ranked_post = sorted(
            teams.values(), key=lambda t: -shrink(t["net_pre"], lm_net, s)
        )
        top5_post = [t["team"] for t in ranked_post[:5]]
        nets = [shrink(t["net_pre"], lm_net, s) for t in teams.values()]
        paper.append(
            {
                "s": s,
                "mean_net_post": round(sum(nets) / n, 8),
                "mean_pace_post": round(
                    sum(shrink(t["pace_pre"], lm_pace, s) for t in teams.values()) / n, 6
                ),
                "net_sd_pre": round(
                    (sum((t["net_pre"] - lm_net) ** 2 for t in teams.values()) / n) ** 0.5,
                    4,
                ),
                "net_sd_post": round(
                    (sum((x - sum(nets) / n) ** 2 for x in nets) / n) ** 0.5, 4
                ),
                "top5_pre": [t["team"] for t in ranked_pre[:5]],
                "top5_post": top5_post,
                "bot5_pre": [t["team"] for t in ranked_pre[-5:]],
                "bot5_post": [t["team"] for t in ranked_post[-5:]],
                "lottery_in_top5_post": [c for c in top5_post if c in lottery],
                "min_net_post": round(shrink(teams["MIN"]["net_pre"], lm_net, s), 4),
                "con_net_post": round(shrink(teams["CON"]["net_pre"], lm_net, s), 4),
            }
        )

    out_teams = {}
    for code, t in sorted(teams.items()):
        out_teams[code] = {
            **{
                k: t[k]
                for k in ("team", "team_name", "w", "l", "gp", "expansion_ytd_only")
            },
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

    post_nets = [row["net_rating"] for row in out_teams.values()]
    pack = {
        "engine_version": "wnba-season-engine-v0.1",
        "as_of": "2026-09-01",
        "season": "2026",
        "season_phase": "midseason_ytd",
        "source": (
            "basketball-reference.com/wnba/years/2026.html#advanced-team "
            "(stats.wnba.com leaguedashteamstats Advanced timed out in build env; "
            "data.wnba.com schedule CDN 403 — Ch0 audit failover)"
        ),
        "source_note": (
            "2026 YTD unadjusted ORtg/DRtg/NRtg/Pace from BR advanced-team. "
            "Same concepts as stats.wnba.com Advanced. Why YTD not 2025: ~40/44 "
            "RS games in; 2025 is a different roster (players in Ch2). "
            "Expansion TOR/POR: YTD+shrink only — no invented 2025 row. "
            "Ch1 shell only — does not emit KEI or blend leftover Aug-1 fair-lines."
        ),
        "formula": (
            "team_prime = league_mean + WNBA_TEAM_CARRY_SHRINK * "
            "(team_2026_ytd - league_mean)"
        ),
        "WNBA_TEAM_CARRY_SHRINK": CHOSEN,
        "paper_sim_s_set": S_SET,
        "paper_sim": paper,
        "league_mean_pre": {
            "ortg": round(lm_ortg, 6),
            "drtg": round(lm_drtg, 6),
            "net_rating": round(lm_net, 8),
            "pace": round(lm_pace, 6),
        },
        "league_mean_post": {
            "ortg": round(
                sum(r["ortg"] for r in out_teams.values()) / n, 6
            ),
            "drtg": round(
                sum(r["drtg"] for r in out_teams.values()) / n, 6
            ),
            "net_rating": round(sum(post_nets) / n, 8),
            "pace": round(sum(r["pace"] for r in out_teams.values()) / n, 6),
        },
        "team_count": EXPECTED_TEAMS,
        "teams": out_teams,
        "forbidden_leftover_fair_line_game_ids": ["401857105", "401857106"],
        "does_not": [
            "write KEI onto /edge-board/wnba",
            "blend leftover Aug-1 fair-lines",
            "reuse NBA TEAM_CARRY_SHRINK",
            "NBA home +2.0 / B2B -1.5",
            "player RAPM / minute grid",
            "team if / Finals bump",
        ],
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(pack, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT} teams={EXPECTED_TEAMS} s={CHOSEN}")


if __name__ == "__main__":
    main()
