#!/usr/bin/env python3
"""t5029u — Lane A CLEAR_ANNOTATE join (DEV_RESEARCH, CERT=0).

Passive offline reader of accepted #682 Q2AsOfSidecar writer outputs
(head 7d89a974 / ACCEPT d17b30fa). Exact identity join onto frozen
2013 REG W2 IF/demo inputs. Emits DEV_RESEARCH annotation labels beside
rows. Does **not** rewrite the #682 writer.

NEVER mutates offense_index_*/defense_index_*/margin_mu/market_blend/L0.
NEVER invokes nfl_simulator / simulate_nfl_game.
NO extra EVAL · NO retune · NO runtime / Layer-3 change.
NO edits to routes/nfl.py, tasks.py, NflGameInputs, ledger, score_t4910u.py.

Authority: OWNER t5029u · card 20dd7940 CLEAR_ANNOTATE · work-package
2db90f76 · guardrails 52c79ee6 · #683 eabd49a6 · wiring 013ec7f8 (N2) ·
ORDER N1 09f70480. NFL NO-GO · DRAFT only · do not merge/deploy/pub/bet.
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

from q2pb.constants import SEALED_SEASONS, TIP_GAMES  # noqa: E402
from q2pb.data import (  # noqa: E402
    DataGuardError,
    Game,
    load_games,
    load_outcomes_score_only,
    sha256_file,
    verify_games_pin,
)
from q2pb.strength import AsOfFeatures, assert_asof_leakage  # noqa: E402

# --- sealed pins (assert refuse-on-mismatch). Do not retune. ---
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
WRITER_HEAD = "7d89a9740a7070de56cf6d104708925d2666b49e"
WRITER_ACCEPT = "d17b30fa"
PROPOSAL_HEAD = "eabd49a6b49afabfa609d0fd6680e85e7c4517a9"
WIRING_CARD = "013ec7f8"
ORDER_N1 = "09f70480"
OWNER = "t5029u"
CARD = "20dd7940"
WORK_PACKAGE = "2db90f76"
GUARDRAILS = "52c79ee6"
ALEX_FORMULA_HELD = "fa36c679"

# Frozen-before-run binds. Changing these files without updating the binds refuses.
SEALED_SIDECAR_SHA = "534f6f0df7414f3c32a9c6367bfa9653904fca7fd6bad5d1e378f1383df66fca"
SEALED_MANIFEST_SHA = "67201f0593d1d2e7537469619d339ad703240ed70093657b53c0ebac9209cb26"
SEALED_IF_DEMO_SHA = "411d0e5dc6917aff2cd5b67ee7b36159ee1c53078b398fc9f5c1cf6535b74493"

FROZEN_SCOPE_SEASON = 2013
FROZEN_SCOPE_WEEK = 2
FROZEN_SCOPE_SEASON_TYPE = "REG"
FROZEN_N_IDENTITIES = 16
FROZEN_GAME_IDS: tuple[str, ...] = (
    "2013_02_NYJ_NE",
    "2013_02_CAR_BUF",
    "2013_02_CLE_BAL",
    "2013_02_DAL_KC",
    "2013_02_MIA_IND",
    "2013_02_MIN_CHI",
    "2013_02_SD_PHI",
    "2013_02_STL_ATL",
    "2013_02_TEN_HOU",
    "2013_02_WAS_GB",
    "2013_02_DET_ARI",
    "2013_02_NO_TB",
    "2013_02_DEN_NYG",
    "2013_02_JAX_OAK",
    "2013_02_SF_SEA",
    "2013_02_PIT_CIN",
)

DEFAULT_GAMES = ROOT / "data" / "games_4fe1cdd7.csv"
DEFAULT_OUTCOMES = ROOT / "data" / "outcomes_2013_2022_score_only.csv"
DEFAULT_FROZEN = ROOT / "frozen" / "FROZEN_CONFIG_Q2PB_t5009u.json"
DEFAULT_FROZEN_MD = ROOT / "frozen" / "FROZEN_CONFIG_Q2PB_t5009u.md"
DEFAULT_MANIFEST = ROOT / "frozen" / "FROZEN_MANIFEST_2013_REG_W2.json"
DEFAULT_SIDECAR = ROOT / "inputs" / "q2_asof_sidecar_t5018u.json"
DEFAULT_IF_DEMO = ROOT / "inputs" / "if_demo_inputs_2013_reg_w2.json"
DEFAULT_OUTDIR = ROOT / "artifacts"

IDENTITY_FIELDS = ("game_id", "season", "week", "home", "away", "kickoff_utc")
SIDECAR_NUMERIC_FIELDS = (
    "q2_home_s",
    "q2_away_s",
    "q2_rating_diff",
    "q2_hfa",
    "q2_n_asof_games",
    "q2_asof_wl_diff",
    "q2_pm_new",
)
SIDECAR_PIN_FIELDS = ("q2_fit_sha", "q2_config_sha", "q2_asof_rule", "q2_games_pin")
STRENGTH_FIELDS = (
    "offense_index_home",
    "offense_index_away",
    "defense_index_home",
    "defense_index_away",
    "margin_mu",
    "total_mu",
    "sigma",
    "market_blend",
    "off_eff_h",
    "off_eff_a",
    "def_eff_h",
    "def_eff_a",
)

# Paths this adapter may open. Gated hist index / scored 1ee90fac are not among them.
ALLOWED_OPEN_NAMES = {
    "games_4fe1cdd7.csv",
    "outcomes_2013_2022_score_only.csv",
    "FROZEN_CONFIG_Q2PB_t5009u.json",
    "FROZEN_CONFIG_Q2PB_t5009u.md",
    "FROZEN_MANIFEST_2013_REG_W2.json",
    "q2_asof_sidecar_t5018u.json",
    "if_demo_inputs_2013_reg_w2.json",
}

# N4: do not emit scored 1ee90fac columns. Provenance mention on games.csv is keep-identical only.
SCORED_1EE90FAC_COLUMNS = (
    "pit_schedule_sha256",
    "pit_schedule_path",
    "trailing_offense",
    "trailing_defense",
    "epa_trailing_spread_home",
    "epa_trailing_total",
)


class AnnotateRefuse(RuntimeError):
    """Fail-closed refusal (row or batch). Never impute. Never expand the sample."""


@dataclass
class PinReport:
    games_sha256: str
    outcomes_sha256: str
    frozen_md_sha256: str
    fit_sha: str
    config_sha: str
    asof_rule: str
    sidecar_sha256: str
    manifest_sha256: str
    if_demo_sha256: str


@dataclass
class JoinResult:
    rows: list[dict[str, Any]]
    pins: PinReport
    artifacts: dict[str, str] = field(default_factory=dict)
    payload_sha256: str = ""


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
        raise AnnotateRefuse(f"{label} sha {digest[:8]} != required prefix {prefix}")


def _require_open(path: Path) -> Path:
    if path.name not in ALLOWED_OPEN_NAMES:
        raise AnnotateRefuse(f"refusing to open non-allowlisted path {path}")
    if not path.is_file():
        raise AnnotateRefuse(f"missing required file {path}")
    return path


def _parse_kickoff(raw: Any) -> datetime:
    if isinstance(raw, datetime):
        dt = raw
    else:
        s = str(raw).strip()
        if not s:
            raise AnnotateRefuse("non-finite / missing kickoff_utc")
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(s)
        except ValueError as exc:
            raise AnnotateRefuse(f"non-finite kickoff_utc: {raw!r}") from exc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def canonical_json_bytes(payload: Mapping[str, Any]) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def identity_tuple(row: Mapping[str, Any]) -> tuple[int, int, str, str]:
    try:
        season = int(row["season"])
        week = int(row["week"])
    except (KeyError, TypeError, ValueError) as exc:
        raise AnnotateRefuse("incomplete Game.key (season/week)") from exc
    home = str(row.get("home") or "").strip()
    away = str(row.get("away") or "").strip()
    if not home or not away:
        raise AnnotateRefuse("incomplete Game.key (home/away)")
    return (season, week, home, away)


def game_id_of(row: Mapping[str, Any]) -> str:
    return str(row.get("game_id") or "").strip()


def join_identity(sidecar: Mapping[str, Any], demo: Mapping[str, Any]) -> str:
    """#681 §3a / #683 §4: game_id if both have it; else Game.key. Fail-closed."""
    sid_gid = game_id_of(sidecar)
    dem_gid = game_id_of(demo)
    sid_key = identity_tuple(sidecar)
    dem_key = identity_tuple(demo)
    if sid_gid and dem_gid:
        if sid_gid != dem_gid:
            raise AnnotateRefuse(
                f"game_id mismatch sidecar={sid_gid!r} demo={dem_gid!r}"
            )
        if sid_key != dem_key:
            raise AnnotateRefuse(
                f"Game.key mismatch under game_id {sid_gid}: {sid_key} != {dem_key}"
            )
        return "game_id"
    if sid_key == dem_key:
        return "Game.key"
    raise AnnotateRefuse(
        f"join failure: neither game_id nor Game.key matched ({sid_key} vs {dem_key})"
    )


def load_json_object(path: Path) -> dict[str, Any]:
    _require_open(path)
    with path.open() as f:
        payload = json.load(f)
    if not isinstance(payload, dict):
        raise AnnotateRefuse(f"{path.name} is not an object")
    return payload


def verify_pins(
    games_path: Path,
    outcomes_path: Path,
    frozen: Mapping[str, Any],
    frozen_md_path: Path,
    sidecar_path: Path,
    manifest_path: Path,
    if_demo_path: Path,
) -> PinReport:
    """Refuse-on-mismatch for games/fit/FROZEN/as-of/outcomes + frozen inputs."""
    _require_open(games_path)
    _require_open(outcomes_path)
    _require_open(frozen_md_path)
    if games_path.name != "games_4fe1cdd7.csv":
        raise AnnotateRefuse(f"games path must be the 4fe1cdd7 pin, got {games_path.name}")
    if outcomes_path.name != "outcomes_2013_2022_score_only.csv":
        raise AnnotateRefuse(
            f"outcomes path must be the 50bda875 extract, got {outcomes_path.name}"
        )

    try:
        games_sha = verify_games_pin(games_path)
    except DataGuardError as exc:
        raise AnnotateRefuse(str(exc)) from exc
    _require_prefix(games_sha, SEALED_GAMES_PIN, "games")
    if games_sha != SEALED_GAMES_SHA:
        raise AnnotateRefuse("games.csv full sha256 != sealed 4fe1cdd7 object")

    outcomes_sha = sha256_file(outcomes_path)
    _require_prefix(outcomes_sha, "50bda875", "outcomes")
    if outcomes_sha != SEALED_OUTCOMES_SHA:
        raise AnnotateRefuse("outcomes extract full sha256 != sealed 50bda875 object")

    fit_sha = str(frozen.get("fit_object_sha256") or "")
    config_sha = str(frozen.get("config_sha256") or "")
    asof_rule = str(frozen.get("tip_asof") or "")
    _require_prefix(fit_sha, "70db070d", "fit")
    _require_prefix(config_sha, "aa2b47b3", "config")
    if fit_sha != SEALED_FIT_SHA:
        raise AnnotateRefuse("frozen fit_object_sha256 != sealed 70db070d")
    if config_sha != SEALED_CONFIG_SHA:
        raise AnnotateRefuse("frozen config_sha256 != sealed aa2b47b3")
    if asof_rule != SEALED_ASOF_RULE:
        raise AnnotateRefuse(f"tip_asof {asof_rule!r} != {SEALED_ASOF_RULE}")
    if str(frozen.get("tip_games") or "") != TIP_GAMES:
        raise AnnotateRefuse("frozen tip_games != 4fe1cdd7")

    try:
        lam = float(frozen["lam"])
        regress_frac = float(frozen["regress_frac"])
        a_q2 = float(frozen["a_q2"])
        b_q2 = float(frozen["b_q2"])
    except (KeyError, TypeError, ValueError) as exc:
        raise AnnotateRefuse("frozen missing sealed lam/r/a_q2/b_q2") from exc
    if lam != SEALED_LAM or regress_frac != SEALED_REGRESS_FRAC:
        raise AnnotateRefuse("frozen λ/r != sealed 20.0 / 0.5 (no retune)")
    if a_q2 != SEALED_A_Q2 or b_q2 != SEALED_B_Q2:
        raise AnnotateRefuse("frozen a_q2/b_q2 != sealed DEV OLS (no refit)")

    frozen_md_sha = sha256_file(frozen_md_path)
    _require_prefix(frozen_md_sha, "28c582a1", "frozen md")
    if frozen_md_sha != SEALED_FROZEN_MD_SHA:
        raise AnnotateRefuse("FROZEN md sha256 != sealed 28c582a1 object")

    sidecar_sha = sha256_file(sidecar_path)
    if sidecar_sha != SEALED_SIDECAR_SHA:
        raise AnnotateRefuse(
            f"sidecar artifact sha {sidecar_sha[:8]} != sealed #682 output {SEALED_SIDECAR_SHA[:8]}"
        )
    manifest_sha = sha256_file(manifest_path)
    if manifest_sha != SEALED_MANIFEST_SHA:
        raise AnnotateRefuse("frozen manifest sha mismatch (sample expanded or edited)")
    if_demo_sha = sha256_file(if_demo_path)
    if if_demo_sha != SEALED_IF_DEMO_SHA:
        raise AnnotateRefuse("IF/demo input sha mismatch (sample expanded or edited)")

    return PinReport(
        games_sha256=games_sha,
        outcomes_sha256=outcomes_sha,
        frozen_md_sha256=frozen_md_sha,
        fit_sha=fit_sha,
        config_sha=config_sha,
        asof_rule=asof_rule,
        sidecar_sha256=sidecar_sha,
        manifest_sha256=manifest_sha,
        if_demo_sha256=if_demo_sha,
    )


def validate_sidecar_row(row: Mapping[str, Any]) -> None:
    if not isinstance(row, Mapping):
        raise AnnotateRefuse("sidecar row is not a mapping")
    extra = set(row) & set(STRENGTH_FIELDS)
    if extra:
        raise AnnotateRefuse(f"sidecar row carries strength keys {sorted(extra)}")
    scored = set(row) & set(SCORED_1EE90FAC_COLUMNS)
    if scored:
        raise AnnotateRefuse(f"sidecar row carries scored 1ee90fac columns {sorted(scored)}")
    for name in IDENTITY_FIELDS + SIDECAR_NUMERIC_FIELDS + SIDECAR_PIN_FIELDS:
        if name not in row or row[name] is None or row[name] == "":
            raise AnnotateRefuse(f"sidecar missing field {name}")
    season = row["season"]
    week = row["week"]
    if not isinstance(season, int) or season != FROZEN_SCOPE_SEASON:
        raise AnnotateRefuse(f"sidecar season outside frozen 2013 REG W2: {season!r}")
    if season in SEALED_SEASONS:
        raise AnnotateRefuse("2024–25 sidecar row refused")
    if not isinstance(week, int) or week != FROZEN_SCOPE_WEEK:
        raise AnnotateRefuse(f"sidecar week outside frozen 2013 REG W2: {week!r}")
    _parse_kickoff(row["kickoff_utc"])
    if not isinstance(row["q2_n_asof_games"], int) or row["q2_n_asof_games"] < 0:
        raise AnnotateRefuse("q2_n_asof_games missing / non-finite")
    for name in SIDECAR_NUMERIC_FIELDS:
        if name == "q2_n_asof_games":
            continue
        if not _isfinite_number(row[name]):
            raise AnnotateRefuse(f"sidecar missing field {name}")
    if row["q2_fit_sha"] != SEALED_FIT_SHA:
        raise AnnotateRefuse("q2_fit_sha != sealed 70db070d")
    if row["q2_config_sha"] != SEALED_CONFIG_SHA:
        raise AnnotateRefuse("q2_config_sha != sealed aa2b47b3")
    if row["q2_asof_rule"] != SEALED_ASOF_RULE:
        raise AnnotateRefuse("q2_asof_rule != cf514078")
    if row["q2_games_pin"] != SEALED_GAMES_PIN:
        raise AnnotateRefuse("q2_games_pin != 4fe1cdd7")
    expected_pm = SEALED_A_Q2 + SEALED_B_Q2 * float(row["q2_rating_diff"])
    if not math.isclose(float(row["q2_pm_new"]), expected_pm, rel_tol=0.0, abs_tol=1e-12):
        raise AnnotateRefuse("q2_pm_new != sealed a_q2 + b_q2 · rating_diff")


def validate_demo_row(row: Mapping[str, Any]) -> None:
    if not isinstance(row, Mapping):
        raise AnnotateRefuse("IF/demo row is not a mapping")
    scored = set(row) & set(SCORED_1EE90FAC_COLUMNS)
    if scored:
        raise AnnotateRefuse(f"IF/demo carries scored 1ee90fac columns {sorted(scored)}")
    for name in IDENTITY_FIELDS + STRENGTH_FIELDS:
        if name not in row or row[name] is None or row[name] == "":
            raise AnnotateRefuse(f"IF/demo missing field {name}")
    if int(row["season"]) != FROZEN_SCOPE_SEASON or int(row["week"]) != FROZEN_SCOPE_WEEK:
        raise AnnotateRefuse("IF/demo row outside frozen 2013 REG W2")
    if int(row["season"]) in SEALED_SEASONS:
        raise AnnotateRefuse("2024–25 IF/demo row refused")
    _parse_kickoff(row["kickoff_utc"])
    for name in STRENGTH_FIELDS:
        if not _isfinite_number(row[name]):
            raise AnnotateRefuse(f"IF/demo non-finite {name}")


def load_frozen_manifest(path: Path) -> list[dict[str, Any]]:
    payload = load_json_object(path)
    if payload.get("frozen_before_run") is not True:
        raise AnnotateRefuse("manifest is not marked frozen_before_run")
    scope = payload.get("scope") or {}
    if (
        int(scope.get("season") or 0) != FROZEN_SCOPE_SEASON
        or int(scope.get("week") or 0) != FROZEN_SCOPE_WEEK
        or str(scope.get("season_type") or "") != FROZEN_SCOPE_SEASON_TYPE
    ):
        raise AnnotateRefuse("manifest scope != 2013 REG W2 (no silent expansion)")
    identities = payload.get("identities")
    if not isinstance(identities, list):
        raise AnnotateRefuse("manifest identities missing")
    if int(payload.get("n_identities") or 0) != FROZEN_N_IDENTITIES:
        raise AnnotateRefuse("manifest n_identities != frozen 16")
    if len(identities) != FROZEN_N_IDENTITIES:
        raise AnnotateRefuse("manifest identity count != frozen 16")
    ids = [game_id_of(row) for row in identities]
    if ids != list(FROZEN_GAME_IDS):
        raise AnnotateRefuse("manifest game_id set/order != frozen 2013 REG W2 eligible set")
    for row in identities:
        if int(row["season"]) != FROZEN_SCOPE_SEASON or int(row["week"]) != FROZEN_SCOPE_WEEK:
            raise AnnotateRefuse("manifest identity outside 2013 REG W2")
        identity_tuple(row)
        _parse_kickoff(row["kickoff_utc"])
    return list(identities)


def _index_by_game_id(rows: Sequence[Mapping[str, Any]], label: str) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        gid = game_id_of(row)
        if not gid:
            raise AnnotateRefuse(f"{label} row missing game_id (frozen demo requires it)")
        if gid in out:
            raise AnnotateRefuse(f"{label} duplicate game_id {gid}")
        out[gid] = dict(row)
    return out


def join_frozen_identities(
    identities: Sequence[Mapping[str, Any]],
    sidecar_rows: Sequence[Mapping[str, Any]],
    demo_rows: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Exact-identity join. Missing / extra / mismatch → refuse. No silent expansion."""
    sidecar_by_id = _index_by_game_id(sidecar_rows, "sidecar")
    demo_by_id = _index_by_game_id(demo_rows, "IF/demo")

    extra_sidecar = set(sidecar_by_id) - set(FROZEN_GAME_IDS)
    extra_demo = set(demo_by_id) - set(FROZEN_GAME_IDS)
    if extra_sidecar or extra_demo:
        raise AnnotateRefuse(
            f"silent sample expansion refused: extra sidecar={sorted(extra_sidecar)} extra demo={sorted(extra_demo)}"
        )

    joined: list[dict[str, Any]] = []
    kept_sidecar: list[dict[str, Any]] = []
    for ident in identities:
        gid = game_id_of(ident)
        if gid not in sidecar_by_id:
            raise AnnotateRefuse(f"missing sidecar identity {gid} (fail-closed)")
        if gid not in demo_by_id:
            raise AnnotateRefuse(f"missing IF/demo identity {gid} (fail-closed)")
        sidecar_row = sidecar_by_id[gid]
        demo_row = demo_by_id[gid]
        validate_sidecar_row(sidecar_row)
        validate_demo_row(demo_row)
        join_identity(ident, sidecar_row)
        join_key = join_identity(sidecar_row, demo_row)
        joined.append(annotate_row(demo_row, sidecar_row, join_key))
        kept_sidecar.append(sidecar_row)

    if len(joined) != FROZEN_N_IDENTITIES:
        raise AnnotateRefuse("joined count != frozen 16 (no silent expansion)")
    return joined, kept_sidecar


def snapshot_strength(row: Mapping[str, Any]) -> dict[str, Any]:
    return {name: row[name] for name in STRENGTH_FIELDS}


def copy_strength_unchanged(demo: Mapping[str, Any]) -> dict[str, Any]:
    copied = snapshot_strength(demo)
    # Isolation: values are copied, never recomputed or blended with q2_*.
    return copied


def annotate_row(
    demo: Mapping[str, Any],
    sidecar: Mapping[str, Any],
    join_key: str,
) -> dict[str, Any]:
    strength = copy_strength_unchanged(demo)
    if strength != snapshot_strength(demo):
        raise AnnotateRefuse("strength mutation during copy")
    row: dict[str, Any] = {
        "game_id": game_id_of(sidecar),
        "season": int(sidecar["season"]),
        "week": int(sidecar["week"]),
        "home": sidecar["home"],
        "away": sidecar["away"],
        "kickoff_utc": sidecar["kickoff_utc"],
    }
    row.update(strength)
    for name in SIDECAR_NUMERIC_FIELDS + SIDECAR_PIN_FIELDS:
        row[name] = sidecar[name]
    row["dev_research_label"] = "DEV_RESEARCH"
    row["cert"] = 0
    row["not_a_forecast_quality_claim"] = True
    row["join_key"] = join_key
    row["annotation"] = {
        "card": CARD,
        "cert": 0,
        "join_key": join_key,
        "label": "DEV_RESEARCH",
        "mode": "CLEAR_ANNOTATE",
        "not_a_forecast_quality_claim": True,
        "owner": OWNER,
        "writer_accept": WRITER_ACCEPT,
        "writer_head": WRITER_HEAD[:8],
    }
    if row["margin_mu"] == row["q2_pm_new"]:
        # Distinct demo values were chosen so this cannot happen by construction.
        # Guard anyway: q2_pm_new must never be written into margin_mu.
        raise AnnotateRefuse("q2_pm_new collided with margin_mu (forbidden write)")
    if snapshot_strength(row) != strength:
        raise AnnotateRefuse("strength fields mutated while attaching annotations")
    scored = set(row) & set(SCORED_1EE90FAC_COLUMNS)
    if scored:
        raise AnnotateRefuse(f"emit carried scored 1ee90fac columns {sorted(scored)}")
    return row


def feats_from_sidecar_rows(rows: Sequence[Mapping[str, Any]]) -> list[AsOfFeatures]:
    feats: list[AsOfFeatures] = []
    for row in rows:
        game = Game(
            season=int(row["season"]),
            week=int(row["week"]),
            game_id=game_id_of(row),
            home=str(row["home"]),
            away=str(row["away"]),
            kickoff_utc=_parse_kickoff(row["kickoff_utc"]),
            home_score=0.0,
            away_score=0.0,
            record_entering_home="0-0",
            record_entering_away="0-0",
            market_spread_home=None,
        )
        feats.append(
            AsOfFeatures(
                game=game,
                home_s=float(row["q2_home_s"]),
                away_s=float(row["q2_away_s"]),
                rating_diff=float(row["q2_rating_diff"]),
                n_asof_games=int(row["q2_n_asof_games"]),
                hfa=float(row["q2_hfa"]),
            )
        )
    return feats


def _payload(result_rows: Sequence[Mapping[str, Any]], pins: PinReport) -> dict[str, Any]:
    return {
        "authority": {
            "alex_formula_held": ALEX_FORMULA_HELD,
            "card": CARD,
            "guardrails": GUARDRAILS,
            "order_n1": ORDER_N1,
            "owner": OWNER,
            "proposal_head": PROPOSAL_HEAD[:8],
            "wiring_card": WIRING_CARD,
            "work_package": WORK_PACKAGE,
            "writer_accept": WRITER_ACCEPT,
            "writer_head": WRITER_HEAD[:8],
        },
        "cert": 0,
        "holds": [
            "CERT=0",
            "pub/bet HOLD",
            "NFL NO-GO",
            "no Layer 3 caller change",
            "no extra EVAL",
            "no retune",
            "no Stage C",
            "no 2024-25",
            "no scored 1ee90fac columns",
            "Alex formula fa36c679 NOT authorized",
            "no #681 §8 amendment",
        ],
        "isolation": {
            "calls_simulate_nfl_game": False,
            "edits_nfl_game_inputs": False,
            "edits_routes_nfl_py": False,
            "edits_score_t4910u": False,
            "edits_tasks_py": False,
            "invokes_asof_for_targets": False,
            "joins_forecast_path": False,
            "mutates_defense_index": False,
            "mutates_l0": False,
            "mutates_margin_mu": False,
            "mutates_market_blend": False,
            "mutates_offense_index": False,
            "rewrites_q2_writer": False,
        },
        "label": "DEV_RESEARCH",
        "mode": "CLEAR_ANNOTATE",
        "n_emitted": len(result_rows),
        "n_identities": FROZEN_N_IDENTITIES,
        "not_a_forecast_quality_claim": True,
        "pins": {
            "asof": pins.asof_rule,
            "config": pins.config_sha,
            "fit": pins.fit_sha,
            "frozen_md": pins.frozen_md_sha256,
            "games": pins.games_sha256,
            "if_demo": pins.if_demo_sha256,
            "manifest": pins.manifest_sha256,
            "outcomes": pins.outcomes_sha256,
            "sidecar": pins.sidecar_sha256,
        },
        "research_consumed_only": True,
        "rows": list(result_rows),
        "scope": {
            "season": FROZEN_SCOPE_SEASON,
            "season_type": FROZEN_SCOPE_SEASON_TYPE,
            "week": FROZEN_SCOPE_WEEK,
        },
    }


def emit_annotations(
    *,
    games_path: Path = DEFAULT_GAMES,
    outcomes_path: Path = DEFAULT_OUTCOMES,
    frozen_path: Path = DEFAULT_FROZEN,
    frozen_md_path: Path = DEFAULT_FROZEN_MD,
    manifest_path: Path = DEFAULT_MANIFEST,
    sidecar_path: Path = DEFAULT_SIDECAR,
    if_demo_path: Path = DEFAULT_IF_DEMO,
    outdir: Path | None = None,
    write_files: bool = True,
) -> JoinResult:
    """Join #682 sidecar onto frozen IF/demo rows. Isolation: files under outdir only."""
    frozen = load_json_object(frozen_path)
    pins = verify_pins(
        games_path,
        outcomes_path,
        frozen,
        frozen_md_path,
        sidecar_path,
        manifest_path,
        if_demo_path,
    )
    identities = load_frozen_manifest(manifest_path)

    sidecar_payload = load_json_object(sidecar_path)
    sidecar_rows = sidecar_payload.get("rows")
    if not isinstance(sidecar_rows, list):
        raise AnnotateRefuse("sidecar artifact missing rows")
    demo_payload = load_json_object(if_demo_path)
    demo_rows = demo_payload.get("rows")
    if not isinstance(demo_rows, list):
        raise AnnotateRefuse("IF/demo artifact missing rows")

    joined, kept_sidecar = join_frozen_identities(identities, sidecar_rows, demo_rows)

    try:
        outcomes = load_outcomes_score_only(outcomes_path, (FROZEN_SCOPE_SEASON,))
        history = load_games(
            games_path, outcomes, (FROZEN_SCOPE_SEASON,), phase="lane_a_annotate_asof"
        )
    except DataGuardError as exc:
        raise AnnotateRefuse(str(exc)) from exc

    feats = feats_from_sidecar_rows(kept_sidecar)
    try:
        assert_asof_leakage(history, feats)
    except AssertionError as exc:
        raise AnnotateRefuse(f"assert_asof_leakage refused: {exc}") from exc

    payload = _payload(joined, pins)
    blob = canonical_json_bytes(payload)
    digest = sha256_bytes(blob)
    result = JoinResult(rows=joined, pins=pins, payload_sha256=digest)
    if write_files:
        dest = Path(outdir) if outdir is not None else DEFAULT_OUTDIR
        dest.mkdir(parents=True, exist_ok=True)
        json_path = dest / "lane_a_annotations_t5029u.json"
        md_path = dest / "lane_a_annotations_t5029u.md"
        json_path.write_bytes(blob)
        md_path.write_text(_markdown(payload, digest), encoding="utf-8")
        result.artifacts = {"json": str(json_path), "md": str(md_path)}
    return result


def _markdown(payload: Mapping[str, Any], digest: str) -> str:
    lines = [
        "# t5029u Lane A CLEAR_ANNOTATE — DEV_RESEARCH labels",
        "",
        "**Label:** DEV_RESEARCH · CERT=0 · NFL NO-GO · NOT a forecast quality claim.",
        "**Mode:** offline identity join only. Do not merge · do not deploy · do not pub/bet.",
        "",
        f"- OWNER `{OWNER}` · card `{CARD}` CLEAR_ANNOTATE · work-package `{WORK_PACKAGE}` · guardrails `{GUARDRAILS}`",
        f"- #682 writer head `{WRITER_HEAD[:8]}` / ACCEPT `{WRITER_ACCEPT}` (read-only; not rewritten)",
        f"- #683 proposal head `{PROPOSAL_HEAD[:8]}` · wiring `{WIRING_CARD}` (N2) · ORDER N1 `{ORDER_N1}`",
        f"- Scope: **2013 REG W2** · n={payload['n_emitted']} · payload sha256 `{digest}`",
        "- Strength / margin / L0 fields copied unchanged. `q2_*` sit beside as annotations.",
        f"- Alex formula `{ALEX_FORMULA_HELD}` NOT authorized. No #681 §8 amendment. No Stage C.",
        "",
        "| game_id | join | q2_rating_diff | q2_pm_new | margin_mu (unchanged) |",
        "| --- | --- | ---: | ---: | ---: |",
    ]
    for row in payload["rows"]:
        lines.append(
            f"| `{row['game_id']}` | {row['join_key']} | {row['q2_rating_diff']:.6f} | "
            f"{row['q2_pm_new']:.6f} | {row['margin_mu']:.4f} |"
        )
    lines.append("")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="t5029u Lane A CLEAR_ANNOTATE join (DEV_RESEARCH, CERT=0)."
    )
    parser.add_argument(
        "--outdir",
        type=Path,
        default=DEFAULT_OUTDIR,
        help="Artifact directory (default: research/.../artifacts)",
    )
    args = parser.parse_args(argv)
    result = emit_annotations(outdir=args.outdir, write_files=True)
    print(
        f"DEV_RESEARCH CERT=0 CLEAR_ANNOTATE n={len(result.rows)} "
        f"sha={result.payload_sha256} out={args.outdir}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
