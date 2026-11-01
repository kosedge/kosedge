#!/usr/bin/env python3
"""t5044u Phase 4 — emit research.q2s.* for W7–W17 (new research copy).

margin_mu_q2s = 0.5 * IF.margin_mu + 0.5 * q2_pm_new
w=0.5 predeclared. Fit 70db070d excludes 2017. Examined 70 never pooled.
Does not rewrite emit_q2_asof_sidecar.py or #685 artifacts.
Does not look / bootstrap / join realized for metrics.
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any, Mapping

PHASE4 = Path(__file__).resolve().parent
PACKET = PHASE4.parent
if str(PHASE4) not in sys.path:
    sys.path.insert(0, str(PHASE4))

from q2pb.constants import (  # noqa: E402
    DEV_SEASONS,
    HISTORY_ONLY_SEASONS,
    SEALED_SEASONS,
    TIP_GAMES,
)
from q2pb.data import (  # noqa: E402
    DataGuardError,
    Game,
    load_games,
    load_outcomes_score_only,
    sha256_file,
    verify_games_pin,
)
from q2pb.metrics import asof_wl_diff  # noqa: E402
from q2pb.strength import asof_for_targets, assert_asof_leakage  # noqa: E402
from q2s.blend import Q2S_WEIGHT, Q2S_WEIGHT_NOTE, BlendRefuse, margin_mu_q2s  # noqa: E402
from q2s.coverage import CoverageRefuse, prove_fit_exclusion  # noqa: E402
from score_if_w7w17 import (  # noqa: E402
    EXAMINED_70,
    IF_TIP,
    MATRIX_SHA256,
    SEALED_T2,
    ScoreRefuse,
)

SEALED_A_Q2 = 2.5637441292077354
SEALED_B_Q2 = 1.660624056183471
SEALED_LAM = 20.0
SEALED_REGRESS_FRAC = 0.5
SEALED_FIT_SHA = "70db070dad3fcdb4d4ff165ba09b7840c173c232a71c8fcd670ba9c3c0bc5571"
SEALED_CONFIG_SHA = "aa2b47b3f0b504f39b785d0cb6fc2918bb7a36fb5a22242e80fb37707b790d49"
SEALED_ASOF_RULE = "cf514078"
SEALED_GAMES_PIN = "4fe1cdd7"
SEALED_GAMES_SHA = "4fe1cdd7f2eb616103ee6107e6a5cb0d5280f8006be420b606af0995351abef8"
SEALED_OUTCOMES_SHA = "50bda875daa8bf1aadd56dd0a3bc19f1bb52dafe42b6a9c921a5816c7d7dc081"
SEALED_FROZEN_MD_SHA = "28c582a1b2b9ac49fcb4b9ea2c3ab264fd81786e6332669db9e071b2995c4f94"
TARGET_SEASON = 2017
RETRO_LABEL = "RETRO_FIT / DEV_RESEARCH"

DEFAULT_GAMES = PACKET / "pins" / "games_4fe1cdd7.csv"
DEFAULT_OUTCOMES = PACKET / "pins" / "outcomes_2013_2022_score_only.csv"
DEFAULT_FROZEN = PHASE4 / "frozen" / "FROZEN_CONFIG_Q2PB_t5009u.json"
DEFAULT_FROZEN_MD = PHASE4 / "frozen" / "FROZEN_CONFIG_Q2PB_t5009u.md"
DEFAULT_IF = PHASE4 / "artifacts" / "IF_MUS_W7W17.json"
DEFAULT_OUT = PHASE4 / "artifacts" / "q2s_rows_w7w17.json"

FORBIDDEN_OUTPUT_KEYS = (
    "offense_index_home",
    "offense_index_away",
    "defense_index_home",
    "defense_index_away",
    "market_blend",
    "independent_fair",
    "trailing_offense",
    "win_prob",
    "ats_prob",
    "ou_prob",
    "candidate_wp",
    "realized_margin",
    "realized_total",
    "home_score",
    "away_score",
)

Q2S_FIELDS = (
    "margin_mu_q2s",
    "w",
    "w_note",
    "q2_pm_new",
    "q2_home_s",
    "q2_away_s",
    "q2_rating_diff",
    "q2_hfa",
    "q2_n_asof_games",
    "q2_asof_wl_diff",
    "q2_fit_sha",
    "q2_config_sha",
    "q2_asof_rule",
    "q2_games_pin",
)


class EmitRefuse(RuntimeError):
    pass


def _isfinite_number(value: Any) -> bool:
    if isinstance(value, bool) or value is None:
        return False
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def load_frozen(path: Path, md_path: Path) -> dict[str, Any]:
    frozen = json.loads(path.read_text())
    if not isinstance(frozen, dict):
        raise EmitRefuse("frozen config is not an object")
    fit_sha = str(frozen.get("fit_object_sha256") or "")
    config_sha = str(frozen.get("config_sha256") or "")
    if fit_sha != SEALED_FIT_SHA:
        raise EmitRefuse("frozen fit_object_sha256 != 70db070d")
    if config_sha != SEALED_CONFIG_SHA:
        raise EmitRefuse("frozen config_sha256 != aa2b47b3")
    if str(frozen.get("tip_asof") or "") != SEALED_ASOF_RULE:
        raise EmitRefuse("tip_asof != cf514078")
    if str(frozen.get("tip_games") or "") != TIP_GAMES:
        raise EmitRefuse("frozen tip_games != 4fe1cdd7")
    if float(frozen["lam"]) != SEALED_LAM or float(frozen["regress_frac"]) != SEALED_REGRESS_FRAC:
        raise EmitRefuse("frozen λ/r != 20.0 / 0.5")
    if float(frozen["a_q2"]) != SEALED_A_Q2 or float(frozen["b_q2"]) != SEALED_B_Q2:
        raise EmitRefuse("frozen a_q2/b_q2 != sealed DEV OLS")
    md_sha = sha256_file(md_path)
    if md_sha != SEALED_FROZEN_MD_SHA:
        raise EmitRefuse(f"frozen md sha {md_sha} != 28c582a1")
    raw_priors = frozen.get("season_end_ratings") or {}
    for key in raw_priors:
        if int(key) >= 2017:
            raise EmitRefuse("season_end_ratings includes 2017+ (fit leak)")
    return frozen


def load_if_mus(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text())
    if int(payload.get("n_scored") or 0) != 141:
        raise EmitRefuse(f"IF n_scored {payload.get('n_scored')} != 141")
    if str(payload.get("if_tip") or "") != IF_TIP:
        raise EmitRefuse("IF tip != 6ca03716")
    if str(payload.get("matrix_sha256") or "") != MATRIX_SHA256:
        raise EmitRefuse("IF mus matrix pin != b56be146")
    if payload.get("look_run") or payload.get("realized_joined") or payload.get("opened_1ee90fac"):
        raise EmitRefuse("IF mus claims look / realized / gated-index open")
    rows = list(payload.get("rows") or [])
    if len(rows) != 141:
        raise EmitRefuse("IF rows != 141")
    ids = [str(r["game_id"]) for r in rows]
    if set(ids) & EXAMINED_70:
        raise EmitRefuse("examined 70 present in IF rows")
    if set(ids) & SEALED_T2:
        raise EmitRefuse("T2 ids present in IF rows")
    if any(r.get("status") != "SCORED" for r in rows):
        raise EmitRefuse("IF row status != SCORED")
    sealed = list(payload.get("sealed_t2_not_scored") or [])
    if {p["game_id"] for p in sealed} != SEALED_T2:
        raise EmitRefuse("IF sealed T2 set mismatch")
    return payload


def _join_target(meta: Mapping[str, Any], by_id: Mapping[str, Game], by_key: Mapping[tuple, Game]) -> Game:
    gid = str(meta["game_id"])
    key = (int(meta["season"]), int(meta["week"]), str(meta["home_team"]), str(meta["away_team"]))
    game = by_id.get(gid) or by_key.get(key)
    if game is None:
        raise EmitRefuse(f"join failure: {gid} not in games pin")
    if (game.season, game.week, game.home, game.away) != key:
        raise EmitRefuse(f"Game.key mismatch under {gid}")
    return game


def _q2_row(feat, history, frozen: Mapping[str, Any], baseline: Mapping[str, Any]) -> dict[str, Any]:
    game = feat.game
    wl = asof_wl_diff(game, history)
    q2_pm = float(frozen["a_q2"]) + float(frozen["b_q2"]) * float(feat.rating_diff)
    if_mu = float(baseline["if_margin_mu"])
    try:
        blended = margin_mu_q2s(if_mu, q2_pm)
    except BlendRefuse as exc:
        raise EmitRefuse(str(exc)) from exc
    research_q2s = {
        "margin_mu_q2s": blended,
        "w": Q2S_WEIGHT,
        "w_note": Q2S_WEIGHT_NOTE,
        "q2_pm_new": q2_pm,
        "q2_home_s": float(feat.home_s),
        "q2_away_s": float(feat.away_s),
        "q2_rating_diff": float(feat.rating_diff),
        "q2_hfa": float(feat.hfa),
        "q2_n_asof_games": int(feat.n_asof_games),
        "q2_asof_wl_diff": float(wl),
        "q2_fit_sha": SEALED_FIT_SHA,
        "q2_config_sha": SEALED_CONFIG_SHA,
        "q2_asof_rule": SEALED_ASOF_RULE,
        "q2_games_pin": SEALED_GAMES_PIN,
        "extra_hfa": 0.0,
        "formula": "0.5*IF.margin_mu + 0.5*q2_pm_new",
    }
    baseline_block = {
        "if_margin_mu": if_mu,
        "if_total_mu": float(baseline["if_total_mu"]),
        "if_sigma": float(baseline["if_sigma"]),
        "if_forecast_wp_home": baseline.get("if_forecast_wp_home"),
        "if_forecast_wp_away": baseline.get("if_forecast_wp_away"),
        "if_tip": IF_TIP,
        "unchanged": True,
        "mc_draws_unchanged": True,
        "no_candidate_probabilities": True,
        "realized_joined": False,
    }
    extra = (set(research_q2s) | set(baseline_block)) & set(FORBIDDEN_OUTPUT_KEYS)
    if extra:
        raise EmitRefuse(f"forbidden output keys: {sorted(extra)}")
    for name in Q2S_FIELDS:
        if name not in research_q2s:
            raise EmitRefuse(f"missing research.q2s.{name}")
        if name in {"w_note", "q2_fit_sha", "q2_config_sha", "q2_asof_rule", "q2_games_pin"}:
            continue
        if name == "q2_n_asof_games":
            if not isinstance(research_q2s[name], int) or research_q2s[name] < 0:
                raise EmitRefuse("q2_n_asof_games missing / non-finite")
            continue
        if not _isfinite_number(research_q2s[name]):
            raise EmitRefuse(f"missing field research.q2s.{name}")
    expected_pm = SEALED_A_Q2 + SEALED_B_Q2 * float(feat.rating_diff)
    if not math.isclose(q2_pm, expected_pm, rel_tol=0.0, abs_tol=1e-12):
        raise EmitRefuse("q2_pm_new != sealed a_q2 + b_q2 · rating_diff")
    expected_blend = Q2S_WEIGHT * if_mu + Q2S_WEIGHT * q2_pm
    if not math.isclose(blended, expected_blend, rel_tol=0.0, abs_tol=1e-12):
        raise EmitRefuse("margin_mu_q2s != 0.5*IF + 0.5*q2_pm_new")
    return {
        "game_id": game.game_id,
        "season": int(game.season),
        "week": int(game.week),
        "home": game.home,
        "away": game.away,
        "kickoff_utc": game.kickoff_utc.isoformat().replace("+00:00", "Z"),
        "label": RETRO_LABEL,
        "cert": 0,
        "baseline": baseline_block,
        "research": {"q2s": research_q2s},
    }


def emit_adapter(
    *,
    if_path: Path = DEFAULT_IF,
    games_path: Path = DEFAULT_GAMES,
    outcomes_path: Path = DEFAULT_OUTCOMES,
    frozen_path: Path = DEFAULT_FROZEN,
    frozen_md_path: Path = DEFAULT_FROZEN_MD,
    out_path: Path = DEFAULT_OUT,
    write_files: bool = True,
) -> dict[str, Any]:
    games_sha = verify_games_pin(games_path)
    if games_sha != SEALED_GAMES_SHA:
        raise EmitRefuse("games.csv full sha != 4fe1cdd7")
    outcomes_sha = sha256_file(outcomes_path)
    if outcomes_sha != SEALED_OUTCOMES_SHA:
        raise EmitRefuse("outcomes sha != 50bda875")
    frozen = load_frozen(frozen_path, frozen_md_path)
    if_payload = load_if_mus(if_path)
    try:
        fit_exclusion = prove_fit_exclusion(if_payload["rows"], frozen)
    except CoverageRefuse as exc:
        raise EmitRefuse(str(exc)) from exc

    hist_seasons = tuple(s for s in range(2013, TARGET_SEASON + 1) if s not in SEALED_SEASONS)
    if hist_seasons != (2013, 2014, 2015, 2016, 2017):
        raise EmitRefuse(f"hist seasons {hist_seasons} != 2013–2017")
    if HISTORY_ONLY_SEASONS != (2017,) or DEV_SEASONS != (2013, 2014, 2015, 2016):
        raise EmitRefuse("DEV / HISTORY_ONLY constants drifted")
    try:
        outcomes = load_outcomes_score_only(outcomes_path, hist_seasons)
        history = load_games(
            games_path, outcomes, hist_seasons, phase="q2s_w7w17_offline_asof"
        )
    except DataGuardError as exc:
        raise EmitRefuse(str(exc)) from exc

    by_id = {g.game_id: g for g in history if g.game_id}
    by_key = {g.key: g for g in history}
    target_games: list[Game] = []
    baseline_by_id: dict[str, dict[str, Any]] = {}
    for meta in if_payload["rows"]:
        game = _join_target(meta, by_id, by_key)
        if game.season != TARGET_SEASON:
            raise EmitRefuse(f"{meta['game_id']} season != 2017")
        target_games.append(game)
        baseline_by_id[game.game_id] = meta

    persist = {
        int(k): {str(t): float(v) for t, v in ratings.items()}
        for k, ratings in (frozen.get("season_end_ratings") or {}).items()
    }
    if any(s >= 2017 for s in persist):
        raise EmitRefuse("persist season_end includes 2017+")
    feats = asof_for_targets(
        history,
        target_games,
        lam=SEALED_LAM,
        regress_frac=SEALED_REGRESS_FRAC,
        persist_season_end=persist,
    )
    assert_asof_leakage(history, feats)
    if len(feats) != 141:
        raise EmitRefuse(f"as-of feats {len(feats)} != 141")

    rows = []
    for feat in feats:
        base = baseline_by_id[feat.game.game_id]
        rows.append(_q2_row(feat, history, frozen, base))
    rows.sort(key=lambda r: (r["week"], r["game_id"]))
    if {r["game_id"] for r in rows} & EXAMINED_70:
        raise EmitRefuse("examined 70 pooled into emit")

    payload = {
        "ticket": "t5044u",
        "phase": 4,
        "label": RETRO_LABEL,
        "cert": 0,
        "nfl": "NO-GO",
        "owner_clear_tip": "12763c08",
        "cos_accept_tip": "adbcf11d",
        "formula": "research.q2s.margin_mu_q2s = 0.5*IF.margin_mu + 0.5*q2_pm_new",
        "w": Q2S_WEIGHT,
        "w_note": Q2S_WEIGHT_NOTE,
        "if_tip": IF_TIP,
        "if_mus_sha256": sha256_file(if_path),
        "matrix_sha256": MATRIX_SHA256,
        "fit_sha": SEALED_FIT_SHA,
        "config_sha": SEALED_CONFIG_SHA,
        "asof_rule": SEALED_ASOF_RULE,
        "games_sha256": games_sha,
        "outcomes_sha256": outcomes_sha,
        "n_emitted": len(rows),
        "n_sealed_t2_not_scored": 24,
        "sealed_t2_not_scored": if_payload["sealed_t2_not_scored"],
        "fit_exclusion": fit_exclusion,
        "look_run": False,
        "bootstrap_run": False,
        "realized_joined_for_look": False,
        "opened_1ee90fac": False,
        "examined_70_pooled": False,
        "new_index_formula": False,
        "rows": rows,
    }
    if write_files:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        digest = sha256_file(out_path)
        (out_path.with_suffix(".json.sha256")).write_text(f"{digest}  {out_path.name}\n")
        payload["path"] = str(out_path.relative_to(PACKET))
        payload["sha256"] = digest
    return payload


def main() -> int:
    try:
        payload = emit_adapter()
    except (EmitRefuse, ScoreRefuse) as exc:
        print(f"EMIT_REFUSE: {exc}", file=sys.stderr)
        return 2
    print(
        json.dumps(
            {
                "ok": True,
                "n_emitted": payload["n_emitted"],
                "path": payload.get("path"),
                "sha256": payload.get("sha256"),
                "look_run": False,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
