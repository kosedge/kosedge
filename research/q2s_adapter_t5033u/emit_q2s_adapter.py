#!/usr/bin/env python3
"""t5033u — offline Layer-2 Q2 strength adapter (DEV_RESEARCH).

CERT=0 · NFL NO-GO · research-consumed only · DRAFT · do not merge/deploy/pub/bet.

Pattern: score_t4910u @ 6ca03716 (sealed caller — do NOT edit).
Generates 70 matching Q2 rows for the frozen 2017 REG manifest and emits
NEW research.q2s.* fields only:

    research.q2s.margin_mu_q2s = 0.5 * IF.margin_mu + 0.5 * q2_pm_new

Baseline IF.margin_mu / total_mu / sigma / MC draws stay UNCHANGED.
No candidate win/ATS/OU probabilities. No extra HFA.

Reuse keep symbols only: asof_for_targets, asof_wl_diff, assert_asof_leakage,
sealed a_q2/b_q2, load_games / verify_games_pin / load_outcomes_score_only.
Does not rewrite emit_q2_asof_sidecar.py.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from q2pb.constants import (  # noqa: E402
    DEV_SEASONS,
    DEV_WEEKS,
    HISTORY_ONLY_SEASONS,
    LABEL,
    SEALED_SEASONS,
    TIP_ASOF_KICKOFF,
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
from q2pb.strength import AsOfFeatures, asof_for_targets, assert_asof_leakage  # noqa: E402
from q2s.blend import Q2S_WEIGHT, Q2S_WEIGHT_NOTE, BlendRefuse, margin_mu_q2s  # noqa: E402
from q2s.coverage import CoverageRefuse, prove_fit_exclusion  # noqa: E402

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
SEALED_KEEP_COMMIT = "af6be4f59c63af222d02c39878266460a37d418a"
SEALED_SCORE_RESULTS_SHA = (
    "2b9f302e097183ef275185a4edb100ab206565a087ca1ce78dbe8062524e877a"
)
SEALED_IF_TIP = "6ca03716fe52930332d5ffba302c312a651980cc"
SEALED_N = 70
TARGET_SEASON = 2017
MAX_TARGET_SEASON = 2022
RETRO_LABEL = "RETRO_FIT / DEV_RESEARCH"

DEFAULT_GAMES = ROOT / "data" / "games_4fe1cdd7.csv"
DEFAULT_OUTCOMES = ROOT / "data" / "outcomes_2013_2022_score_only.csv"
DEFAULT_FROZEN = ROOT / "frozen" / "FROZEN_CONFIG_Q2PB_t5009u.json"
DEFAULT_FROZEN_MD = ROOT / "frozen" / "FROZEN_CONFIG_Q2PB_t5009u.md"
DEFAULT_SCORE = ROOT / "pins" / "t4910u" / "SCORE_RESULTS.json"
DEFAULT_MANIFEST = ROOT / "pins" / "t4910u" / "SAMPLE_MANIFEST_70.json"
DEFAULT_OUTDIR = ROOT / "artifacts"

ALLOWED_OPEN_NAMES = {
    "games_4fe1cdd7.csv",
    "outcomes_2013_2022_score_only.csv",
    "FROZEN_CONFIG_Q2PB_t5009u.json",
    "FROZEN_CONFIG_Q2PB_t5009u.md",
    "SCORE_RESULTS.json",
    "SAMPLE_MANIFEST_70.json",
}

FORBIDDEN_OUTPUT_KEYS = (
    "offense_index_home",
    "offense_index_away",
    "defense_index_home",
    "defense_index_away",
    "off_eff_h",
    "off_eff_a",
    "def_eff_h",
    "def_eff_a",
    "market_blend",
    "independent_fair",
    "trailing_offense",
    "trailing_defense",
    "win_prob",
    "ats_prob",
    "ou_prob",
    "candidate_wp",
    "candidate_sigma",
    "mc_draws",
)

# research.q2s.* only — never overwrite baseline IF mus.
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

BASELINE_FIELDS = (
    "if_margin_mu",
    "if_total_mu",
    "if_sigma",
    "if_forecast_wp_home",
    "if_forecast_wp_away",
    "realized_margin",
    "realized_total",
    "if_tip",
    "score_results_sha",
)


class AdapterRefuse(RuntimeError):
    """Fail-closed. Preserve missing coverage. No synthetic fallback."""


@dataclass
class PinReport:
    games_sha256: str
    outcomes_sha256: str
    frozen_md_sha256: str
    score_results_sha256: str
    manifest_sha256: str
    fit_sha: str
    config_sha: str
    asof_rule: str
    lam: float
    regress_frac: float
    a_q2: float
    b_q2: float
    season_end_ratings: dict[int, dict[str, float]]


@dataclass
class EmitResult:
    rows: list[dict[str, Any]]
    missing: list[dict[str, Any]]
    pins: PinReport
    fit_exclusion: dict[str, Any]
    artifacts: dict[str, str] = field(default_factory=dict)
    n_history: int = 0
    refused: bool = False
    blocker: str | None = None


def _isfinite_number(value: Any) -> bool:
    if isinstance(value, bool) or value is None:
        return False
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def _require_prefix(digest: str, prefix: str, label: str) -> None:
    if not str(digest).startswith(prefix):
        raise AdapterRefuse(f"{label} sha {digest[:8]} != required prefix {prefix}")


def _parse_kickoff(raw: Any) -> datetime:
    if isinstance(raw, datetime):
        dt = raw
    else:
        s = str(raw).strip()
        if not s:
            raise AdapterRefuse("non-finite / missing kickoff_utc")
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(s)
        except ValueError as exc:
            raise AdapterRefuse(f"non-finite kickoff_utc: {raw!r}") from exc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def load_json_object(path: Path) -> dict[str, Any]:
    if path.name not in ALLOWED_OPEN_NAMES:
        raise AdapterRefuse(f"refusing to open non-pin path {path}")
    with path.open() as f:
        payload = json.load(f)
    if not isinstance(payload, dict):
        raise AdapterRefuse(f"{path.name} is not a JSON object")
    return payload


def verify_pins(
    games_path: Path,
    outcomes_path: Path,
    frozen: Mapping[str, Any],
    frozen_md_path: Path,
    score_path: Path,
    manifest_path: Path,
) -> PinReport:
    if games_path.name != "games_4fe1cdd7.csv":
        raise AdapterRefuse(f"games path must be the 4fe1cdd7 pin, got {games_path.name}")
    if outcomes_path.name != "outcomes_2013_2022_score_only.csv":
        raise AdapterRefuse(f"outcomes path must be the 50bda875 extract, got {outcomes_path.name}")
    if score_path.name != "SCORE_RESULTS.json":
        raise AdapterRefuse("SCORE_RESULTS pin required")
    if manifest_path.name != "SAMPLE_MANIFEST_70.json":
        raise AdapterRefuse("SAMPLE_MANIFEST_70 pin required")

    games_sha = verify_games_pin(games_path)
    _require_prefix(games_sha, SEALED_GAMES_PIN, "games")
    if games_sha != SEALED_GAMES_SHA:
        raise AdapterRefuse("games.csv full sha256 != sealed 4fe1cdd7 object")

    outcomes_sha = sha256_file(outcomes_path)
    _require_prefix(outcomes_sha, "50bda875", "outcomes")
    if outcomes_sha != SEALED_OUTCOMES_SHA:
        raise AdapterRefuse("outcomes extract full sha256 != sealed 50bda875 object")

    score_sha = sha256_file(score_path)
    if score_sha != SEALED_SCORE_RESULTS_SHA:
        raise AdapterRefuse(
            f"SCORE_RESULTS sha {score_sha} != sealed 2b9f302e control"
        )

    manifest_sha = sha256_file(manifest_path)

    fit_sha = str(frozen.get("fit_object_sha256") or "")
    config_sha = str(frozen.get("config_sha256") or "")
    asof_rule = str(frozen.get("tip_asof") or "")
    _require_prefix(fit_sha, "70db070d", "fit")
    _require_prefix(config_sha, "aa2b47b3", "config")
    if fit_sha != SEALED_FIT_SHA:
        raise AdapterRefuse("frozen fit_object_sha256 != sealed 70db070d")
    if config_sha != SEALED_CONFIG_SHA:
        raise AdapterRefuse("frozen config_sha256 != sealed aa2b47b3")
    if asof_rule != SEALED_ASOF_RULE:
        raise AdapterRefuse(f"tip_asof {asof_rule!r} != {SEALED_ASOF_RULE}")
    if str(frozen.get("tip_games") or "") != TIP_GAMES:
        raise AdapterRefuse("frozen tip_games != 4fe1cdd7")

    try:
        lam = float(frozen["lam"])
        regress_frac = float(frozen["regress_frac"])
        a_q2 = float(frozen["a_q2"])
        b_q2 = float(frozen["b_q2"])
    except (KeyError, TypeError, ValueError) as exc:
        raise AdapterRefuse("frozen missing sealed lam/r/a_q2/b_q2") from exc
    if lam != SEALED_LAM or regress_frac != SEALED_REGRESS_FRAC:
        raise AdapterRefuse("frozen λ/r != sealed 20.0 / 0.5 (no retune)")
    if a_q2 != SEALED_A_Q2 or b_q2 != SEALED_B_Q2:
        raise AdapterRefuse("frozen a_q2/b_q2 != sealed DEV OLS (no refit)")

    frozen_md_sha = sha256_file(frozen_md_path)
    _require_prefix(frozen_md_sha, "28c582a1", "frozen md")

    raw_priors = frozen.get("season_end_ratings") or {}
    season_end: dict[int, dict[str, float]] = {}
    if isinstance(raw_priors, dict):
        for key, ratings in raw_priors.items():
            season = int(key)
            if season >= 2017:
                raise AdapterRefuse("season_end_ratings includes 2017+ (fit leak)")
            if not isinstance(ratings, dict):
                raise AdapterRefuse(f"season_end_ratings[{season}] is not a map")
            season_end[season] = {str(t): float(v) for t, v in ratings.items()}

    return PinReport(
        games_sha256=games_sha,
        outcomes_sha256=outcomes_sha,
        frozen_md_sha256=frozen_md_sha,
        score_results_sha256=score_sha,
        manifest_sha256=manifest_sha,
        fit_sha=fit_sha,
        config_sha=config_sha,
        asof_rule=asof_rule,
        lam=lam,
        regress_frac=regress_frac,
        a_q2=a_q2,
        b_q2=b_q2,
        season_end_ratings=season_end,
    )


def load_manifest_targets(manifest: Mapping[str, Any], score: Mapping[str, Any]) -> list[dict[str, Any]]:
    if int(manifest.get("n") or 0) != SEALED_N:
        raise AdapterRefuse(f"manifest n {manifest.get('n')} != 70")
    if int(score.get("n") or 0) != SEALED_N:
        raise AdapterRefuse(f"SCORE_RESULTS n {score.get('n')} != 70")
    if str(score.get("if_tip") or "") != SEALED_IF_TIP:
        raise AdapterRefuse("SCORE_RESULTS if_tip != sealed 6ca03716")
    man_games = list(manifest.get("games") or [])
    score_rows = list(score.get("rows") or [])
    if len(man_games) != SEALED_N or len(score_rows) != SEALED_N:
        raise AdapterRefuse("manifest / SCORE_RESULTS row count != 70")
    man_ids = [str(g["game_id"]) for g in man_games]
    score_ids = [str(r["game_id"]) for r in score_rows]
    if man_ids != score_ids:
        raise AdapterRefuse("SCORE_RESULTS game_id list != SAMPLE_MANIFEST_70")
    if len(set(man_ids)) != SEALED_N:
        raise AdapterRefuse("duplicate game_id in 70-game manifest")
    out: list[dict[str, Any]] = []
    for g, r in zip(man_games, score_rows):
        if g["game_id"] != r["game_id"]:
            raise AdapterRefuse("manifest/SCORE_RESULTS order mismatch")
        if r.get("status") != "SCORED":
            raise AdapterRefuse(f"{r['game_id']} SCORE_RESULTS status != SCORED")
        if not _isfinite_number(r.get("forecast_margin")):
            raise AdapterRefuse(f"{r['game_id']} missing IF forecast_margin")
        if not _isfinite_number(r.get("realized_margin")):
            raise AdapterRefuse(f"{r['game_id']} missing realized_margin")
        out.append(
            {
                "game_id": str(r["game_id"]),
                "season": 2017,
                "week": int(r["matchup_week"]),
                "home": str(r["home_team"]),
                "away": str(r["away_team"]),
                "kickoff_utc": g.get("kickoff_utc"),
                "if_margin_mu": float(r["forecast_margin"]),
                "if_total_mu": float(r["forecast_total"]),
                "if_sigma": float(r["if_sigma"]),
                "if_forecast_wp_home": r.get("forecast_wp_home"),
                "if_forecast_wp_away": r.get("forecast_wp_away"),
                "realized_margin": float(r["realized_margin"]),
                "realized_total": float(r["realized_total"]),
                "baseline_label": r.get("epa_success_label") or RETRO_LABEL,
            }
        )
    return out


def _join_history_game(
    target: Mapping[str, Any],
    by_id: Mapping[str, Game],
    by_key: Mapping[tuple[int, int, str, str], Game],
) -> Game:
    gid = str(target["game_id"])
    key = (int(target["season"]), int(target["week"]), str(target["home"]), str(target["away"]))
    game = by_id.get(gid)
    if game is None:
        game = by_key.get(key)
        if game is None:
            raise AdapterRefuse(f"join failure: {gid} not in games pin / Game.key {key}")
    if (game.season, game.week, game.home, game.away) != key:
        raise AdapterRefuse(f"Game.key mismatch under game_id {gid}")
    if game.game_id and game.game_id != gid:
        raise AdapterRefuse(f"game_id mismatch {game.game_id} vs {gid}")
    return game


def _q2_row(
    feat: AsOfFeatures,
    history: Sequence[Game],
    pins: PinReport,
    baseline: Mapping[str, Any],
) -> dict[str, Any]:
    game = feat.game
    wl = asof_wl_diff(game, history)
    q2_pm = float(pins.a_q2) + float(pins.b_q2) * float(feat.rating_diff)
    if_mu = float(baseline["if_margin_mu"])
    try:
        blended = margin_mu_q2s(if_mu, q2_pm)
    except BlendRefuse as exc:
        raise AdapterRefuse(str(exc)) from exc

    # Isolation: baseline IF fields are copied, never overwritten.
    baseline_block = {
        "if_margin_mu": if_mu,
        "if_total_mu": float(baseline["if_total_mu"]),
        "if_sigma": float(baseline["if_sigma"]),
        "if_forecast_wp_home": baseline.get("if_forecast_wp_home"),
        "if_forecast_wp_away": baseline.get("if_forecast_wp_away"),
        "realized_margin": float(baseline["realized_margin"]),
        "realized_total": float(baseline["realized_total"]),
        "if_tip": SEALED_IF_TIP,
        "score_results_sha": pins.score_results_sha256,
        "unchanged": True,
        "mc_draws_unchanged": True,
        "no_candidate_probabilities": True,
    }
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
        "q2_fit_sha": pins.fit_sha,
        "q2_config_sha": pins.config_sha,
        "q2_asof_rule": pins.asof_rule,
        "q2_games_pin": SEALED_GAMES_PIN,
        "extra_hfa": 0.0,
        "formula": "0.5*IF.margin_mu + 0.5*q2_pm_new",
    }
    extra = set(research_q2s) & set(FORBIDDEN_OUTPUT_KEYS)
    extra |= set(baseline_block) & set(FORBIDDEN_OUTPUT_KEYS)
    if extra:
        raise AdapterRefuse(f"forbidden output keys present: {sorted(extra)}")
    for name in Q2S_FIELDS:
        if name not in research_q2s:
            raise AdapterRefuse(f"missing research.q2s.{name}")
        if name in {"w_note", "q2_fit_sha", "q2_config_sha", "q2_asof_rule", "q2_games_pin"}:
            continue
        if name == "q2_n_asof_games":
            if not isinstance(research_q2s[name], int) or research_q2s[name] < 0:
                raise AdapterRefuse("q2_n_asof_games missing / non-finite")
            continue
        if not _isfinite_number(research_q2s[name]):
            raise AdapterRefuse(f"missing field research.q2s.{name}")
    expected_pm = SEALED_A_Q2 + SEALED_B_Q2 * float(feat.rating_diff)
    if not math.isclose(q2_pm, expected_pm, rel_tol=0.0, abs_tol=1e-12):
        raise AdapterRefuse("q2_pm_new != sealed a_q2 + b_q2 · rating_diff")
    expected_blend = Q2S_WEIGHT * if_mu + Q2S_WEIGHT * q2_pm
    if not math.isclose(blended, expected_blend, rel_tol=0.0, abs_tol=1e-12):
        raise AdapterRefuse("margin_mu_q2s != 0.5*IF + 0.5*q2_pm_new")
    # Isolation: blended must not equal a write into IF.margin_mu.
    if blended == if_mu and q2_pm != if_mu:
        pass  # allowed only if coincidentally equal
    return {
        "game_id": game.game_id,
        "season": int(game.season),
        "week": int(game.week),
        "home": game.home,
        "away": game.away,
        "kickoff_utc": game.kickoff_utc.astimezone(timezone.utc).isoformat(),
        "label": RETRO_LABEL,
        "cert": 0,
        "baseline": baseline_block,
        "research": {"q2s": research_q2s},
    }


def emit_adapter(
    *,
    games_path: Path = DEFAULT_GAMES,
    outcomes_path: Path = DEFAULT_OUTCOMES,
    frozen_path: Path = DEFAULT_FROZEN,
    frozen_md_path: Path = DEFAULT_FROZEN_MD,
    score_path: Path = DEFAULT_SCORE,
    manifest_path: Path = DEFAULT_MANIFEST,
    outdir: Path | None = None,
    write_files: bool = True,
) -> EmitResult:
    frozen = load_json_object(frozen_path)
    score = load_json_object(score_path)
    manifest = load_json_object(manifest_path)
    pins = verify_pins(
        games_path, outcomes_path, frozen, frozen_md_path, score_path, manifest_path
    )
    targets_meta = load_manifest_targets(manifest, score)
    try:
        fit_exclusion = prove_fit_exclusion(targets_meta, frozen)
    except CoverageRefuse as exc:
        result = EmitResult(
            rows=[],
            missing=[{"reason": str(exc)}],
            pins=pins,
            fit_exclusion={"ok": False, "blocker": str(exc)},
            refused=True,
            blocker=str(exc),
        )
        if write_files:
            result.artifacts = write_artifacts(result, Path(outdir) if outdir else DEFAULT_OUTDIR)
        return result

    hist_seasons = tuple(s for s in range(2013, TARGET_SEASON + 1) if s not in SEALED_SEASONS)
    try:
        outcomes = load_outcomes_score_only(outcomes_path, hist_seasons)
        history = load_games(
            games_path, outcomes, hist_seasons, phase="q2s_adapter_offline_asof"
        )
    except DataGuardError as exc:
        raise AdapterRefuse(str(exc)) from exc

    by_id = {g.game_id: g for g in history if g.game_id}
    by_key = {g.key: g for g in history}
    missing: list[dict[str, Any]] = []
    target_games: list[Game] = []
    baseline_by_id: dict[str, dict[str, Any]] = {}
    for meta in targets_meta:
        try:
            game = _join_history_game(meta, by_id, by_key)
            if game.margin is None:
                raise AdapterRefuse(f"{meta['game_id']} missing score-only outcome")
            if game.season != TARGET_SEASON:
                raise AdapterRefuse(f"{meta['game_id']} season != 2017")
            target_games.append(game)
            baseline_by_id[game.game_id] = meta
        except AdapterRefuse as exc:
            missing.append({"game_id": meta["game_id"], "reason": str(exc)})

    if missing or len(target_games) != SEALED_N:
        blocker = (
            f"incomplete same-game real coverage: have {len(target_games)} / {SEALED_N}; "
            f"missing={missing}"
        )
        result = EmitResult(
            rows=[],
            missing=missing,
            pins=pins,
            fit_exclusion=fit_exclusion,
            n_history=len(history),
            refused=True,
            blocker=blocker,
        )
        if write_files:
            result.artifacts = write_artifacts(result, Path(outdir) if outdir else DEFAULT_OUTDIR)
        return result

    persist = {int(k): dict(v) for k, v in pins.season_end_ratings.items() if k < 2017}
    feats = asof_for_targets(
        history,
        target_games,
        pins.lam,
        pins.regress_frac,
        persist_season_end=persist,
    )
    feats = sorted(feats, key=lambda f: (f.game.kickoff_utc, f.game.game_id))
    try:
        assert_asof_leakage(history, feats)
    except AssertionError as exc:
        raise AdapterRefuse(f"as-of leakage: {exc}") from exc

    rows: list[dict[str, Any]] = []
    kept: list[AsOfFeatures] = []
    for feat in feats:
        try:
            assert_asof_leakage(history, [feat])
            row = _q2_row(feat, history, pins, baseline_by_id[feat.game.game_id])
        except (AssertionError, AdapterRefuse) as exc:
            missing.append({"game_id": feat.game.game_id, "reason": str(exc)})
            continue
        kept.append(feat)
        rows.append(row)

    if len(rows) != SEALED_N or missing:
        blocker = (
            f"incomplete Q2 rows after as-of: have {len(rows)} / {SEALED_N}; "
            f"missing={missing}"
        )
        result = EmitResult(
            rows=[],
            missing=missing,
            pins=pins,
            fit_exclusion=fit_exclusion,
            n_history=len(history),
            refused=True,
            blocker=blocker,
        )
        if write_files:
            result.artifacts = write_artifacts(result, Path(outdir) if outdir else DEFAULT_OUTDIR)
        return result

    assert_asof_leakage(history, kept)
    result = EmitResult(
        rows=rows,
        missing=[],
        pins=pins,
        fit_exclusion=fit_exclusion,
        n_history=len(history),
        refused=False,
        blocker=None,
    )
    if write_files:
        result.artifacts = write_artifacts(result, Path(outdir) if outdir else DEFAULT_OUTDIR)
    return result


def _manifest(result: EmitResult) -> dict[str, Any]:
    return {
        "label": RETRO_LABEL,
        "packet_label": LABEL,
        "cert": 0,
        "nfl": "NO-GO",
        "ticket": "t5033u",
        "amend": "fdf91ff5",
        "delegation": "d7e0a6bc",
        "work_package": "2db90f76",
        "guardrails": "52c79ee6",
        "q2_eval_closed": "03a4dd90",
        "score_results_control": "2b9f302e",
        "mode": "offline_layer2_q2s_adapter",
        "research_consumed_only": True,
        "refused": result.refused,
        "blocker": result.blocker,
        "pins": {
            "q2_fit_sha": result.pins.fit_sha,
            "q2_config_sha": result.pins.config_sha,
            "q2_asof_rule": result.pins.asof_rule,
            "q2_games_pin": SEALED_GAMES_PIN,
            "q2_games_sha256": result.pins.games_sha256,
            "q2_outcomes_sha": result.pins.outcomes_sha256,
            "q2_frozen_md_sha": result.pins.frozen_md_sha256,
            "score_results_sha": result.pins.score_results_sha256,
            "manifest_sha": result.pins.manifest_sha256,
            "lam": result.pins.lam,
            "regress_frac": result.pins.regress_frac,
            "a_q2": result.pins.a_q2,
            "b_q2": result.pins.b_q2,
            "if_tip": SEALED_IF_TIP,
            "tip_asof_kickoff": TIP_ASOF_KICKOFF,
            "dev_seasons": list(DEV_SEASONS),
            "dev_weeks": list(DEV_WEEKS),
            "history_only_seasons": list(HISTORY_ONLY_SEASONS),
        },
        "isolation": {
            "writes_offense_index": False,
            "writes_defense_index": False,
            "writes_l0_off_eff": False,
            "writes_independent_fair_margin_mu": False,
            "writes_l0_market_blend": False,
            "writes_if_total_mu": False,
            "writes_if_sigma": False,
            "shifts_mc_draws": False,
            "emits_candidate_win_ats_ou": False,
            "calls_simulate_nfl_game": False,
            "edits_score_t4910u": False,
            "edits_emit_q2_asof_sidecar": False,
            "layer3": False,
            "research_fields_only": "research.q2s.*",
        },
        "amend_681": {
            "section": "§4 research-field isolation + H6",
            "scope": "this single comparison only",
            "allows": "research.q2s.margin_mu_q2s beside unchanged IF mus",
            "forbids": "write IF.margin_mu / total_mu / sigma / MC / Layer 3",
        },
        "annotate_684": {
            "accept": "9982d42f",
            "status": "undisturbed",
            "note": "2013 REG W2 demo fixtures remain mechanical-only; never outcome scoring",
        },
        "fit_exclusion": result.fit_exclusion,
        "n_history": result.n_history,
        "n_emitted": len(result.rows),
        "n_missing": len(result.missing),
        "missing": result.missing,
        "rows": result.rows,
        "holds": [
            "CERT=0",
            "NFL NO-GO",
            "pub/bet HOLD",
            "no Layer 3",
            "no second weight",
            "no second look from this emit",
            "Q2 EVAL 03a4dd90 CLOSED",
            "no Stage C",
            "no 2024-25",
            "no 1ee90fac scored columns",
        ],
    }


def write_artifacts(result: EmitResult, outdir: Path) -> dict[str, str]:
    outdir.mkdir(parents=True, exist_ok=True)
    payload = _manifest(result)
    json_path = outdir / "q2s_rows_t5033u.json"
    cov_path = outdir / "COVERAGE_PROOF.json"
    miss_path = outdir / "MISSING_COVERAGE.json"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    cov_path.write_text(
        json.dumps(
            {
                "label": RETRO_LABEL,
                "cert": 0,
                "fit_exclusion": result.fit_exclusion,
                "n_emitted": len(result.rows),
                "n_missing": len(result.missing),
                "refused": result.refused,
                "blocker": result.blocker,
                "score_results_sha": result.pins.score_results_sha256,
                "fit_sha": result.pins.fit_sha,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    miss_path.write_text(
        json.dumps(
            {"missing": result.missing, "blocker": result.blocker, "label": RETRO_LABEL},
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    md_path = outdir / "q2s_rows_t5033u.md"
    md_path.write_text(_render_md(result))
    return {
        "json": str(json_path),
        "coverage": str(cov_path),
        "missing": str(miss_path),
        "md": str(md_path),
    }


def _render_md(result: EmitResult) -> str:
    pins = result.pins
    lines = [
        "# t5033u — research.q2s adapter rows (DEV_RESEARCH)",
        "",
        f"**{RETRO_LABEL} · CERT=0 · NFL NO-GO · do not merge/deploy/pub/bet.**",
        "",
        "NEW `research.q2s.*` only. Baseline IF mus / sigma / MC draws unchanged.",
        "w=0.5 is a predeclared research candidate — NOT fitted or proven optimum.",
        "",
        "## Pins",
        "",
        f"- games `{pins.games_sha256[:8]}` (require `4fe1cdd7`)",
        f"- outcomes `{pins.outcomes_sha256[:8]}` (require `50bda875`)",
        f"- fit `{pins.fit_sha[:8]}` (require `70db070d`)",
        f"- config `{pins.config_sha[:8]}` (require `aa2b47b3`)",
        f"- as-of `{pins.asof_rule}` (require `cf514078`)",
        f"- frozen md `{pins.frozen_md_sha256[:8]}` (require `28c582a1`)",
        f"- SCORE_RESULTS `{pins.score_results_sha256[:8]}` (require `2b9f302e`)",
        f"- IF tip `6ca03716` (sealed caller; not edited)",
        "",
        "## Fit exclusion",
        "",
        f"- ok: `{result.fit_exclusion.get('ok')}`",
        f"- {result.fit_exclusion.get('note')}",
        "",
        "## Counts",
        "",
        f"- history games: {result.n_history}",
        f"- emitted rows: {len(result.rows)}",
        f"- missing: {len(result.missing)}",
        f"- refused: {result.refused}",
        "",
    ]
    if result.blocker:
        lines.extend(["## Blocker", "", result.blocker, ""])
    lines.extend(
        [
            "## Isolation",
            "",
            "No writes to IF.margin_mu / total_mu / sigma / MC draws / L0 /",
            "NflGameInputs / Layer 3. No candidate win/ATS/OU probabilities.",
            "#684 ACCEPT `9982d42f` undisturbed. Q2 EVAL `03a4dd90` CLOSED.",
            "",
        ]
    )
    return "\n".join(lines)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--games", type=Path, default=DEFAULT_GAMES)
    p.add_argument("--outcomes", type=Path, default=DEFAULT_OUTCOMES)
    p.add_argument("--frozen", type=Path, default=DEFAULT_FROZEN)
    p.add_argument("--frozen-md", type=Path, default=DEFAULT_FROZEN_MD)
    p.add_argument("--score", type=Path, default=DEFAULT_SCORE)
    p.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    p.add_argument("--out", type=Path, default=DEFAULT_OUTDIR)
    p.add_argument("--dry-run", action="store_true")
    return p.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    result = emit_adapter(
        games_path=args.games,
        outcomes_path=args.outcomes,
        frozen_path=args.frozen,
        frozen_md_path=args.frozen_md,
        score_path=args.score,
        manifest_path=args.manifest,
        outdir=args.out,
        write_files=not args.dry_run,
    )
    print(
        f"t5033u q2s adapter emitted={len(result.rows)} missing={len(result.missing)} "
        f"refused={result.refused} SCORE_RESULTS={result.pins.score_results_sha256[:8]} "
        f"fit={result.pins.fit_sha[:8]}"
    )
    if result.blocker:
        print(f"BLOCKER: {result.blocker}", file=sys.stderr)
        return 2
    if result.artifacts:
        for kind, path in result.artifacts.items():
            print(f"  {kind}: {path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AdapterRefuse, DataGuardError, CoverageRefuse) as exc:
        print(f"REFUSE: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
