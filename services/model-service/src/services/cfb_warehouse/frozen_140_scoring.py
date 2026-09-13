"""Frozen MATCHUP_RESPONSE=1.40 scoring on the reconstructed v1 universe.

Research only. Does not change coefficients, QB weights, class multipliers,
PPG, feature definitions, close semantics, or gates. Does not unseal 2025.
Does not read 2026 W1/W2 as a fitting target. Does not publish PLAY.

Primary decision split is Val-1 (2024 W1–14), per
``data/ops/cfb-qb-calibration-protocol-20260911.md``.
"""

from __future__ import annotations

import math
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from src.services.cfb_season_engine import priors as P
from src.services.cfb_season_engine.coaching_continuity import build_coaching_continuity
from src.services.cfb_season_engine.efficiency import build_efficiency_profile
from src.services.cfb_season_engine.historical_calibration import (
    ratings_to_efficiency_map,
)
from src.services.cfb_season_engine.home_field import build_home_field_profile
from src.services.cfb_season_engine.position_groups import build_position_groups
from src.services.cfb_season_engine.qb_feature_contract import (
    QB_FEATURE_CONTRACT_VERSION,
    assert_counting_stats_season_legal,
)
from src.services.cfb_season_engine.qb_situation import build_qb_situation
from src.services.cfb_season_engine.roster_construction import build_roster_construction
from src.services.cfb_season_engine.team_projection import compose_team_projection, project_game
from src.services.cfb_season_engine.types import EngineUniverse, TeamProjectionState
from src.services.cfb_warehouse.close_recovery_2022 import (
    join_2022_closes,
    load_lake_from_parquet,
    load_2022_game_universe,
)
from src.services.cfb_warehouse.identity import known_engine_codes
from src.services.cfb_warehouse.paths import HD_ODDS_CFB, REPO_ODDS_CFB, hd_mounted

_HERE = Path(__file__).resolve()
_MONOREPO = next(
    (
        p
        for p in _HERE.parents
        if (p / "apps" / "web").is_dir()
        and (p / "services" / "model-service").is_dir()
        and (p / "data" / "ops").is_dir()
    ),
    Path("/workspace"),
)

LAYER_A_DIR = (
    _MONOREPO
    / "services/model-service/src/services/cfb_season_engine/data/cfb_qb_layer_a"
)
SDV_CACHE = _MONOREPO / "data/cfb/raw/sdv"

LEGAL_SEASONS = (2022, 2023, 2024)
SEALED_SEASONS = frozenset({2025})
CONFIRM_ONLY_SEASONS = frozenset({2026})
CHAIN_WEEKS = frozenset(range(1, 15))
TRAIN0_GATE = 700
VAL1_GATE = 700
HIGH_TOTAL_TAIL = 68.0
PICK_EDGE_PTS = 0.5
JUICE = 110.0

SPLITS: Dict[str, Dict[str, Any]] = {
    "train_0": {"seasons": (2022,), "weeks": "1-14", "role": "fit_window_not_used"},
    "val_0": {"seasons": (2023,), "weeks": "1-14", "role": "first_out_of_time"},
    "train_1": {"seasons": (2022, 2023), "weeks": "1-14", "role": "forward_chain_train"},
    "val_1": {"seasons": (2024,), "weeks": "1-14", "role": "decision_val"},
}

# Year-Y Power membership. Do not use the 2026 conference map (realignment leak).
_SEC_CORE = {
    "ALA", "ARK", "AUB", "UF", "UGA", "UK", "LSU", "MISS", "MSST", "MIZZ",
    "SCAR", "TENN", "TAMU", "TXAM", "TA&M", "VAN", "OLE",
}
_B1G_CORE = {
    "ILL", "IU", "IOWA", "MD", "MICH", "MSU", "MINN", "NEB", "NW", "OSU",
    "PSU", "PUR", "RUT", "WIS",
}
_ACC_CORE = {
    "BC", "CLEM", "DUKE", "FSU", "GT", "LOU", "MIA", "UNC", "NCSU", "PITT",
    "SYR", "UVA", "VT", "WAKE",
}
_B12_CORE = {"BAY", "ISU", "KU", "KSU", "OKST", "OU", "TCU", "TEX", "TTU", "WVU"}
_PAC12 = {
    "ARIZ", "ASU", "CAL", "COLO", "ORE", "ORST", "STAN", "UCLA", "USC",
    "UTAH", "WASH", "WSU",
}
_B12_2023_ADD = {"CIN", "UCF", "HOU", "BYU"}

TOTAL_BUCKETS = (
    ("lt_48", 0.0, 48.0),
    ("48_54", 48.0, 54.0),
    ("54_60", 54.0, 60.0),
    ("60_68", 60.0, 68.0),
    ("ge_68", 68.0, None),
)
DISAGREE_BUCKETS = (
    ("lt_3", 0.0, 3.0),
    ("3_7", 3.0, 7.0),
    ("7_10", 7.0, 10.0),
    ("10_14", 10.0, 14.0),
    ("ge_14", 14.0, None),
)

# Live 2026 / hist-cal reference numbers (diagnosis only; not a fit target).
PRIOR_PATHOLOGY = {
    "live_2026_w1_total_vs_market_bias": 8.12,
    "live_2026_w2_total_vs_market_bias": 9.94,
    "live_2026_w1_mean_kei_total": 60.67,
    "live_2026_w1_mean_market_total": 52.55,
    "hist_cal_placeholder50_2023_24_total_vs_close_bias": -0.48,
    "hist_cal_placeholder50_spread_vs_close_mae": 8.27,
    "high_tail_definition": HIGH_TOTAL_TAIL,
    "source": [
        "docs/CFB_TOTALS_HOT_AUDIT.md",
        "data/ops/cfb-p0-residual-audit-20260911.md",
        "data/ops/cfb-historical-calibration-20260805.md",
        "PR #539 / cfb-qb-calibration-protocol-20260911",
    ],
}


class FrozenScoringError(RuntimeError):
    pass


def assert_frozen_priors() -> None:
    if float(P.MATCHUP_RESPONSE) != 1.40:
        raise FrozenScoringError(f"MATCHUP_RESPONSE drifted: {P.MATCHUP_RESPONSE}")
    if QB_FEATURE_CONTRACT_VERSION != "cfb-qb-feature-v1":
        raise FrozenScoringError("qb feature contract drifted")


def refuse_sealed_or_confirm(seasons: Iterable[int]) -> None:
    bad = [int(s) for s in seasons if int(s) in SEALED_SEASONS or int(s) in CONFIRM_ONLY_SEASONS]
    if bad:
        raise FrozenScoringError(
            f"refusing sealed/confirm seasons {bad}; 2025 sealed, 2026 not in the loss"
        )
    illegal = [int(s) for s in seasons if int(s) not in LEGAL_SEASONS]
    if illegal:
        raise FrozenScoringError(f"illegal scoring seasons {illegal}")


def power_codes_for_season(season: int) -> set[str]:
    """Year-Y Power 5 (2022–23) / Power 4 (2024). Not the 2026 map."""
    if int(season) <= 2023:
        b12 = set(_B12_CORE)
        if int(season) >= 2023:
            b12 |= set(_B12_2023_ADD)
        return set(_SEC_CORE) | set(_B1G_CORE) | set(_ACC_CORE) | b12 | set(_PAC12)
    # 2024 Power 4 after realignment.
    sec = set(_SEC_CORE) | {"OU", "TEX"}
    b1g = set(_B1G_CORE) | {"ORE", "WASH", "UCLA", "USC"}
    acc = set(_ACC_CORE) | {"CAL", "STAN", "SMU"}
    b12 = (set(_B12_CORE) - {"OU", "TEX"}) | set(_B12_2023_ADD) | {
        "UTAH",
        "ARIZ",
        "ASU",
        "COLO",
    }
    return sec | b1g | acc | b12


def _in_bucket(value: float, lo: float, hi: Optional[float]) -> bool:
    if hi is None:
        return value >= lo
    return lo <= value < hi


def _mean(xs: Sequence[float]) -> Optional[float]:
    return statistics.fmean(xs) if xs else None


def _mae(xs: Sequence[float]) -> Optional[float]:
    return _mean([abs(x) for x in xs])


def _rmse(xs: Sequence[float]) -> Optional[float]:
    if not xs:
        return None
    return math.sqrt(statistics.fmean(x * x for x in xs))


def _median_abs(xs: Sequence[float]) -> Optional[float]:
    if not xs:
        return None
    return float(statistics.median(abs(x) for x in xs))


def _quantiles(
    xs: Sequence[float],
    probs: Sequence[float] = (0.10, 0.25, 0.50, 0.75, 0.90),
) -> Dict[str, Optional[float]]:
    if not xs:
        return {f"p{int(p * 100)}": None for p in probs}
    ordered = sorted(float(x) for x in xs)

    def _q(p: float) -> float:
        if len(ordered) == 1:
            return ordered[0]
        idx = p * (len(ordered) - 1)
        lo = int(math.floor(idx))
        hi = int(math.ceil(idx))
        if lo == hi:
            return ordered[lo]
        weight = idx - lo
        return ordered[lo] * (1.0 - weight) + ordered[hi] * weight

    return {f"p{int(p * 100)}": _q(p) for p in probs}


def roi_minus_110(hits: Sequence[bool]) -> Optional[float]:
    """Unit ROI at −110: win +100/110, lose −1. Per unit risked."""
    if not hits:
        return None
    pnl = sum((100.0 / JUICE) if hit else -1.0 for hit in hits)
    return pnl / len(hits)


def locate_season_lake(season: int) -> Dict[str, Any]:
    refuse_sealed_or_confirm([season])
    name = f"snapshots-{int(season)}.parquet"
    tried = [
        {
            "id": "hd_parquet",
            "path": str(HD_ODDS_CFB / name),
            "present": (HD_ODDS_CFB / name).is_file(),
            "hd_mounted": hd_mounted(),
        },
        {
            "id": "repo_parquet",
            "path": str(REPO_ODDS_CFB / name),
            "present": (REPO_ODDS_CFB / name).is_file(),
        },
        {
            "id": "monorepo_parquet",
            "path": str(
                _MONOREPO / "data/cfb/warehouse/clean/odds_cfb" / name
            ),
            "present": (
                _MONOREPO / "data/cfb/warehouse/clean/odds_cfb" / name
            ).is_file(),
        },
    ]
    chosen = next((row["id"] for row in tried if row.get("present")), None)
    return {"season": int(season), "chosen": chosen, "mounted": chosen is not None, "tried": tried}


def load_season_lake(season: int) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    loc = locate_season_lake(season)
    if loc["chosen"] == "hd_parquet":
        snaps = load_lake_from_parquet(HD_ODDS_CFB / f"snapshots-{season}.parquet")
    elif loc["chosen"] == "repo_parquet":
        snaps = load_lake_from_parquet(REPO_ODDS_CFB / f"snapshots-{season}.parquet")
    elif loc["chosen"] == "monorepo_parquet":
        snaps = load_lake_from_parquet(
            _MONOREPO / "data/cfb/warehouse/clean/odds_cfb" / f"snapshots-{season}.parquet"
        )
    else:
        return [], loc
    kept: List[Dict[str, Any]] = []
    for row in snaps:
        try:
            season_i = int(row["season"]) if row.get("season") not in (None, "") else None
        except (TypeError, ValueError):
            season_i = None
        if season_i in SEALED_SEASONS or season_i in CONFIRM_ONLY_SEASONS:
            continue
        if season_i == int(season):
            kept.append(dict(row))
    loc["raw_rows_loaded"] = len(snaps)
    loc["raw_rows_season"] = len(kept)
    return kept, loc


def load_layer_a(season: int) -> Dict[str, Any]:
    refuse_sealed_or_confirm([season])
    path = LAYER_A_DIR / f"season_{int(season)}.json"
    payload = __import__("json").loads(path.read_text(encoding="utf-8"))
    if payload.get("qb_feature_contract_version") != QB_FEATURE_CONTRACT_VERSION:
        raise FrozenScoringError(f"{season} Layer A contract drifted")
    if int(payload.get("prediction_season") or 0) != int(season):
        raise FrozenScoringError(f"{season} Layer A prediction_season mismatch")
    if int(payload.get("prior_season") or 0) != int(season) - 1:
        raise FrozenScoringError(f"{season} Layer A prior_season leakage")
    for code, row in (payload.get("teams") or {}).items():
        assert_counting_stats_season_legal(
            stats_season=int(row.get("prior_season") or payload["prior_season"]),
            prediction_season=int(season),
            week=0,
        )
        if row.get("ol_support") is not None or row.get("weapons_support") is not None:
            raise FrozenScoringError(f"{season} {code} Layer B cast was filled")
        if row.get("recruiting_class_score") is not None:
            raise FrozenScoringError(f"{season} {code} recruiting was filled")
    return payload


def load_season_games(season: int, *, cache_dir: Optional[Path] = None):
    refuse_sealed_or_confirm([season])
    if int(season) == 2022:
        return load_2022_game_universe(cache_dir=cache_dir or SDV_CACHE)
    from src.services.cfb_warehouse.ingest import ingest_season

    games, closes, _snaps, skipped = ingest_season(
        int(season), cache_dir=cache_dir or SDV_CACHE, known=known_engine_codes()
    )
    if any(int(g.get("season") or 0) in SEALED_SEASONS for g in games):
        raise FrozenScoringError("2025 leaked into scoring game universe")
    return games, closes, {
        "n_games": len(games),
        "n_sdv_closes": len(closes),
        "skipped": skipped,
        "source": "sportsdataverse espn_cfb_betting + team_box + linescores + schedules",
        "cache_dir": str(cache_dir or SDV_CACHE),
    }


def build_v1_state(
    code: str,
    layer_row: Mapping[str, Any],
    efficiency,
    *,
    home_field_payload: Optional[Mapping[str, Any]] = None,
) -> TeamProjectionState:
    """League-avg roster/units + Layer A QB. Layer B cast held out at 50."""
    roster = build_roster_construction(
        code,
        {
            "returning_production": 50.0,
            "portal_in_value": 50.0,
            "portal_out_value": 50.0,
            "recruiting_class_score": 50.0,
            "experience_index": 50.0,
            "fidelity": "placeholder",
            "source": "historical_reconstruction_league_avg",
            "notes": "Layer B roster/recruiting MISSING; league-average fill.",
        },
        default_source="historical_reconstruction_league_avg",
    )
    groups = build_position_groups(
        code,
        {
            "ol": 50.0,
            "skill": 50.0,
            "front_seven": 50.0,
            "secondary": 50.0,
            "special_teams": 50.0,
            "fidelity": "placeholder",
            "source": "historical_reconstruction_league_avg",
        },
        default_source="historical_reconstruction_league_avg",
    )
    qb = build_qb_situation(
        code,
        {
            "qb_class": layer_row.get("qb_class"),
            "qb_talent": layer_row.get("qb_talent"),
            "ol_support": 50.0,
            "weapons_support": 50.0,
            "supporting_cast": 50.0,
            "experience_starts": layer_row.get("experience_starts") or 0,
            "is_portal": bool(layer_row.get("is_portal")),
            "starter_name": layer_row.get("starter_name") or "",
            "starter_key": layer_row.get("starter_key") or "",
            "fidelity": "approximate",
            "source": "cfb-qb-feature-v1-layer-a",
            "notes": "Layer B cast MISSING; held out at 50 so cast_mult=1.0.",
        },
        default_source="cfb-qb-feature-v1-layer-a",
    )
    home_field = build_home_field_profile(code, home_field_payload)
    coaching = build_coaching_continuity(
        code,
        {
            "new_hc": False,
            "new_oc": False,
            "new_dc": False,
            "fidelity": "placeholder",
            "source": "historical_reconstruction_all_returning",
            "notes": "Historical coaching flags not wired; assume returning.",
        },
    )
    return compose_team_projection(
        code,
        roster,
        qb,
        groups,
        efficiency=efficiency or build_efficiency_profile(code, None),
        home_field=home_field,
        coaching=coaching,
    )


def build_v1_universe(
    season: int,
    layer_a: Mapping[str, Any],
    efficiency_by_code: Mapping[str, Any],
) -> EngineUniverse:
    from src.services.cfb_season_engine.conferences import load_conference_map
    from src.services.cfb_season_engine.loaders import load_packaged_team_priors

    priors = load_packaged_team_priors()
    teams: Dict[str, TeamProjectionState] = {}
    for code, row in (layer_a.get("teams") or {}).items():
        payload = (priors.get("teams") or {}).get(code) or {}
        teams[code] = build_v1_state(
            code,
            row,
            efficiency_by_code.get(code),
            home_field_payload=payload.get("home_field"),
        )
    return EngineUniverse(
        season=int(season),
        teams=teams,
        schedule=[],
        conferences=load_conference_map(),
        player_hooks={},
        notes={
            "mode": "frozen_140_v1_layer_a",
            "qb_feature_contract_version": QB_FEATURE_CONTRACT_VERSION,
            "matchup_response": P.MATCHUP_RESPONSE,
            "layer_b_cast": "MISSING_held_out_50",
            "efficiency_prior_season": str(int(season) - 1),
            "detail": (
                f"Frozen 1.40 scoring universe for {season}: Layer A QB "
                f"(cfb-qb-feature-v1) + prior-year efficiency + league-avg "
                "roster/units. Cast held out (identity). 2025 sealed."
            ),
        },
    )


def _eligible(row: Mapping[str, Any], *, lake_only: bool) -> bool:
    if int(row.get("season") or 0) in SEALED_SEASONS:
        return False
    if int(row.get("week") or 0) not in CHAIN_WEEKS:
        return False
    if not row.get("fbs_fbs"):
        return False
    if not row.get("actual_available"):
        return False
    if not row.get("layer_a_both"):
        return False
    if row.get("conflict"):
        return False
    if row.get("close_spread_home") is None or row.get("close_total") is None:
        return False
    if lake_only:
        return bool(row.get("valid_pregame_lake_close")) and row.get("close_source") == "odds_api_lake"
    return True


def score_joined_rows(
    joined: Sequence[Mapping[str, Any]],
    universes: Mapping[int, EngineUniverse],
    *,
    lake_only: bool = True,
    with_components: bool = False,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    skipped = {"no_universe": 0, "missing_team": 0, "ineligible": 0}
    for raw in joined:
        if not _eligible(raw, lake_only=lake_only):
            skipped["ineligible"] += 1
            continue
        season = int(raw["season"])
        universe = universes.get(season)
        if universe is None:
            skipped["no_universe"] += 1
            continue
        home = str(raw["home_team_id"])
        away = str(raw["away_team_id"])
        if home not in universe.teams or away not in universe.teams:
            skipped["missing_team"] += 1
            continue
        proj = project_game(
            universe,
            home_team=home,
            away_team=away,
            week=int(raw["week"]),
            season=season,
            neutral_site=False,
            engine_version=P.ENGINE_VERSION,
        )
        actual_margin = float(int(raw["home_score"]) - int(raw["away_score"]))
        actual_total = float(int(raw["home_score"]) + int(raw["away_score"]))
        model_spread = float(proj.spread_home)
        model_total = float(proj.expected_total)
        model_wp = float(proj.home_win_prob)
        close_spread = float(raw["close_spread_home"])
        close_total = float(raw["close_total"])

        cover_margin = actual_margin + close_spread
        home_covers = None if abs(cover_margin) < 1e-9 else cover_margin > 0
        model_home_edge = close_spread - model_spread
        ats_hit = None
        if home_covers is not None:
            if model_home_edge > PICK_EDGE_PTS:
                ats_hit = bool(home_covers)
            elif model_home_edge < -PICK_EDGE_PTS:
                ats_hit = not bool(home_covers)

        ou_diff = actual_total - close_total
        over_hit = None if abs(ou_diff) < 1e-9 else ou_diff > 0
        ou_hit = None
        if over_hit is not None:
            if model_total > close_total + PICK_EDGE_PTS:
                ou_hit = bool(over_hit)
            elif model_total < close_total - PICK_EDGE_PTS:
                ou_hit = not bool(over_hit)

        home_won = int(raw["home_score"]) > int(raw["away_score"])
        power = power_codes_for_season(season)
        home_power = home in power
        away_power = away in power
        if home_power and away_power:
            ident = "power_vs_power"
        elif home_power or away_power:
            ident = "power_vs_g5"
        else:
            ident = "g5_vs_g5"

        home_qb = universe.teams[home].qb
        away_qb = universe.teams[away].qb
        rows.append(
            {
                "game_id": raw.get("game_id"),
                "season": season,
                "week": int(raw["week"]),
                "home": home,
                "away": away,
                "actual_margin": actual_margin,
                "actual_total": actual_total,
                "close_spread_home": close_spread,
                "close_total": close_total,
                "close_source": raw.get("close_source"),
                "model_spread_home": model_spread,
                "model_total": model_total,
                "model_home_wp": model_wp,
                "err_spread_vs_close": model_spread - close_spread,
                "err_margin_vs_actual": (-model_spread) - actual_margin,
                "err_total_vs_close": model_total - close_total,
                "err_total_vs_actual": model_total - actual_total,
                "abs_disagree_spread": abs(model_spread - close_spread),
                "abs_disagree_total": abs(model_total - close_total),
                "ats_hit": ats_hit,
                "ou_hit": ou_hit,
                "ml_hit": (model_wp >= 0.5) == home_won,
                "brier": (model_wp - (1.0 if home_won else 0.0)) ** 2,
                "favorite_home": close_spread < 0,
                "early_w1_2": int(raw["week"]) <= 2,
                "identity_slice": ident,
                "high_total_tail": model_total >= HIGH_TOTAL_TAIL,
                "established_both": bool(
                    (home_qb.qb_talent or 0) and getattr(home_qb, "experience_starts", 0) is not None
                ),
                "home_qb_talent": float(home_qb.qb_talent),
                "away_qb_talent": float(away_qb.qb_talent),
                "home_qb_class": home_qb.qb_class,
                "away_qb_class": away_qb.qb_class,
            }
        )
        if with_components:
            home_st = universe.teams[home]
            away_st = universe.teams[away]
            matchup = (proj.drivers or {}).get("matchup") or {}
            home_diag = matchup.get("home_points_diag") or {}
            away_diag = matchup.get("away_points_diag") or {}
            hfa = home_diag.get("hfa") or {}
            home_eff = home_st.efficiency
            away_eff = away_st.efficiency
            rows[-1].update(
                {
                    "home_off_idx": home_st.offense_index,
                    "home_def_idx": home_st.defense_index,
                    "away_off_idx": away_st.offense_index,
                    "away_def_idx": away_st.defense_index,
                    "home_pace_factor": home_st.pace_factor,
                    "away_pace_factor": away_st.pace_factor,
                    "home_qb_index": float(home_qb.qb_situation_index),
                    "away_qb_index": float(away_qb.qb_situation_index),
                    "home_off_eff": float(home_eff.off_eff) if home_eff else None,
                    "home_def_eff": float(home_eff.def_eff) if home_eff else None,
                    "away_off_eff": float(away_eff.off_eff) if away_eff else None,
                    "away_def_eff": float(away_eff.def_eff) if away_eff else None,
                    "home_explosiveness": (
                        float(home_eff.explosiveness) if home_eff else None
                    ),
                    "away_explosiveness": (
                        float(away_eff.explosiveness) if away_eff else None
                    ),
                    "home_ratio_raw": home_diag.get("matchup_ratio_raw"),
                    "away_ratio_raw": away_diag.get("matchup_ratio_raw"),
                    "home_ratio": home_diag.get("matchup_ratio"),
                    "away_ratio": away_diag.get("matchup_ratio"),
                    "home_matchup_mult": home_diag.get("matchup_mult"),
                    "away_matchup_mult": away_diag.get("matchup_mult"),
                    "home_pace_used": home_diag.get("pace"),
                    "away_pace_used": away_diag.get("pace"),
                    "home_pre_clamp": home_diag.get("pre_clamp"),
                    "away_pre_clamp": away_diag.get("pre_clamp"),
                    "home_clamped": bool(home_diag.get("clamped")),
                    "away_clamped": bool(away_diag.get("clamped")),
                    "home_hfa_pts": hfa.get("hfa_points"),
                    "expected_home_score": float(proj.expected_home_score),
                    "expected_away_score": float(proj.expected_away_score),
                }
            )
    return rows, skipped


def _block(subset: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    if not subset:
        return {"n": 0}
    spread_close = [float(r["err_spread_vs_close"]) for r in subset]
    margin_act = [float(r["err_margin_vs_actual"]) for r in subset]
    total_close = [float(r["err_total_vs_close"]) for r in subset]
    total_act = [float(r["err_total_vs_actual"]) for r in subset]
    ats = [bool(r["ats_hit"]) for r in subset if r["ats_hit"] is not None]
    ou = [bool(r["ou_hit"]) for r in subset if r["ou_hit"] is not None]
    return {
        "n": len(subset),
        "spread_vs_close_n": len(spread_close),
        "spread_vs_close_mae": _mae(spread_close),
        "spread_vs_close_rmse": _rmse(spread_close),
        "spread_vs_close_bias": _mean(spread_close),
        "spread_vs_close_median_abs": _median_abs(spread_close),
        "margin_vs_actual_n": len(margin_act),
        "margin_vs_actual_mae": _mae(margin_act),
        "margin_vs_actual_rmse": _rmse(margin_act),
        "margin_vs_actual_bias": _mean(margin_act),
        "margin_vs_actual_median_abs": _median_abs(margin_act),
        "total_vs_close_n": len(total_close),
        "total_vs_close_mae": _mae(total_close),
        "total_vs_close_rmse": _rmse(total_close),
        "total_vs_close_bias": _mean(total_close),
        "total_vs_close_median_abs": _median_abs(total_close),
        "total_vs_actual_n": len(total_act),
        "total_vs_actual_mae": _mae(total_act),
        "total_vs_actual_rmse": _rmse(total_act),
        "total_vs_actual_bias": _mean(total_act),
        "total_vs_actual_median_abs": _median_abs(total_act),
        "mean_model_total": _mean([float(r["model_total"]) for r in subset]),
        "mean_close_total": _mean([float(r["close_total"]) for r in subset]),
        "mean_actual_total": _mean([float(r["actual_total"]) for r in subset]),
        "mean_abs_model_spread": _mean([abs(float(r["model_spread_home"])) for r in subset]),
        "mean_abs_close_spread": _mean([abs(float(r["close_spread_home"])) for r in subset]),
        "ats_n": len(ats),
        "ats_hit_rate": (sum(ats) / len(ats)) if ats else None,
        "ats_roi_minus_110": roi_minus_110(ats),
        "ou_n": len(ou),
        "ou_hit_rate": (sum(ou) / len(ou)) if ou else None,
        "ou_roi_minus_110": roi_minus_110(ou),
        "brier_home_wp": _mean([float(r["brier"]) for r in subset]),
        "disagree_vs_close_quantiles": _quantiles(total_close),
        "error_vs_actual_quantiles": _quantiles(total_act),
        "mean_abs_disagree_total": _mae(total_close),
        "std_model_total": (
            statistics.pstdev([float(r["model_total"]) for r in subset])
            if len(subset) > 1
            else 0.0
        ),
        "model_total_quantiles": _quantiles([float(r["model_total"]) for r in subset]),
        "actual_total_quantiles": _quantiles([float(r["actual_total"]) for r in subset]),
    }


def summarize_scored(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    def sl(pred) -> List[Mapping[str, Any]]:
        return [r for r in rows if pred(r)]

    def split_rows(name: str) -> List[Mapping[str, Any]]:
        seasons = set(SPLITS[name]["seasons"])
        return sl(lambda r: int(r["season"]) in seasons and int(r["week"]) in CHAIN_WEEKS)

    def slices_for(subset: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
        return {
            "home_favorite": _block([r for r in subset if r["favorite_home"]]),
            "home_dog": _block([r for r in subset if not r["favorite_home"]]),
            "early_w1_2": _block([r for r in subset if r["early_w1_2"]]),
            "rest_w3_14": _block([r for r in subset if not r["early_w1_2"]]),
            "power_vs_power": _block(
                [r for r in subset if r["identity_slice"] == "power_vs_power"]
            ),
            "power_vs_g5": _block(
                [r for r in subset if r["identity_slice"] == "power_vs_g5"]
            ),
            "g5_vs_g5": _block([r for r in subset if r["identity_slice"] == "g5_vs_g5"]),
            "high_total_tail_ge_68": _block([r for r in subset if r["high_total_tail"]]),
            "not_high_total_tail": _block(
                [r for r in subset if not r["high_total_tail"]]
            ),
        }

    def bucket_map(subset, key, spec):
        out = {}
        for name, lo, hi in spec:
            out[name] = _block([r for r in subset if _in_bucket(float(r[key]), lo, hi)])
        return out

    splits: Dict[str, Any] = {}
    for name in SPLITS:
        subset = split_rows(name)
        block = _block(subset)
        block["slices"] = slices_for(subset)
        block["projected_total_buckets"] = bucket_map(subset, "model_total", TOTAL_BUCKETS)
        block["spread_disagree_buckets"] = bucket_map(subset, "abs_disagree_spread", DISAGREE_BUCKETS)
        block["total_disagree_buckets"] = bucket_map(subset, "abs_disagree_total", DISAGREE_BUCKETS)
        splits[name] = block

    by_season = {}
    for season in sorted({int(r["season"]) for r in rows}):
        subset = sl(lambda r, s=season: int(r["season"]) == s)
        by_season[str(season)] = {
            **_block(subset),
            "slices": slices_for(subset),
            "projected_total_buckets": bucket_map(subset, "model_total", TOTAL_BUCKETS),
        }

    return {
        "n_scored": len(rows),
        "overall": _block(rows),
        "splits": splits,
        "by_season": by_season,
        "identity_option_slice": "dropped — prior-year rush/QB-rush tag not built; not proxied from 2026",
    }


def decide(summary: Mapping[str, Any]) -> Dict[str, Any]:
    """One pre-registered decision. Primary evidence is Val-1 (2024)."""
    val1 = (summary.get("splits") or {}).get("val_1") or {}
    train0 = (summary.get("splits") or {}).get("train_0") or {}
    n = int(val1.get("n") or 0)
    train_n = int(train0.get("n") or 0)
    reasons: List[str] = []
    if n < VAL1_GATE or train_n < TRAIN0_GATE:
        return {
            "decision": "INSUFFICIENT EVIDENCE",
            "why": [
                f"Val-1 n={n} (need {VAL1_GATE})",
                f"Train-0 n={train_n} (need {TRAIN0_GATE})",
            ],
            "val_1_n": n,
            "train_0_n": train_n,
        }

    total_bias = val1.get("total_vs_close_bias")
    high = (val1.get("slices") or {}).get("high_total_tail_ge_68") or {}
    high_bias = high.get("total_vs_close_bias")
    high_n = int(high.get("n") or 0)
    model_abs = val1.get("mean_abs_model_spread")
    close_abs = val1.get("mean_abs_close_spread")
    spread_gap = None
    if model_abs is not None and close_abs is not None:
        spread_gap = float(model_abs) - float(close_abs)

    pathology = False
    if total_bias is not None and float(total_bias) >= 4.0:
        pathology = True
        reasons.append(f"Val-1 total vs close bias {float(total_bias):+.2f} ≥ +4")
    if high_n >= 30 and high_bias is not None and float(high_bias) >= 5.0:
        pathology = True
        reasons.append(
            f"Val-1 high-tail n={high_n} total vs close bias {float(high_bias):+.2f} ≥ +5"
        )
    if spread_gap is not None and spread_gap >= 3.0:
        pathology = True
        reasons.append(f"Val-1 mean |model spread| − |close| = {spread_gap:+.2f} ≥ +3")

    if pathology:
        return {
            "decision": "RECALIBRATION JUSTIFIED",
            "why": reasons,
            "val_1_n": n,
            "train_0_n": train_n,
            "val_1_total_vs_close_bias": total_bias,
            "val_1_high_tail_bias": high_bias,
            "val_1_spread_abs_gap": spread_gap,
            "note": "ATS/ROI cannot override a failed MAE/bias gate.",
        }

    if total_bias is not None and abs(float(total_bias)) < 2.5 and (
        spread_gap is None or spread_gap < 3.0
    ):
        return {
            "decision": "FROZEN 1.40 VALIDATED",
            "why": [
                f"Val-1 n={n} ≥ {VAL1_GATE}",
                f"Val-1 total vs close bias {float(total_bias):+.2f} inside ±2.5",
                "high-tail / spread-separation gates did not fire",
            ],
            "val_1_n": n,
            "train_0_n": train_n,
            "val_1_total_vs_close_bias": total_bias,
            "val_1_spread_abs_gap": spread_gap,
        }

    return {
        "decision": "INSUFFICIENT EVIDENCE",
        "why": [
            f"Val-1 n={n} clears the sample gate, but totals/spread signal is mixed",
            f"total vs close bias={total_bias}",
            f"spread |model|−|close|={spread_gap}",
            "Layer B cast and historical roster remain held out",
        ],
        "val_1_n": n,
        "train_0_n": train_n,
        "val_1_total_vs_close_bias": total_bias,
        "val_1_spread_abs_gap": spread_gap,
    }


def load_legal_scoring_bundle(
    *,
    cache_dir: Optional[Path] = None,
    lake_only: bool = True,
) -> Dict[str, Any]:
    """Load 2022–24 lake joins + v1 universes once. Refuses 2025/2026.

    ``lake_only`` is recorded for callers; eligibility is applied later in
    ``score_joined_rows``. Does not change MATCHUP_RESPONSE.
    """
    assert_frozen_priors()
    refuse_sealed_or_confirm(LEGAL_SEASONS)
    cache = cache_dir or SDV_CACHE

    layer_by_season: Dict[int, Dict[str, Any]] = {}
    lake_locate: Dict[str, Any] = {}
    joined_all: List[Dict[str, Any]] = []
    universes: Dict[int, EngineUniverse] = {}
    load_meta: Dict[str, Any] = {}

    for season in LEGAL_SEASONS:
        layer = load_layer_a(season)
        layer_by_season[season] = layer
        lake, loc = load_season_lake(season)
        lake_locate[str(season)] = loc
        games, sdv_closes, game_meta = load_season_games(season, cache_dir=cache)
        codes = set((layer.get("teams") or {}).keys())
        audit = join_2022_closes(games, sdv_closes, lake, layer_a_codes=codes)
        joined = list(audit.pop("joined") or [])
        joined_all.extend(joined)
        load_meta[str(season)] = {
            "games": game_meta,
            "join_funnel": audit.get("funnel"),
            "layer_a_n": len(codes),
            "lake_n": len(lake),
        }
        eff = ratings_to_efficiency_map(season - 1, cache_dir=cache)
        universes[season] = build_v1_universe(season, layer, eff)

    qb_talent = {
        str(season): {
            "n": len(art.get("teams") or {}),
            "mean": _mean(
                [float(r["qb_talent"]) for r in (art.get("teams") or {}).values()]
            ),
        }
        for season, art in layer_by_season.items()
    }
    return {
        "joined": joined_all,
        "universes": universes,
        "lake_locate": lake_locate,
        "load": load_meta,
        "layer_a_talent": qb_talent,
        "lake_only": lake_only,
        "qb_feature_contract_version": QB_FEATURE_CONTRACT_VERSION,
        "matchup_response_frozen": P.MATCHUP_RESPONSE,
    }


def run_frozen_140_scoring(
    *,
    cache_dir: Optional[Path] = None,
    lake_only: bool = True,
) -> Dict[str, Any]:
    bundle = load_legal_scoring_bundle(cache_dir=cache_dir, lake_only=lake_only)
    scored, skipped = score_joined_rows(
        bundle["joined"], bundle["universes"], lake_only=lake_only
    )
    summary = summarize_scored(scored)
    gate = decide(summary)
    return {
        "qb_feature_contract_version": QB_FEATURE_CONTRACT_VERSION,
        "matchup_response": P.MATCHUP_RESPONSE,
        "engine_version": P.ENGINE_VERSION,
        "kill_switch": True,
        "opened_2025": False,
        "used_2026_for_fitting": False,
        "scored_frozen_140": True,
        "recalibrated": False,
        "play": False,
        "lake_only": lake_only,
        "lake_locate": bundle["lake_locate"],
        "load": bundle["load"],
        "layer_a_talent": bundle["layer_a_talent"],
        "skipped": skipped,
        "metrics": summary,
        "decision": gate,
        "prior_pathology": PRIOR_PATHOLOGY,
        "reconstruction_limits": [
            "Layer A QB only (talent + class + portal). Layer B cast/recruiting MISSING and held out at 50.",
            "Roster / units / coaching are league-average fills — same as hist-cal identity layers.",
            "Efficiency is prior-year cfb_ratings adj EPA, not live SP+.",
            "HFA is curated 2026 venue proxies.",
            "Closes: owned Odds-API lake last-legal-pre-kick DK→FD; SDV is fill only and excluded from the primary lake_only score.",
            "2025 labels sealed. 2026 W1/W2 not scored.",
            "Identity/option slice dropped (no prior-year rush tag).",
        ],
        "n_joined_omitted_from_json": len(scored),
    }
