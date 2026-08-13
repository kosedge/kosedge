#!/usr/bin/env python3
"""2026 preseason model lock — hard release gate.

Fails nonzero if any check fails. Pointer must not flip on red.

Usage:
  python scripts/nfl/preseason_release_gate.py --bundle data/ops/nfl-preseason-sim-2026-...
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service" / "src"))
sys.path.insert(0, str(ROOT / "scripts" / "nfl"))

from check_nfl_invariants import WINS_TARGET, WINS_TOL, check_bundle  # noqa: E402
from check_nfl_sot_qb_checksum import checksum as sot_qb_checksum  # noqa: E402
from services.nfl_fantasy_draft_rankings import (  # noqa: E402
    rank_season_fantasy_players,
)

POINTER = ROOT / "data/ops/nfl-web-launch-bundle.json"
LOCK_TAG = "nfl-season-engine-2026-preseason-lock"
WALKER_RUSH_MIN = 1_050.0
WALKER_RUSH_MAX = 1_650.0
QB_4000_MAX = 31  # not 32/32 ≥ 4000
QB_LEFT_TAIL_MAX = 3_200.0
TOP5_RB_SPREAD_MIN = 50.0


def _load_mod(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _norm(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (name or "").lower())


def _canon_team(team: str) -> str:
    token = (team or "").strip().upper()
    if token in {"LA", "LAR"}:
        return "LAR"
    if token in {"JAC", "JAX"}:
        return "JAX"
    return token


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


def _find(rows: Sequence[Dict[str, Any]], *needles: str) -> Optional[Dict[str, Any]]:
    norms = [_norm(n) for n in needles]
    for row in rows:
        n = _norm(str(row.get("player_name") or ""))
        if any(needle and (needle == n or needle in n) for needle in norms):
            return row
    return None


def _load_players(bundle: Path) -> List[Dict[str, Any]]:
    path = bundle / "player_regular_season_totals.csv"
    if not path.is_file():
        return []
    return list(csv.DictReader(path.open(encoding="utf-8")))


def _identity_from_bundle(bundle: Path) -> str:
    for name in ("run_summary.json", "quality_checks.json"):
        path = bundle / name
        if not path.is_file():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        for key in ("identity", "lock_tag", "web_bundle_id", "engine_version"):
            val = payload.get(key)
            if val:
                n = payload.get("n_team_sims")
                if key == "engine_version" and n:
                    return f"{val} · N_team={n}"
                return str(val)
    if POINTER.is_file():
        try:
            pointer = json.loads(POINTER.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pointer = {}
        active = str(pointer.get("active_run_id") or pointer.get("bundle_id") or "")
        if active == bundle.name:
            return str(pointer.get("identity") or pointer.get("lock_tag") or "")
    return ""


def run_gate(bundle: Path) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []

    def add(check_id: str, ok: bool, detail: str) -> None:
        checks.append({"id": check_id, "ok": bool(ok), "detail": detail})

    players = _load_players(bundle)
    if not players:
        add("players_csv", False, f"missing {bundle / 'player_regular_season_totals.csv'}")
        return {
            "ok": False,
            "bundle": str(bundle),
            "checks": checks,
        }

    scored = []
    for row in players:
        pos = str(row.get("position") or "").upper()
        if pos not in {"QB", "RB", "WR", "TE"}:
            continue
        item = dict(row)
        item["total_points"] = half_ppr(row)
        scored.append(item)
    ranked = rank_season_fantasy_players(scored)

    walker = _find(ranked, "Kenneth Walker", "Kenneth Walker III")
    charb = _find(ranked, "Zach Charbonnet")
    evans = _find(ranked, "Mike Evans")
    egbuka = _find(ranked, "Emeka Egbuka")
    johnson = _find(ranked, "Emmett Johnson")

    w_team = _canon_team(str((walker or {}).get("team") or ""))
    add(
        "walker_kc",
        bool(walker) and w_team == "KC",
        f"Walker team={w_team or 'MISSING'} (need KC)",
    )
    c_team = _canon_team(str((charb or {}).get("team") or ""))
    add(
        "charbonnet_sea",
        bool(charb) and c_team == "SEA",
        f"Charbonnet team={c_team or 'MISSING'} (need SEA)",
    )
    e_team = _canon_team(str((evans or {}).get("team") or ""))
    add(
        "evans_sf",
        bool(evans) and e_team == "SF",
        f"Evans team={e_team or 'MISSING'} (need SF)",
    )
    g_team = _canon_team(str((egbuka or {}).get("team") or ""))
    add(
        "egbuka_tb",
        bool(egbuka) and g_team == "TB",
        f"Egbuka team={g_team or 'MISSING'} (need TB)",
    )

    walker_rush = _f(walker or {}, "rush_yards_total") if walker else 0.0
    johnson_rush = _f(johnson or {}, "rush_yards_total") if johnson else 0.0
    walker_vol_ok = (
        bool(walker)
        and WALKER_RUSH_MIN <= walker_rush <= WALKER_RUSH_MAX
        and (not johnson or walker_rush > johnson_rush)
    )
    add(
        "walker_feature_volume",
        walker_vol_ok,
        f"Walker rush={walker_rush:.0f} (need {WALKER_RUSH_MIN:.0f}–{WALKER_RUSH_MAX:.0f} "
        f"and > Johnson {johnson_rush:.0f}; not 1,800 invented)",
    )

    chk = sot_qb_checksum(bundle)
    add(
        "checksum_qbs",
        bool(chk.get("ok")),
        "Tua ATL / Willis MIA / Kyler MIN / ARI ≠ Kyler"
        if chk.get("ok")
        else "; ".join(chk.get("failed") or ["checksum failed"]),
    )

    qb_pass = [
        _f(r, "pass_yards_total")
        for r in ranked
        if str(r.get("position") or "").upper() == "QB"
    ]
    n_4000 = sum(1 for y in qb_pass if y >= 4_000)
    n_qb = len(qb_pass)
    left = min(qb_pass) if qb_pass else 0.0
    qb_shape_ok = n_qb > 0 and n_4000 <= QB_4000_MAX and left < QB_LEFT_TAIL_MAX
    add(
        "qb_pass_shape",
        qb_shape_ok,
        f"{n_4000}/{n_qb} QBs ≥4000; min={left:.0f} (need not 32/32 ≥4000 and min<{QB_LEFT_TAIL_MAX:.0f})",
    )

    rbs = [r for r in ranked if str(r.get("position") or "").upper() == "RB"]
    rbs.sort(key=lambda r: int(r.get("rank_position") or 99))
    top5_pts = [float(r.get("total_points") or 0) for r in rbs[:5]]
    spread = (max(top5_pts) - min(top5_pts)) if top5_pts else 0.0
    add(
        "top5_rb_spread",
        spread >= TOP5_RB_SPREAD_MIN,
        f"top-5 Half-PPR spread={spread:.1f} (need ≥{TOP5_RB_SPREAD_MIN:.0f})",
    )

    suite = check_bundle(bundle)
    i1 = next((r for r in suite.results if r.id == "I1"), None)
    add(
        "season_wl_conservation",
        bool(i1 and i1.ok),
        i1.detail if i1 else f"I1 missing; target Σ wins={WINS_TARGET}±{WINS_TOL}",
    )
    add("invariants_all", suite.ok, "I1–week1 suite" if suite.ok else "see check_nfl_invariants")

    identity = _identity_from_bundle(bundle)
    add(
        "bundle_identity",
        bool(identity.strip()),
        identity.strip() or "missing identity string (engine · N · date / lock_tag)",
    )

    audit_mod = _load_mod(
        "audit_nfl_pack_vs_market",
        ROOT / "scripts/nfl/audit_nfl_pack_vs_market.py",
    )
    market = audit_mod.audit()
    n_clear = int((market.get("counts") or {}).get("CLEAR_ERROR") or 0)
    add(
        "pack_vs_fp_clear_error",
        n_clear == 0,
        f"CLEAR_ERROR={n_clear} (need 0)",
    )

    ok = all(c["ok"] for c in checks)
    return {
        "ok": ok,
        "bundle": str(bundle.relative_to(ROOT) if bundle.is_relative_to(ROOT) else bundle),
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
        "lock_tag": LOCK_TAG,
        "checks": checks,
        "walker": {
            "team": w_team,
            "rush": round(walker_rush, 1),
            "pos_rank": (walker or {}).get("rank_position"),
            "overall": (walker or {}).get("rank_overall"),
            "pts": round(float((walker or {}).get("total_points") or 0), 1),
        },
        "charbonnet": {
            "team": c_team,
            "rush": round(_f(charb or {}, "rush_yards_total"), 1),
            "pos_rank": (charb or {}).get("rank_position"),
        },
        "top5_rb_spread": round(spread, 1),
        "qb_ge_4000": n_4000,
        "identity": identity,
        "pack_vs_market": market.get("counts"),
    }


def render_markdown(report: Dict[str, Any]) -> str:
    rows = report.get("checks") or []
    lines = [
        "# NFL preseason release gate",
        "",
        f"- **Bundle:** `{report.get('bundle')}`",
        f"- **Generated:** {report.get('generated_at_utc')}",
        f"- **Lock tag:** `{report.get('lock_tag')}`",
        f"- **Result:** {'**PASS**' if report.get('ok') else '**FAIL**'}",
        f"- **Identity:** {report.get('identity') or '—'}",
        "",
        "| Check | Result | Detail |",
        "|-------|--------|--------|",
    ]
    for row in rows:
        flag = "PASS" if row.get("ok") else "FAIL"
        detail = str(row.get("detail") or "").replace("|", "/")
        lines.append(f"| `{row.get('id')}` | **{flag}** | {detail} |")
    walker = report.get("walker") or {}
    charb = report.get("charbonnet") or {}
    lines.extend(
        [
            "",
            "## Named",
            "",
            f"- Walker: {walker.get('team')} rush={walker.get('rush')} "
            f"RB{walker.get('pos_rank')} ov{walker.get('overall')} {walker.get('pts')} Half-PPR",
            f"- Charbonnet: {charb.get('team')} rush={charb.get('rush')} RB{charb.get('pos_rank')}",
            f"- Top-5 RB spread: {report.get('top5_rb_spread')}",
            f"- QBs ≥4000: {report.get('qb_ge_4000')}",
            "",
        ]
    )
    return "\n".join(lines) + "\n"


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bundle", type=Path, required=True)
    ap.add_argument("--md-out", type=Path, default=None)
    ap.add_argument("--json-out", type=Path, default=None)
    args = ap.parse_args(argv)

    bundle = args.bundle.resolve()
    if not bundle.is_dir():
        print(f"FAIL: bundle not found: {bundle}", file=sys.stderr)
        return 2

    report = run_gate(bundle)
    md = render_markdown(report)
    print(md)
    day = datetime.now(timezone.utc).strftime("%Y%m%d")
    md_out = args.md_out or (ROOT / f"data/ops/nfl-preseason-release-gate-{day}.md")
    md_out.parent.mkdir(parents=True, exist_ok=True)
    md_out.write_text(md, encoding="utf-8")
    if args.json_out:
        args.json_out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE {md_out}")
    if not report.get("ok"):
        print("PRESEASON RELEASE GATE FAILED — pointer must not flip.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
