#!/usr/bin/env python3
"""CFBD coverage audit. No bulk ingest. No production writes."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src.services.cfb_warehouse.cfbd_ingest import (  # noqa: E402
    RESEARCH_CALL_BUDGET,
    run_cfbd_coverage_audit,
)

OUT_JSON = ROOT / "data/ops/cfb-cfbd-acquisition-20260912.json"
OUT_MD = ROOT / "data/ops/cfb-cfbd-acquisition-20260912.md"


def _fmt(value: object) -> str:
    if value is None:
        return "—"
    return str(value)


def write_markdown(payload: dict) -> str:
    gate = payload.get("decision") or {}
    lines = [
        "# CFBD acquisition / coverage audit — Data Layer v2",
        "",
        f"**Generated:** `{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}`",
        f"**Production MATCHUP_RESPONSE:** `{payload.get('matchup_response_frozen')}` (unchanged)",
        f"**Kill switch:** `{payload.get('kill_switch')}`  **#532:** DO NOT MERGE",
        f"**Key present:** `{payload.get('key_present')}`  "
        f"**Calls used:** `{payload.get('calls_used')}` / `{payload.get('call_budget_max')}`",
        f"**Bulk ingest:** `{payload.get('bulk_ingest')}`  "
        f"**HIGH_ENV rerun:** `{payload.get('high_env_rerun')}`  "
        f"**Opened 2025:** `{payload.get('opened_2025')}`",
        "",
        "## Decision",
        "",
        f"**{gate.get('decision')}**",
        "",
        "Ship: **false**. Winner: **none**. PLAY: **false**.",
        "",
        str(gate.get("note") or ""),
        "",
        "This is an acquisition report. The scoring model was not modified. "
        "No 40–60% capture target. Free-tier budget is 1,000 requests/month; "
        "this audit used a 12-call probe only.",
        "",
        "If every probe is HTTP 401, the secret store was loaded but CFBD "
        "rejected it. Do not rotate or guess the key in this chat. Replace "
        "`CFBD_API_KEY` in gitignored `.env.local` with the exact generated "
        "value, then rerun the audit. Screenshot line-wrapping is enough to "
        "break a key.",
        "",
        "## Feature map",
        "",
        "| v2 need | CFBD source | classification | point-in-time note |",
        "|---|---|---|---|",
    ]
    for row in payload.get("feature_map") or []:
        lines.append(
            f"| {row.get('need')} | `{row.get('endpoint')}` | **{row.get('class')}** | "
            f"{row.get('pit')} |"
        )
    budget = payload.get("research_call_budget") or RESEARCH_CALL_BUDGET
    lines += [
        "",
        "## Request budget (research universe, not this audit)",
        "",
        "Train-0 / Val-0 / Val-1 = 2022–2024 weeks 1–14.",
        "",
        "| work | estimated calls |",
        "|---|---:|",
        f"| rolling `/stats/season/advanced` endWeek=1..14 × 3 seasons | {budget.get('advanced_rolling_w1_14')} |",
        f"| `/games` schedule × 3 seasons | {budget.get('games_schedule')} |",
        f"| `/player/returning` 2021–2024 | {budget.get('returning_2021_2024')} |",
        f"| `/ratings/sp` prior-year benchmark only | {budget.get('sp_plus_prior_year_only')} |",
        f"| **first pass (no PBP, no CORE)** | **{budget.get('first_pass_no_pbp_no_core')}** |",
        f"| optional CORE throughWeek snapshots | {budget.get('core_optional_research')} |",
        f"| deferred `/plays` one-call-per-week | {budget.get('plays_deferred')} |",
        f"| free-tier monthly ceiling | {budget.get('monthly_free_tier')} |",
        "",
        "First-pass ingest fits in ~52 calls. Do not pull PBP until rolling "
        "advanced stats are frozen and reviewed. Owned SportsDataverse PBP "
        "already covers 2021–2024 on the HD lake for custom explosive-rate work.",
        "",
        "## Probe results",
        "",
        "| id | endpoint | status | rows | bytes | error |",
        "|---|---|---:|---:|---:|---|",
    ]
    for row in payload.get("probes") or []:
        lines.append(
            f"| {row.get('id')} | `{row.get('path')}` | {_fmt(row.get('status'))} | "
            f"{_fmt(row.get('n_rows'))} | {_fmt(row.get('bytes'))} | {_fmt(row.get('error'))} |"
        )
    lines += [
        "",
        "## Ingestion architecture (proposed, not executed at scale)",
        "",
        "```",
        "CFBD_API_KEY (server env)",
        "  → GET /stats/season/advanced?year=Y&endWeek=W-1",
        "  → immutable raw lake  raw/cfbd/stats_season_advanced/year=Y/",
        "  → normalized team-week  clean/cfbd/team_week/team_week_Y_through_WW.json",
        "  → HIGH_ENV join later (not this commit)",
        "```",
        "",
        "Every team-week row carries `season`, `through_week`, `team`, `source`, "
        "`source_version`, `is_point_in_time_safe`. Week 1 current-season values "
        "are missing. Never 50-fill.",
        "",
        "SP+ is an external benchmark and only legal as a **prior-year** feature. "
        "CORE is research-only until a live-archive vs retrospective test exists. "
        "`/lines` is diagnostic. `/games/weather` is Patreon-only on the public swagger.",
        "",
        "## What this is not",
        "",
        "- Not a production change.",
        "- Not a new MATCHUP_RESPONSE, α, A1, E3, or C2.",
        "- Not a HIGH_ENV rerun.",
        "- Not bulk CFBD ingestion.",
        "- Not permission to open 2025 or turn the board on.",
        "- Not a frontend/browser CFBD integration.",
        "",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    payload = run_cfbd_coverage_audit(max_calls=12, prefer_hd=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    OUT_MD.write_text(write_markdown(payload), encoding="utf-8")
    print(f"wrote {OUT_JSON}")
    print(f"wrote {OUT_MD}")
    print("decision", (payload.get("decision") or {}).get("decision"))
    print("key_present", payload.get("key_present"))
    print("calls_used", payload.get("calls_used"))
    print("opened_2025", payload.get("opened_2025"))
    print("MATCHUP_RESPONSE still", payload.get("matchup_response_frozen"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
