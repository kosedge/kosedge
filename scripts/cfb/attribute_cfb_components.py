#!/usr/bin/env python3
"""CFB totals component attribution on the legal 2022–24 v1 universe.

Does not change production constants.
Does not sweep MATCHUP_RESPONSE below 0.70.
Does not unseal 2025. Does not use 2026. Does not publish PLAY.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "services/model-service"))

from src.services.cfb_season_engine.priors import (  # noqa: E402
    LEAGUE_TEAM_PPG,
    MATCHUP_RESPONSE,
)
from src.services.cfb_season_engine.qb_feature_contract import (  # noqa: E402
    QB_FEATURE_CONTRACT_VERSION,
)
from src.services.cfb_warehouse.component_attribution import (  # noqa: E402
    AUTHORIZED_FLOOR,
    FAMILIES,
    run_component_attribution,
    totals_equation_doc,
)

OPS_MD = REPO / "data/ops/cfb-component-attribution-20260912.md"
OPS_JSON = REPO / "data/ops/cfb-component-attribution-20260912.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _fmt(val: Any, digits: int = 3) -> str:
    if val is None:
        return "—"
    if isinstance(val, float):
        return f"{val:.{digits}f}"
    return str(val)


def _find(panel: List[Mapping[str, Any]], family_id: str) -> Optional[Mapping[str, Any]]:
    return next((r for r in panel if r.get("family_id") == family_id), None)


def _val1(rec: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    if not rec:
        return {}
    return (rec.get("splits") or {}).get("val_1") or {}


def _family_table(
    panel: List[Mapping[str, Any]],
    reference_id: str,
) -> str:
    ref = _val1(_find(panel, reference_id))
    lines = [
        "| family | Val-1 n | MAE | bias | RMSE | mean model | std model | |m−c| | tail n | tail bias | ΔMAE vs ref | Δbias vs ref |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    order = [reference_id] + [f["id"] for f in FAMILIES]
    seen = set()
    for fid in order:
        rec = _find(panel, fid)
        if rec is None or fid in seen:
            continue
        seen.add(fid)
        card = _val1(rec)
        mae = card.get("mae_vs_actual")
        bias = card.get("bias_vs_actual")
        d_mae = None
        d_bias = None
        if mae is not None and ref.get("mae_vs_actual") is not None:
            d_mae = float(mae) - float(ref["mae_vs_actual"])
        if bias is not None and ref.get("bias_vs_actual") is not None:
            d_bias = float(bias) - float(ref["bias_vs_actual"])
        lines.append(
            "| {fid} | {n} | {mae} | {bias} | {rmse} | {mean} | {std} | {dis} | {tail} | {tb} | {dmae} | {dbias} |".format(
                fid=fid,
                n=card.get("n", 0),
                mae=_fmt(mae),
                bias=_fmt(bias),
                rmse=_fmt(card.get("rmse_vs_actual")),
                mean=_fmt(card.get("mean_model_total")),
                std=_fmt(card.get("std_model_total")),
                dis=_fmt(card.get("mean_abs_disagree_total")),
                tail=card.get("high_tail_n", 0),
                tb=_fmt(card.get("high_tail_bias_vs_actual")),
                dmae=_fmt(d_mae),
                dbias=_fmt(d_bias),
            )
        )
    return "\n".join(lines)


def _bin_table(card: Mapping[str, Any]) -> str:
    buckets = card.get("projected_total_buckets") or {}
    if not buckets:
        return "_No predicted-total bins._"
    lines = [
        "| predicted total | n | MAE vs actual | bias vs actual | mean model | mean actual | |m−c| |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for name in ("lt_48", "48_54", "54_60", "60_68", "ge_68"):
        brow = buckets.get(name) or {}
        lines.append(
            "| {name} | {n} | {mae} | {bias} | {mm} | {ma} | {dis} |".format(
                name=name,
                n=brow.get("n", 0),
                mae=_fmt(brow.get("mae_vs_actual")),
                bias=_fmt(brow.get("bias_vs_actual")),
                mm=_fmt(brow.get("mean_model_total")),
                ma=_fmt(brow.get("mean_actual_total")),
                dis=_fmt(brow.get("mean_abs_disagree_total")),
            )
        )
    return "\n".join(lines)


def _od_table(card: Mapping[str, Any]) -> str:
    combo = card.get("od_combos") or {}
    cells = combo.get("cells") or {}
    if not cells:
        return "_No O/D combination table._"
    lines = [
        "| offense tertile × facing defense tertile | n | team-share bias vs actual | mean model total |",
        "| --- | ---: | ---: | ---: |",
    ]
    for key, brow in cells.items():
        lines.append(
            "| {key} | {n} | {bias} | {mean} |".format(
                key=key,
                n=brow.get("n_team_games", 0),
                bias=_fmt(brow.get("bias_vs_actual_teamshare")),
                mean=_fmt(brow.get("mean_model_total")),
            )
        )
    return "\n".join(lines)


def _moments_block(card: Mapping[str, Any], title: str) -> List[str]:
    m = card.get("moments") or {}
    loc = m.get("location_decomposition") or {}
    lines = [
        f"### {title}",
        "",
        f"- mean offense index: `{_fmt(m.get('mean_offense_index'), 4)}`",
        f"- mean defense index: `{_fmt(m.get('mean_defense_index'), 4)}`",
        f"- mean(off) − mean(def): `{_fmt(m.get('mean_off_minus_def'), 4)}`",
        f"- mean raw ratio: `{_fmt(m.get('mean_raw_ratio'), 4)}`",
        f"- mean matchup multiplier: `{_fmt(m.get('mean_matchup_mult'), 4)}`",
        f"- mean pace: `{_fmt(m.get('mean_pace'), 4)}`",
        f"- mean HFA points: `{_fmt(m.get('mean_hfa_points'), 3)}`",
        f"- mean QB index: `{_fmt(m.get('mean_qb_index'), 4)}`",
        f"- mean off_eff / def_eff: `{_fmt(m.get('mean_off_eff'))}` / `{_fmt(m.get('mean_def_eff'))}`",
        f"- clamp game rate: `{_fmt(m.get('clamp_game_rate'), 4)}`",
        f"- 2×PPG: `{_fmt(loc.get('two_league_ppg'))}`",
        f"- approx matchup lift: `{_fmt(loc.get('approx_matchup_lift'))}`",
        f"- approx pace lift: `{_fmt(loc.get('approx_pace_lift'))}`",
        f"- mean HFA added to total: `{_fmt(loc.get('mean_hfa_added_to_total'))}`",
        "",
    ]
    return lines


def write_report(payload: Dict[str, Any]) -> None:
    gate = payload.get("decision") or {}
    panel_140 = list(payload.get("panel_140") or [])
    panel_070 = list(payload.get("panel_070") or [])
    v140 = _val1(_find(panel_140, "frozen_140"))
    v070 = _val1(_find(panel_070, "floor_070"))
    eq = payload.get("totals_equation") or totals_equation_doc()
    lines: List[str] = [
        "# CFB broader recalibration — component attribution",
        "",
        f"**Generated:** `{payload.get('generated_at')}`  ",
        f"**Contract:** `{QB_FEATURE_CONTRACT_VERSION}`  ",
        f"**Production MATCHUP_RESPONSE:** `{MATCHUP_RESPONSE}` (unchanged)  ",
        f"**Production LEAGUE_TEAM_PPG:** `{LEAGUE_TEAM_PPG}` (unchanged)  ",
        f"**Authorized floor (not a coefficient):** `{AUTHORIZED_FLOOR}`  ",
        "**Objective:** actual MAE / bias / tail. Close is diagnostic only.  ",
        "**Kill switch:** ON. 2025 sealed. 2026 excluded. No PLAY. No Line Curve.",
        "",
        "## Decision",
        "",
        f"**{gate.get('recommendation')}**",
        "",
    ]
    for why in gate.get("why") or []:
        lines.append(f"- {why}")
    lines += [
        "",
        f"Evidence required to open parameters: {gate.get('evidence_required_to_open_parameters')}",
        "",
        "Do not:",
        "",
    ]
    for item in gate.get("do_not") or []:
        lines.append(f"- {item}")
    lines += [
        "",
        "## Ranked root-cause attribution",
        "",
        "| rank | family | \\|Δbias\\| @1.40 | \\|Δbias\\| @0.70 | MAE improve @1.40 | tail n drop @1.40 |",
        "| ---: | --- | ---: | ---: | ---: | ---: |",
    ]
    for i, row in enumerate(gate.get("ranked") or [], start=1):
        lines.append(
            "| {i} | {fid} | {b140} | {b070} | {m140} | {tail} |".format(
                i=i,
                fid=row.get("family_id"),
                b140=_fmt(row.get("abs_bias_move_vs_140")),
                b070=_fmt(row.get("abs_bias_move_vs_070")),
                m140=_fmt(row.get("mae_improve_vs_140")),
                tail=_fmt(row.get("tail_n_drop_vs_140"), 1),
            )
        )
    err = gate.get("error_type") or v140.get("error_type") or {}
    lines += [
        "",
        f"Error type @ frozen 1.40: **{err.get('primary')}** `{err.get('flags')}`",
        "",
        "## Train-0 / Val-0 / Val-1 confirmation (top families)",
        "",
        "Identity matchup, QB neutralization, and O/D centering are the same causal chain: "
        "Layer A talent ~69–71 → mean QB index 1.23 → mean offense index 1.14 vs defense 1.01 "
        "→ mean ratio 1.13 → `ratio**r` lifts both sides. Turning any one of those three off "
        "collapses location. Identity matchup also collapses prediction std to ~0.57 — a "
        "location diagnostic, not a shippable model.",
        "",
    ]

    def _split_row(panel, fid, split):
        rec = _find(panel, fid)
        if not rec:
            return "— / — / —"
        card = (rec.get("splits") or {}).get(split) or {}
        return "{n} / {mae} / {bias}".format(
            n=card.get("n", 0),
            mae=_fmt(card.get("mae_vs_actual")),
            bias=_fmt(card.get("bias_vs_actual")),
        )

    lines += [
        "### Panel A vs frozen 1.40",
        "",
        "| family | Train-0 n / MAE / bias | Val-0 n / MAE / bias | Val-1 n / MAE / bias |",
        "| --- | --- | --- | --- |",
    ]
    for fid in (
        "frozen_140",
        "qb_talent_scale",
        "od_strength_centering",
        "multiplicative_matchup",
        "double_counted_strength",
        "home_field",
    ):
        lines.append(
            f"| {fid} | {_split_row(panel_140, fid, 'train_0')} | "
            f"{_split_row(panel_140, fid, 'val_0')} | "
            f"{_split_row(panel_140, fid, 'val_1')} |"
        )
    lines += [
        "",
        "### Panel B vs authorized 0.70 remaining-error reference",
        "",
        "| family | Train-0 n / MAE / bias | Val-0 n / MAE / bias | Val-1 n / MAE / bias |",
        "| --- | --- | --- | --- |",
    ]
    for fid in (
        "floor_070",
        "qb_talent_scale",
        "od_strength_centering",
        "multiplicative_matchup",
        "double_counted_strength",
        "home_field",
    ):
        lines.append(
            f"| {fid} | {_split_row(panel_070, fid, 'train_0')} | "
            f"{_split_row(panel_070, fid, 'val_0')} | "
            f"{_split_row(panel_070, fid, 'val_1')} |"
        )
    lines += [
        "",
        "## Complete totals equation",
        "",
        "```",
        "qb_index = clamp((1+(talent-50)/80) * class_mult * cast_mult)",
        "offense_score = 0.34*off_eff + 0.22*roster + 0.24*qb_score + 0.10*skill + 0.10*ol",
        "defense_score = 0.36*def_eff + 0.12*roster + 0.24*F7 + 0.20*secondary + 0.08*exp",
        "index = clamp(1 + (score-50)/68)  then multiplicative post-compose blends",
        "ratio = soft_clamp(off / max(0.50, opp_def), 0.52, 1.45, retain=0.42)",
        "pts = clamp(25.9 * ratio**r * boost * dampen * pace + HFA + coach, 7, 55)",
        "total = home_pts + away_pts + ST_nudge",
        "```",
        "",
        "Terms that can move the predicted total:",
        "",
    ]
    for term in (eq.get("terms_that_can_move_the_total") or []):
        lines.append(f"- {term}")
    lines += [
        "",
        (eq.get("why_140_can_need_a_huge_downward_response") or ""),
        "",
        "## Panel A — one family vs frozen 1.40",
        "",
        "Actual-primary. Negative ΔMAE / Δbias is an improvement versus 1.40.",
        "",
        _family_table(panel_140, "frozen_140"),
        "",
        "## Panel B — one family vs authorized 0.70 remaining-error reference",
        "",
        "0.70 is **not** an earned coefficient. This panel attributes the leftover +4–5 bias.",
        "",
        _family_table(panel_070, "floor_070"),
        "",
        "## Calibration by predicted-total bin (Val-1)",
        "",
        "### Frozen 1.40",
        "",
        _bin_table(v140),
        "",
        "### Authorized 0.70 floor",
        "",
        _bin_table(v070),
        "",
        "## Offense × defense strength combinations (Val-1)",
        "",
        "### Frozen 1.40",
        "",
        _od_table(v140),
        "",
        "### Authorized 0.70 floor",
        "",
        _od_table(v070),
        "",
    ]
    lines += _moments_block(v140, "Location decomposition — frozen 1.40 (Val-1)")
    lines += _moments_block(v070, "Location decomposition — authorized 0.70 (Val-1)")
    lines += [
        "## Provenance / limits",
        "",
        f"- lake mounted: `{payload.get('lake_mounted')}`",
        f"- Layer A talent: `{payload.get('layer_a_talent')}`",
        f"- sanity: `{json.dumps(((payload.get('decision') or {}).get('error_type') or {}), default=str)[:600]}`",
        "",
    ]
    for note in payload.get("reconstruction_limits") or []:
        lines.append(f"- {note}")
    lines += [
        "",
        "## GO / STOP",
        "",
        f"**{gate.get('recommendation')}**",
        "",
        "STOP. Do not touch 2025, 2026, production CFB, PLAY labels, or Line Curve. "
        "Do not write a new production coefficient. Do not resume MATCHUP_RESPONSE "
        "sweeps below 0.70.",
        "",
    ]
    OPS_MD.parent.mkdir(parents=True, exist_ok=True)
    OPS_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    if MATCHUP_RESPONSE != 1.40:
        raise SystemExit(f"MATCHUP_RESPONSE drifted: {MATCHUP_RESPONSE}")
    if abs(float(LEAGUE_TEAM_PPG) - 25.9) > 1e-9:
        raise SystemExit(f"LEAGUE_TEAM_PPG drifted: {LEAGUE_TEAM_PPG}")
    payload = run_component_attribution(lake_only=True)
    payload["generated_at"] = _utc()
    write_report(payload)
    OPS_JSON.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ops_md": str(OPS_MD),
                "ops_json": str(OPS_JSON),
                "decision": (payload.get("decision") or {}).get("recommendation"),
                "n_panel_140": len(payload.get("panel_140") or []),
                "n_panel_070": len(payload.get("panel_070") or []),
                "matchup_response_still": MATCHUP_RESPONSE,
                "ppg_still": LEAGUE_TEAM_PPG,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
