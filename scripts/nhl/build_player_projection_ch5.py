#!/usr/bin/env python3
"""Build NHL Chapter 5 PlayerProjection from Ch2 TOI × rates + tandem × SV%.

Skater: TOI_EV TOI_PP G A P SOG + σ
Goalie: start_share SV_pct SA GAA SAVES + σ

Identity: Σ skater G ≈ Ch1 GF/G within NHL_TEAM_REBASE_RESIDUAL_CAP.
Σ goalie start_share ≈ 1.0 per team (from Ch2 tandem).

No board emit. No props. No new TOI grid. No MoneyPuck. Do not retune 0.85.

Usage:
  python3 scripts/nhl/build_player_projection_ch5.py
"""

from __future__ import annotations

import json
import math
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import pstdev
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))

from src.services.nhl_data import NHL_TEAM_ABBREVS  # noqa: E402
from src.services.nhl_season_engine import priors as P  # noqa: E402

DATA = ROOT / "services/model-service/src/services/nhl_season_engine/data"
TOI_PATH = DATA / "nhl_toi_grid_2026.json"
TANDEM_PATH = DATA / "nhl_goalie_tandem_2026.json"
PRIOR_PATH = DATA / "nhl_team_prior_2026.json"
SKATER_BOX = DATA / "nhl_skater_box_2023_2025.json"
GOALIE_BOX = DATA / "nhl_goalie_box_2023_2025.json"
OUT_PATH = DATA / "nhl_player_projection_2026.json"

WEIGHTS = dict(P.PLAYER_YEAR_WEIGHTS_BY_SEASON_ID)
RESIDUAL_CAP = float(P.NHL_TEAM_REBASE_RESIDUAL_CAP)
TOI_SUM = float(P.NHL_TOI_GRID_SKATER_MINUTES)
EXPECTED_TEAMS = 32
SKATER_KEYS = ("g", "a", "p", "sog")


def _utc_today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _primary_team(team_field: Any) -> Optional[str]:
    if team_field is None:
        return None
    parts = [p.strip().upper() for p in str(team_field).split(",") if p.strip()]
    return parts[-1] if parts else None


def _weighted_mean(pairs: List[Tuple[float, float]]) -> Tuple[float, float]:
    num = 0.0
    den = 0.0
    for val, w in pairs:
        if w <= 0:
            continue
        num += float(val) * float(w)
        den += float(w)
    if den <= 0:
        return 0.0, 0.0
    return num / den, den


def _sigma_from_rates(year_vals: List[float], mean: float) -> float:
    if len(year_vals) >= 2:
        return float(pstdev(year_vals))
    return max(0.15 * abs(float(mean)), 1e-4)


def _index_skater_box(pack: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """player_id → seasons of per-minute rates + meta."""
    out: Dict[str, Dict[str, Any]] = {}
    for season_key, rows in (pack.get("by_season") or {}).items():
        season_id = int(season_key)
        for row in rows or []:
            pid = str(row.get("player_id") or "")
            if not pid:
                continue
            gp = float(row.get("gp") or 0)
            toi_sec = float(row.get("toi_per_game") or 0)
            if gp <= 0 or toi_sec <= 0:
                continue
            toi_min = toi_sec / 60.0
            slot = out.setdefault(
                pid,
                {
                    "player_name": row.get("player_name"),
                    "position": row.get("position"),
                    "rates": {k: {} for k in SKATER_KEYS},
                    "toi_min": {},
                },
            )
            slot["player_name"] = row.get("player_name") or slot.get("player_name")
            slot["position"] = row.get("position") or slot.get("position")
            slot["toi_min"][season_id] = toi_min
            for k in SKATER_KEYS:
                per_g = float(row.get(k) or 0) / gp
                slot["rates"][k][season_id] = per_g / toi_min
    return out


def _index_goalie_box(pack: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for season_key, rows in (pack.get("by_season") or {}).items():
        season_id = int(season_key)
        for row in rows or []:
            pid = str(row.get("player_id") or "")
            if not pid:
                continue
            gs = float(row.get("gs") or 0)
            gp = float(row.get("gp") or 0)
            if gs <= 0 and gp <= 0:
                continue
            slot = out.setdefault(
                pid,
                {
                    "player_name": row.get("player_name"),
                    "sv_pct": {},
                    "gaa": {},
                    "sa_per_gs": {},
                    "gs": {},
                },
            )
            slot["player_name"] = row.get("player_name") or slot.get("player_name")
            if row.get("sv_pct") is not None:
                slot["sv_pct"][season_id] = float(row["sv_pct"])
            if row.get("gaa") is not None:
                slot["gaa"][season_id] = float(row["gaa"])
            sa = float(row.get("sa") or 0)
            if gs > 0:
                slot["sa_per_gs"][season_id] = sa / gs
            slot["gs"][season_id] = gs
    return out


def _rate_bundle(
    rate_by_season: Dict[int, float],
) -> Tuple[float, float, List[float]]:
    pairs = []
    vals = []
    for sid, rate in rate_by_season.items():
        w = float(WEIGHTS.get(sid) or 0)
        if w <= 0:
            continue
        pairs.append((float(rate), w))
        vals.append(float(rate))
    mean, mass = _weighted_mean(pairs)
    if mass <= 0:
        return 0.0, 1e-4, []
    return mean, _sigma_from_rates(vals, mean), vals


def main() -> None:
    toi_pack = json.loads(TOI_PATH.read_text(encoding="utf-8"))
    tandem_pack = json.loads(TANDEM_PATH.read_text(encoding="utf-8"))
    prior_pack = json.loads(PRIOR_PATH.read_text(encoding="utf-8"))
    skater_idx = _index_skater_box(json.loads(SKATER_BOX.read_text(encoding="utf-8")))
    goalie_idx = _index_goalie_box(json.loads(GOALIE_BOX.read_text(encoding="utf-8")))

    skaters_out: Dict[str, Dict[str, Any]] = {}
    goalies_out: Dict[str, Dict[str, Any]] = {}
    team_checks: Dict[str, Dict[str, Any]] = {}

    for team in NHL_TEAM_ABBREVS:
        prior = (prior_pack.get("teams") or {}).get(team) or {}
        gp = float(prior.get("gp") or 82) or 82.0
        target_gf_pg = float(prior.get("gf") or 0) / gp

        slots = list((toi_pack.get("teams") or {}).get(team) or [])
        built: List[Dict[str, Any]] = []
        for slot in slots:
            pid = str(slot.get("player_id") or "")
            minutes = float(slot.get("toi_min") or 0)
            if not pid or minutes <= 0:
                continue
            box = skater_idx.get(pid) or {
                "player_name": slot.get("player_name"),
                "position": slot.get("position"),
                "rates": {k: {} for k in SKATER_KEYS},
            }
            rate_means = {}
            rate_sigmas = {}
            for k in SKATER_KEYS:
                mean, sig, _ = _rate_bundle(box.get("rates", {}).get(k) or {})
                # Tiny prior if missing box (not MoneyPuck).
                if mean == 0 and not (box.get("rates", {}).get(k) or {}):
                    defaults = {"g": 0.008, "a": 0.012, "p": 0.02, "sog": 0.08}
                    mean = defaults[k]
                    sig = max(0.15 * mean, 1e-4)
                rate_means[k] = mean
                rate_sigmas[k] = sig

            raw_g = rate_means["g"] * minutes
            raw_a = rate_means["a"] * minutes
            raw_sog = rate_means["sog"] * minutes
            # Prefer G+A for P consistency with identity-scaled G later.
            raw_p = raw_g + raw_a
            built.append(
                {
                    "player_id": pid,
                    "player_name": slot.get("player_name") or box.get("player_name"),
                    "team": team,
                    "type": "skater",
                    "position": slot.get("position") or box.get("position"),
                    "TOI_EV": minutes,  # raw has no PP TOI
                    "TOI_PP": 0.0,
                    "_raw_g": raw_g,
                    "_raw_a": raw_a,
                    "_raw_p": raw_p,
                    "_raw_sog": raw_sog,
                    "_sig_g": rate_sigmas["g"] * minutes,
                    "_sig_a": rate_sigmas["a"] * minutes,
                    "_sig_p": math.sqrt(
                        (rate_sigmas["g"] * minutes) ** 2
                        + (rate_sigmas["a"] * minutes) ** 2
                    ),
                    "_sig_sog": rate_sigmas["sog"] * minutes,
                }
            )

        raw_g_sum = sum(p["_raw_g"] for p in built) or 1e-9
        g_scale = target_gf_pg / raw_g_sum if target_gf_pg > 0 else 1.0

        sum_g = 0.0
        sum_toi = 0.0
        for p in built:
            g = p.pop("_raw_g") * g_scale
            a = p.pop("_raw_a")
            sog = p.pop("_raw_sog")
            # Keep A/SOG rate shape; P = G + A after G identity.
            pts = g + a
            sig_g = p.pop("_sig_g") * g_scale
            sig_a = p.pop("_sig_a")
            p.pop("_sig_p")
            sig_sog = p.pop("_sig_sog")
            p.pop("_raw_p")
            proj = {
                **p,
                "G": round(g, 4),
                "A": round(a, 4),
                "P": round(pts, 4),
                "SOG": round(sog, 4),
                "TOI_EV": round(float(p["TOI_EV"]), 4),
                "TOI_PP": 0.0,
                "sigma": {
                    "TOI_EV": 0.0,
                    "TOI_PP": 0.0,
                    "G": round(sig_g, 4),
                    "A": round(sig_a, 4),
                    "P": round(math.sqrt(sig_g**2 + sig_a**2), 4),
                    "SOG": round(sig_sog, 4),
                },
                "g_identity_scale": round(g_scale, 6),
                "pp_toi_source": "missing_in_raw_box_EV_eq_toi_min_PP_eq_0",
            }
            skaters_out[f"{team}:{p['player_id']}"] = proj
            sum_g += proj["G"]
            sum_toi += proj["TOI_EV"] + proj["TOI_PP"]

        drift = abs(sum_g - target_gf_pg)
        if drift > RESIDUAL_CAP + 1e-6:
            raise SystemExit(
                f"G identity failed for {team}: sum={sum_g:.4f} "
                f"target={target_gf_pg:.4f} drift={drift:.4f} > cap={RESIDUAL_CAP}"
            )
        if abs(sum_toi - TOI_SUM) > 0.05:
            raise SystemExit(f"TOI sum failed for {team}: {sum_toi}")

        # Goalies from Ch2 tandem.
        tandem = (tandem_pack.get("teams") or {}).get(team) or {}
        goalie_rows = list(tandem.get("goalies") or [])
        sum_share = 0.0
        for grow in goalie_rows:
            pid = str(grow.get("player_id") or "")
            share = float(grow.get("gs_share") or 0)
            if not pid or share <= 0:
                continue
            box = goalie_idx.get(pid) or {}
            sv_mean, sv_sig, _ = _rate_bundle(box.get("sv_pct") or {})
            if sv_mean <= 0:
                sv_mean, sv_sig = 0.900, 0.015
            gaa_mean, gaa_sig, _ = _rate_bundle(box.get("gaa") or {})
            if gaa_mean <= 0:
                gaa_mean, gaa_sig = 2.80, 0.30
            sa_mean, sa_sig, _ = _rate_bundle(box.get("sa_per_gs") or {})
            if sa_mean <= 0:
                sa_mean, sa_sig = 28.0, 3.0

            sa = sa_mean * share
            saves = sa * sv_mean
            # GAA remains in-net rate (not volume-scaled).
            proj_g = {
                "player_id": pid,
                "player_name": grow.get("player_name") or box.get("player_name"),
                "team": team,
                "type": "goalie",
                "role": grow.get("role"),
                "start_share": round(share, 8),
                "SV_pct": round(sv_mean, 6),
                "SA": round(sa, 4),
                "GAA": round(gaa_mean, 4),
                "SAVES": round(saves, 4),
                "sigma": {
                    "start_share": 0.0,
                    "SV_pct": round(sv_sig, 6),
                    "SA": round(sa_sig * share, 4),
                    "GAA": round(gaa_sig, 4),
                    "SAVES": round(sa_sig * share * sv_mean, 4),
                },
            }
            goalies_out[f"{team}:{pid}"] = proj_g
            sum_share += share

        if abs(sum_share - 1.0) > 1e-6:
            raise SystemExit(f"goalie share sum failed for {team}: {sum_share}")

        team_checks[team] = {
            "sum_toi": round(sum_toi, 4),
            "sum_g": round(sum_g, 4),
            "target_gf_pg": round(target_gf_pg, 6),
            "g_drift": round(drift, 6),
            "residual_cap": RESIDUAL_CAP,
            "g_identity_scale": round(g_scale, 6),
            "sum_start_share": round(sum_share, 8),
        }

    pack = {
        "engine_version": P.ENGINE_VERSION,
        "as_of": _utc_today(),
        "season": "2026-27",
        "chapter": 5,
        "object": "PlayerProjection",
        "NHL_TEAM_REBASE_RESIDUAL_CAP": RESIDUAL_CAP,
        "NHL_TEAM_CARRY_SHRINK_unchanged": P.NHL_TEAM_CARRY_SHRINK,
        "NHL_TOI_GRID_SKATER_MINUTES": TOI_SUM,
        "NHL_GOALIE_TANDEM_SHARE_SUM": P.NHL_GOALIE_TANDEM_SHARE_SUM,
        "PLAYER_YEAR_WEIGHTS": P.PLAYER_YEAR_WEIGHTS,
        "PLAYER_YEAR_WEIGHTS_BY_SEASON_ID": {
            str(k): v for k, v in WEIGHTS.items()
        },
        "pp_toi_source": "missing_in_raw_box_EV_eq_toi_min_PP_eq_0",
        "formula": (
            "skater rates = Σ w_y · ((stat/gp) / (toi_sec/60)); "
            "raw = rate × Ch2 toi_min; G scaled so Σ G = Ch1 gf/gp; "
            "TOI_EV = toi_min, TOI_PP = 0 (no PP TOI in raw); "
            "goalie: start_share from Ch2 tandem; SV%/GAA/SA weighted; "
            "SA = sa_per_gs × start_share; SAVES = SA × SV%; "
            "σ from season-rate dispersion (computed, not hardcoded)"
        ),
        "reads": [
            TOI_PATH.name,
            TANDEM_PATH.name,
            PRIOR_PATH.name,
            SKATER_BOX.name,
            GOALIE_BOX.name,
        ],
        "skater_count": len(skaters_out),
        "goalie_count": len(goalies_out),
        "team_count": EXPECTED_TEAMS,
        "team_checks": team_checks,
        "skaters": skaters_out,
        "goalies": goalies_out,
        "does_not": [
            "fill KEINHL / board emit",
            "props PLAY",
            "new TOI grid",
            "MoneyPuck as the mean",
            "team if",
            "changing 0.85",
            "NBA/WNBA/CFB/NFL",
            "situation (Ch3)",
            "KEI emit (Ch4)",
        ],
    }

    OUT_PATH.write_text(json.dumps(pack, indent=2) + "\n", encoding="utf-8")
    print(
        f"wrote {OUT_PATH} skaters={len(skaters_out)} goalies={len(goalies_out)} "
        f"cap={RESIDUAL_CAP}"
    )
    # Sample stars
    for key in ("COL:8477492", "COL:8478402", "FLA:8475683"):
        # resolve by name scan for display
        pass
    col = [
        r
        for r in skaters_out.values()
        if r["team"] == "COL"
        and r["player_name"]
        in {"Nathan MacKinnon", "Cale Makar", "Mikko Rantanen"}
    ]
    print(
        "COL sample",
        [(r["player_name"], r["G"], r["A"], r["P"], r["TOI_EV"]) for r in sorted(col, key=lambda x: -x["P"])],
    )
    fla_g = [
        r for r in goalies_out.values() if r["team"] == "FLA"
    ]
    print(
        "FLA tandem",
        [
            (r["role"], r["player_name"], r["start_share"], r["SV_pct"], r["SAVES"])
            for r in sorted(fla_g, key=lambda x: -x["start_share"])
        ],
    )


if __name__ == "__main__":
    main()
