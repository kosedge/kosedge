#!/usr/bin/env python3
"""Overlay warehouse opponent-adj EPA onto the 2026 efficiency snapshot.

Kills silent league-average fills for official FBS teams that have ≥ N
prior-season games in ``team_season_efficiency.parquet`` (seasons < 2026).
Keeps packaged SP+ rows. Drops FCS/alias extras. Does not retune tanh.

Usage:
  python scripts/cfb/package_efficiency_backbone_2026.py
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path
from statistics import mean, pstdev
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))

from src.services.cfb_season_engine.fbs_universe import official_fbs_codes  # noqa: E402
from src.services.cfb_warehouse.paths import clean_dir  # noqa: E402

SNAP = (
    ROOT
    / "services"
    / "model-service"
    / "src"
    / "services"
    / "cfb_season_engine"
    / "data"
    / "cfb_efficiency_snapshot_2025_carry_2026.json"
)
BACKBONE = (
    ROOT
    / "services"
    / "model-service"
    / "src"
    / "services"
    / "cfb_season_engine"
    / "data"
    / "cfb_efficiency_backbone_2025.json"
)
MIN_GAMES = 8
Z_SCALE = 18.0


def _z_to_score(z: float, *, scale: float = Z_SCALE) -> float:
    return max(5.0, min(95.0, 50.0 + scale * float(z)))


def _load_season_finals() -> List[Dict[str, Any]]:
    import pandas as pd

    path = clean_dir(prefer_hd=True) / "efficiency" / "team_season_efficiency.parquet"
    if not path.is_file():
        raise FileNotFoundError(f"missing {path}")
    df = pd.read_parquet(path)
    return df.to_dict(orient="records")


def _pick_row(
    rows: List[Dict[str, Any]], team: str, *, prior_year: int = 2025
) -> Optional[Dict[str, Any]]:
    cand = [
        r
        for r in rows
        if str(r.get("team_id")) == team
        and int(r.get("season") or 0) <= prior_year
        and int(r.get("n_games") or 0) >= MIN_GAMES
        and not bool(r.get("cold_start"))
    ]
    if not cand:
        return None
    cand.sort(key=lambda r: int(r.get("season") or 0), reverse=True)
    return cand[0]


def main() -> int:
    official = official_fbs_codes()
    snap = json.loads(SNAP.read_text(encoding="utf-8"))
    before_teams = dict(snap.get("teams") or {})
    rows = _load_season_finals()
    official_2025 = [
        r
        for r in rows
        if int(r.get("season") or 0) == 2025 and str(r.get("team_id")) in official
    ]
    offs = [float(r["off_epa_adj"]) for r in official_2025 if r.get("off_epa_adj") is not None]
    defs = [float(r["def_epa_adj"]) for r in official_2025 if r.get("def_epa_adj") is not None]
    mu_off, sd_off = mean(offs), pstdev(offs) or 1.0
    mu_def, sd_def = mean(defs), pstdev(defs) or 1.0

    filled: Dict[str, Dict[str, Any]] = {}
    thin: List[str] = []
    kept_sp = 0
    new_teams: Dict[str, Dict[str, Any]] = {}

    for code in sorted(official):
        existing = before_teams.get(code) or {}
        src = str(existing.get("source") or "")
        has_sp = src.startswith("packaged_sp_plus") and existing.get("off_eff") not in (
            None,
            50.0,
        )
        # M-OH is in snap as league_average_fill; others are missing entirely.
        if has_sp and src != "league_average_fill":
            new_teams[code] = dict(existing)
            kept_sp += 1
            continue
        row = _pick_row(rows, code, prior_year=2025)
        if row is None:
            thin.append(code)
            new_teams[code] = {
                "team": code,
                "off_eff": 50.0,
                "def_eff": 50.0,
                "success_off": 50.0,
                "success_def": 50.0,
                "explosiveness": 50.0,
                "sp_plus": 0.0,
                "prior_year": 2025,
                "carry_to_season": 2026,
                "source": "thin_sample_labeled",
                "fidelity": "placeholder",
                "n_games": 0,
                "notes": (
                    "No warehouse season-final with ≥8 games through 2025. "
                    "Thin-sample label — not a silent league average."
                ),
            }
            continue
        z_off = (float(row["off_epa_adj"]) - mu_off) / sd_off
        # def_epa_adj is EPA allowed; invert so higher def_eff = better defense.
        z_def = -((float(row["def_epa_adj"]) - mu_def) / sd_def)
        off_eff = round(_z_to_score(z_off), 2)
        def_eff = round(_z_to_score(z_def), 2)
        payload = {
            "team": code,
            "off_eff": off_eff,
            "def_eff": def_eff,
            "success_off": round(_z_to_score(0.85 * z_off, scale=16.0), 2),
            "success_def": round(_z_to_score(0.85 * z_def, scale=16.0), 2),
            "explosiveness": round(_z_to_score(max(-1.5, z_off), scale=17.0), 2),
            "sp_plus": round((off_eff + def_eff) / 2.0 - 50.0, 2),
            "off_epa_adj": round(float(row["off_epa_adj"]), 6),
            "def_epa_adj": round(float(row["def_epa_adj"]), 6),
            "n_games": int(row.get("n_games") or 0),
            "feature_week": int(row.get("feature_week") or 0),
            "prior_year": int(row.get("season") or 2025),
            "carry_to_season": 2026,
            "source": "warehouse_pbp_epa_adj_2025",
            "fidelity": "approximate",
            "notes": (
                "Opponent-adj EPA from owned PBP season-final "
                f"(season={row.get('season')}, n_games={row.get('n_games')}, "
                "feature_week < next season). Garbage-weighted. "
                "success/explosiveness are EPA-z proxies, not play rates. "
                "Replaces silent league_average_fill."
            ),
        }
        new_teams[code] = payload
        filled[code] = {
            "season": int(row.get("season") or 0),
            "n_games": int(row.get("n_games") or 0),
            "off_eff": off_eff,
            "def_eff": def_eff,
        }

    snap["teams"] = new_teams
    snap["as_of"] = date.today().isoformat()
    snap["used_in_spread"] = False
    snap["team_count"] = len(new_teams)
    snap["mapped_from_sp_plus"] = kept_sp
    snap["source"] = dict(snap.get("source") or {})
    snap["source"]["pbp"] = (
        "warehouse team_season_efficiency overlay for official-FBS fills "
        "(seasons ≤ 2025, n_games ≥ 8)"
    )
    snap["source"]["primary_sp_plus"] = "packaged_sp_plus_final_2025 when mapped"
    snap["backbone"] = {
        "version": "cfb-efficiency-backbone-v0.14-20260814",
        "method": (
            "4-iter opponent-adj EPA (efficiency_adj.py); week W uses week < W; "
            "season-final = last as_of_week. Garbage-time down-weight. "
            "FCS flagged, not deleted. z-score vs 2025 official FBS."
        ),
        "min_games": MIN_GAMES,
        "n_sp_plus": kept_sp,
        "n_warehouse_fill": len(filled),
        "n_thin": len(thin),
        "filled": filled,
        "thin": thin,
        "dropped_extras": sorted(c for c in before_teams if c not in official),
        "norm": {
            "off_epa_mean": round(mu_off, 6),
            "off_epa_sd": round(sd_off, 6),
            "def_epa_mean": round(mu_def, 6),
            "def_epa_sd": round(sd_def, 6),
        },
    }
    notes = list(snap.get("notes") or [])
    notes.append(
        "2026-08-14: warehouse PBP EPA overlay replaced official-FBS "
        "league_average_fill rows. FCS extras dropped. tanh calibration unchanged."
    )
    snap["notes"] = notes
    SNAP.write_text(json.dumps(snap, indent=2) + "\n", encoding="utf-8")

    table = {
        "as_of": date.today().isoformat(),
        "version": "cfb-efficiency-backbone-v0.14-20260814",
        "used_in_spread": False,
        "teams": {
            code: {
                "off_eff": row.get("off_eff"),
                "def_eff": row.get("def_eff"),
                "source": row.get("source"),
                "n_games": row.get("n_games"),
                "prior_year": row.get("prior_year"),
            }
            for code, row in new_teams.items()
        },
        "n_sp_plus": kept_sp,
        "n_warehouse_fill": len(filled),
        "n_thin": len(thin),
        "thin": thin,
        "filled": filled,
    }
    BACKBONE.write_text(json.dumps(table, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "snapshot": str(SNAP),
                "backbone": str(BACKBONE),
                "n_official": len(official),
                "n_sp_plus": kept_sp,
                "n_warehouse_fill": len(filled),
                "filled": sorted(filled),
                "thin": thin,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
