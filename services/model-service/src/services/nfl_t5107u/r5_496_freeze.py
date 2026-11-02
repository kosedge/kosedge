"""t5155u R5 Phase 1 FREEZE — DEV_R5_496 opt-in (CERT=0).

Isolated Worker A path. Preserves earlier runners/forecasts/results.
NOT EVAL / production / market-edge / GREEN. No target scoring loader.

Worker B owns N1 + market intersection + integration-owner combine.
This module does not edit metric_cohorts / eval_result_contract / verify_integrate.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from .builder import challenger_margin
from .cohort_enforcement import (
    DEV_IF437_IDENTITY_SHA256,
    FEATURE_RECON_REG496_ARTIFACT_PATH,
    FEATURE_RECON_REG496_ARTIFACT_SHA256,
    PROFILE_DEV_IF437,
    PROFILE_FEATURE_RECON_REG496,
    REG496_IDENTITY_SHA256,
    OutcomeReadSpy,
    check_cohort_before_feature_output_finalization,
    check_cohort_before_target_outcome_loading,
    expected_profile_ids,
    load_artifact_game_ids,
    sha256_file,
)
from .if_control import REQUIRED_FIELDS
from .if_produce import (
    FW_SHA256,
    IF_TIP,
    SIM_SHA256,
    SIMULATIONS,
    produce_if_mu,
    seed_for,
    sha256_file as sha256_if_file,
)
from .last_played_cohort import (
    EXPECTED_REG,
    EXPECTED_REG_TOTAL,
    SCHEDULE_PATH,
    SCHEDULE_SHA256,
    WILDCARD_2020_W18,
)
from .q2 import (
    A_Q2,
    B_Q2,
    FIT_POLICY,
    GAMES_SHA256,
    LAMBDA,
    OUTCOMES_SHA256,
    PARAMETER_LABEL,
    REGRESS_FRAC,
    TRAINING_SEASONS,
    Game,
    Q2Refuse,
    asof_for_targets,
    assert_asof_no_self_target,
    parse_kickoff,
    q2_pm_new,
    verify_q2_transfer_policy,
)
from .recon_contract import CONTRACT_27, EPA_FIELDS, INDEX_FIELDS, REST_FIELDS, TEXT_FIELDS, _finite
from .recon_driver import DEFAULT_GAMES_CANDIDATES, DEFAULT_OUTCOMES_CANDIDATES

SCHEMA = "nfl-t5155u-r5-496-freeze-v1"
PATH_ID = "DEV_R5_496"
TICKET = "t5155u"
OWNER_CLEAR_SHA8 = "659cd7d9"
COS_ORDER_SHA8 = "3e14602b"
PARENT_TIP_SHA8 = "t5155u"
CERT_CANDIDATE = 0
LABEL_RECONSTRUCTED = "RECONSTRUCTED"
LABEL_RETRO_FIT = "RETRO_FIT"
LABEL_RESEARCH = "RESEARCH_CONSUMED_RETRO"

FEATURE_MATRIX_PATH = (
    "data/ops/nfl-t5146u-r4-last-played-dev/DEV_RECON_LAST_PLAYED_2020_2021_REG_MATRIX.csv"
)
FEATURE_MATRIX_SHA256 = (
    "a3b9d8ecb94902078ddcb89206a5a1ff16d5f1a3b4e8080186238d6578c52409"
)
OLD_IF_FREEZE_PATH = "data/ops/nfl-forecast-builder-t5107u/FORECAST_FREEZE_t5112u.json"
OLD_IF_FREEZE_SHA256 = (
    "9e704b980b6ce33acc883725823c39766ea19f8a86a7a781ac2a02d95344a732"
)
EXACT_WEEK_MATRIX = {
    2020: "data/ops/nfl-forecast-builder-t5107u/recon/RECON_MATRIX_2020_REG_W2W18.csv",
    2021: "data/ops/nfl-forecast-builder-t5107u/recon/RECON_MATRIX_2021_REG_W2W18.csv",
}
R4_496_ACCEPTED_TIP = "bc1b62fc13a1c16ba1e39ccce39fb60180dc565e"
R4_496_STAMP = "c58ec422204406950d5605cdff5c172b54bd1a82"
R3_STOP = "81b6c0fc"
R3_WEIGHT_STOPPED = 0.75
CANDIDATE_WEIGHT = 0.5
KO_MINUS = timedelta(minutes=60)
REPLAY_REL = 1e-9
SEALED_SEASONS = (2022, 2023, 2024, 2025, 2026)
EARLIER_YEARS = (2013, 2014, 2015, 2016, 2017, 2018, 2019)
PROVEN_REG_YEARS = (2020, 2021)
OUT_DIR = Path("data/ops/nfl-t5155u-r5-496-freeze")

FORBIDDEN_SCORE_KEYS = (
    "actual_margin",
    "actual_total",
    "home_score",
    "away_score",
    "error",
    "abs_error",
    "signed_error",
    "look",
    "eval_score",
    "ats",
    "cover",
)
WORKER_B_OWNED = (
    "metric_cohorts.py numerical strengthening",
    "eval_result_contract.py",
    "verify_integrate.py",
    "N1",
    "market intersection",
    "integration-owner combine",
)

LIMITATIONS = {
    "publication_timestamp_status": "unverified",
    "observation_timestamp_status": "unverified",
    "fit_label": LABEL_RETRO_FIT,
    "label": LABEL_RECONSTRUCTED,
    "research_label": LABEL_RESEARCH,
    "production_causal_claim": False,
    "nfl_green": False,
    "eval": None,
    "scoring": None,
    "market_edge": None,
    "cert_candidate": CERT_CANDIDATE,
}


class R5FreezeRefuse(ValueError):
    """Fail-closed R5 Phase 1 freeze."""


class TargetScoringRefuse(R5FreezeRefuse):
    """Phase 1 must not load target scoring labels."""


def _repo_root(root: Path | None) -> Path:
    if root is not None:
        return Path(root)
    return Path(__file__).resolve().parents[5]


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def replay_ok(new: float, old: float) -> bool:
    """Identical IF pins/seed must replay within 1e-9 * max(1, |old|)."""
    return abs(float(new) - float(old)) <= REPLAY_REL * max(1.0, abs(float(old)))


def _as_ids(values: Sequence[str] | None) -> list[str]:
    return [str(v) for v in (values or [])]


def _n_by_season(game_ids: Sequence[str]) -> dict[str, int]:
    return dict(sorted(Counter(str(g).split("_", 1)[0] for g in game_ids).items()))


def _scan_forbidden_scores(payload: Mapping[str, Any], *, where: str) -> None:
    blob = json.dumps(payload, default=str).casefold()
    for key in FORBIDDEN_SCORE_KEYS:
        token = f'"{key}"'
        if token in blob:
            raise TargetScoringRefuse(f"{where} contains forbidden target-score key {key}")


def refuse_week_le_18_proxy(*, claimed_reg: bool, used_week_le_18: bool) -> None:
    if claimed_reg and used_week_le_18:
        raise R5FreezeRefuse(
            "No week<=18 REG proxy — season_type=REG on an approved schedule is required"
        )


def freeze_identities(root: Path | None = None) -> dict[str, Any]:
    """Freeze FEATURE_RECON_REG496 identities first. 240+256 REG W2+; keep 2021 W18; refuse 6 WC."""
    repo = _repo_root(root)
    artifact = repo / FEATURE_RECON_REG496_ARTIFACT_PATH
    matrix = repo / FEATURE_MATRIX_PATH
    digest = sha256_file(artifact)
    if digest != FEATURE_RECON_REG496_ARTIFACT_SHA256:
        raise R5FreezeRefuse(
            f"FEATURE_RECON_REG496 artifact sha {digest} != pin 282f979b"
        )
    matrix_digest = sha256_file(matrix)
    if matrix_digest != FEATURE_MATRIX_SHA256:
        raise R5FreezeRefuse(f"REG496 matrix sha {matrix_digest} != pin a3b9d8ec")
    schedule_ids = expected_profile_ids(PROFILE_FEATURE_RECON_REG496, repo)
    if437 = expected_profile_ids(PROFILE_DEV_IF437, repo)
    artifact_ids = load_artifact_game_ids(artifact)
    if set(WILDCARD_2020_W18) & set(artifact_ids):
        raise R5FreezeRefuse("FEATURE_RECON_REG496 contains 6 2020 Wild Cards — refuse")
    if set(WILDCARD_2020_W18) & set(schedule_ids):
        raise R5FreezeRefuse("schedule FEATURE_RECON_REG496 leaked 2020 Wild Cards")
    w18 = [g for g in schedule_ids if g.startswith("2021_18_")]
    if len(w18) != 16:
        raise R5FreezeRefuse(f"2021 REG week 18 not retained ({len(w18)} != 16)")
    if any(g.startswith("2020_18_") for g in schedule_ids):
        raise R5FreezeRefuse("2020 week-18 (Wild Card) leaked into FEATURE_RECON_REG496")
    gate = check_cohort_before_feature_output_finalization(
        PROFILE_FEATURE_RECON_REG496,
        artifact_ids,
        candidate_bytes_sha=digest,
        expected_bytes_sha=FEATURE_RECON_REG496_ARTIFACT_SHA256,
        root=repo,
    )
    if gate["identity_sha256"] != REG496_IDENTITY_SHA256:
        raise R5FreezeRefuse("FEATURE_RECON_REG496 identity drifted from 6429f859")
    if _n_by_season(schedule_ids) != {"2020": 240, "2021": 256}:
        raise R5FreezeRefuse(f"REG496 season counts drifted {_n_by_season(schedule_ids)}")
    if set(artifact_ids) != set(schedule_ids):
        raise R5FreezeRefuse("artifact ID set != schedule FEATURE_RECON_REG496")
    if len(schedule_ids) != EXPECTED_REG_TOTAL:
        raise R5FreezeRefuse(f"n={len(schedule_ids)} != 496")
    payload = {
        "schema_version": SCHEMA,
        "path_id": PATH_ID,
        "ticket": TICKET,
        "profile": PROFILE_FEATURE_RECON_REG496,
        "n": len(schedule_ids),
        "n_by_season": {"2020": 240, "2021": 256},
        "identity_sha256": REG496_IDENTITY_SHA256,
        "identity_order": "schedule_results_2020_2023.csv season_type=REG week>=2 (2020_02_ATL_DAL first)",
        "artifact_order_first": artifact_ids[0],
        "schedule_order_first": schedule_ids[0],
        "sets_match_sources_differ": True,
        "artifact_path": FEATURE_RECON_REG496_ARTIFACT_PATH,
        "artifact_sha256": FEATURE_RECON_REG496_ARTIFACT_SHA256,
        "matrix_path": FEATURE_MATRIX_PATH,
        "matrix_sha256": FEATURE_MATRIX_SHA256,
        "schedule_path": SCHEDULE_PATH,
        "schedule_sha256": SCHEDULE_SHA256,
        "membership_rule": "season_type=REG; week>=2; not week<=18",
        "week_le_18_proxy": False,
        "r4_496_accepted_tip": R4_496_ACCEPTED_TIP,
        "r4_496_stamp": R4_496_STAMP,
        "pr_698": True,
        "game_ids": schedule_ids,
        "artifact_game_ids": artifact_ids,
        "reg_week18_2021_retained": w18,
        "wildcard_2020_refused": list(WILDCARD_2020_W18),
        "dev_if437_n": len(if437),
        "dev_if437_identity_sha256": DEV_IF437_IDENTITY_SHA256,
        "labels": [LABEL_RECONSTRUCTED, LABEL_RETRO_FIT],
        **LIMITATIONS,
    }
    _scan_forbidden_scores(payload, where="identity freeze")
    return payload


def split_scaffolding(
    reg496_ids: Sequence[str],
    if437_ids: Sequence[str],
) -> dict[str, Any]:
    """full496 / old437 / new59 from frozen identities — not outcomes."""
    full = _as_ids(reg496_ids)
    old = _as_ids(if437_ids)
    if len(full) != 496:
        raise R5FreezeRefuse(f"full496 n={len(full)} != 496")
    if len(old) != 437:
        raise R5FreezeRefuse(f"old437 n={len(old)} != 437")
    extra = sorted(set(old) - set(full))
    if extra:
        raise R5FreezeRefuse(f"old437 not subset of FEATURE_RECON_REG496: {extra[:8]}")
    new = [g for g in full if g not in set(old)]
    if len(new) != 59:
        raise R5FreezeRefuse(f"new59 n={len(new)} != 59")
    if set(WILDCARD_2020_W18) & set(full):
        raise R5FreezeRefuse("split scaffolding leaked 2020 Wild Cards")
    return {
        "schema_version": SCHEMA,
        "path_id": PATH_ID,
        "from_outcomes": False,
        "from_frozen_identities": True,
        "full496": {
            "n": 496,
            "n_by_season": _n_by_season(full),
            "identity_sha256": REG496_IDENTITY_SHA256,
            "game_ids": full,
        },
        "old437": {
            "n": 437,
            "n_by_season": _n_by_season(old),
            "identity_sha256": DEV_IF437_IDENTITY_SHA256,
            "game_ids": old,
            "source": "DEV_IF437 / previously-complete exact-week no-bye",
        },
        "new59": {
            "n": 59,
            "n_by_season": _n_by_season(new),
            "game_ids": new,
            "source": "FEATURE_RECON_REG496 minus DEV_IF437 (last-played recovered + remaining REG)",
        },
        "labels": [LABEL_RECONSTRUCTED, LABEL_RETRO_FIT],
        "cert_candidate": CERT_CANDIDATE,
        "eval": None,
        "scoring": None,
    }


def load_feature_matrix(root: Path | None = None) -> list[dict[str, str]]:
    repo = _repo_root(root)
    path = repo / FEATURE_MATRIX_PATH
    digest = sha256_file(path)
    if digest != FEATURE_MATRIX_SHA256:
        raise R5FreezeRefuse(f"feature matrix sha {digest} != a3b9d8ec")
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise R5FreezeRefuse("feature matrix empty")
    return rows


def packets_from_matrix(rows: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, dict[str, Any]]]:
    by_game: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        by_game[str(row["game_id"])].append(row)
    packets: dict[str, dict[str, dict[str, Any]]] = {}
    for gid, cells in by_game.items():
        packet: dict[str, dict[str, Any]] = {}
        for cell in cells:
            field = str(cell["field"])
            packet[field] = {
                "status": cell.get("status"),
                "reconstructed_value": cell.get("reconstructed_value"),
                "source_path": cell.get("source_path"),
                "source_sha256": cell.get("source_sha256"),
                "derivation_lineage": cell.get("derivation_lineage"),
                "availability_evidence": cell.get("availability_evidence"),
                "label": cell.get("label"),
                "fit_label": cell.get("fit_label"),
                "row_sha256": cell.get("row_sha256"),
                "pregame_cutoff_utc": cell.get("pregame_cutoff_utc"),
            }
        packets[gid] = packet
    return packets


def _numeric_fields() -> set[str]:
    return set(CONTRACT_27) - TEXT_FIELDS


def validate_27_inputs(
    rows: Sequence[Mapping[str, Any]],
    *,
    expected_ids: Sequence[str],
    identities: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Validate all 27 required inputs + lineage / finiteness / identity."""
    packets = packets_from_matrix(rows)
    expected = _as_ids(expected_ids)
    if set(packets) != set(expected):
        extra = sorted(set(packets) - set(expected))
        missing = sorted(set(expected) - set(packets))
        raise R5FreezeRefuse(
            f"matrix IDs != FEATURE_RECON_REG496 extra={extra[:8]} missing={missing[:8]}"
        )
    ident_by = {str(r["game_id"]): r for r in (identities or [])}
    fails: list[dict[str, Any]] = []
    complete: list[str] = []
    for gid in expected:
        packet = packets[gid]
        missing_fields = [f for f in REQUIRED_FIELDS if f not in packet]
        if missing_fields:
            fails.append({"game_id": gid, "reason": "missing_fields", "fields": missing_fields})
            continue
        extra_fields = sorted(set(packet) - set(CONTRACT_27))
        if extra_fields:
            fails.append({"game_id": gid, "reason": "unknown_fields", "fields": extra_fields})
        ok = True
        for field in CONTRACT_27:
            cell = packet[field]
            if str(cell.get("status") or "") != "DERIVED_PREGAME":
                fails.append({"game_id": gid, "field": field, "reason": "status_not_DERIVED_PREGAME"})
                ok = False
                continue
            if cell.get("label") != LABEL_RECONSTRUCTED or cell.get("fit_label") != LABEL_RETRO_FIT:
                fails.append({"game_id": gid, "field": field, "reason": "labels"})
                ok = False
            if not cell.get("source_sha256") or not cell.get("derivation_lineage"):
                fails.append({"game_id": gid, "field": field, "reason": "lineage_or_source_hash"})
                ok = False
            value = cell.get("reconstructed_value")
            if field in TEXT_FIELDS:
                if value in (None, ""):
                    fails.append({"game_id": gid, "field": field, "reason": "empty_identity"})
                    ok = False
            else:
                try:
                    number = float(value)
                except (TypeError, ValueError):
                    fails.append({"game_id": gid, "field": field, "reason": "non_numeric"})
                    ok = False
                    continue
                if not math.isfinite(number):
                    fails.append({"game_id": gid, "field": field, "reason": "non_finite"})
                    ok = False
        ident = ident_by.get(gid)
        if ident is not None:
            if int(ident.get("derived") or 0) != 27 or int(ident.get("missing") or 0) != 0:
                fails.append({"game_id": gid, "reason": "identity_not_27_of_27"})
                ok = False
            labels = set(ident.get("labels") or [])
            if LABEL_RECONSTRUCTED not in labels or LABEL_RETRO_FIT not in labels:
                fails.append({"game_id": gid, "reason": "identity_labels"})
                ok = False
        if str(packet["game_id"]["reconstructed_value"]) != gid:
            fails.append({"game_id": gid, "reason": "game_id_mismatch"})
            ok = False
        if ok:
            complete.append(gid)
    if fails or len(complete) != 496:
        raise R5FreezeRefuse(
            f"27-input validation failed n_complete={len(complete)} n_fails={len(fails)} "
            f"sample={fails[:4]}"
        )
    return {
        "schema_version": SCHEMA,
        "n": 496,
        "n_complete_27": 496,
        "n_partial": 0,
        "n_refused": 0,
        "n_fails": 0,
        "required_fields": list(CONTRACT_27),
        "labels": [LABEL_RECONSTRUCTED, LABEL_RETRO_FIT],
        "lineage_required": True,
        "finiteness_required": True,
        "identity_required": True,
        "complete_game_ids": complete,
        **LIMITATIONS,
    }


def _locate_pin(candidates: Sequence[Path], expected_sha: str, label: str) -> tuple[Path | None, str | None]:
    for path in candidates:
        if path.is_file():
            digest = sha256_file(path)
            if digest != expected_sha:
                raise R5FreezeRefuse(f"{label} sha {digest} != pin {expected_sha[:8]}")
            return path, digest
    return None, None


def freeze_q2_history_sources(root: Path | None = None) -> dict[str, Any]:
    """Freeze score-source hashes + REG membership proof. No week<=18 proxy.

    2013–2019 have no approved season_type=REG extract in-repo. HOLD Q2 prior.
    2020–2021 REG membership is proven via schedule_results_2020_2023.csv.
    """
    repo = _repo_root(root)
    refuse_week_le_18_proxy(claimed_reg=True, used_week_le_18=False)
    transfer = verify_q2_transfer_policy(proposed_refit=False)
    games_path, games_sha = _locate_pin(DEFAULT_GAMES_CANDIDATES, GAMES_SHA256, "games.csv")
    outcomes_path, outcomes_sha = _locate_pin(
        DEFAULT_OUTCOMES_CANDIDATES, OUTCOMES_SHA256, "outcomes 50bda875"
    )
    schedule = repo / SCHEDULE_PATH
    schedule_sha = sha256_file(schedule)
    if schedule_sha != SCHEDULE_SHA256:
        raise R5FreezeRefuse("REG schedule pin drifted")

    proven: dict[str, Any] = {}
    with schedule.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            season = int(row["season"])
            if season not in PROVEN_REG_YEARS:
                continue
            if str(row["season_type"]).upper() != "REG":
                continue
            proven.setdefault(str(season), []).append(str(row["game_id"]))

    missing_earlier: list[dict[str, Any]] = []
    for year in EARLIER_YEARS:
        missing_earlier.append(
            {
                "season": year,
                "reg_membership": "UNPROVEN",
                "prior": "UNPROVEN",
                "missing_proof": (
                    f"{year} has no approved season_type=REG schedule extract. "
                    "games.csv 4fe1cdd7 has kickoff_utc but no season_type "
                    f"(week 18 n>0 for {year} — POST/WC cannot be filtered without "
                    "week<=18 REG proxy, which is refused). outcomes 50bda875 is "
                    "score-only and also lacks season_type."
                ),
            }
        )

    hold_q2 = True
    hold_reason = (
        "Q2 prior/carry requires canonically identified REG score history for "
        "2013–2019. Those years are UNPROVEN. HOLD Q2 leg. IF pipeline continues. "
        "No invented history. Disclose: this is not the old kickoff-only as-of."
    )
    return {
        "schema_version": SCHEMA,
        "path_id": PATH_ID,
        "history_rule": {
            "name": "R5_REG_SCORE_HISTORY_V1",
            "disclose_not_old_kickoff_only_asof": True,
            "old_asof": "cf514078 kickoff strictly before target (same-week earlier games allowed)",
            "r5": (
                "approved 2013–2021 REG only; for target season/week only earlier "
                "seasons + strictly earlier NFL weeks with kickoff < KO-60; "
                "no same-week / own-target / later rows; no week<=18 REG proxy"
            ),
            "ko_minus_minutes": 60,
        },
        "transfer": transfer,
        "a_q2": A_Q2,
        "b_q2": B_Q2,
        "ridge": LAMBDA,
        "prior_reg": REGRESS_FRAC,
        "refit": False,
        "search": False,
        "parameter_label": PARAMETER_LABEL,
        "fit_policy": FIT_POLICY,
        "training_seasons": list(TRAINING_SEASONS),
        "score_sources": {
            "games_csv": {
                "sha256": games_sha or GAMES_SHA256,
                "path": str(games_path) if games_path else None,
                "present": games_path is not None,
                "season_type_column": False,
                "role": "kickoff identity only — not REG membership",
            },
            "outcomes_50bda875": {
                "sha256": outcomes_sha or OUTCOMES_SHA256,
                "path": str(outcomes_path) if outcomes_path else None,
                "present": outcomes_path is not None,
                "season_type_column": False,
                "role": "score-only 2013–2022 — REG membership not proven by this file",
            },
            "schedule_results_2020_2023": {
                "sha256": schedule_sha,
                "path": SCHEDULE_PATH,
                "present": True,
                "season_type_column": True,
                "proven_reg_years": list(PROVEN_REG_YEARS),
                "role": "authoritative REG membership 2020–21 (and 2022–23 unused here)",
            },
        },
        "reg_membership": {
            str(year): {
                "status": "PROVEN",
                "n_reg_ids": len(proven.get(str(year), [])),
                "source": SCHEDULE_PATH,
            }
            for year in PROVEN_REG_YEARS
        }
        | {str(row["season"]): row for row in missing_earlier},
        "q2_leg": "HOLD",
        "hold_q2": hold_q2,
        "hold_reason": hold_reason,
        "invented_history": False,
        "week_le_18_proxy": False,
        "r3_weight_stopped": R3_WEIGHT_STOPPED,
        "r3_stop": R3_STOP,
        "candidate_weight": CANDIDATE_WEIGHT,
        "cert_candidate": CERT_CANDIDATE,
        "eval": None,
        "scoring": None,
    }


def r5_history_for_target(
    history: Sequence[Game],
    target: Game,
    *,
    proven_reg_ids: Sequence[str] | None = None,
    proven_reg_years: Sequence[int] | None = None,
) -> list[Game]:
    """Earlier seasons + strictly earlier NFL weeks, kickoff < KO-60. No same-week."""
    if target.season in SEALED_SEASONS:
        raise R5FreezeRefuse(f"refusing sealed/forbidden season {target.season}")
    cutoff = target.kickoff_utc - KO_MINUS
    allowed_years = set(proven_reg_years) if proven_reg_years is not None else set(PROVEN_REG_YEARS)
    allowed_ids = set(proven_reg_ids) if proven_reg_ids is not None else None
    out: list[Game] = []
    for row in history:
        if row.game_id == target.game_id:
            continue
        if str(row.season_type or "REG").upper() != "REG":
            continue
        if row.season in SEALED_SEASONS:
            raise R5FreezeRefuse(f"history includes sealed season {row.season}")
        if row.season not in allowed_years and (allowed_ids is None or row.game_id not in (allowed_ids or set())):
            # Unproven year — do not invent; skip rather than treat week<=18 as REG.
            continue
        if allowed_ids is not None and row.game_id not in allowed_ids and row.season not in allowed_years:
            continue
        if row.season > target.season:
            continue
        if row.season == target.season and row.week >= target.week:
            continue
        if row.kickoff_utc >= cutoff:
            continue
        if row.kickoff_utc >= target.kickoff_utc:
            continue
        out.append(row)
    return sorted(out, key=lambda g: (g.kickoff_utc, g.game_id))


def history_id_list(games: Sequence[Game]) -> list[str]:
    return [g.game_id for g in games]


def q2_margin_or_hold(
    target: Game,
    history: Sequence[Game],
    *,
    history_freeze: Mapping[str, Any],
    proven_reg_ids: Sequence[str] | None = None,
) -> dict[str, Any]:
    if history_freeze.get("hold_q2"):
        return {
            "game_id": target.game_id,
            "m_q2": None,
            "q2_status": "HOLD",
            "hold_reason": history_freeze.get("hold_reason"),
            "history_ids": [],
            "n_history": 0,
            "rating_diff": None,
            "n_asof_games": None,
        }
    allowed = r5_history_for_target(
        history,
        target,
        proven_reg_ids=proven_reg_ids,
        proven_reg_years=PROVEN_REG_YEARS,
    )
    feats = asof_for_targets(allowed, [target])
    assert_asof_no_self_target(allowed, feats)
    if not feats:
        raise Q2Refuse(f"no Q2 as-of for {target.game_id}")
    feat = feats[0]
    return {
        "game_id": target.game_id,
        "m_q2": q2_pm_new(feat.rating_diff),
        "q2_status": "ok",
        "hold_reason": None,
        "history_ids": history_id_list(allowed),
        "n_history": len(allowed),
        "rating_diff": feat.rating_diff,
        "n_asof_games": feat.n_asof_games,
    }


def target_rows_from_matrix(
    rows: Sequence[Mapping[str, Any]],
    identities: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    first: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        gid = str(row["game_id"])
        first.setdefault(gid, row)
    ident_by = {str(r["game_id"]): r for r in identities}
    out = []
    for gid, row in first.items():
        ident = ident_by[gid]
        kick = str(row.get("pregame_cutoff_utc") or "")
        if not kick:
            raise R5FreezeRefuse(f"{gid} missing pregame_cutoff_utc")
        out.append(
            {
                "game_id": gid,
                "season": int(ident["season"]),
                "week": int(ident["week"]),
                "season_type": "REG",
                "home": ident["home"],
                "away": ident["away"],
                "kickoff_utc": kick,
            }
        )
    return out


def produce_if_forecasts(
    packets: Mapping[str, Mapping[str, Any]],
    targets: Sequence[Mapping[str, Any]],
    *,
    produce: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
) -> dict[str, dict[str, Any]]:
    fn = produce or produce_if_mu
    out: dict[str, dict[str, Any]] = {}
    for target in targets:
        gid = str(target["game_id"])
        packet = packets[gid]
        produced = dict(fn(packet))
        mu = produced.get("if_margin_mu")
        if not _finite(mu):
            raise R5FreezeRefuse(f"{gid} non-finite IF mu")
        if int(produced.get("simulations") or 0) != SIMULATIONS:
            raise R5FreezeRefuse(f"{gid} simulations != 4000")
        if int(produced.get("seed") or 0) != seed_for(gid):
            raise R5FreezeRefuse(f"{gid} seed drifted from existing per-game seed")
        out[gid] = produced
    return out


def assemble_forecasts(
    targets: Sequence[Mapping[str, Any]],
    *,
    if_rows: Mapping[str, Mapping[str, Any]],
    q2_rows: Mapping[str, Mapping[str, Any]],
    history_freeze: Mapping[str, Any],
    code_hashes: Mapping[str, str],
) -> dict[str, Any]:
    forecasts = []
    warnings: list[str] = []
    for target in targets:
        gid = str(target["game_id"])
        if_row = if_rows[gid]
        q2_row = q2_rows[gid]
        m_if = float(if_row["if_margin_mu"])
        m_q2 = q2_row.get("m_q2")
        blocked: list[str] = []
        m_c = None
        if q2_row.get("q2_status") != "ok" or m_q2 is None:
            blocked.append("q2")
            blocked.append("challenger")
            warnings.append(f"{gid}: Q2 HOLD — candidate withheld (no invented history)")
        else:
            m_c = challenger_margin(m_if, m_q2, w=CANDIDATE_WEIGHT)
        forecasts.append(
            {
                "game_id": gid,
                "season": int(target["season"]),
                "week": int(target["week"]),
                "season_type": "REG",
                "home": target["home"],
                "away": target["away"],
                "kickoff_utc": target["kickoff_utc"],
                "split": "DEV",
                "m_if": m_if,
                "m_q2": None if m_q2 is None else float(m_q2),
                "m_candidate": m_c,
                "m_challenger": m_c,
                "candidate_formula": "0.5*IF+0.5*Q2",
                "candidate_weight": CANDIDATE_WEIGHT,
                "r3_weight_stopped": R3_WEIGHT_STOPPED,
                "if_status": "reconstructed",
                "if_label": "RECONSTRUCTED_IF_6ca03716",
                "q2_status": q2_row.get("q2_status"),
                "q2_parameter_label": PARAMETER_LABEL,
                "q2_hold_reason": q2_row.get("hold_reason"),
                "history_ids": list(q2_row.get("history_ids") or []),
                "n_history": q2_row.get("n_history"),
                "rating_diff": q2_row.get("rating_diff"),
                "n_asof_games": q2_row.get("n_asof_games"),
                "seed": int(if_row["seed"]),
                "simulations": SIMULATIONS,
                "if_tip": IF_TIP,
                "simulator_sha256": SIM_SHA256,
                "framework_sha256": FW_SHA256,
                "blocked_legs": blocked,
                "label": LABEL_RECONSTRUCTED,
                "fit_label": LABEL_RETRO_FIT,
                "research_label": LABEL_RESEARCH,
                "cert_candidate": CERT_CANDIDATE,
                "eval": None,
                "scoring": None,
                "stage_c": None,
            }
        )
    payload = {
        "schema_version": SCHEMA,
        "path_id": PATH_ID,
        "ticket": TICKET,
        "n_forecasts": len(forecasts),
        "n_if_finite": sum(1 for r in forecasts if _finite(r["m_if"])),
        "n_q2_finite": sum(1 for r in forecasts if r["m_q2"] is not None),
        "n_q2_hold": sum(1 for r in forecasts if r["q2_status"] == "HOLD"),
        "n_candidate_finite": sum(1 for r in forecasts if r["m_candidate"] is not None),
        "if_tip": IF_TIP,
        "simulator_sha256": SIM_SHA256,
        "framework_sha256": FW_SHA256,
        "simulations": SIMULATIONS,
        "candidate": "0.5*IF+0.5*Q2",
        "r3_stop": R3_STOP,
        "r3_weight_stopped": R3_WEIGHT_STOPPED,
        "history_rule": history_freeze.get("history_rule"),
        "q2_hold": history_freeze.get("hold_q2"),
        "q2_hold_reason": history_freeze.get("hold_reason"),
        "code_hashes": dict(code_hashes),
        "source_hashes": {
            "feature_json": FEATURE_RECON_REG496_ARTIFACT_SHA256,
            "feature_matrix": FEATURE_MATRIX_SHA256,
            "games_csv": GAMES_SHA256,
            "outcomes": OUTCOMES_SHA256,
            "schedule": SCHEDULE_SHA256,
        },
        "warnings": warnings,
        "forecasts": forecasts,
        "game_ids": [r["game_id"] for r in forecasts],
        **LIMITATIONS,
    }
    _scan_forbidden_scores(payload, where="R5 forecasts")
    if payload["n_if_finite"] != len(forecasts):
        raise R5FreezeRefuse("not all IF mus finite")
    return payload


def _matrix_values(rows: Sequence[Mapping[str, Any]], game_ids: Sequence[str]) -> dict[tuple[str, str], Any]:
    want = set(game_ids)
    out: dict[tuple[str, str], Any] = {}
    for row in rows:
        gid = str(row["game_id"])
        if gid not in want:
            continue
        out[(gid, str(row["field"]))] = row.get("reconstructed_value")
    return out


def load_exact_week_matrix(root: Path | None = None) -> list[dict[str, str]]:
    repo = _repo_root(root)
    rows: list[dict[str, str]] = []
    for season, rel in EXACT_WEEK_MATRIX.items():
        path = repo / rel
        if not path.is_file():
            raise R5FreezeRefuse(f"exact-week matrix missing {rel}")
        with path.open(newline="", encoding="utf-8") as handle:
            rows.extend(list(csv.DictReader(handle)))
    return rows


def compare_inputs(
    last_played: Mapping[tuple[str, str], Any],
    exact_week: Mapping[tuple[str, str], Any],
    game_ids: Sequence[str],
) -> dict[str, Any]:
    """Explain every 27-input discrepancy vs the immutable exact-week freeze."""
    discrepancies: list[dict[str, Any]] = []
    identical: list[str] = []
    missing_old: list[str] = []
    for gid in game_ids:
        fields_differ: list[dict[str, Any]] = []
        missing = False
        for field in CONTRACT_27:
            new = last_played.get((gid, field))
            old = exact_week.get((gid, field))
            if old is None:
                missing = True
                continue
            if field in TEXT_FIELDS:
                if str(new) != str(old):
                    fields_differ.append({"field": field, "last_played": new, "exact_week": old})
                continue
            try:
                a = float(new)
                b = float(old)
            except (TypeError, ValueError):
                fields_differ.append({"field": field, "last_played": new, "exact_week": old})
                continue
            if field in INDEX_FIELDS:
                tol = 1e-6
            elif field in EPA_FIELDS or field in REST_FIELDS:
                tol = 1e-9
            else:
                tol = 0.0
            if abs(a - b) > tol:
                fields_differ.append(
                    {
                        "field": field,
                        "last_played": a,
                        "exact_week": b,
                        "delta": a - b,
                        "tol": tol,
                    }
                )
        if missing:
            missing_old.append(gid)
        elif fields_differ:
            discrepancies.append(
                {
                    "game_id": gid,
                    "n_fields": len(fields_differ),
                    "fields": fields_differ,
                    "explanation": (
                        "last-played T2 selector vs exact-week T2 (rating_week=week-1). "
                        "Not an IF pin/seed change."
                    ),
                }
            )
        else:
            identical.append(gid)
    return {
        "n_compared": len(game_ids),
        "n_identical_27": len(identical),
        "n_input_discrepancy": len(discrepancies),
        "n_missing_from_old_matrix": len(missing_old),
        "identical_game_ids": identical,
        "discrepancies": discrepancies,
        "missing_from_old_matrix": missing_old,
    }


def compare_437_if(
    forecasts: Sequence[Mapping[str, Any]],
    old_freeze: Mapping[str, Any],
    *,
    input_compare: Mapping[str, Any],
) -> dict[str, Any]:
    old_by = {str(r["game_id"]): r for r in old_freeze.get("forecasts") or []}
    new_by = {str(r["game_id"]): r for r in forecasts}
    identical_inputs = set(input_compare.get("identical_game_ids") or [])
    blockers: list[dict[str, Any]] = []
    replayed: list[str] = []
    explained: list[dict[str, Any]] = []
    missing_old_if: list[str] = []
    for gid in sorted(set(new_by) & set(expected_ids_from_input(input_compare))):
        new = new_by[gid]
        old = old_by.get(gid)
        if old is None:
            missing_old_if.append(gid)
            continue
        new_mu = float(new["m_if"])
        old_mu = float(old["m_if"])
        same_seed = int(new["seed"]) == seed_for(gid)
        if gid in identical_inputs:
            if not same_seed or not replay_ok(new_mu, old_mu):
                blockers.append(
                    {
                        "game_id": gid,
                        "reason": "IF_REPLAY_BLOCKER",
                        "new_m_if": new_mu,
                        "old_m_if": old_mu,
                        "delta": new_mu - old_mu,
                        "tol": REPLAY_REL * max(1.0, abs(old_mu)),
                        "seed_ok": same_seed,
                    }
                )
            else:
                replayed.append(gid)
        else:
            explained.append(
                {
                    "game_id": gid,
                    "new_m_if": new_mu,
                    "old_m_if": old_mu,
                    "delta": new_mu - old_mu,
                    "reason": "27-input discrepancy vs exact-week freeze — IF mu not required to match",
                }
            )
    if blockers:
        raise R5FreezeRefuse(
            f"IF replay BLOCKER n={len(blockers)} sample={blockers[:3]}"
        )
    return {
        "schema_version": SCHEMA,
        "old_if_freeze_path": OLD_IF_FREEZE_PATH,
        "old_if_freeze_sha256": OLD_IF_FREEZE_SHA256,
        "n_common": len(input_compare.get("identical_game_ids") or [])
        + len(input_compare.get("discrepancies") or [])
        + len(input_compare.get("missing_from_old_matrix") or []),
        "n_replayed_within_tol": len(replayed),
        "n_explained_input_discrepancy": len(explained),
        "n_missing_old_if": len(missing_old_if),
        "n_blocker": 0,
        "replay_tol": "1e-9*max(1,|old|)",
        "identical_pins": {
            "if_tip": IF_TIP,
            "simulator_sha256": SIM_SHA256,
            "framework_sha256": FW_SHA256,
            "simulations": SIMULATIONS,
            "seed_rule": "201710+sha256(game_id)%1000003",
        },
        "input_compare": {
            "n_identical_27": input_compare.get("n_identical_27"),
            "n_input_discrepancy": input_compare.get("n_input_discrepancy"),
            "n_missing_from_old_matrix": input_compare.get("n_missing_from_old_matrix"),
            "discrepancies": input_compare.get("discrepancies"),
        },
        "explained_if_deltas": explained,
        "replayed_game_ids": replayed,
        "missing_old_if": missing_old_if,
        "cert_candidate": CERT_CANDIDATE,
        "eval": None,
        "scoring": None,
        "ml_from_point_margin": False,
        "totals_from_point_margin": False,
        "joint_from_point_margin": False,
    }


def expected_ids_from_input(input_compare: Mapping[str, Any]) -> list[str]:
    ids = list(input_compare.get("identical_game_ids") or [])
    ids.extend(str(r["game_id"]) for r in (input_compare.get("discrepancies") or []))
    ids.extend(input_compare.get("missing_from_old_matrix") or [])
    return ids


def refuse_target_scoring(
    *,
    profile: str = PROFILE_FEATURE_RECON_REG496,
    candidate_ids: Sequence[str],
    root: Path | None = None,
    outcome_loader: OutcomeReadSpy | Callable[[], Any] | None = None,
    coverage_blocked: bool = True,
) -> dict[str, Any]:
    """Phase 1 STOP: hooks run; target labels must stay unread (spy reads == 0)."""
    spy = outcome_loader if outcome_loader is not None else OutcomeReadSpy(
        lambda: {"__should_never_load__": {"home_score": 1}}
    )
    try:
        check_cohort_before_target_outcome_loading(
            profile,
            candidate_ids,
            coverage_blocked=coverage_blocked,
            outcome_loader=spy,
            root=root,
        )
        raise TargetScoringRefuse(
            "Phase 1 must STOP before target scoring; unexpected hook pass"
        )
    except Exception as exc:
        if isinstance(exc, TargetScoringRefuse):
            raise
        reads = getattr(spy, "reads", None)
        if reads not in (None, 0):
            raise TargetScoringRefuse(f"target scoring loader read {reads} times") from exc
        returned = getattr(spy, "ids_returned", None) or []
        if returned:
            raise TargetScoringRefuse("target scoring loader returned labels") from exc
        return {
            "refused": True,
            "reason": str(exc),
            "outcome_loader_reads": 0,
            "target_labels_loaded": 0,
            "phase": 1,
            "stop": "AWAITING_ALEX_PREFLIGHT_AND_COS_BIND",
            "cert_candidate": CERT_CANDIDATE,
            "eval": None,
            "scoring": None,
        }


def phase2_positive_path() -> dict[str, Any]:
    """Documented later path — not executed in Phase 1."""
    return {
        "schema_version": SCHEMA,
        "phase": 2,
        "executed": False,
        "requires": [
            "Alex source/numerical-identity PREFLIGHT GO",
            "Cos bind / EXEC release for target scoring loader",
        ],
        "steps": [
            "Reuse frozen FEATURE_RECON_REG496 IDs (this Phase 1 identity manifest).",
            "Call check_cohort_before_target_outcome_loading(FEATURE_RECON_REG496, frozen_ids).",
            "Only after hook ok: load target home/away scores for those IDs.",
            "Score IF / Q2 / candidate home-margin vs actual. No market-edge / GREEN here.",
            "Worker B still owns N1 + market intersection + integration-owner combine.",
        ],
        "refuses_if": [
            "Alex preflight missing",
            "Cos bind missing",
            "hook fail / changed frozen bytes / blocked coverage",
            "2022–23 regen/scoring",
            "2024–26",
            "Q2/2017 reopen",
            "Stage C / R2-C change",
        ],
        "cert_candidate": CERT_CANDIDATE,
        "eval": None,
        "scoring": None,
    }


def code_hashes(root: Path | None = None) -> dict[str, str]:
    repo = _repo_root(root)
    files = {
        "r5_496_freeze.py": Path(__file__),
        "if_produce.py": Path(__file__).with_name("if_produce.py"),
        "q2.py": Path(__file__).with_name("q2.py"),
        "cohort_enforcement.py": Path(__file__).with_name("cohort_enforcement.py"),
        "run_nfl_r5_496_freeze_t5155u.py": repo
        / "scripts"
        / "nfl"
        / "run_nfl_r5_496_freeze_t5155u.py",
    }
    out = {}
    for name, path in files.items():
        if path.is_file():
            out[name] = sha256_if_file(path)
    return out


def load_old_if_freeze(root: Path | None = None) -> dict[str, Any]:
    repo = _repo_root(root)
    path = repo / OLD_IF_FREEZE_PATH
    digest = sha256_file(path)
    if digest != OLD_IF_FREEZE_SHA256:
        raise R5FreezeRefuse(f"old IF freeze sha {digest} != immutable 9e704b98")
    return json.loads(path.read_text(encoding="utf-8"))


def run_phase1_freeze(
    *,
    root: Path | None = None,
    produce: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
    write: bool = True,
    compare_old_if: bool = True,
) -> dict[str, Any]:
    """Identity → 27-validate → IF produce → Q2 HOLD → 437 compare → STOP. No scores."""
    repo = _repo_root(root)
    identities = freeze_identities(repo)
    if437 = expected_profile_ids(PROFILE_DEV_IF437, repo)
    splits = split_scaffolding(identities["game_ids"], if437)
    artifact = json.loads((repo / FEATURE_RECON_REG496_ARTIFACT_PATH).read_text(encoding="utf-8"))
    matrix_rows = load_feature_matrix(repo)
    validation = validate_27_inputs(
        matrix_rows,
        expected_ids=identities["artifact_game_ids"],
        identities=artifact.get("identities") or [],
    )
    history_freeze = freeze_q2_history_sources(repo)
    packets = packets_from_matrix(matrix_rows)
    targets = target_rows_from_matrix(matrix_rows, artifact.get("identities") or [])
    target_by = {t["game_id"]: t for t in targets}
    ordered = [target_by[gid] for gid in identities["artifact_game_ids"]]
    if_rows = produce_if_forecasts(packets, ordered, produce=produce)
    q2_rows = {
        t["game_id"]: q2_margin_or_hold(
            Game(
                season=int(t["season"]),
                week=int(t["week"]),
                game_id=t["game_id"],
                home=t["home"],
                away=t["away"],
                kickoff_utc=parse_kickoff(t["kickoff_utc"]),
            ),
            [],
            history_freeze=history_freeze,
        )
        for t in ordered
    }
    hashes = code_hashes(repo)
    forecasts = assemble_forecasts(
        ordered,
        if_rows=if_rows,
        q2_rows=q2_rows,
        history_freeze=history_freeze,
        code_hashes=hashes,
    )
    exact_rows = load_exact_week_matrix(repo)
    input_compare = compare_inputs(
        _matrix_values(matrix_rows, splits["old437"]["game_ids"]),
        _matrix_values(exact_rows, splits["old437"]["game_ids"]),
        splits["old437"]["game_ids"],
    )
    if compare_old_if:
        old_freeze = load_old_if_freeze(repo)
        compare = compare_437_if(
            forecasts["forecasts"], old_freeze, input_compare=input_compare
        )
    else:
        compare = {
            "schema_version": SCHEMA,
            "skipped": True,
            "reason": "compare_old_if=False (test/harness); real freeze must compare",
            "input_compare": {
                "n_identical_27": input_compare.get("n_identical_27"),
                "n_input_discrepancy": input_compare.get("n_input_discrepancy"),
            },
            "cert_candidate": CERT_CANDIDATE,
            "eval": None,
            "scoring": None,
        }
    stop = {
        "schema_version": SCHEMA,
        "stop": "AWAITING_ALEX_PREFLIGHT_AND_COS_BIND",
        "phase": 1,
        "target_scoring_loader_executed": False,
        "diagnostic_execution": False,
        "owner_clear_sha8": OWNER_CLEAR_SHA8,
        "cos_order_sha8": COS_ORDER_SHA8,
        "closed_quality_do_not_reopen": {
            "pr_700_tip": "12ccc482",
            "stamp": "9d436eb1",
            "alex": "f4147e76",
            "cos": "4b23584a",
            "component": "ACCEPT only",
            "return_record": "7057e5a9",
        },
        "worker_b_owns": list(WORKER_B_OWNED),
        "forbidden": [
            "paid pulls",
            "2024-26",
            "2022-23 regen/scoring",
            "Q2/2017 reopen",
            "merge/deploy",
            "secrets",
            "new installs",
            "Stage C change",
            "R2-C change",
        ],
        **LIMITATIONS,
    }
    scoring_refuse = refuse_target_scoring(
        candidate_ids=identities["game_ids"],
        root=repo,
        coverage_blocked=True,
    )
    phase2 = phase2_positive_path()
    out_dir = repo / OUT_DIR
    written: dict[str, str] = {}
    bundle = {
        "SPEC": {
            "schema_version": SCHEMA,
            "path_id": PATH_ID,
            "ticket": TICKET,
            "opt_in": True,
            "phase": 1,
            "experiment": "DEV_R5_496",
            "owner_clear_sha8": OWNER_CLEAR_SHA8,
            "cos_order_sha8": COS_ORDER_SHA8,
            "cert_candidate": CERT_CANDIDATE,
            "eval": None,
            "production": False,
            "market_edge": False,
            "green": False,
            "preserve_earlier_runners": True,
            "r3_stop": R3_STOP,
            "candidate": "0.5*IF+0.5*Q2",
            "labels": [LABEL_RECONSTRUCTED, LABEL_RETRO_FIT],
        },
        "IDENTITY_MANIFEST": identities,
        "FEATURE_VALIDATION": validation,
        "Q2_HISTORY_FREEZE": history_freeze,
        "SPLIT_SCAFFOLDING": splits,
        "FORECASTS_DEV_R5_496": forecasts,
        "COMPARE_437": compare,
        "STOP_AWAITING_ALEX_PREFLIGHT_AND_COS_BIND": stop,
        "PHASE2_POSITIVE_PATH": phase2,
        "SCORING_REFUSE": scoring_refuse,
        "SOURCE_PINS": {
            "schema_version": SCHEMA,
            "pins": {
                "feature_json": FEATURE_RECON_REG496_ARTIFACT_SHA256,
                "feature_matrix": FEATURE_MATRIX_SHA256,
                "reg496_identity": REG496_IDENTITY_SHA256,
                "dev_if437_identity": DEV_IF437_IDENTITY_SHA256,
                "old_if_freeze": OLD_IF_FREEZE_SHA256,
                "if_tip": IF_TIP,
                "simulator": SIM_SHA256,
                "framework": FW_SHA256,
                "games": GAMES_SHA256,
                "outcomes": OUTCOMES_SHA256,
                "schedule": SCHEDULE_SHA256,
                "r4_496_tip": R4_496_ACCEPTED_TIP,
                "r4_496_stamp": R4_496_STAMP,
            },
            "code_hashes": hashes,
            "holds": {
                "R3_STOP": R3_STOP,
                "R2_C": "unchanged",
                "Stage_C": "unchanged",
                "Q2_2017": "not reopened",
            },
        },
    }
    if write:
        out_dir.mkdir(parents=True, exist_ok=True)
        for name, payload in bundle.items():
            dest = out_dir / f"{name}.json"
            dest.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
            written[name] = sha256_file(dest)
        manifest = {
            "schema_version": SCHEMA,
            "path_id": PATH_ID,
            "ticket": TICKET,
            "cert_candidate": CERT_CANDIDATE,
            "files": written,
            "n_forecasts": forecasts["n_forecasts"],
            "n_if_finite": forecasts["n_if_finite"],
            "n_q2_hold": forecasts["n_q2_hold"],
            "n_candidate_finite": forecasts["n_candidate_finite"],
            "identity_sha256": REG496_IDENTITY_SHA256,
            "stop": stop["stop"],
            **LIMITATIONS,
        }
        dest = out_dir / "FREEZE_MANIFEST.json"
        dest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        written["FREEZE_MANIFEST"] = sha256_file(dest)
        bundle["FREEZE_MANIFEST"] = manifest
    bundle["written"] = written
    return bundle
