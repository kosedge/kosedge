#!/usr/bin/env python3
"""Recover 2022 Odds-API/warehouse closes and join to frozen Layer A / game universe.

Does not change v1, starter/talent, coefficients, MATCHUP_RESPONSE, PPG, λ,
Line Curve, Edge Board, or production behavior. Does not score frozen 1.40.
Does not open 2025. Does not live-densify The Odds API.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "services/model-service"))

from src.services.cfb_season_engine.priors import MATCHUP_RESPONSE  # noqa: E402
from src.services.cfb_season_engine.qb_feature_contract import (  # noqa: E402
    QB_FEATURE_CONTRACT_VERSION,
)
from src.services.cfb_warehouse.close_recovery_2022 import (  # noqa: E402
    SEASON,
    TRAIN0_GATE,
    gate_memo,
    join_2022_closes,
    load_2022_game_universe,
    load_2022_lake,
    load_layer_a_2022_codes,
)

OPS_MD = REPO / "data/ops/cfb-2022-close-recovery-20260911.md"
OPS_JSON = REPO / "data/ops/cfb-2022-close-recovery-20260911.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _md_table(rows: List[Dict[str, Any]], keys: List[str]) -> str:
    if not rows:
        return "_none_"
    head = "| " + " | ".join(keys) + " |"
    sep = "| " + " | ".join("---" for _ in keys) + " |"
    lines = [head, sep]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(k, ""))[:48] for k in keys) + " |")
    return "\n".join(lines)


def write_report(payload: Dict[str, Any]) -> None:
    audit = payload["audit"]
    funnel = audit["funnel"]
    loc = payload["lake_locate"]
    memo = payload["gate"]
    lines = [
        "# 2022 Odds-API / warehouse closing-line recovery",
        "",
        f"**Generated:** `{payload['generated_at']}`  ",
        f"**Contract:** `{QB_FEATURE_CONTRACT_VERSION}` (untouched)  ",
        f"**MATCHUP_RESPONSE:** `{MATCHUP_RESPONSE}` frozen; not scored  ",
        "**Scope:** market-data recovery + join audit only. CFB stays dark. No PLAY.",
        "",
        "## Decision",
        "",
        f"**{memo['decision']}** — Train-0 lake close+actual n=`{memo['train0_n_lake']}` "
        f"(lake-or-SDV-fill n=`{memo['train0_n_lake_or_fill']}`) vs gate `{TRAIN0_GATE}`.",
        "",
        f"Lake mounted this run: `{memo['lake_mounted']}`. Chosen source: `{loc.get('chosen')}`.",
        "",
        "Frozen 1.40 was **not** scored. Recalibration is **not** authorized.",
        "2025 remains sealed. 2026 remains outside the loss.",
        "",
        "## Funnel (2022)",
        "",
        "raw events → valid pregame closes → identity-matched → FBS/FBS → actual available → close+actual eval",
        "",
        f"| Step | n |",
        f"| --- | ---: |",
        f"| raw lake events (date, home, away) | {funnel['raw_events']} |",
        f"| raw lake snaps | {funnel['raw_snaps']} |",
        f"| valid pregame lake closes | {funnel['valid_pregame_closes']} |",
        f"| identity-matched | {funnel['identity_matched']} |",
        f"| FBS/FBS | {funnel['fbs_fbs']} |",
        f"| actual available | {funnel['actual_available']} |",
        f"| close+actual eval (all weeks, Layer A both) | {funnel['close_actual_eval_universe_all_weeks']} |",
        f"| **Train-0 W1–14 close+actual (lake)** | **{funnel['train0_close_actual_lake']}** |",
        f"| Train-0 W1–14 close+actual (lake or SDV fill) | {funnel['train0_close_actual_lake_or_sdv_fill']} |",
        "",
        "SDV fill (not the Odds-API lake) — shown so the hole is exact, not vibes:",
        "",
        json.dumps(audit.get("sdv_fill_breakdown") or {}, indent=2),
        "",
        f"Deficit vs gate: lake `{TRAIN0_GATE - funnel['train0_close_actual_lake']}` "
        f"(need {TRAIN0_GATE}, have {funnel['train0_close_actual_lake']}).",
        "",
        "Spread / total independently:",
        "",
        f"| | n |",
        f"| --- | ---: |",
        f"| joined spread available | {audit['availability']['spread_available_joined']} |",
        f"| joined total available | {audit['availability']['total_available_joined']} |",
        f"| Train-0 lake spread | {audit['availability']['train0_spread_lake']} |",
        f"| Train-0 lake total | {audit['availability']['train0_total_lake']} |",
        f"| Train-0 fill spread | {audit['availability']['train0_spread_fill']} |",
        f"| Train-0 fill total | {audit['availability']['train0_total_fill']} |",
        "",
        "## Provenance",
        "",
        "Authoritative artifact (when mounted): `/Volumes/KosEdgeData/clean/odds/cfb/snapshots-2022.parquet`",
        "exported 2026-08-13 from `odds_snapshots` (`the-odds-api-historical-enterprise`).",
        "Documented counts: 28,322 snaps / 838 close spreads / 717 lake-primary / 900 warehouse games.",
        "",
        "Close selection: last snap with `captured_at` **strictly before kickoff**; DraftKings then FanDuel.",
        "Open = first legal snap. Intermediate = legal snaps between open and close.",
        "Same timestamp as kickoff is illegal. Post-kick snaps are dropped.",
        "Identity: `cfb_warehouse.identity.resolve_team_code`. Join key `(game_date, home_name, away_name)`.",
        "Conflicts (multi-game, dual ±1-day, flipped orientation) are reason-coded and excluded — no silent pick.",
        "Raw source values are stored beside normalized engine codes / closes.",
        "",
        "Sources tried:",
        "",
    ]
    for row in loc.get("tried") or []:
        lines.append(
            f"- `{row.get('id')}` present=`{row.get('present')}` "
            f"{row.get('path') or row.get('reason') or row.get('provenance') or ''}"
        )
    lines += [
        "",
        "## Duplicates / conflicts",
        "",
        json.dumps(audit["duplicates"], indent=2),
        "",
        "## Unmatched reason codes (games without a valid pregame lake close)",
        "",
        json.dumps(audit["unmatched_game_reason_counts"], indent=2),
        "",
        f"Unmatched lake events (lake side, no warehouse game): `{audit['unmatched_lake_events']}`",
        "",
        "## FBS / FCS exclusions",
        "",
        json.dumps(audit["fcs_exclusions"], indent=2),
        "",
        "## Leakage / contract tests",
        "",
        f"- rule: `{audit['leakage']['rule']}`",
        f"- failures: `{audit['leakage']['n_failures']}`",
        f"- ok: `{audit['leakage']['ok']}`",
        f"- MATCHUP_RESPONSE still `{MATCHUP_RESPONSE}`",
        f"- qb contract still `{QB_FEATURE_CONTRACT_VERSION}`",
        f"- opened_2025: `{payload['opened_2025']}`",
        "",
        "## Source / date coverage",
        "",
        json.dumps(audit["coverage"], indent=2),
        "",
        "## Representative joined rows",
        "",
        _md_table(
            audit.get("representative_rows") or [],
            [
                "game_id",
                "week",
                "home_team_id",
                "away_team_id",
                "close_spread_home",
                "close_total",
                "close_source",
                "train0_lake",
            ],
        ),
        "",
        "## Methodology if n<700",
        "",
        json.dumps(memo.get("methodology"), indent=2),
        "",
        "## GO / STOP",
        "",
        f"**{memo['decision']}**",
        "",
        "Do not score frozen 1.40 in this assignment. Do not recalibrate.",
        "CFB remains dark.",
        "",
    ]
    OPS_MD.parent.mkdir(parents=True, exist_ok=True)
    OPS_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    if MATCHUP_RESPONSE != 1.40:
        raise SystemExit(f"MATCHUP_RESPONSE drifted: {MATCHUP_RESPONSE}")
    if QB_FEATURE_CONTRACT_VERSION != "cfb-qb-feature-v1":
        raise SystemExit("qb feature contract drifted")

    lake_snaps, loc = load_2022_lake()
    layer_codes, layer_meta = load_layer_a_2022_codes()
    games, sdv_closes, game_meta = load_2022_game_universe()
    audit = join_2022_closes(
        games, sdv_closes, lake_snaps, layer_a_codes=layer_codes
    )
    joined = audit.pop("joined")
    memo = gate_memo(audit, loc)
    payload = {
        "generated_at": _utc(),
        "season": SEASON,
        "qb_feature_contract_version": QB_FEATURE_CONTRACT_VERSION,
        "matchup_response_frozen": MATCHUP_RESPONSE,
        "kill_switch": True,
        "opened_2025": False,
        "used_2026_for_reconstruction": False,
        "scored_frozen_140": False,
        "recalibrated": False,
        "play": False,
        "lake_locate": loc,
        "layer_a": layer_meta,
        "game_universe": game_meta,
        "audit": audit,
        "gate": memo,
        "n_joined_rows_omitted_from_json": len(joined),
    }
    write_report(payload)
    OPS_JSON.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps({"ops_md": str(OPS_MD), "ops_json": str(OPS_JSON), "gate": memo}, indent=2))
    return 0 if memo["decision"].startswith("GO") or memo["decision"] == "STOP" else 1


if __name__ == "__main__":
    raise SystemExit(main())
