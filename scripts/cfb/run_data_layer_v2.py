#!/usr/bin/env python3
"""CFB Data Layer v2 + frozen HIGH_ENV sufficiency. No production writes."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src.services.cfb_warehouse.data_layer_v2 import (  # noqa: E402
    run_data_layer_v2,
)

OUT_JSON = ROOT / "data/ops/cfb-data-layer-v2-20260912.json"
OUT_MD = ROOT / "data/ops/cfb-data-layer-v2-20260912.md"


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


def _named(card: dict, fid: str) -> dict:
    if fid == "rank_avg_v2_env":
        return card.get("composite") or {}
    for feat in card.get("features") or []:
        if feat.get("id") == fid:
            return feat
    return {}


def _top_rows(card: dict, *, n: int = 16, roles=None, min_coverage: float = 0.05) -> list:
    feats = list(card.get("features") or [])
    if card.get("composite"):
        feats = feats + [card["composite"]]
    if roles is not None:
        feats = [f for f in feats if f.get("role") in roles]
    feats = [
        f
        for f in feats
        if f.get("auc") is not None and float(f.get("coverage") or 0.0) >= min_coverage
    ]
    feats.sort(key=lambda f: float(f["auc"]), reverse=True)
    return feats[:n]


def write_markdown(payload: dict) -> str:
    gate = payload.get("decision") or {}
    v1 = (payload.get("splits") or {}).get("val_1") or {}
    v0 = (payload.get("splits") or {}).get("val_0") or {}
    t0 = (payload.get("splits") or {}).get("train_0") or {}
    target = payload.get("target") or {}
    leak = payload.get("leakage") or {}
    source = payload.get("source_meta") or {}
    cov = payload.get("coverage_by_season_week") or {}
    lines = [
        "# CFB Data Layer v2 — HIGH_ENV information sufficiency",
        "",
        f"**Generated:** `{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}`",
        f"**Production MATCHUP_RESPONSE:** `{payload.get('matchup_response_frozen')}` (unchanged)",
        f"**Kill switch:** `{payload.get('kill_switch')}`  **#532:** DO NOT MERGE",
        f"**Scoring equation:** frozen  **Lake mounted:** `{payload.get('lake_mounted')}`",
        "",
        "Target locked: "
        f"`{target.get('rule')}` (threshold {target.get('threshold')}). "
        f"Capture target: `{target.get('capture_target')}`.",
        "Frozen splits unchanged: Train-0=2022, Val-0=2023, Val-1=2024 W1–14.",
        "2025 sealed. 2026 not in the loss. Actual totals are the labels. Close is diagnostic.",
        "α / A1 / E3 / C2 were not retuned. No scoring-model fitting. No threshold shopping.",
        "",
        "## Decision",
        "",
        f"**{gate.get('decision')}**",
        "",
        "Ship: **false**. Winner: **none**. PLAY: **false**.",
        "",
        str(gate.get("note") or ""),
        "",
        f"Stable features: `{gate.get('stable_features')}`",
        f"Stable families: `{gate.get('stable_families')}`",
        f"New PBP families that cleared: `{gate.get('pbp_stable_features')}`",
        "",
        "## What was asked",
        "",
        "Not another coefficient. Not a 40–60% capture hunt.",
        "",
        "Build a point-in-time-safe feature layer that can represent scoring "
        "environment, then rerun the frozen HIGH_ENV ≥68 protocol on Train-0 / "
        "Val-0 / Val-1. Let the data say how predictable this tail is.",
        "",
        f"Val-1: {v1.get('high_env_n')} / {v1.get('n')} = {_pct(v1.get('prevalence'))}. "
        f"Those games averaged {_fmt(v1.get('mean_actual_total_high'))}. "
        f"The rest averaged {_fmt(v1.get('mean_actual_total_other'))}.",
        "",
        "Stability gate (predeclared, not shopped): AUC ≥ 0.55 **and** "
        "top-decile HIGH_ENV rate > prevalence on **all three** windows.",
        "",
        "## Source inventory",
        "",
        "Raw SportsDataverse PBP on `/Volumes/KosEdgeData/raw/cfb/pbp/` for "
        "2021–2024 only. 2021 is prior-year for Train-0. The 2025 parquet is "
        "on disk and was not opened.",
        "",
        "| season | plays | team-games | EPA_explosive hits | havoc hits | TFL hits | sack hits | drive.result hits | missing requested cols |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for season in ("2021", "2022", "2023", "2024"):
        meta = source.get(season) or {}
        hits = meta.get("col_hits") or {}
        missing = meta.get("cols_requested_missing") or []
        lines.append(
            f"| {season} | {meta.get('rows')} | {meta.get('n_team_games')} | "
            f"{hits.get('EPA_explosive')} | {hits.get('havoc')} | {hits.get('TFL')} | "
            f"{hits.get('sack')} | {hits.get('drive.result')} | "
            f"{missing if missing else 'none'} |"
        )
    lines += [
        "",
        "Explosive definition: raw `EPA_explosive` boolean. No `epa>=1.0` / "
        "`yards>=15` fallback. Finishing: `drive.result` decode TD=6 / FG=3 "
        "because `drive.pts` is absent. Seconds/play uses half-clock "
        "`start/end.TimeSecsRem` with 0 < dt ≤ 45.",
        "",
        "PIT: current `as_of_week W` uses only same-season `week < W`. "
        f"Prior season always Y−1 = `{leak.get('prior_season_always_ym1')}`. "
        f"Opened 2025 = `{leak.get('opened_2025')}`. "
        f"Close in v2 features = `{leak.get('close_in_v2_features')}`. "
        f"Missing means missing = `{leak.get('missing_means_missing')}`.",
        "",
        "## Source gaps (not invented)",
        "",
    ]
    for row in payload.get("source_gaps") or []:
        lines.append(f"- **{row.get('id')}:** {row.get('why')}")

    lines += [
        "",
        "## Coverage by week (eligible lake games)",
        "",
        "Current-season PBP features need ≥2 completed same-season games. "
        "Week 1 is structurally missing. Week 2 is thin.",
        "",
        "| season-week | n | HIGH_ENV | curr both available | prior both available |",
        "|---|---:|---:|---:|---:|",
    ]
    for key in sorted(cov):
        block = cov[key]
        n = block.get("n") or 0
        lines.append(
            f"| {key} | {n} | {block.get('high_env_n')} | "
            f"{block.get('curr_both')} ({_pct((block.get('curr_both') or 0) / n if n else None)}) | "
            f"{block.get('prior_both')} ({_pct((block.get('prior_both') or 0) / n if n else None)}) |"
        )

    lines += [
        "",
        f"Val-1 current-both available: {_pct(v1.get('curr_both_available_rate'))} "
        f"({v1.get('curr_both_available_n')} / {v1.get('n')}). "
        f"Prior-both: {_pct(v1.get('prior_both_available_rate'))}.",
        "",
        "## Val-1 discrimination",
        "",
        "### v2 families",
        "",
        "| feature | family | AUC | PR-AUC | top-decile rate | lift | capture | coverage |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for feat in _top_rows(v1, n=24, roles={"v2"}):
        lines.append(
            f"| {feat.get('id')} | {feat.get('family')} | {_fmt(feat.get('auc'))} | "
            f"{_fmt(feat.get('pr_auc'))} | {_pct(feat.get('top_decile_rate'))} | "
            f"{_fmt(feat.get('top_decile_lift'))} | {_pct(feat.get('top_decile_capture'))} | "
            f"{_pct(feat.get('coverage'))} |"
        )
    lines += [
        "",
        "### Diagnostic / v1 reference / source gap",
        "",
        "| feature | role | AUC | lift | capture | coverage |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for feat in _top_rows(v1, n=12, roles={"diagnostic", "v1_reference", "source_gap"}):
        lines.append(
            f"| {feat.get('id')} | {feat.get('role')} | {_fmt(feat.get('auc'))} | "
            f"{_fmt(feat.get('top_decile_lift'))} | {_pct(feat.get('top_decile_capture'))} | "
            f"{_pct(feat.get('coverage'))} |"
        )

    week4 = v1.get("week_ge4") or {}
    lines += [
        "",
        f"### Val-1 week ≥ 4 (current-season families only; n={week4.get('n')}, "
        f"HIGH_ENV={week4.get('high_env_n')})",
        "",
        "| feature | AUC | lift | capture | coverage |",
        "|---|---:|---:|---:|---:|",
    ]
    w4_card = {
        "features": week4.get("features") or [],
        "composite": week4.get("composite") or {},
    }
    for feat in _top_rows(w4_card, n=16, roles={"v2"}):
        lines.append(
            f"| {feat.get('id')} | {_fmt(feat.get('auc'))} | "
            f"{_fmt(feat.get('top_decile_lift'))} | "
            f"{_pct(feat.get('top_decile_capture'))} | {_pct(feat.get('coverage'))} |"
        )

    focus = [
        "curr_sum_off_epa",
        "curr_sum_def_epa",
        "curr_sum_explosive_allowed",
        "curr_sum_pace_plays",
        "curr_mean_sec_per_play",
        "curr_sum_finish",
        "curr_sum_ppp",
        "curr_sum_havoc_created",
        "curr_sum_success_allowed",
        "curr_mean_game_total",
        "prior_mean_game_total",
        "prior_sum_def_epa",
        "rank_avg_v2_env",
        "v1_sum_off_eff",
        "v1_e3_proxy",
        "close_total",
        "layer_b_returning",
    ]
    lines += [
        "",
        "## Stability across splits",
        "",
        "| feature | Train-0 AUC / lift / cov | Val-0 AUC / lift / cov | Val-1 AUC / lift / capture |",
        "|---|---|---|---|",
    ]
    for fid in focus:
        a = _named(t0, fid)
        b = _named(v0, fid)
        c = _named(v1, fid)
        lines.append(
            f"| {fid} | {_fmt(a.get('auc'))} / {_fmt(a.get('top_decile_lift'))} / "
            f"{_pct(a.get('coverage'))} | {_fmt(b.get('auc'))} / "
            f"{_fmt(b.get('top_decile_lift'))} / {_pct(b.get('coverage'))} | "
            f"{_fmt(c.get('auc'))} / {_fmt(c.get('top_decile_lift'))} / "
            f"{_pct(c.get('top_decile_capture'))} |"
        )

    table = gate.get("stability_table") or {}
    cleared = [fid for fid, row in table.items() if row.get("stable")]
    lines += [
        "",
        f"Predeclared gate cleared by: `{cleared}`.",
        "",
        "## Rank-average composite (predeclared, not fitted)",
        "",
        "Equal-weight average of within-split percentile ranks of "
        + ", ".join(f"`{m}`" for m in (payload.get("composite_members") or []))
        + ". Needs ≥2 present members. Not a fit. No capture target.",
        "",
    ]
    comp = v1.get("composite") or {}
    lines += [
        f"Val-1 AUC `{_fmt(comp.get('auc'))}`  top-decile rate `{_pct(comp.get('top_decile_rate'))}`  "
        f"lift `{_fmt(comp.get('top_decile_lift'))}`  capture `{_pct(comp.get('top_decile_capture'))}`  "
        f"coverage `{_pct(comp.get('coverage'))}`",
        "",
        "| decile (1=lowest) | n | HIGH_ENV n | rate | lift |",
        "|---:|---:|---:|---:|---:|",
    ]
    for row in ((comp.get("deciles") or {}).get("bins") or []):
        lines.append(
            f"| {row.get('decile')} | {row.get('n')} | {row.get('high_env_n')} | "
            f"{_pct(row.get('high_env_rate'))} | {_fmt(row.get('lift_vs_prevalence'))} |"
        )

    sec = _named(v1, "curr_mean_sec_per_play")
    off = _named(v1, "curr_sum_off_epa")
    layer_b = _named(v1, "layer_b_returning")
    lines += [
        "",
        "## Reading",
        "",
        "The predeclared three-window gate fired. New PBP families cleared, "
        "not only the already-known schedule environment columns. The scoring "
        "equation stayed frozen. The 40–60% capture number from the v1 fork "
        "was not a target.",
        "",
        f"The composite ranks HIGH_ENV at AUC `{_fmt(_named(t0, 'rank_avg_v2_env').get('auc'))}` / "
        f"`{_fmt(_named(v0, 'rank_avg_v2_env').get('auc'))}` / "
        f"`{_fmt(comp.get('auc'))}` — matching the close "
        f"(`{_fmt(_named(t0, 'close_total').get('auc'))}` / "
        f"`{_fmt(_named(v0, 'close_total').get('auc'))}` / "
        f"`{_fmt(_named(v1, 'close_total').get('auc'))}`) without using it. "
        f"Val-1 top-decile capture is still `{_pct(comp.get('top_decile_capture'))}` "
        f"of the {v1.get('high_env_n')} shootouts. The tail is rankable. "
        "It is not isolatable. No 40% pocket appeared.",
        "",
        "What is stable across Train-0 / Val-0 / Val-1:",
        "",
        "- Defensive EPA allowed (current and prior-year).",
        "- Explosive-play rate allowed (current and prior-year), from the raw `EPA_explosive` flag.",
        "- True pace as plays/game (current and prior-year).",
        "- Team scoring-environment history (current week < W, and prior-year).",
        "",
        "What is not:",
        "",
        f"- Offense still dies out of sample. `curr_sum_off_epa` Val-1 AUC is "
        f"`{_fmt(off.get('auc'))}` — the same diagnosis as v1 `sum_off_eff`. "
        "Finishing created / PPP created fail Val-1 with them.",
        "- Havoc / TFL / sack do not clear all three windows.",
        f"- Layer B remains a source gap (coverage `{_pct(layer_b.get('coverage'))}`). "
        "Missing, not filled with 50.",
        f"- `curr_mean_sec_per_play` is a coverage mirage "
        f"(`{_pct(sec.get('coverage'))}` present). The clock columns exist; "
        "usable 0 < dt ≤ 45 play durations almost never survive. Not a signal.",
        "",
        "Architecture v2 may now be designed from the stable families. "
        "This pass does not design it, does not pick a winner, and does not "
        "write a coefficient.",
        "",
        "## What this is not",
        "",
        "- Not a production change.",
        "- Not a new MATCHUP_RESPONSE, α, A1, E3, or C2.",
        "- Not permission to open 2025 or turn the board on.",
        "- Not a market-fitted totals model.",
        "- Not a feature search after seeing Val-1. The list was predeclared.",
        "- Not a 40–60% capture optimization.",
        "- Not scoring architecture v2. That is the next design step, not this merge.",
        "",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    payload = run_data_layer_v2(lake_only=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    OUT_MD.write_text(write_markdown(payload), encoding="utf-8")
    print(f"wrote {OUT_JSON}")
    print(f"wrote {OUT_MD}")
    print("decision", (payload.get("decision") or {}).get("decision"))
    print("stable", (payload.get("decision") or {}).get("stable_features"))
    print("MATCHUP_RESPONSE still", payload.get("matchup_response_frozen"))
    print("opened_2025", payload.get("opened_2025"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
