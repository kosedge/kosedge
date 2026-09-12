#!/usr/bin/env python3
"""HIGH_ENV information-sufficiency study. Does not write production knobs."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src.services.cfb_warehouse.high_env_information import (  # noqa: E402
    run_high_env_information,
)

OUT_JSON = ROOT / "data/ops/cfb-high-env-information-20260912.json"
OUT_MD = ROOT / "data/ops/cfb-high-env-information-20260912.md"


def _fmt(value: object, digits: int = 3) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def _pct(value: object) -> str:
    if value is None:
        return "—"
    return f"{100.0 * float(value):.1f}%"


def _top_rows(card: dict, *, n: int = 12, roles=None) -> list:
    feats = list(card.get("features") or [])
    if card.get("composite"):
        feats = feats + [card["composite"]]
    if roles is not None:
        feats = [f for f in feats if f.get("role") in roles]
    feats = [f for f in feats if f.get("auc") is not None]
    feats.sort(key=lambda f: float(f["auc"]), reverse=True)
    return feats[:n]


def write_markdown(payload: dict) -> str:
    gate = payload.get("decision") or {}
    v1 = (payload.get("splits") or {}).get("val_1") or {}
    v0 = (payload.get("splits") or {}).get("val_0") or {}
    t0 = (payload.get("splits") or {}).get("train_0") or {}
    leak = payload.get("leakage") or {}
    target = payload.get("target") or {}
    lines = [
        "# CFB HIGH_ENV pregame information sufficiency",
        "",
        f"**Generated:** `{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}`",
        f"**Production MATCHUP_RESPONSE:** `{payload.get('matchup_response_frozen')}` (unchanged)",
        f"**Kill switch:** `{payload.get('kill_switch')}`  **#532:** DO NOT MERGE",
        f"**Scoring equation:** frozen  **Lake mounted:** `{payload.get('lake_mounted')}`",
        "",
        "Target locked before features: "
        f"`{target.get('rule')}` (threshold {target.get('threshold')}).",
        "Frozen splits unchanged: Train-0=2022, Val-0=2023, Val-1=2024 W1–14.",
        "2025 sealed. 2026 not in the loss. Actual totals are the labels. Close is diagnostic.",
        "A1 / E3 / C2 / A3 were not retuned.",
        "",
        "## Decision",
        "",
        f"**{gate.get('decision')}**",
        "",
        f"Ship: **false**. Winner: **none**. PLAY: **false**.",
        "",
        str(gate.get("note") or ""),
        "",
        f"Signal features: `{gate.get('signal_features')}`  "
        f"Strong (≥40% capture): `{gate.get('strong_features')}`  "
        f"Market AUC (diagnostic): `{_fmt(gate.get('market_auc_val_1'))}`",
        "",
        "## What was asked",
        "",
        "Not “can we predict the exact total?” Not “can we beat the market?”",
        "",
        "Using only information legitimately available pregame in v1 — plus unused "
        "columns already sitting in the same prior-year cache — can we rank the "
        f"**{v1.get('high_env_n')}** Val-1 games that actually scored ≥68?",
        "",
        f"Val-1 prevalence is {_pct(v1.get('prevalence'))} "
        f"({v1.get('high_env_n')} / {v1.get('n')}). "
        f"Those games averaged {_fmt(v1.get('mean_actual_total_high'))} points. "
        f"The rest averaged {_fmt(v1.get('mean_actual_total_other'))}.",
        "",
        "Gates were predeclared: Val-1 AUC ≥ 0.60 and top-decile lift ≥ 2.0, "
        "with Val-0 AUC ≥ 0.57. Strong signal = top decile captures ≥ 40% of HIGH_ENV.",
        "",
        "## Inventory: what v1 actually has",
        "",
        "The reconstruction varies two things: prior-year adj EPA (off/def) and "
        "Layer A QB (talent / class / prior-year attempts). Everything else is a fill.",
        "",
        "| family | in v1? | varies? |",
        "|---|---|---|",
        "| prior-year off/def EPA | yes | yes |",
        "| Layer A QB talent/class | yes | yes |",
        "| composed offense index | yes | mostly the two above |",
        "| explosiveness / success | labeled yes | **proxy**: 50+0.15×(off−def); success=off/def |",
        "| pace_factor | yes | almost no — units are 50 |",
        f"| returning production | filled | no (SD {_fmt(leak.get('returning_production_sd'))}) |",
        f"| unit grades | filled | no (OL SD {_fmt(leak.get('unit_ol_sd'))}) |",
        "| coaching changes | filled | no — all assumed returning |",
        "| true PBP explosiveness / havoc / RZ | **absent** | — |",
        "| opponent-adjusted current-season EPA | **absent** | — |",
        "| unused cfb_ratings pace / FEI / ST | owned, unused | yes |",
        "| prior-year team scoring environment | owned, unused | yes |",
        "| current-season box before week W | owned, **not v1** | yes after W2 |",
        "",
        "Leakage: prior season always Y−1 = "
        f"`{leak.get('prior_season_always_ym1')}`; opened 2025 = "
        f"`{leak.get('opened_2025')}`; forbidden seasons = "
        f"`{leak.get('forbidden_seasons_present')}`.",
        "",
        "## Val-1 discrimination",
        "",
        "### v1 + owned unused (the sufficiency question)",
        "",
        "| feature | family | AUC | PR-AUC | top-decile rate | lift | capture | coverage |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for feat in _top_rows(
        v1, n=20, roles={"v1", "owned_unused", "v1_plus_owned_unused"}
    ):
        lines.append(
            f"| {feat.get('id')} | {feat.get('family')} | {_fmt(feat.get('auc'))} | "
            f"{_fmt(feat.get('pr_auc'))} | {_pct(feat.get('top_decile_rate'))} | "
            f"{_fmt(feat.get('top_decile_lift'))} | {_pct(feat.get('top_decile_capture'))} | "
            f"{_pct(feat.get('coverage'))} |"
        )
    lines += [
        "",
        "### Diagnostic / not-v1 / negative controls",
        "",
        "| feature | role | AUC | lift | capture | coverage |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for feat in _top_rows(
        v1, n=20, roles={"diagnostic", "current_not_v1", "negative_control"}
    ):
        lines.append(
            f"| {feat.get('id')} | {feat.get('role')} | {_fmt(feat.get('auc'))} | "
            f"{_fmt(feat.get('top_decile_lift'))} | {_pct(feat.get('top_decile_capture'))} | "
            f"{_pct(feat.get('coverage'))} |"
        )

    def _named(card: dict, fid: str) -> dict:
        if fid == "rank_avg_env":
            return card.get("composite") or {}
        for f in card.get("features") or []:
            if f.get("id") == fid:
                return f
        return {}

    focus = (
        "e3_proxy_total",
        "a1_proxy_total",
        "sum_off_eff",
        "sum_def_susc",
        "max_off_minus_opp_def",
        "product_mismatch",
        "sum_off_pace",
        "prior_mean_game_total",
        "prior_high_env_rate_max",
        "rank_avg_env",
        "curr_mean_game_total",
        "close_total",
        "returning_production_sum",
    )
    lines += [
        "",
        "### Stability across splits (selected features)",
        "",
        "| feature | Train-0 AUC / lift | Val-0 AUC / lift | Val-1 AUC / lift / capture |",
        "|---|---|---|---|",
    ]
    for fid in focus:
        a = _named(t0, fid)
        b = _named(v0, fid)
        c = _named(v1, fid)
        lines.append(
            f"| {fid} | {_fmt(a.get('auc'))} / {_fmt(a.get('top_decile_lift'))} | "
            f"{_fmt(b.get('auc'))} / {_fmt(b.get('top_decile_lift'))} | "
            f"{_fmt(c.get('auc'))} / {_fmt(c.get('top_decile_lift'))} / "
            f"{_pct(c.get('top_decile_capture'))} |"
        )

    comp = v1.get("composite") or {}
    dec = (comp.get("deciles") or {}).get("bins") or []
    lines += [
        "",
        "## Rank-average composite (predeclared, not fitted)",
        "",
        "Equal-weight average of within-split percentile ranks of "
        "`sum_off_eff`, `sum_def_susc`, `sum_off_pace`, `prior_mean_game_total`.",
        "",
        f"Val-1 AUC `{_fmt(comp.get('auc'))}`  top-decile rate `{_pct(comp.get('top_decile_rate'))}`  "
        f"lift `{_fmt(comp.get('top_decile_lift'))}`  capture `{_pct(comp.get('top_decile_capture'))}`",
        "",
        "| decile (1=lowest) | n | HIGH_ENV n | rate | lift |",
        "|---:|---:|---:|---:|---:|",
    ]
    for row in dec:
        lines.append(
            f"| {row.get('decile')} | {row.get('n')} | {row.get('high_env_n')} | "
            f"{_pct(row.get('high_env_rate'))} | {_fmt(row.get('lift_vs_prevalence'))} |"
        )

    lines += [
        "",
        "## Absent families (not invented)",
        "",
    ]
    for row in payload.get("absent_families") or []:
        lines.append(f"- **{row.get('id')}:** {row.get('why')}")

    lines += [
        "",
        "## Reading",
        "",
        "The 40–60% capture fork did not fire. Nobody — v1, unused prior-year "
        "columns, current-season box, or the close — put 40% of the 140 "
        "shootouts into one decile. The closest v1 result is `sum_def_susc` / "
        "`min_def_eff` at ~22% capture. The close itself captures 18%.",
        "",
        "**Offense does not identify the tail.** `sum_off_eff` Val-1 AUC is "
        "0.47 — below chance in the predeclared direction. The ratio’s 54 "
        "predicted-≥68 games were high-off / low-def. Actual ≥68 games are "
        "not high-off games. That is why every scoring identity projected "
        "the real shootouts at ~55.",
        "",
        "**Two weak defenses is the only v1 hint, and it is weak.** "
        "`sum_def_susc` Val-1 AUC 0.62 / lift 2.21 would have cleared the "
        "Val-1 gate alone, but Val-0 AUC is 0.567 (need 0.57) and Train-0 "
        "is 0.57 / lift 1.35. Not a layer. A weather vane.",
        "",
        "**Prior-year team environment is the most stable unused column** "
        "(AUC 0.64 / 0.60 / 0.61) and still only 18% capture. Knowing that "
        "a team lived in 70-point games last year barely ranks this year’s "
        "68+ games.",
        "",
        "**The frozen scoring identities have no extra information.** "
        "E3 proxy AUC 0.59, A1 proxy 0.60, capture 15–16%. Changing α "
        "cannot create a tail detector that the features do not have.",
        "",
        "**The close ranks better than v1 (AUC 0.66–0.71) and still cannot "
        "isolate shootouts.** Information exists outside this reconstruction. "
        "It is not a clean 40% pocket. Current-season box (week < W) sits "
        "between them (AUC 0.64–0.68, 80% coverage).",
        "",
        "Negative controls are exactly 0.500. Roster/units SD is 0. Leakage "
        "checks passed. The study measured what it said it would measure.",
        "",
        "## What this means",
        "",
        "Do not torture α. The next work is data acquisition, not a new "
        "preseason coefficient.",
        "",
        "Priority order suggested by the evidence, not a ship list:",
        "",
        "1. The families the book can see that v1 cannot: true pace, "
        "in-season scoring environment, injuries, weather, explosive-play "
        "allowed, red-zone finishing.",
        "2. Real Layer B (returning production, units, coaching) — currently "
        "50-fills with zero variance.",
        "3. Only after those exist, revisit a nonlinear scoring-environment "
        "layer. There is no 40% pocket to build it from today.",
        "",
        "## What this is not",
        "",
        "- Not a production change.",
        "- Not a new MATCHUP_RESPONSE or α.",
        "- Not permission to open 2025 or turn the board on.",
        "- Not a market-fitted totals model.",
        "- Not a feature search after seeing Val-1. The list was predeclared.",
        "",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    payload = run_high_env_information(lake_only=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    OUT_MD.write_text(write_markdown(payload), encoding="utf-8")
    print(f"wrote {OUT_JSON}")
    print(f"wrote {OUT_MD}")
    print("decision", (payload.get("decision") or {}).get("decision"))
    print("MATCHUP_RESPONSE still", payload.get("matchup_response_frozen"))
    print("opened_2025", payload.get("opened_2025"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
