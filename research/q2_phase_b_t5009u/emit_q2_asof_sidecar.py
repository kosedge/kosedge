#!/usr/bin/env python3
"""t5018u — offline Q2AsOfSidecar artifact writer (DEV_RESEARCH).

CERT=0 · NFL NO-GO · research-consumed only · DRAFT · do not merge/deploy/pub/bet.

Passively emits JSON/CSV/md sidecar *annotations* from frozen Q2 Phase B
symbols. Does **not** join into forecasts, does **not** call any simulator,
does **not** write NflGameInputs / L0 / Independent Fair mus.

Reuse only (#681 §9): asof_for_targets, asof_wl_diff, assert_asof_leakage,
sealed coefficients, load_games / verify_games_pin / load_outcomes_score_only.

Authority: OWNER CLEAR tip 1e71808d (OWNER_WIRING_CARD_t5015u_Q2_SIDECAR,
offline artifact writer only) · contract #681 e30e6f9c · CoS ACCEPT tip
fc03a463 · keep packet #679 af6be4f5 / FROZEN 28c582a1.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from q2pb.constants import (  # noqa: E402
    DEV_WEEKS,
    EXPECTED_GAMES_SHA256_PREFIX,
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
    window_rows,
)
from q2pb.metrics import asof_wl_diff  # noqa: E402
from q2pb.strength import AsOfFeatures, asof_for_targets, assert_asof_leakage  # noqa: E402

# --- sealed pins (contract #681 §3d / §3e). Do not refit. ---
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
CONTRACT_HEAD = "e30e6f9c78b2a5a4d4ab105cff012a741a36c3ca"
OWNER_CLEAR_WRITER = "1e71808d"
COS_ACCEPT_TIP = "fc03a463"

DEFAULT_GAMES = ROOT / "data" / "games_4fe1cdd7.csv"
DEFAULT_OUTCOMES = ROOT / "data" / "outcomes_2013_2022_score_only.csv"
DEFAULT_FROZEN = ROOT / "frozen" / "FROZEN_CONFIG_Q2PB_t5009u.json"
DEFAULT_FROZEN_MD = ROOT / "frozen" / "FROZEN_CONFIG_Q2PB_t5009u.md"
DEFAULT_OUTDIR = ROOT / "artifacts"

# Contract §3 required sidecar fields. Isolation: this is the *only* emit schema.
IDENTITY_FIELDS = ("game_id", "season", "week", "home", "away", "kickoff_utc")
NUMERIC_FIELDS = (
    "q2_home_s",
    "q2_away_s",
    "q2_rating_diff",
    "q2_hfa",
    "q2_n_asof_games",
    "q2_asof_wl_diff",
    "q2_pm_new",
)
PIN_FIELDS = ("q2_fit_sha", "q2_config_sha", "q2_asof_rule", "q2_games_pin")
OPTIONAL_PROVENANCE = (
    "q2_frozen_md_sha",
    "q2_keep_commit",
    "q2_outcomes_sha",
)
ROW_FIELDS = IDENTITY_FIELDS + NUMERIC_FIELDS + PIN_FIELDS + OPTIONAL_PROVENANCE

FORBIDDEN_OUTPUT_KEYS = (
    "offense_index_home",
    "offense_index_away",
    "defense_index_home",
    "defense_index_away",
    "off_eff_h",
    "off_eff_a",
    "def_eff_h",
    "def_eff_a",
    "margin_mu",
    "total_mu",
    "sigma",
    "market_blend",
    "independent_fair",
    "trailing_offense",
    "trailing_defense",
)

# Paths this writer may open. The gated hist index is not among them.
ALLOWED_OPEN_NAMES = {
    "games_4fe1cdd7.csv",
    "outcomes_2013_2022_score_only.csv",
    "FROZEN_CONFIG_Q2PB_t5009u.json",
    "FROZEN_CONFIG_Q2PB_t5009u.md",
}

MAX_TARGET_SEASON = 2022  # score-only extract ceiling; 2023 reserve / 2024–25 sealed


class SidecarRefuse(RuntimeError):
    """Fail-closed refusal (row or batch). Never impute."""


@dataclass
class PinReport:
    games_sha256: str
    outcomes_sha256: str
    frozen_md_sha256: str
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
    refused: list[dict[str, Any]]
    pins: PinReport
    artifacts: dict[str, str] = field(default_factory=dict)
    n_history: int = 0
    n_targets: int = 0


def _isfinite_number(value: Any) -> bool:
    if isinstance(value, bool) or value is None:
        return False
    if isinstance(value, int):
        return True
    if isinstance(value, float):
        return math.isfinite(value)
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def _require_prefix(digest: str, prefix: str, label: str) -> None:
    if not str(digest).startswith(prefix):
        raise SidecarRefuse(f"{label} sha {digest[:8]} != required prefix {prefix}")


def _parse_kickoff(raw: Any) -> datetime:
    if isinstance(raw, datetime):
        dt = raw
    else:
        s = str(raw).strip()
        if not s:
            raise SidecarRefuse("non-finite / missing kickoff_utc")
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(s)
        except ValueError as exc:
            raise SidecarRefuse(f"non-finite kickoff_utc: {raw!r}") from exc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def load_frozen_config(path: Path) -> dict[str, Any]:
    if path.name not in ALLOWED_OPEN_NAMES:
        raise SidecarRefuse(f"refusing to open non-frozen path {path}")
    with path.open() as f:
        cfg = json.load(f)
    if not isinstance(cfg, dict):
        raise SidecarRefuse("frozen config is not an object")
    return cfg


def verify_pins(
    games_path: Path,
    outcomes_path: Path,
    frozen: Mapping[str, Any],
    frozen_md_path: Path | None = None,
) -> PinReport:
    """Contract §3e / appendix A2 — pin sha match. Fail-closed on mismatch."""
    if games_path.name != "games_4fe1cdd7.csv":
        raise SidecarRefuse(f"games path must be the 4fe1cdd7 pin, got {games_path.name}")
    if outcomes_path.name != "outcomes_2013_2022_score_only.csv":
        raise SidecarRefuse(
            f"outcomes path must be the 50bda875 extract, got {outcomes_path.name}"
        )
    games_sha = verify_games_pin(games_path)
    _require_prefix(games_sha, SEALED_GAMES_PIN, "games")
    if games_sha != SEALED_GAMES_SHA:
        raise SidecarRefuse("games.csv full sha256 != sealed 4fe1cdd7 object")

    outcomes_sha = sha256_file(outcomes_path)
    _require_prefix(outcomes_sha, "50bda875", "outcomes")
    if outcomes_sha != SEALED_OUTCOMES_SHA:
        raise SidecarRefuse("outcomes extract full sha256 != sealed 50bda875 object")

    fit_sha = str(frozen.get("fit_object_sha256") or "")
    config_sha = str(frozen.get("config_sha256") or "")
    asof_rule = str(frozen.get("tip_asof") or "")
    _require_prefix(fit_sha, "70db070d", "fit")
    _require_prefix(config_sha, "aa2b47b3", "config")
    if fit_sha != SEALED_FIT_SHA:
        raise SidecarRefuse("frozen fit_object_sha256 != sealed 70db070d")
    if config_sha != SEALED_CONFIG_SHA:
        raise SidecarRefuse("frozen config_sha256 != sealed aa2b47b3")
    if asof_rule != SEALED_ASOF_RULE:
        raise SidecarRefuse(f"tip_asof {asof_rule!r} != {SEALED_ASOF_RULE}")
    if str(frozen.get("tip_games") or "") != TIP_GAMES:
        raise SidecarRefuse("frozen tip_games != 4fe1cdd7")

    try:
        lam = float(frozen["lam"])
        regress_frac = float(frozen["regress_frac"])
        a_q2 = float(frozen["a_q2"])
        b_q2 = float(frozen["b_q2"])
    except (KeyError, TypeError, ValueError) as exc:
        raise SidecarRefuse("frozen missing sealed lam/r/a_q2/b_q2") from exc
    if lam != SEALED_LAM or regress_frac != SEALED_REGRESS_FRAC:
        raise SidecarRefuse("frozen λ/r != sealed 20.0 / 0.5 (no retune)")
    if a_q2 != SEALED_A_Q2 or b_q2 != SEALED_B_Q2:
        raise SidecarRefuse("frozen a_q2/b_q2 != sealed DEV OLS (no refit)")

    frozen_md_sha = ""
    md_path = frozen_md_path or DEFAULT_FROZEN_MD
    if md_path.exists():
        frozen_md_sha = sha256_file(md_path)
        _require_prefix(frozen_md_sha, "28c582a1", "frozen md")

    raw_priors = frozen.get("season_end_ratings") or {}
    season_end: dict[int, dict[str, float]] = {}
    if isinstance(raw_priors, dict):
        for key, ratings in raw_priors.items():
            try:
                season = int(key)
            except (TypeError, ValueError) as exc:
                raise SidecarRefuse(f"non-int season_end_ratings key {key!r}") from exc
            if season >= 2023:
                raise SidecarRefuse("season_end_ratings includes 2023+ (refused)")
            if not isinstance(ratings, dict):
                raise SidecarRefuse(f"season_end_ratings[{season}] is not a map")
            season_end[season] = {str(t): float(v) for t, v in ratings.items()}

    return PinReport(
        games_sha256=games_sha,
        outcomes_sha256=outcomes_sha,
        frozen_md_sha256=frozen_md_sha,
        fit_sha=fit_sha,
        config_sha=config_sha,
        asof_rule=asof_rule,
        lam=lam,
        regress_frac=regress_frac,
        a_q2=a_q2,
        b_q2=b_q2,
        season_end_ratings=season_end,
    )


def validate_row(row: Mapping[str, Any]) -> None:
    """Contract §7 — refuse the row if any required field is missing/non-finite."""
    if not isinstance(row, Mapping):
        raise SidecarRefuse("row is not a mapping")
    extra = set(row) & set(FORBIDDEN_OUTPUT_KEYS)
    if extra:
        raise SidecarRefuse(f"forbidden output keys present: {sorted(extra)}")

    for name in IDENTITY_FIELDS + NUMERIC_FIELDS + PIN_FIELDS:
        if name not in row:
            raise SidecarRefuse(f"missing field {name}")
        if row[name] is None or row[name] == "":
            raise SidecarRefuse(f"missing field {name}")

    season = row["season"]
    week = row["week"]
    home = row["home"]
    away = row["away"]
    if not isinstance(season, int) or season < 2013 or season > MAX_TARGET_SEASON:
        raise SidecarRefuse(f"season out of approved scope: {season!r}")
    if season in SEALED_SEASONS:
        raise SidecarRefuse("2024–25 row refused")
    if not isinstance(week, int) or week < 1 or week > 18:
        raise SidecarRefuse(f"week out of range: {week!r}")
    if not isinstance(home, str) or not home.strip():
        raise SidecarRefuse("missing field home")
    if not isinstance(away, str) or not away.strip():
        raise SidecarRefuse("missing field away")

    game_id = row["game_id"]
    if not isinstance(game_id, str) or not game_id.strip():
        # Contract §3a: game_id required if the other side has it. Offline
        # writer has no IF/L0 peer; Game.key must still be complete.
        if not (season and week and home and away):
            raise SidecarRefuse("join failure: empty game_id and incomplete Game.key")

    _parse_kickoff(row["kickoff_utc"])

    if not isinstance(row["q2_n_asof_games"], int) or row["q2_n_asof_games"] < 0:
        raise SidecarRefuse("q2_n_asof_games missing / non-finite")
    for name in NUMERIC_FIELDS:
        if name == "q2_n_asof_games":
            continue
        if not _isfinite_number(row[name]):
            raise SidecarRefuse(f"missing field {name}")

    if row["q2_fit_sha"] != SEALED_FIT_SHA:
        raise SidecarRefuse("q2_fit_sha != sealed 70db070d")
    if row["q2_config_sha"] != SEALED_CONFIG_SHA:
        raise SidecarRefuse("q2_config_sha != sealed aa2b47b3")
    if row["q2_asof_rule"] != SEALED_ASOF_RULE:
        raise SidecarRefuse("q2_asof_rule != cf514078")
    if row["q2_games_pin"] != SEALED_GAMES_PIN:
        raise SidecarRefuse("q2_games_pin != 4fe1cdd7")
    expected_pm = SEALED_A_Q2 + SEALED_B_Q2 * float(row["q2_rating_diff"])
    if not math.isclose(float(row["q2_pm_new"]), expected_pm, rel_tol=0.0, abs_tol=1e-12):
        raise SidecarRefuse("q2_pm_new != sealed a_q2 + b_q2 · rating_diff")


def _q2_pm_new(rating_diff: float, a_q2: float, b_q2: float) -> float:
    return float(a_q2) + float(b_q2) * float(rating_diff)


def row_from_feat(
    feat: AsOfFeatures,
    history: Sequence[Game],
    pins: PinReport,
) -> dict[str, Any]:
    game = feat.game
    wl = asof_wl_diff(game, history)
    row = {
        "game_id": game.game_id,
        "season": int(game.season),
        "week": int(game.week),
        "home": game.home,
        "away": game.away,
        "kickoff_utc": game.kickoff_utc.astimezone(timezone.utc).isoformat(),
        "q2_home_s": float(feat.home_s),
        "q2_away_s": float(feat.away_s),
        "q2_rating_diff": float(feat.rating_diff),
        "q2_hfa": float(feat.hfa),
        "q2_n_asof_games": int(feat.n_asof_games),
        "q2_asof_wl_diff": float(wl),
        "q2_pm_new": _q2_pm_new(feat.rating_diff, pins.a_q2, pins.b_q2),
        "q2_fit_sha": pins.fit_sha,
        "q2_config_sha": pins.config_sha,
        "q2_asof_rule": pins.asof_rule,
        "q2_games_pin": SEALED_GAMES_PIN,
        "q2_frozen_md_sha": pins.frozen_md_sha256 or SEALED_FROZEN_MD_SHA,
        "q2_keep_commit": SEALED_KEEP_COMMIT,
        "q2_outcomes_sha": pins.outcomes_sha256,
    }
    validate_row(row)
    return row


def _history_seasons(target_seasons: Sequence[int]) -> tuple[int, ...]:
    if not target_seasons:
        raise SidecarRefuse("no target seasons")
    lo = min(target_seasons)
    hi = max(target_seasons)
    if hi > MAX_TARGET_SEASON or lo < 2013:
        raise SidecarRefuse("target seasons outside approved 2013–2022 scope")
    if set(target_seasons) & set(SEALED_SEASONS):
        raise SidecarRefuse("refusing 2024–25 targets")
    hist = tuple(s for s in range(2013, hi + 1) if s not in SEALED_SEASONS and s <= MAX_TARGET_SEASON)
    return hist


def emit_sidecar(
    *,
    games_path: Path = DEFAULT_GAMES,
    outcomes_path: Path = DEFAULT_OUTCOMES,
    frozen_path: Path = DEFAULT_FROZEN,
    frozen_md_path: Path = DEFAULT_FROZEN_MD,
    seasons: Sequence[int] = (2013,),
    weeks: Sequence[int] = (2,),
    outdir: Path | None = None,
    write_files: bool = True,
) -> EmitResult:
    """Build sidecar rows. Isolation: writes JSON/CSV/md under outdir only."""
    if set(seasons) & set(SEALED_SEASONS):
        raise SidecarRefuse("refusing 2024–25")
    if any(s > MAX_TARGET_SEASON for s in seasons):
        raise SidecarRefuse("refusing 2023+ targets (reserve / sealed)")
    if any(s < 2013 for s in seasons):
        raise SidecarRefuse("season before approved games pin")

    frozen = load_frozen_config(frozen_path)
    pins = verify_pins(games_path, outcomes_path, frozen, frozen_md_path)

    hist_seasons = _history_seasons(seasons)
    # phase name is not phase1_dev so 2017 can be history for later seasons;
    # 2024–25 still refused by loaders + SEALED_SEASONS.
    try:
        outcomes = load_outcomes_score_only(outcomes_path, hist_seasons)
        history = load_games(
            games_path, outcomes, hist_seasons, phase="sidecar_offline_asof"
        )
    except DataGuardError as exc:
        raise SidecarRefuse(str(exc)) from exc

    targets = window_rows(history, seasons, weeks)
    if not targets:
        raise SidecarRefuse("no scored targets in requested window")

    persist = {int(k): dict(v) for k, v in pins.season_end_ratings.items() if k < 2023}
    feats = asof_for_targets(
        history,
        targets,
        pins.lam,
        pins.regress_frac,
        persist_season_end=persist,
    )
    feats = sorted(feats, key=lambda f: (f.game.kickoff_utc, f.game.game_id))

    rows: list[dict[str, Any]] = []
    refused: list[dict[str, Any]] = []
    kept_feats: list[AsOfFeatures] = []
    for feat in feats:
        ident = {
            "game_id": feat.game.game_id,
            "season": feat.game.season,
            "week": feat.game.week,
            "home": feat.game.home,
            "away": feat.game.away,
        }
        try:
            assert_asof_leakage(history, [feat])
            row = row_from_feat(feat, history, pins)
        except (AssertionError, SidecarRefuse) as exc:
            refused.append({**ident, "reason": str(exc)})
            continue
        kept_feats.append(feat)
        rows.append(row)

    if kept_feats:
        # Contract §6: leakage assert green on the emitted set (reuse, no new guard).
        assert_asof_leakage(history, kept_feats)
        for row in rows:
            validate_row(row)

    result = EmitResult(
        rows=rows,
        refused=refused,
        pins=pins,
        n_history=len(history),
        n_targets=len(targets),
    )
    if write_files:
        dest = Path(outdir) if outdir is not None else DEFAULT_OUTDIR
        result.artifacts = write_artifacts(result, dest)
    return result


def _manifest(result: EmitResult) -> dict[str, Any]:
    return {
        "label": LABEL,
        "cert": 0,
        "ticket": "t5018u",
        "mode": "offline_artifact_writer",
        "research_consumed_only": True,
        "contract": "research/q2_phase_b_t5009u/Q2_ASOF_SIDECAR_FIELD_CONTRACT_t5015u.md",
        "contract_head": CONTRACT_HEAD,
        "contract_sections": ["§3", "§3a", "§3b", "§3c", "§3d", "§3e", "§4", "§5", "§6", "§7", "§9", "A1", "A2"],
        "authority": {
            "owner_clear_writer": OWNER_CLEAR_WRITER,
            "wiring_card": "OWNER_WIRING_CARD_t5015u_Q2_SIDECAR",
            "cos_accept": COS_ACCEPT_TIP,
            "keep_commit": SEALED_KEEP_COMMIT,
        },
        "pins": {
            "q2_fit_sha": result.pins.fit_sha,
            "q2_config_sha": result.pins.config_sha,
            "q2_asof_rule": result.pins.asof_rule,
            "q2_games_pin": SEALED_GAMES_PIN,
            "q2_games_sha256": result.pins.games_sha256,
            "q2_outcomes_sha": result.pins.outcomes_sha256,
            "q2_frozen_md_sha": result.pins.frozen_md_sha256,
            "lam": result.pins.lam,
            "regress_frac": result.pins.regress_frac,
            "a_q2": result.pins.a_q2,
            "b_q2": result.pins.b_q2,
            "expected_games_prefix": EXPECTED_GAMES_SHA256_PREFIX,
            "tip_asof_kickoff": TIP_ASOF_KICKOFF,
        },
        "isolation": {
            "writes_offense_index": False,
            "writes_defense_index": False,
            "writes_l0_off_eff": False,
            "writes_independent_fair_margin_mu": False,
            "writes_l0_market_blend": False,
            "calls_simulate_nfl_game": False,
            "joins_forecast_path": False,
            "model_consumption": False,
        },
        "holds": [
            "CERT=0",
            "pub/bet HOLD",
            "no Layer 3 caller change",
            "no second EVAL",
            "no Stage C",
            "no 2024-25",
            "no 1ee90fac scored columns",
        ],
        "n_history": result.n_history,
        "n_targets": result.n_targets,
        "n_emitted": len(result.rows),
        "n_refused": len(result.refused),
        "refused": result.refused,
        "rows": result.rows,
    }


def write_artifacts(result: EmitResult, outdir: Path) -> dict[str, str]:
    outdir.mkdir(parents=True, exist_ok=True)
    stem = "q2_asof_sidecar_t5018u"
    json_path = outdir / f"{stem}.json"
    csv_path = outdir / f"{stem}.csv"
    md_path = outdir / f"{stem}.md"

    payload = _manifest(result)
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")

    with csv_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(ROW_FIELDS), extrasaction="raise")
        writer.writeheader()
        for row in result.rows:
            writer.writerow({k: row[k] for k in ROW_FIELDS})

    md_path.write_text(_render_md(result))
    return {
        "json": str(json_path),
        "csv": str(csv_path),
        "md": str(md_path),
    }


def _render_md(result: EmitResult) -> str:
    pins = result.pins
    lines = [
        "# t5018u — Q2AsOfSidecar offline artifacts (DEV_RESEARCH)",
        "",
        "**CERT=0 · NFL NO-GO · research-consumed only · do not merge/deploy/pub/bet.**",
        "",
        "Passive annotation beside Independent Fair. Not a forecast join.",
        "Contract: `Q2_ASOF_SIDECAR_FIELD_CONTRACT_t5015u.md` (§3–§7, §9, A1–A2).",
        "",
        "## Pins",
        "",
        f"- games `{pins.games_sha256[:8]}` (require `{SEALED_GAMES_PIN}`)",
        f"- outcomes `{pins.outcomes_sha256[:8]}` (require `50bda875`)",
        f"- fit `{pins.fit_sha[:8]}` (require `70db070d`)",
        f"- config `{pins.config_sha[:8]}` (require `aa2b47b3`)",
        f"- as-of `{pins.asof_rule}` (require `{SEALED_ASOF_RULE}`)",
        f"- frozen md `{pins.frozen_md_sha256[:8] or 'absent'}` (require `28c582a1`)",
        f"- λ={pins.lam} r={pins.regress_frac} a_q2={pins.a_q2} b_q2={pins.b_q2}",
        "",
        "## Isolation",
        "",
        "No writes to `offense_index_*` / `defense_index_*` / L0 `off_eff_*` /",
        "`independent_fair.margin_mu` / `L0.market_blend`. No `simulate_nfl_game*`.",
        "",
        "## Counts",
        "",
        f"- history games: {result.n_history}",
        f"- window targets: {result.n_targets}",
        f"- emitted rows: {len(result.rows)}",
        f"- refused rows: {len(result.refused)}",
        "",
        "## Emitted (identity + q2_pm_new)",
        "",
    ]
    for row in result.rows:
        lines.append(
            f"- `{row['game_id']}` {row['away']}@{row['home']} "
            f"W{row['week']} {row['season']} pm_new={row['q2_pm_new']:.4f} "
            f"n_asof={row['q2_n_asof_games']}"
        )
    if result.refused:
        lines.append("")
        lines.append("## Refused")
        lines.append("")
        for item in result.refused:
            lines.append(f"- `{item.get('game_id')}` {item.get('reason')}")
    lines.append("")
    lines.append("## Holds")
    lines.append("")
    lines.append("No second EVAL · no Stage C · no 2024–25 · no `1ee90fac` scored columns · CERT=0.")
    lines.append("")
    return "\n".join(lines)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--games", type=Path, default=DEFAULT_GAMES)
    p.add_argument("--outcomes", type=Path, default=DEFAULT_OUTCOMES)
    p.add_argument("--frozen", type=Path, default=DEFAULT_FROZEN)
    p.add_argument("--frozen-md", type=Path, default=DEFAULT_FROZEN_MD)
    p.add_argument(
        "--seasons",
        default="2013",
        help="comma-separated seasons (default 2013; max 2022; no 2024–25)",
    )
    p.add_argument(
        "--weeks",
        default="2",
        help="comma-separated REG weeks (default 2 = bounded DEV demo)",
    )
    p.add_argument("--out", type=Path, default=DEFAULT_OUTDIR)
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="build rows and run guards; do not write artifacts",
    )
    return p.parse_args(argv)


def _parse_ints(raw: str, *, allowed: Iterable[int], label: str) -> tuple[int, ...]:
    allow = set(allowed)
    out: list[int] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        value = int(part)
        if value not in allow:
            raise SidecarRefuse(f"{label} {value} not in approved set {sorted(allow)}")
        out.append(value)
    if not out:
        raise SidecarRefuse(f"empty {label} list")
    return tuple(out)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    seasons = _parse_ints(args.seasons, allowed=range(2013, 2023), label="season")
    weeks = _parse_ints(args.weeks, allowed=DEV_WEEKS, label="week")
    result = emit_sidecar(
        games_path=args.games,
        outcomes_path=args.outcomes,
        frozen_path=args.frozen,
        frozen_md_path=args.frozen_md,
        seasons=seasons,
        weeks=weeks,
        outdir=args.out,
        write_files=not args.dry_run,
    )
    print(
        f"Q2AsOfSidecar t5018u emitted={len(result.rows)} refused={len(result.refused)} "
        f"pins=games:{result.pins.games_sha256[:8]} fit:{result.pins.fit_sha[:8]} "
        f"config:{result.pins.config_sha[:8]} asof:{result.pins.asof_rule}"
    )
    if result.artifacts:
        for kind, path in result.artifacts.items():
            print(f"  {kind}: {path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (SidecarRefuse, DataGuardError) as exc:
        print(f"REFUSE: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
