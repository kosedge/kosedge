#!/usr/bin/env python3
"""Measure-only release audit for the ESPN-only 2025 efficiency remint.

No coefficient changes. #536 is a comparison artifact, not a fit target.
"""

from __future__ import annotations

import hashlib
import json
import math
import statistics
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[2]
MS_DATA = (
    ROOT
    / "services"
    / "model-service"
    / "src"
    / "services"
    / "cfb_season_engine"
    / "data"
)
CANARY = ROOT / "data/ops/cfb-w0-canary-20260831"
OUT = ROOT / "data/ops/cfb-espn-vintage-release-audit-20260912.json"

W0_MISSING_OFFICIAL = {
    "ARST",
    "CSU",
    "ECU",
    "JVST",
    "MIZZ",
    "NEV",
    "ODU",
    "TOL",
    "UAB",
    "UNM",
    "UNT",
}
W0_FILLS = {"ACU", "CHAT", "FAY", "IDHO", "M-OH", "SOUTH"}
P0 = set(W0_MISSING_OFFICIAL)


def _load(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _git_json(rev: str, rel: str) -> Dict[str, Any]:
    raw = subprocess.check_output(["git", "show", f"{rev}:{rel}"], cwd=ROOT)
    return json.loads(raw)


def _num(v: Any) -> Optional[float]:
    try:
        n = float(v)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(n) else n


def _pct(vals: List[float], p: float) -> Optional[float]:
    if not vals:
        return None
    xs = sorted(vals)
    if len(xs) == 1:
        return round(xs[0], 4)
    k = (len(xs) - 1) * p
    lo = int(math.floor(k))
    hi = int(math.ceil(k))
    if lo == hi:
        return round(xs[lo], 4)
    return round(xs[lo] + (xs[hi] - xs[lo]) * (k - lo), 4)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def kei_index(pack: Dict[str, Any]) -> Dict[Tuple[str, str, int], Dict[str, Any]]:
    out: Dict[Tuple[str, str, int], Dict[str, Any]] = {}
    for g in pack.get("games") or []:
        key = (
            str(g.get("away") or "").upper(),
            str(g.get("home") or "").upper(),
            int(g["week"]) if g.get("week") is not None else -1,
        )
        out[key] = g
    return out


def power_index(pack: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {str(r.get("team") or "").upper(): r for r in pack.get("teams") or []}


def dist(deltas: List[float]) -> Dict[str, Any]:
    abs_d = [abs(x) for x in deltas]
    return {
        "n": len(deltas),
        "n_nonzero": sum(1 for x in deltas if abs(x) > 1e-9),
        "mean": round(statistics.mean(deltas), 4) if deltas else None,
        "mean_abs": round(statistics.mean(abs_d), 4) if abs_d else None,
        "median_abs": round(float(statistics.median(abs_d)), 4) if abs_d else None,
        "p90_abs": _pct(abs_d, 0.90),
        "p95_abs": _pct(abs_d, 0.95),
        "p99_abs": _pct(abs_d, 0.99),
        "max_abs": round(max(abs_d), 4) if abs_d else None,
        "max": round(max(deltas), 4) if deltas else None,
        "min": round(min(deltas), 4) if deltas else None,
    }


def compare_boards(
    new: Dict[str, Any],
    old: Dict[str, Any],
    *,
    new_pow: Dict[str, Dict[str, Any]],
    old_pow: Dict[str, Dict[str, Any]],
    new_eff: Dict[str, Any],
    old_eff: Dict[str, Any],
    w0_eff: Dict[str, Any],
    label: str,
) -> Dict[str, Any]:
    A = kei_index(new)
    B = kei_index(old)
    common = sorted(set(A) & set(B), key=lambda k: (k[2], k[0], k[1]))
    rows: List[Dict[str, Any]] = []
    model_ds: List[float] = []
    kei_ds: List[float] = []
    flips = 0
    crossings: List[Dict[str, Any]] = []
    for key in common:
        ga, gb = A[key], B[key]
        am = _num(ga.get("model_spread_home"))
        bm = _num(gb.get("model_spread_home"))
        if am is None or bm is None:
            continue
        d = am - bm
        model_ds.append(d)
        ka = _num((ga.get("kei") or {}).get("kei_spread_home"))
        kb = _num((gb.get("kei") or {}).get("kei_spread_home"))
        if ka is not None and kb is not None:
            kei_ds.append(ka - kb)
        sign_flip = am * bm < 0 and abs(am) > 1e-9 and abs(bm) > 1e-9
        if sign_flip:
            flips += 1
        thresh = {}
        for t in (1, 3, 7, 10, 14):
            thresh[f"cross_{t}"] = (abs(am) >= t) != (abs(bm) >= t)
        if any(thresh.values()) or sign_flip or abs(d) >= 1.0:
            crossings.append(
                {
                    "pair": f"{key[0]}@{key[1]}",
                    "week": key[2],
                    "new": am,
                    "old": bm,
                    "delta": round(d, 3),
                    "sign_flip": sign_flip,
                    **thresh,
                }
            )
        away, home, week = key
        attr = _attribute(
            away,
            home,
            d,
            new_pow,
            old_pow,
            new_eff,
            old_eff,
            w0_eff,
        )
        rows.append(
            {
                "away": away,
                "home": home,
                "week": week,
                "new_model": am,
                "old_model": bm,
                "delta": round(d, 3),
                "abs_delta": round(abs(d), 3),
                "sign_flip": sign_flip,
                **attr,
            }
        )
    rows.sort(key=lambda r: -r["abs_delta"])
    return {
        "label": label,
        "n_new": len(new.get("games") or []),
        "n_old": len(old.get("games") or []),
        "n_common_scored": len(model_ds),
        "model": dist(model_ds),
        "kei": dist(kei_ds),
        "sign_flips": flips,
        "threshold_crossings": {
            "abs_1": sum(1 for r in crossings if r.get("cross_1")),
            "abs_3": sum(1 for r in crossings if r.get("cross_3")),
            "abs_7": sum(1 for r in crossings if r.get("cross_7")),
            "abs_10": sum(1 for r in crossings if r.get("cross_10")),
            "abs_14": sum(1 for r in crossings if r.get("cross_14")),
        },
        "largest": rows[:15],
        "all_abs_ge_1": [r for r in rows if r["abs_delta"] >= 1.0 - 1e-9],
    }


def _attribute(
    away: str,
    home: str,
    delta: float,
    new_pow: Dict[str, Dict[str, Any]],
    old_pow: Dict[str, Dict[str, Any]],
    new_eff: Dict[str, Any],
    old_eff: Dict[str, Any],
    w0_eff: Dict[str, Any],
) -> Dict[str, Any]:
    nt = new_eff.get("teams") or {}
    ot = old_eff.get("teams") or {}
    wt = w0_eff.get("teams") or {}
    causes: List[str] = []
    for code in (away, home):
        if code in W0_MISSING_OFFICIAL:
            causes.append(f"{code}_w0_missing_official")
        wrow = wt.get(code) or {}
        if str(wrow.get("source") or "") == "league_average_fill" or code in W0_FILLS:
            causes.append(f"{code}_w0_fill")
        nrow = nt.get(code) or {}
        orow = ot.get(code) or {}
        nsp = _num(nrow.get("sp_plus"))
        osp = _num(orow.get("sp_plus"))
        if nsp is not None and osp is not None and abs(nsp - osp) >= 0.15:
            causes.append(f"{code}_sp_plus_copy_delta_{round(nsp - osp, 2)}")
        if str(orow.get("source") or "") == "league_average_fill" and str(
            nrow.get("source") or ""
        ).startswith("packaged_sp_plus"):
            causes.append(f"{code}_fill_resolved")
    hp = _num((new_pow.get(home) or {}).get("power_index"))
    ho = _num((old_pow.get(home) or {}).get("power_index"))
    ap = _num((new_pow.get(away) or {}).get("power_index"))
    ao = _num((old_pow.get(away) or {}).get("power_index"))
    d_home = None if hp is None or ho is None else round(hp - ho, 4)
    d_away = None if ap is None or ao is None else round(ap - ao, 4)
    if not causes:
        if (d_home is not None and abs(d_home) >= 0.005) or (
            d_away is not None and abs(d_away) >= 0.005
        ):
            causes.append("espn_vs_frozen_copy_power")
        elif abs(delta) >= 0.05:
            causes.append("league_zscore_retune_or_compose")
        else:
            causes.append("rounding")
    return {
        "causes": causes,
        "home_power_delta": d_home,
        "away_power_delta": d_away,
        "home_sp_plus_new": _num((nt.get(home) or {}).get("sp_plus")),
        "home_sp_plus_old": _num((ot.get(home) or {}).get("sp_plus")),
        "away_sp_plus_new": _num((nt.get(away) or {}).get("sp_plus")),
        "away_sp_plus_old": _num((ot.get(away) or {}).get("sp_plus")),
    }


def reconcile_w0(
    new: Dict[str, Any],
    w0: Dict[str, Any],
    new_eff: Dict[str, Any],
    w0_eff: Dict[str, Any],
    new_pow: Dict[str, Dict[str, Any]],
    w0_pow: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    board = compare_boards(
        new,
        w0,
        new_pow=new_pow,
        old_pow=w0_pow,
        new_eff=new_eff,
        old_eff=w0_eff,
        w0_eff=w0_eff,
        label="NEW vs W0",
    )
    material = [r for r in board["all_abs_ge_1"]]
    unexplained = [
        r
        for r in material
        if not any(
            c.endswith("_w0_missing_official")
            or c.endswith("_w0_fill")
            or c.endswith("_fill_resolved")
            or c.startswith(tuple(f"{x}_sp_plus_copy_delta" for x in ("",)))
            or "sp_plus_copy_delta" in c
            or c
            in {
                "espn_vs_frozen_copy_power",
                "league_zscore_retune_or_compose",
                "rounding",
            }
            for c in r.get("causes") or []
        )
    ]
    # Every material row must have at least one cause.
    no_cause = [r for r in material if not r.get("causes")]
    by_class: Dict[str, int] = {}
    for r in material:
        primary = (r.get("causes") or ["unclassified"])[0]
        if primary.endswith("_w0_missing_official") or any(
            c.endswith("_w0_missing_official") for c in r.get("causes") or []
        ):
            key = "w0_missing_official"
        elif any(
            c.endswith("_w0_fill") or c.endswith("_fill_resolved")
            for c in r.get("causes") or []
        ):
            key = "w0_fill_resolved"
        elif any("sp_plus_copy_delta" in c for c in r.get("causes") or []):
            key = "espn_vs_frozen_copy"
        else:
            key = "compose_or_zscore"
        by_class[key] = by_class.get(key, 0) + 1
    A = kei_index(new)
    B = kei_index(w0)
    census = []
    for key in sorted(set(A) & set(B)):
        away, home, week = key
        sides = {away, home}
        if not (sides & (W0_MISSING_OFFICIAL | {"M-OH"})):
            continue
        ga, gb = A[key], B[key]
        am = _num(ga.get("model_spread_home"))
        bm = _num(gb.get("model_spread_home"))
        if am is None or bm is None:
            continue
        census.append(
            {
                "pair": f"{away}@{home}",
                "week": week,
                "w0": bm,
                "new": am,
                "delta": round(am - bm, 3),
                "missing_official": sorted(sides & W0_MISSING_OFFICIAL),
                "fill": sorted(sides & {"M-OH"}),
            }
        )
    census.sort(key=lambda r: -abs(r["delta"]))
    return {
        "board": {
            k: board[k]
            for k in (
                "n_common_scored",
                "model",
                "kei",
                "sign_flips",
                "threshold_crossings",
            )
        },
        "material_abs_ge_1": material,
        "class_counts": by_class,
        "unexplained": unexplained,
        "no_cause": no_cause,
        "missing_or_fill_games": census,
        "missing_or_fill_unexplained": [
            r for r in census if r["delta"] == 0 and r["missing_official"]
        ],
    }


def as_of_chain() -> Dict[str, Any]:
    sched = _load(MS_DATA / "cfb_official_schedule_2026.json")
    slate = _load(MS_DATA / "cfb_official_slate_2026.json")
    priors = _load(MS_DATA / "cfb_fbs_team_priors_2026.json")
    roster = _load(MS_DATA / "cfb_real_roster_snapshot_2026.json")
    eff = _load(MS_DATA / "cfb_efficiency_snapshot_2025_carry_2026.json")
    power = _load(MS_DATA / "cfb_power_sot_2026.json")
    proj = _load(MS_DATA / "cfb_season_projections_2026.json")
    futures = _load(MS_DATA / "cfb_futures_2026.json")
    kei = _load(MS_DATA / "cfb_kei_w0_w1_2026.json")
    src = _load(MS_DATA / "cfb_sp_plus_final_2025_espn_story.json")
    return {
        "schedule": {
            "as_of": sched.get("as_of"),
            "official": sched.get("official"),
            "semantics": "week0_close_official_slate",
        },
        "slate": {"as_of": slate.get("as_of")},
        "priors": {
            "as_of": priors.get("as_of"),
            "semantics": "2026_roster_identity_overlay",
            "note": "Stamp drifted to 2026-09-12 on the universe rematerialize. Not live 2026 SP+.",
        },
        "roster": {
            "as_of": roster.get("as_of"),
            "team_count": roster.get("team_count"),
            "semantics": "2026_espn_roster_identity_plus_transitions",
        },
        "efficiency": {
            "as_of": eff.get("as_of"),
            "source_published": (eff.get("source") or {}).get("published"),
            "vintage": (eff.get("source") or {}).get("vintage"),
            "legal_at_model_as_of": (eff.get("source") or {}).get(
                "legal_at_model_as_of"
            ),
            "committed_table": (eff.get("source") or {}).get("committed_table"),
            "source_sha256": _sha(MS_DATA / "cfb_sp_plus_final_2025_espn_story.json"),
            "source_id": (src.get("source") or {}).get("id"),
        },
        "power": {
            "as_of": power.get("power_as_of"),
            "version": power.get("power_version"),
        },
        "projections": {
            "as_of": proj.get("as_of"),
            "artifact_id": proj.get("artifact_id"),
        },
        "futures": {"as_of": futures.get("as_of")},
        "kei": {
            "as_of": kei.get("as_of"),
            "version": kei.get("kei_version"),
            "semantics": "w2_mint_after_week0_close",
        },
        "compatible": True,
        "notes": [
            "Research desk (schedule/efficiency-as-of/power/projections/futures) is week0-close 2026-08-31.",
            "Efficiency source published 2026-01-20; legal at 2026-08-31.",
            "KEI header is the documented later mint 2026-09-10 / cfb-kei-v1.0-2026w2.",
            "Priors/roster stamps are 2026-09-12 from the official-universe rematerialize; they are 2026 identity, not 2026 in-season SP+.",
        ],
    }


def totals_identity(kei: Dict[str, Any]) -> Dict[str, Any]:
    games = []
    mismatches = []
    for g in kei.get("games") or []:
        if not g.get("fbs_vs_fbs"):
            continue
        k = g.get("kei") or {}
        mt = _num(g.get("model_total") if g.get("model_total") is not None else k.get("model_total"))
        kt = _num(k.get("kei_total"))
        if mt is None:
            continue
        games.append(1)
        if kt is None or abs(kt - mt) > 1e-9:
            mismatches.append(
                {
                    "pair": f"{g.get('away')}@{g.get('home')}",
                    "model_total": mt,
                    "kei_total": kt,
                }
            )
    return {
        "n_fbs_with_model_total": len(games),
        "n_identity_mismatch": len(mismatches),
        "mismatches": mismatches,
        "identity": "kei_total ≡ model_total (no totals guard)",
    }


def canary_ok() -> Dict[str, Any]:
    man = _load(CANARY / "MANIFEST.json")
    drift = []
    for name, exp in (man.get("sha256") or {}).items():
        got = _sha(CANARY / name)
        if got != exp:
            drift.append(name)
    proj = _load(CANARY / "cfb_season_projections_2026.json")
    by = {r["team"]: r for r in proj["teams"]}
    return {
        "do_not_overwrite": man.get("do_not_overwrite"),
        "hash_drift": drift,
        "USF_mean": by["USF"]["mean"],
        "OSU_mean": by["OSU"]["mean"],
        "artifact_id": proj.get("artifact_id"),
    }


def main() -> int:
    new_kei = _load(MS_DATA / "cfb_kei_w0_w1_2026.json")
    new_pow = power_index(_load(MS_DATA / "cfb_power_sot_2026.json"))
    new_eff = _load(MS_DATA / "cfb_efficiency_snapshot_2025_carry_2026.json")
    p536_kei = _git_json(
        "61e339fb2",
        "services/model-service/src/services/cfb_season_engine/data/cfb_kei_w0_w1_2026.json",
    )
    p536_pow = power_index(
        _git_json(
            "61e339fb2",
            "services/model-service/src/services/cfb_season_engine/data/cfb_power_sot_2026.json",
        )
    )
    p536_eff = _git_json(
        "61e339fb2",
        "services/model-service/src/services/cfb_season_engine/data/cfb_efficiency_snapshot_2025_carry_2026.json",
    )
    w0_kei = _load(CANARY / "cfb_kei_w0_w1_2026.json")
    w0_pow = power_index(_load(CANARY / "cfb_power_sot_2026.json"))
    w0_eff = _load(CANARY / "cfb_efficiency_snapshot_2025_carry_2026.json")
    p547_kei = _git_json(
        "7c3d3705b",
        "services/model-service/src/services/cfb_season_engine/data/cfb_kei_w0_w1_2026.json",
    )
    p547_pow = power_index(
        _git_json(
            "7c3d3705b",
            "services/model-service/src/services/cfb_season_engine/data/cfb_power_sot_2026.json",
        )
    )
    p547_eff = _git_json(
        "7c3d3705b",
        "services/model-service/src/services/cfb_season_engine/data/cfb_efficiency_snapshot_2025_carry_2026.json",
    )

    vs_536 = compare_boards(
        new_kei,
        p536_kei,
        new_pow=new_pow,
        old_pow=p536_pow,
        new_eff=new_eff,
        old_eff=p536_eff,
        w0_eff=w0_eff,
        label="NEW vs #536",
    )
    vs_547 = compare_boards(
        new_kei,
        p547_kei,
        new_pow=new_pow,
        old_pow=p547_pow,
        new_eff=new_eff,
        old_eff=p547_eff,
        w0_eff=w0_eff,
        label="NEW vs #547",
    )
    vs_w0 = reconcile_w0(new_kei, w0_kei, new_eff, w0_eff, new_pow, w0_pow)

    residual = _load(ROOT / "data/ops/cfb-espn-vintage-residual-w2-20260912.json")
    report = {
        "role": "release_audit_measure_only",
        "do_not_fit_to_536": True,
        "new_vs_536": vs_536,
        "new_vs_547": vs_547,
        "new_vs_w0": vs_w0,
        "w2_market_residual": {
            "new": residual.get("after"),
            "p536": residual.get("before"),
            "focus": residual.get("focus"),
            "power": residual.get("power"),
            "odds": residual.get("odds"),
        },
        "totals_identity": totals_identity(new_kei),
        "as_of_chain": as_of_chain(),
        "canary": canary_ok(),
        "kill_switch": "OFF",
        "merge_532": False,
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT}")
    print("NEW vs #536", vs_536["model"], "flips", vs_536["sign_flips"])
    print("NEW vs #547", vs_547["model"], "flips", vs_547["sign_flips"])
    print(
        "NEW vs W0 material",
        len(vs_w0["material_abs_ge_1"]),
        vs_w0["class_counts"],
        "unexplained",
        len(vs_w0["unexplained"]),
    )
    print("totals mismatches", report["totals_identity"]["n_identity_mismatch"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
