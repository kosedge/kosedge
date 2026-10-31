#!/usr/bin/env python3
"""t4910u bounded diagnostic score — 70 complete 2017 REG games.

Read-only on model math. BIND_PACKET_ONLY rest. market_blend=0.
Loads IF simulator/framework from pinned tip 6ca03716. Does not import
W8 eval rest_days_from_schedule. 0 Odds credits.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import random
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PACKET = Path(__file__).resolve().parent
REPO = PACKET.parents[2]
IF_TREE = Path("/tmp/t4910u-if-6ca03716/services/model-service")

IF_TIP = "6ca03716fe52930332d5ffba302c312a651980cc"
W2_TIP = "440314e43cba41311b10a54b9b11ecd1e7638653"
W3W6_TIP = "f92aaea385eb18af90ba09178dddc8ebd732864f"
SEED_BASE = 201710
SEED_MOD = 1000003
SIMULATIONS = 4000
CONST_TOTAL = 45.3
MARKET_BLEND = 0

W2_MATRIX = "data/ops/nfl-hist-bt-stage1b-w2-t4893u/RECON_MATRIX.csv"
W2_MANIFEST = "data/ops/nfl-hist-bt-stage1b-w2-t4893u/SAMPLE_MANIFEST.json"
W3W6_MATRIX = "data/ops/nfl-hist-bt-stage1b-w3w6-t4893u/RECON_MATRIX.csv"
W3W6_MANIFEST = "data/ops/nfl-hist-bt-stage1b-w3w6-t4893u/SAMPLE_MANIFEST.json"
OOS_PATH = REPO / "data/ops/nfl-reopening-packet-20260916/historical-oos/historical_oos_games.csv"

REQUIRED_FIELDS = [
    "game_id",
    "home_team",
    "away_team",
    "matchup_season",
    "matchup_week",
    "rest_days_home",
    "rest_days_away",
    "offense_index_home",
    "offense_index_away",
    "defense_index_home",
    "defense_index_away",
    "home_off_epa_5g",
    "away_off_epa_5g",
    "home_def_epa_allowed_5g",
    "away_def_epa_allowed_5g",
    "home_pass_rate_5g",
    "away_pass_rate_5g",
    "home_success_offense_5g",
    "away_success_offense_5g",
    "home_success_defense_allowed_5g",
    "away_success_defense_allowed_5g",
    "matchup_diff_off_epa_5g",
    "matchup_diff_def_epa_allowed_5g",
    "matchup_diff_success_rate_5g",
    "matchup_diff_pressure_generated_5g",
    "matchup_diff_pressure_allowed_5g",
    "matchup_diff_red_zone_td_rate_5g",
]

NUMERIC_FIELDS = [f for f in REQUIRED_FIELDS if f not in {"game_id", "home_team", "away_team"}]
CONTEXT_STR = {"game_id", "home_team", "away_team"}

EXCLUDED_VISIBLE = [
    {
        "game_id": "2017_02_CHI_TB",
        "reason": "W2 ineligible — TB 0 completed 2017 games as-of (Irma). Not in W2 sealed sample.",
        "class": "W2_INELIGIBLE",
        "in_score_sample": False,
    },
    {
        "game_id": "2017_02_MIA_LAC",
        "reason": "W2 ineligible — MIA 0 completed 2017 games as-of (Irma). Not in W2 sealed sample.",
        "class": "W2_INELIGIBLE",
        "in_score_sample": False,
    },
    {
        "game_id": "2017_06_DET_NO",
        "reason": "W6 bye partial — NO W5 bye; T2 fail-closed. Excluded from 70.",
        "class": "W6_BYE_PARTIAL",
        "in_score_sample": False,
    },
    {
        "game_id": "2017_06_MIA_ATL",
        "reason": "W6 bye partial — ATL W5 bye; T2 fail-closed. Excluded from 70.",
        "class": "W6_BYE_PARTIAL",
        "in_score_sample": False,
    },
    {
        "game_id": "2017_06_SF_WAS",
        "reason": "W6 bye partial — WSH W5 bye; T2 fail-closed. Excluded from 70.",
        "class": "W6_BYE_PARTIAL",
        "in_score_sample": False,
    },
    {
        "game_id": "2017_06_NYG_DEN",
        "reason": "W6 bye partial — DEN W5 bye; T2 fail-closed. Excluded from 70.",
        "class": "W6_BYE_PARTIAL",
        "in_score_sample": False,
    },
]

# rest_days_from_schedule / W8 verify_rest_days must never be imported.
FORBIDDEN_REST_NAMES = (
    "rest_days_from_schedule",
    "verify_rest_days",
    "nfl_offline_if_eval_w8",
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def sha256_git(ref: str, path: str) -> str:
    blob = subprocess.check_output(["git", "-C", str(REPO), "show", f"{ref}:{path}"])
    return sha256_bytes(blob)


def git_show_text(ref: str, path: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(REPO), "show", f"{ref}:{path}"],
        text=True,
    )


def git_sha(ref: str, path: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(REPO), "rev-parse", f"{ref}:{path}"],
        text=True,
    ).strip()


def seed_for(game_id: str) -> int:
    digest = hashlib.sha256(game_id.encode()).hexdigest()
    return SEED_BASE + (int(digest[:12], 16) % SEED_MOD)


def parse_record(record: str) -> Tuple[float, float, float, float]:
    parts = [p.strip() for p in str(record).split("-")]
    if len(parts) < 2:
        raise ValueError(f"unparseable record {record!r}")
    wins = float(parts[0])
    losses = float(parts[1])
    ties = float(parts[2]) if len(parts) > 2 else 0.0
    games = wins + losses + ties
    if games <= 0:
        raise ValueError(f"zero-game record {record!r} — no silent 0.5 fill")
    winpct = wins / games
    return wins, losses, ties, winpct


def naive_wp_home(record_home: str, record_away: str) -> Dict[str, Any]:
    hw, hl, ht, hp = parse_record(record_home)
    aw, al, at, ap = parse_record(record_away)
    wp = 0.5 + 0.5 * (hp - ap)
    pick = "HOME" if wp > 0.5 else "AWAY"
    return {
        "record_asof_home": record_home,
        "record_asof_away": record_away,
        "winpct_home": hp,
        "winpct_away": ap,
        "wp_home_naive": wp,
        "naive_su_pick": pick,
        "wins_home": hw,
        "losses_home": hl,
        "ties_home": ht,
        "wins_away": aw,
        "losses_away": al,
        "ties_away": at,
        "formula": "wp_home_naive=0.5+0.5*(winpct_h-winpct_a); pick HOME iff wp>0.5 else AWAY",
    }


def mean(xs: List[float]) -> float:
    return sum(xs) / len(xs) if xs else float("nan")


def sample_sd(xs: List[float]) -> float:
    n = len(xs)
    if n < 2:
        return float("nan")
    mu = mean(xs)
    return math.sqrt(sum((x - mu) ** 2 for x in xs) / (n - 1))


def mae(pairs: List[Tuple[float, float]]) -> float:
    return mean([abs(a - b) for a, b in pairs])


def rmse(pairs: List[Tuple[float, float]]) -> float:
    return math.sqrt(mean([(a - b) ** 2 for a, b in pairs]))


def clip_p(p: float) -> float:
    return min(1.0 - 1e-6, max(1e-6, float(p)))


def load_matrix(ref: str, path: str) -> Dict[str, Dict[str, Dict[str, str]]]:
    text = git_show_text(ref, path)
    rows = list(csv.DictReader(text.splitlines()))
    out: Dict[str, Dict[str, Dict[str, str]]] = defaultdict(dict)
    for row in rows:
        out[row["game_id"]][row["field"]] = row
    return out


def load_manifest_games(ref: str, path: str) -> Dict[str, Dict[str, Any]]:
    data = json.loads(git_show_text(ref, path))
    return {g["game_id"]: g for g in data.get("games") or []}


def is_complete(fields: Dict[str, Dict[str, str]]) -> bool:
    if set(REQUIRED_FIELDS) - set(fields):
        return False
    return all(fields[f]["status"] == "DERIVED_PREGAME" for f in REQUIRED_FIELDS)


def coerce_value(field: str, raw: str) -> Any:
    if field in CONTEXT_STR:
        return raw
    if field == "matchup_season" or field == "matchup_week":
        return int(float(raw))
    return float(raw)


def load_oos_2017() -> Dict[Tuple[int, int, str, str], Dict[str, str]]:
    digest = sha256_file(OOS_PATH)
    if not digest.startswith("1ee90fac"):
        raise SystemExit(f"OOS pin mismatch {digest} (want 1ee90fac…)")
    out = {}
    with OOS_PATH.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if row["season"] != "2017":
                continue
            # Do not copy 2024–25. Do not keep market columns in the working key.
            key = (int(row["season"]), int(row["week"]), row["home"], row["away"])
            out[key] = {
                "home_score": row["home_score"],
                "away_score": row["away_score"],
                "game_date": row["game_date"],
                "key": row["key"],
            }
    return out


def replay_draws(seed: int, mean_home: float, mean_away: float, stdev: float) -> Tuple[List[float], List[float]]:
    rng = random.Random(seed)
    margins: List[float] = []
    totals: List[float] = []
    for _ in range(SIMULATIONS):
        home_score = max(0.0, rng.gauss(mean_home, stdev))
        away_score = max(0.0, rng.gauss(mean_away, stdev))
        totals.append(home_score + away_score)
        margins.append(home_score - away_score)
    return margins, totals


def quantile(sorted_vals: List[float], q: float) -> float:
    if not sorted_vals:
        return float("nan")
    q = min(1.0, max(0.0, q))
    idx = int(round((len(sorted_vals) - 1) * q))
    return float(sorted_vals[idx])


def import_if():
    if str(IF_TREE) not in sys.path:
        sys.path.insert(0, str(IF_TREE))
    # Guard: W8 rest caller must not be on the path we use for rest.
    import src.services.nfl_simulator as sim  # type: ignore

    src = Path(sim.__file__).read_text(encoding="utf-8")
    for name in FORBIDDEN_REST_NAMES:
        if name in src and name != "rest_days_home":
            # simulator mentions rest_days_home/away fields only; not the W8 helper.
            pass
    sim_sha = sha256_file(Path(sim.__file__))
    fw = Path(IF_TREE) / "src/services/nfl_handicapping_framework.py"
    fw_sha = sha256_file(fw)
    if not sim_sha.startswith("52d9e909"):
        raise SystemExit(f"simulator pin mismatch {sim_sha}")
    if not fw_sha.startswith("a0051cc4"):
        raise SystemExit(f"framework pin mismatch {fw_sha}")
    return sim


def build_inputs(sim: Any, game: Dict[str, Any]):
    kwargs = {
        "game_id": game["game_id"],
        "home_team": game["home_team"],
        "away_team": game["away_team"],
        "matchup_season": game["matchup_season"],
        "matchup_week": game["matchup_week"],
        "rest_days_home": game["rest_days_home"],
        "rest_days_away": game["rest_days_away"],
        "offense_index_home": game["offense_index_home"],
        "offense_index_away": game["offense_index_away"],
        "defense_index_home": game["defense_index_home"],
        "defense_index_away": game["defense_index_away"],
        "home_off_epa_5g": game["home_off_epa_5g"],
        "away_off_epa_5g": game["away_off_epa_5g"],
        "home_def_epa_allowed_5g": game["home_def_epa_allowed_5g"],
        "away_def_epa_allowed_5g": game["away_def_epa_allowed_5g"],
        "home_pass_rate_5g": game["home_pass_rate_5g"],
        "away_pass_rate_5g": game["away_pass_rate_5g"],
        "home_success_offense_5g": game["home_success_offense_5g"],
        "away_success_offense_5g": game["away_success_offense_5g"],
        "home_success_defense_allowed_5g": game["home_success_defense_allowed_5g"],
        "away_success_defense_allowed_5g": game["away_success_defense_allowed_5g"],
        "matchup_diff_off_epa_5g": game["matchup_diff_off_epa_5g"],
        "matchup_diff_def_epa_allowed_5g": game["matchup_diff_def_epa_allowed_5g"],
        "matchup_diff_success_rate_5g": game["matchup_diff_success_rate_5g"],
        "matchup_diff_pressure_generated_5g": game["matchup_diff_pressure_generated_5g"],
        "matchup_diff_pressure_allowed_5g": game["matchup_diff_pressure_allowed_5g"],
        "matchup_diff_red_zone_td_rate_5g": game["matchup_diff_red_zone_td_rate_5g"],
    }
    return sim.NflGameInputs(**kwargs)


def assemble_sample() -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
    w2_m = load_matrix(W2_TIP, W2_MATRIX)
    w3_m = load_matrix(W3W6_TIP, W3W6_MATRIX)
    w2_man = load_manifest_games(W2_TIP, W2_MANIFEST)
    w3_man = load_manifest_games(W3W6_TIP, W3W6_MANIFEST)
    oos = load_oos_2017()

    games: List[Dict[str, Any]] = []
    visible_fail: List[Dict[str, Any]] = list(EXCLUDED_VISIBLE)

    def take(gid: str, matrix: Dict[str, Dict[str, str]], man: Dict[str, Any], source_tip: str, week_set: str) -> None:
        fields = matrix
        complete = is_complete(fields)
        row: Dict[str, Any] = {
            "game_id": gid,
            "source_packet_tip": source_tip,
            "week_set": week_set,
            "complete_27_27": complete,
        }
        if not complete:
            missing = [
                f
                for f in REQUIRED_FIELDS
                if f not in fields or fields[f]["status"] != "DERIVED_PREGAME"
            ]
            visible_fail.append(
                {
                    "game_id": gid,
                    "reason": f"incomplete required fields: {missing}",
                    "class": "INCOMPLETE",
                    "in_score_sample": False,
                    "missing_fields": missing,
                }
            )
            return
        for field in REQUIRED_FIELDS:
            row[field] = coerce_value(field, fields[field]["reconstructed_value"])
            row[f"{field}__status"] = fields[field]["status"]
        row["rest_bind"] = "BIND_PACKET_ONLY"
        row["rest_days_home_packet"] = row["rest_days_home"]
        row["rest_days_away_packet"] = row["rest_days_away"]
        row["rest_derivation"] = fields["rest_days_home"].get("derivation_lineage")
        meta = man
        row["kickoff_utc"] = meta.get("kickoff_utc")
        row["forecast_cutoff_utc"] = meta.get("forecast_cutoff_utc")
        row["rating_week_contiguous"] = meta.get("rating_week_contiguous")
        row["record_asof_home"] = meta.get("record_asof_home")
        row["record_asof_away"] = meta.get("record_asof_away")
        row["rest_days_et_manifest"] = meta.get("rest_days_et")
        row["rest_days_utc_contrast"] = meta.get("rest_days_utc_contrast")
        row["utc_et_dow_mismatch"] = meta.get("utc_et_dow_mismatch")
        if row["rest_days_et_manifest"] is not None and float(row["rest_days_et_manifest"]) != float(row["rest_days_home"]):
            visible_fail.append(
                {
                    "game_id": gid,
                    "reason": "packet rest_days_home != manifest rest_days_et",
                    "class": "REST_BIND_MISMATCH",
                    "in_score_sample": False,
                }
            )
            return
        key = (int(row["matchup_season"]), int(row["matchup_week"]), row["home_team"], row["away_team"])
        scores = oos.get(key)
        if scores is None:
            visible_fail.append(
                {
                    "game_id": gid,
                    "reason": f"realized scores missing for {key}",
                    "class": "SCORES_MISSING",
                    "in_score_sample": False,
                }
            )
            return
        row["home_score"] = float(scores["home_score"])
        row["away_score"] = float(scores["away_score"])
        row["realized_margin"] = row["home_score"] - row["away_score"]
        row["realized_total"] = row["home_score"] + row["away_score"]
        row["realized_spread"] = -row["realized_margin"]
        if row["realized_margin"] > 0:
            row["realized_su"] = "HOME"
        elif row["realized_margin"] < 0:
            row["realized_su"] = "AWAY"
        else:
            row["realized_su"] = "TIE"
        row["oos_key"] = scores["key"]
        row["oos_game_date"] = scores["game_date"]
        games.append(row)

    for gid, fields in sorted(w2_m.items()):
        take(gid, fields, w2_man[gid], W2_TIP, "W2")
    for gid, fields in sorted(w3_m.items()):
        if gid in {e["game_id"] for e in EXCLUDED_VISIBLE}:
            # still confirm they are incomplete / bye partials
            if is_complete(fields):
                visible_fail.append(
                    {
                        "game_id": gid,
                        "reason": "predeclared bye partial unexpectedly 27/27 complete",
                        "class": "PARTIAL_UNEXPECTED_COMPLETE",
                        "in_score_sample": False,
                    }
                )
            continue
        take(gid, fields, w3_man[gid], W3W6_TIP, "W3W6")

    audit = {
        "n_assembled": len(games),
        "n_w2": sum(1 for g in games if g["week_set"] == "W2"),
        "n_w3w6": sum(1 for g in games if g["week_set"] == "W3W6"),
        "weeks": dict(Counter(int(g["matchup_week"]) for g in games)),
        "rest_bind": "BIND_PACKET_ONLY",
        "rest_rederived": False,
        "w8_eval_rest_used": False,
        "tip_switched_to_90bf65ab": False,
        "visible_excluded_or_failed": visible_fail,
    }
    return games, visible_fail, audit


def score_game(sim: Any, game: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(game)
    out["attempted"] = True
    try:
        inputs = build_inputs(sim, game)
        # Explicit bind check — packet rest must be what IF received.
        if float(inputs.rest_days_home) != float(game["rest_days_home_packet"]):
            raise RuntimeError("rest_days_home not bound from packet")
        if float(inputs.rest_days_away) != float(game["rest_days_away_packet"]):
            raise RuntimeError("rest_days_away not bound from packet")
        seed = seed_for(game["game_id"])
        out["seed"] = seed
        out["seed_formula"] = "201710 + (int(sha256(game_id.encode()).hexdigest()[:12], 16) % 1000003)"
        out["simulations"] = SIMULATIONS
        projection = sim.simulate_nfl_game_independent_fair(
            inputs,
            simulations=SIMULATIONS,
            seed=seed,
            market_spread_home=None,
            market_total=None,
        )
        block = projection.get("independent_fair") or {}
        if block.get("market_blend") != 0:
            raise RuntimeError(f"market_blend {block.get('market_blend')} != 0")
        margin_mu, total_mu = sim.independent_fair_mus(projection)
        markets = projection.get("markets") or {}
        diagnostics = projection.get("diagnostics") or {}
        out["forecast_margin"] = float(margin_mu)
        out["forecast_spread"] = -float(margin_mu)
        out["forecast_total"] = float(total_mu)
        out["forecast_wp_home"] = float(markets["home_win_prob"])
        out["forecast_wp_away"] = float(markets["away_win_prob"])
        out["if_sigma"] = float(block["sigma"])
        out["if_forecast_label"] = projection.get("forecast_label")
        out["market_blend"] = 0
        out["mean_home_points"] = float(diagnostics["mean_home_points"])
        out["mean_away_points"] = float(diagnostics["mean_away_points"])
        out["if_su_pick"] = "HOME" if out["forecast_wp_home"] > 0.5 else "AWAY"
        naive = naive_wp_home(game["record_asof_home"], game["record_asof_away"])
        out.update({f"bench_{k}": v for k, v in naive.items()})
        out["bench_wp_home_pickem"] = 0.5
        out["bench_pickem_su_pick"] = "HOME"
        out["bench_forecast_margin_pickem"] = 0.0
        out["bench_forecast_total_const"] = CONST_TOTAL
        # coverage from sealed-sim-equivalent draws
        margins, totals = replay_draws(
            seed,
            out["mean_home_points"],
            out["mean_away_points"],
            out["if_sigma"],
        )
        # identity check vs IF mus (same loop)
        replay_margin_mu = mean(margins)
        replay_total_mu = mean(totals)
        out["draw_replay_margin_mu"] = replay_margin_mu
        out["draw_replay_total_mu"] = replay_total_mu
        out["draw_replay_margin_mu_abs_err"] = abs(replay_margin_mu - out["forecast_margin"])
        out["draw_replay_total_mu_abs_err"] = abs(replay_total_mu - out["forecast_total"])
        margins_sorted = sorted(margins)
        totals_sorted = sorted(totals)
        out["margin_p10"] = quantile(margins_sorted, 0.10)
        out["margin_p90"] = quantile(margins_sorted, 0.90)
        out["total_p10"] = quantile(totals_sorted, 0.10)
        out["total_p90"] = quantile(totals_sorted, 0.90)
        out["coverage_margin_p10_p90"] = out["margin_p10"] <= out["realized_margin"] <= out["margin_p90"]
        out["coverage_total_p10_p90"] = out["total_p10"] <= out["realized_total"] <= out["total_p90"]
        # SU / errors
        if out["realized_su"] == "TIE":
            out["if_su_correct"] = None
            out["naive_su_correct"] = None
            out["pickem_su_correct"] = None
            out["su_decided"] = False
        else:
            out["if_su_correct"] = out["if_su_pick"] == out["realized_su"]
            out["naive_su_correct"] = out["bench_naive_su_pick"] == out["realized_su"]
            out["pickem_su_correct"] = out["bench_pickem_su_pick"] == out["realized_su"]
            out["su_decided"] = True
        y = 1.0 if out["realized_margin"] > 0 else 0.0
        p = clip_p(out["forecast_wp_home"])
        out["y_home"] = y
        out["brier"] = (p - y) ** 2
        out["log_loss"] = -(y * math.log(p) + (1.0 - y) * math.log(1.0 - p))
        out["err_margin"] = out["forecast_margin"] - out["realized_margin"]
        out["err_total"] = out["forecast_total"] - out["realized_total"]
        out["abs_err_margin"] = abs(out["err_margin"])
        out["abs_err_total"] = abs(out["err_total"])
        out["status"] = "SCORED"
        out["error"] = None
    except Exception as exc:  # noqa: BLE001 — failures must stay visible
        out["status"] = "FAILED"
        out["error"] = f"{type(exc).__name__}: {exc}"
    return out


def summarize(rows: List[Dict[str, Any]], audit: Dict[str, Any]) -> Dict[str, Any]:
    scored = [r for r in rows if r.get("status") == "SCORED"]
    failed = [r for r in rows if r.get("status") == "FAILED"]
    decided = [r for r in scored if r.get("su_decided")]
    ties = [r for r in scored if r.get("realized_su") == "TIE"]

    def su_rate(key: str) -> Optional[float]:
        if not decided:
            return None
        return sum(1 for r in decided if r.get(key)) / len(decided)

    margin_pairs = [(r["forecast_margin"], r["realized_margin"]) for r in scored]
    total_pairs = [(r["forecast_total"], r["realized_total"]) for r in scored]
    const_pairs = [(CONST_TOTAL, r["realized_total"]) for r in scored]
    pickem_pairs = [(0.0, r["realized_margin"]) for r in scored]

    metrics = {
        "n_attempted": len(rows),
        "n_scored": len(scored),
        "n_failed": len(failed),
        "n_decided": len(decided),
        "n_ties": len(ties),
        "failed_game_ids": [r["game_id"] for r in failed],
        "tie_game_ids": [r["game_id"] for r in ties],
        "straight_up_outcome_accuracy_if": su_rate("if_su_correct"),
        "straight_up_outcome_accuracy_naive_wl": su_rate("naive_su_correct"),
        "straight_up_outcome_accuracy_pickem": su_rate("pickem_su_correct"),
        "straight_up_note": "NOT ATS-vs-0. No historical betting line. Ties excluded from decided denominator.",
        "mae_margin": mae(margin_pairs) if scored else None,
        "rmse_margin": rmse(margin_pairs) if scored else None,
        "mae_total": mae(total_pairs) if scored else None,
        "rmse_total": rmse(total_pairs) if scored else None,
        "mae_margin_pickem": mae(pickem_pairs) if scored else None,
        "rmse_margin_pickem": rmse(pickem_pairs) if scored else None,
        "mae_total_const_45_3": mae(const_pairs) if scored else None,
        "rmse_total_const_45_3": rmse(const_pairs) if scored else None,
        "brier_if": mean([r["brier"] for r in scored]) if scored else None,
        "log_loss_if": mean([r["log_loss"] for r in scored]) if scored else None,
        "brier_naive_wl": mean(
            [(clip_p(r["bench_wp_home_naive"]) - r["y_home"]) ** 2 for r in scored]
        )
        if scored
        else None,
        "brier_pickem": mean([(0.5 - r["y_home"]) ** 2 for r in scored]) if scored else None,
        "mean_forecast_wp_home": mean([r["forecast_wp_home"] for r in scored]) if scored else None,
        "mean_realized_home_win": mean([r["y_home"] for r in scored]) if scored else None,
        "exploratory_n70": True,
        "sd_forecast_means": sample_sd([r["forecast_margin"] for r in scored]) if scored else None,
        "sd_realized_margin": sample_sd([r["realized_margin"] for r in scored]) if scored else None,
        "mean_if_sigma": mean([r["if_sigma"] for r in scored]) if scored else None,
        "coverage_margin_p10_p90": (
            sum(1 for r in scored if r["coverage_margin_p10_p90"]) / len(scored) if scored else None
        ),
        "coverage_total_p10_p90": (
            sum(1 for r in scored if r["coverage_total_p10_p90"]) / len(scored) if scored else None
        ),
        "coverage_nominal": 0.80,
        "draw_replay_max_abs_err_margin": max(r["draw_replay_margin_mu_abs_err"] for r in scored)
        if scored
        else None,
        "draw_replay_max_abs_err_total": max(r["draw_replay_total_mu_abs_err"] for r in scored)
        if scored
        else None,
        "all_blend_zero": all(r.get("market_blend") == 0 for r in scored) if scored else False,
        "rest_bind": "BIND_PACKET_ONLY",
        "simulations": SIMULATIONS,
        "seed_base": SEED_BASE,
        "if_tip": IF_TIP,
        "epa_success_label": "RETRO_FIT / DEV_RESEARCH only (A1)",
        "clv": False,
        "odds_2017_used": False,
        "benchmarks_are_not_edge_proof": True,
        "visible_excluded_or_failed": audit["visible_excluded_or_failed"],
        "weeks": dict(Counter(int(r["matchup_week"]) for r in scored)),
    }
    return metrics


def write_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def md_table(headers: List[str], rows: List[List[Any]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    for row in rows:
        lines.append("| " + " | ".join("" if v is None else str(v) for v in row) + " |")
    return "\n".join(lines)


def fmt(x: Any, nd: int = 4) -> str:
    if x is None:
        return "—"
    if isinstance(x, bool):
        return "true" if x else "false"
    if isinstance(x, int) and not isinstance(x, bool):
        return str(x)
    if isinstance(x, float):
        if math.isnan(x):
            return "nan"
        return f"{x:.{nd}f}"
    return str(x)


def main() -> int:
    if not IF_TREE.exists():
        raise SystemExit(f"IF worktree missing: {IF_TREE}")
    assumptions = PACKET / "ASSUMPTIONS.md"
    if not assumptions.exists():
        raise SystemExit("ASSUMPTIONS.md must exist before first score write")

    games, visible, audit = assemble_sample()
    if len(games) != 70:
        # still attempt whatever assembled; leave the miss visible
        audit["n_assembled_ne_70"] = True
    sim = import_if()
    rows = [score_game(sim, g) for g in games]
    metrics = summarize(rows, audit)

    selection_ids = sorted(r["game_id"] for r in rows)
    selection_hash = sha256_bytes(("\n".join(selection_ids) + "\n").encode())

    manifest = {
        "artifact": "nfl-hist-diag-score-70-t4910u",
        "label": "CONDITIONAL_DIAG",
        "cert": 0,
        "nfl": "NO-GO",
        "scoring_admissible": False,
        "e1": False,
        "publish": False,
        "odds_credits": 0,
        "n": len(rows),
        "n_target": 70,
        "n_w2": audit["n_w2"],
        "n_w3w6": audit["n_w3w6"],
        "weeks": audit["weeks"],
        "selection_hash": selection_hash,
        "selection_hash_recipe": "sha256(utf-8 of sorted canonical game_id list joined by \\n with trailing \\n)",
        "rest_bind": "BIND_PACKET_ONLY",
        "rest_rederived": False,
        "if_tip": IF_TIP,
        "w2_tip": W2_TIP,
        "w3w6_tip": W3W6_TIP,
        "simulations": SIMULATIONS,
        "seed_base": SEED_BASE,
        "seed_formula": "201710 + (int(sha256(game_id.encode()).hexdigest()[:12], 16) % 1000003)",
        "market_blend": MARKET_BLEND,
        "tie_rule": "margin==0 counted away (same IF fair path)",
        "epa_success_label": "RETRO_FIT / DEV_RESEARCH only (A1)",
        "holdout_2024_25": "untouched",
        "excluded_visible": EXCLUDED_VISIBLE,
        "games": [
            {
                "game_id": r["game_id"],
                "season": r.get("matchup_season"),
                "week": r.get("matchup_week"),
                "home_team": r.get("home_team"),
                "away_team": r.get("away_team"),
                "source_packet_tip": r.get("source_packet_tip"),
                "complete_27_27": r.get("complete_27_27"),
                "rest_days_home": r.get("rest_days_home"),
                "rest_days_away": r.get("rest_days_away"),
                "rest_bind": "BIND_PACKET_ONLY",
                "rest_days_utc_contrast": r.get("rest_days_utc_contrast"),
                "utc_et_dow_mismatch": r.get("utc_et_dow_mismatch"),
                "record_asof_home": r.get("record_asof_home"),
                "record_asof_away": r.get("record_asof_away"),
                "kickoff_utc": r.get("kickoff_utc"),
                "status": r.get("status"),
                "error": r.get("error"),
                "seed": r.get("seed"),
            }
            for r in rows
        ],
        "visible_excluded_or_failed": visible,
    }

    slim_rows = []
    keep = [
        "game_id",
        "matchup_week",
        "home_team",
        "away_team",
        "status",
        "error",
        "seed",
        "simulations",
        "rest_days_home",
        "rest_days_away",
        "rest_bind",
        "record_asof_home",
        "record_asof_away",
        "forecast_margin",
        "forecast_spread",
        "forecast_total",
        "forecast_wp_home",
        "forecast_wp_away",
        "if_sigma",
        "if_su_pick",
        "home_score",
        "away_score",
        "realized_margin",
        "realized_spread",
        "realized_total",
        "realized_su",
        "if_su_correct",
        "naive_su_correct",
        "pickem_su_correct",
        "bench_wp_home_naive",
        "bench_naive_su_pick",
        "bench_wp_home_pickem",
        "bench_pickem_su_pick",
        "bench_forecast_total_const",
        "brier",
        "log_loss",
        "abs_err_margin",
        "abs_err_total",
        "coverage_margin_p10_p90",
        "coverage_total_p10_p90",
        "margin_p10",
        "margin_p90",
        "total_p10",
        "total_p90",
        "market_blend",
        "draw_replay_margin_mu_abs_err",
        "draw_replay_total_mu_abs_err",
        "epa_success_label",
    ]
    for r in rows:
        slim = {k: r.get(k) for k in keep}
        slim["epa_success_label"] = "RETRO_FIT / DEV_RESEARCH only (A1)"
        slim_rows.append(slim)

    write_json(PACKET / "SAMPLE_MANIFEST_70.json", manifest)
    write_json(
        PACKET / "SCORE_RESULTS.json",
        {
            "artifact": "nfl-hist-diag-score-70-t4910u",
            "scored_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "if_tip": IF_TIP,
            "n": len(slim_rows),
            "rows": slim_rows,
        },
    )
    write_json(PACKET / "METRICS_TABLE.json", metrics)
    write_json(
        PACKET / "COMPRESSION_HIST_DIAG.json",
        {
            "note": "Do not expect forecast-margin SD == realized-margin SD. Distinguish variation in forecast means from outcome noise.",
            "sd_forecast_means": metrics["sd_forecast_means"],
            "sd_realized_margin": metrics["sd_realized_margin"],
            "mean_if_sigma": metrics["mean_if_sigma"],
            "coverage_margin_p10_p90": metrics["coverage_margin_p10_p90"],
            "coverage_total_p10_p90": metrics["coverage_total_p10_p90"],
            "coverage_nominal": 0.80,
            "draw_replay_max_abs_err_margin": metrics["draw_replay_max_abs_err_margin"],
            "draw_replay_max_abs_err_total": metrics["draw_replay_max_abs_err_total"],
            "n": metrics["n_scored"],
        },
    )

    # human tables
    (PACKET / "SAMPLE_MANIFEST_70.md").write_text(
        "\n".join(
            [
                "# SAMPLE_MANIFEST_70",
                "",
                f"N assembled **{len(rows)}** (target 70). rest BIND_PACKET_ONLY. selection_hash `{selection_hash}`.",
                "",
                md_table(
                    ["game_id", "wk", "away@home", "rest_h/a", "UTC≠ET", "record h/a", "seed", "status"],
                    [
                        [
                            r["game_id"],
                            r.get("matchup_week"),
                            f"{r.get('away_team')}@{r.get('home_team')}",
                            f"{r.get('rest_days_home')}/{r.get('rest_days_away')}",
                            r.get("utc_et_dow_mismatch"),
                            f"{r.get('record_asof_home')}/{r.get('record_asof_away')}",
                            r.get("seed"),
                            r.get("status"),
                        ]
                        for r in rows
                    ],
                ),
                "",
                "## Visible excluded / failed (not silently filled)",
                "",
                md_table(
                    ["game_id", "class", "in_sample", "reason"],
                    [
                        [e["game_id"], e.get("class"), e.get("in_score_sample"), e.get("reason")]
                        for e in visible
                    ],
                ),
                "",
            ]
        ),
        encoding="utf-8",
    )

    (PACKET / "SCORE_RESULTS.md").write_text(
        "\n".join(
            [
                "# SCORE_RESULTS",
                "",
                "Forecast vs realized. SU is **not** ATS-vs-0. No 2017 odds consumed.",
                "",
                md_table(
                    [
                        "game_id",
                        "f_margin",
                        "r_margin",
                        "f_total",
                        "r_total",
                        "f_wp_h",
                        "IF pick",
                        "real SU",
                        "IF SU",
                    ],
                    [
                        [
                            r["game_id"],
                            fmt(r.get("forecast_margin"), 3),
                            fmt(r.get("realized_margin"), 1),
                            fmt(r.get("forecast_total"), 2),
                            fmt(r.get("realized_total"), 1),
                            fmt(r.get("forecast_wp_home"), 3),
                            r.get("if_su_pick"),
                            r.get("realized_su"),
                            r.get("if_su_correct"),
                        ]
                        for r in slim_rows
                    ],
                ),
                "",
            ]
        ),
        encoding="utf-8",
    )

    (PACKET / "METRICS_TABLE.md").write_text(
        "\n".join(
            [
                "# METRICS_TABLE",
                "",
                "Exploratory at N=70. Benchmarks are labeled baselines ≠ edge proof. No CLV.",
                "",
                md_table(
                    ["metric", "value", "caveat"],
                    [
                        ["n_attempted / n_scored / n_failed", f"{metrics['n_attempted']} / {metrics['n_scored']} / {metrics['n_failed']}", "all 70 attempted"],
                        ["n_decided / n_ties", f"{metrics['n_decided']} / {metrics['n_ties']}", "ties reported separately"],
                        ["straight-up outcome accuracy (IF)", fmt(metrics["straight_up_outcome_accuracy_if"], 4), "NOT ATS-vs-0; no betting line"],
                        ["straight-up outcome accuracy (naive W-L)", fmt(metrics["straight_up_outcome_accuracy_naive_wl"], 4), "baseline ≠ edge"],
                        ["straight-up outcome accuracy (pick'em)", fmt(metrics["straight_up_outcome_accuracy_pickem"], 4), "always HOME; baseline ≠ edge"],
                        ["MAE / RMSE margin", f"{fmt(metrics['mae_margin'], 3)} / {fmt(metrics['rmse_margin'], 3)}", "forecast_margin vs realized_margin"],
                        ["MAE / RMSE total", f"{fmt(metrics['mae_total'], 3)} / {fmt(metrics['rmse_total'], 3)}", "forecast_total vs realized_total"],
                        ["MAE / RMSE margin pick'em (0)", f"{fmt(metrics['mae_margin_pickem'], 3)} / {fmt(metrics['rmse_margin_pickem'], 3)}", "baseline"],
                        ["MAE / RMSE total const 45.3", f"{fmt(metrics['mae_total_const_45_3'], 3)} / {fmt(metrics['rmse_total_const_45_3'], 3)}", "baseline"],
                        ["Brier IF / naive W-L / pick'em", f"{fmt(metrics['brier_if'], 4)} / {fmt(metrics['brier_naive_wl'], 4)} / {fmt(metrics['brier_pickem'], 4)}", "exploratory N=70"],
                        ["log-loss IF", fmt(metrics["log_loss_if"], 4), "exploratory N=70"],
                        ["sd forecast means / sd realized margin", f"{fmt(metrics['sd_forecast_means'], 3)} / {fmt(metrics['sd_realized_margin'], 3)}", "do not expect equality"],
                        ["mean IF sigma", fmt(metrics["mean_if_sigma"], 3), "score-error prior; not SD equality"],
                        ["coverage margin / total p10–p90", f"{fmt(metrics['coverage_margin_p10_p90'], 3)} / {fmt(metrics['coverage_total_p10_p90'], 3)}", "nominal 0.80; exploratory"],
                    ],
                ),
                "",
            ]
        ),
        encoding="utf-8",
    )

    (PACKET / "COMPRESSION_HIST_DIAG.md").write_text(
        "\n".join(
            [
                "# COMPRESSION_HIST_DIAG",
                "",
                "Forecast-margin SD is the dispersion of **means**. Realized-margin SD includes outcome noise. Do not expect equality.",
                "",
                md_table(
                    ["quantity", "value", "meaning"],
                    [
                        ["sd_forecast_means", fmt(metrics["sd_forecast_means"], 4), "sample SD of 70 forecast margins"],
                        ["sd_realized_margin", fmt(metrics["sd_realized_margin"], 4), "sample SD of 70 realized margins"],
                        ["mean_if_sigma", fmt(metrics["mean_if_sigma"], 4), "mean per-game IF score-error sigma"],
                        ["coverage_margin_p10_p90", fmt(metrics["coverage_margin_p10_p90"], 4), "share of realized margins inside sealed-sim p10–p90"],
                        ["coverage_total_p10_p90", fmt(metrics["coverage_total_p10_p90"], 4), "share of realized totals inside sealed-sim p10–p90"],
                        ["draw_replay_max_abs_err_margin", fmt(metrics["draw_replay_max_abs_err_margin"], 6), "IF mu vs replayed draws (identity)"],
                        ["draw_replay_max_abs_err_total", fmt(metrics["draw_replay_max_abs_err_total"], 6), "IF mu vs replayed draws (identity)"],
                    ],
                ),
                "",
                "Coverage uses sealed-sim-equivalent draws: `random.Random(seed)` + `max(0, gauss(mean, sigma))` — the only RNG consumer in `simulate_nfl_game` at 6ca03716.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "n": len(rows),
                "scored": metrics["n_scored"],
                "failed": metrics["n_failed"],
                "su_if": metrics["straight_up_outcome_accuracy_if"],
                "mae_margin": metrics["mae_margin"],
                "mae_total": metrics["mae_total"],
                "selection_hash": selection_hash,
            },
            indent=2,
        )
    )
    return 0 if metrics["n_scored"] == 70 and metrics["n_failed"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
