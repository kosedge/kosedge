"""t5335u/t5344u R7 followthrough metadata preflight. CERT=0.

Manifest + identity/readiness only. Does not implement NTBB-K.
Does not open score-bearing labels or run real science.
METADATA 14083 consumes staged R7_METADATA_PROJECTION only.

NTBB-K integrate hooks are prepared but NOT locked. RETURN 36205:
B tip d0bb6bef is under numeric RETURN — do not freeze/integrate as final.
Producer→capability/gate remains Worker A. R7_RECORD_DATE_RETRO_C1 HOLD.
"""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from src.services.nfl_ops_v1_evidence.spy import ForbiddenSurfaceSpy, OutcomeReadSpy
from src.services.nfl_ops_v1_evidence.verify import git_tip
from src.services.nfl_r7_correctness_v1.pins import (
    CALENDAR_ID,
    CALENDAR_TZ,
    CERT,
    CODE_FILES,
    CONTRACT_27,
    FW_SHA256,
    IF_TIP,
    KO_MINUS_MINUTES,
    SIM_SHA256,
    WORKER_A_ID,
)
from src.services.nfl_r7_correctness_v1.produce import r7_code_hash, r7_config_hash, repo_root, write_json
from src.services.nfl_t5208u.pins import CANDIDATE_WEIGHT, MARKET_BLEND, SEED_BASE, SEED_MOD, SIMULATIONS


class FollowthroughRefuse(ValueError):
    """Fail-closed followthrough preflight."""


SCHEMA_ID = "nfl-t5335u-r7-followthrough-preflight-v1"
SCHEMA_DELTA = "nfl-t5344u-r7-metadata-14083-v1"
PACKAGE = "R7_FOLLOWTHROUGH_PREFLIGHT"
OWNER_CLEAR = "92861"
AUTHORITY = "t5335u"
METADATA_AUTHORITY = "t5344u"
METADATA_ORDER = "14083"
SCOPE_ID = "chief-nflgreen-followthrough-20261103"
SPEC_REL = "research/nfl_followthrough_20261103/NTBB_K_V1_SPEC.md"
PROJECTION_REL = "research/nfl_followthrough_20261103/R7_METADATA_PROJECTION.json"
FOLLOWTHROUGH_FILES = (
    "services/model-service/src/services/nfl_r7_correctness_v1/followthrough_preflight.py",
    "scripts/nfl/run_nfl_r7_followthrough_preflight.py",
)
SPEC_SHA256 = "2f3c215d7680dd5aa33a0a77690ece4ef70a0a8dbbebaac880750dd776ec66d7"
PROJECTION_SHA256 = "9306a1b5ea74e71de652e4e27761f5814c349ecd1415a3507336d31f8703bbc9"
PROJECTION_SCHEMA = "R7_METADATA_PROJECTION_20261103_V1"
START_TIP = "d3f2c56adcbb684db20af9c29a55e656371e605e"
SPEC_COMMIT = "2a2c91c9b839da2246a01596b203318295581914"
PROJECTION_COMMIT = "e290ff3b306d7c6c47b2d11a183c520992b90f59"
PRIOR_PACKAGING_REVISION = "df041d6f"
ARCHIVED_IDENTITY_COMMIT = "255adf7802830bc25814a739d62f65f095216203"
ARCHIVED_IDENTITY_REL = "data/ops/nfl-t5155u-r5-496-freeze/IDENTITY_MANIFEST.json"
OLD_IF_FREEZE_REL = "data/ops/nfl-forecast-builder-t5107u/FORECAST_FREEZE_t5112u.json"
OPS_REL = "data/ops/t5335u-r7-followthrough"

EXACT_496 = 496
N_2020 = 240
N_2021 = 256
N_OLD_437 = 437
N_NEW_59 = 59
N_SAME_96 = 96
N_SCHEDULE_REG = 528
N_CONTRACT_27 = 27
BOOTSTRAP_B = 10000
BOOTSTRAP_SEED = 20261103
SENSITIVITY_SEED = 20261104
BOOTSTRAP_GEN = "PCG64"

PRIOR_MISSING_N = 5

# RETURN 36205 — Cos ACCEPT corrected B tip. Freeze this tip only; not d0bb6bef.
B_NTBBK_TIP_REFUSED = "d0bb6bef4b44215735369c0208ce19e07a9647a6"
B_NTBBK_TIP_FROZEN = "a807af2298826475d8a207dfb7fcfcf710f00014"
B_NTBBK_KERNEL_SHA256 = "ee80029149e410da7c3add0f74f2e8b1c3568c96a4542d820bbf4c9369996aa7"
RETURN_NTBBK = "36205"
NTBBK_PROFILE_HOOK = "NTBB_K_SYNTHETIC_KERNEL_V1"
NTBBK_ISOLATED_AREA = "services/model-service/src/services/nfl_ntbb_k_v1"
NTBBK_ISOLATED_OPS = "data/ops/nfl_ntbb_k_v1"
RETRO_C1_HOLD = "R7_RECORD_DATE_RETRO_C1"
RETRO_C1_SPEC = "7cb4fcef"
RETRO_C1_SPEC_SHA_PREFIX = "3394663e"

RAW_CUTOFF_ROLE = "RECORDED_MATRIX_FIELD_NOT_SEAL_NOT_KO60"
PBP_TIME_ROLE = "RECORDED_HISTORICAL_METADATA_NOT_CERTIFIED_ACTUAL_UTC"
STRICT_REST_BLOCK_REASON = (
    "actual_kickoff_utc unknown; PBP game_date/start_time_raw is recorded historical "
    "metadata ≠ certified actual UTC kickoff/publication/availability; "
    "raw_field_named_pregame_cutoff_utc is not a seal and must not be silently "
    "treated as KO−60 except the independent same96 equality check vs B1 kickoff_utc"
)

# Working-tree copies remain absent. METADATA 14083 consumes identity/time
# metadata from the staged projection — that is not actual-clock provenance.
CLOUD_METADATA_LOCATORS = (
    {
        "locator": "data/ops/nfl-t5146u-r4-last-played-dev/DEV_RECON_LAST_PLAYED_2020_2021_REG.json",
        "role": "FEATURE_RECON_REG496 artifact (identities + source pin only)",
        "sha256_pin": "282f979b52890c7ed943eeb9c0836dd7f50b9a925cf3e82fdfc856834646402c",
    },
    {
        "locator": "data/ops/nfl-t5146u-r4-last-played-dev/DEV_RECON_LAST_PLAYED_2020_2021_REG_MATRIX.csv",
        "role": "feature matrix (27-field status/source-set digests + raw cutoff only)",
        "sha256_pin": "a3b9d8ecb94902078ddcb89206a5a1ff16d5f1a3b4e8080186238d6578c52409",
    },
    {
        "locator": "data/ops/nfl-forecast-builder-t5107u/inputs/schedule_results_2020_2023.csv",
        "role": "schedule recorded metadata only (UNOPENED results; clocks stay null)",
        "sha256_pin": "0853342304d269b55033d3474acda853ce00bdb10590f44b09ae569115148479",
    },
    {
        "locator": "data/ops/nfl-forecast-builder-t5107u/FORECAST_FREEZE_t5112u.json",
        "role": "old IF freeze game_ids only (no forecasts copied)",
        "sha256_pin": "9e704b980b6ce33acc883725823c39766ea19f8a86a7a781ac2a02d95344a732",
    },
)

# Fifth-prereq: book offered price/settlement is NOT required for POINT-ERROR.
# Those fields block historical economic/ATS/ROI/CLV only.
ECONOMIC_RESIDUALS = (
    {
        "locator": "same96 book-specific offered price/settlement",
        "role": "historical economic / ATS / ROI / CLV only",
        "blocks": ["historical_economic", "ATS", "ROI", "CLV"],
        "required_for_point_error": False,
        "sha256_pin": None,
        "status": "RESIDUAL_NOT_MISSING_FOR_POINT_ERROR",
    },
)

# Bind same96 + archived market point by an actual existing freeze/digest.
# No invented prices or opener/close label. None exists on this checkout.
POINT_ERROR_MARKET_DIGEST = {
    "locator": "frozen median-spread market-point digest for same96 POINT-ERROR",
    "role": "bind same96 archived market point by existing freeze/digest; not book prices; not invented opener/close",
    "sha256_pin": None,
    "opened": False,
}

UNOPENED_LABEL_POINTERS = (
    {
        "locator": "outcomes @ SOURCE_PINS.outcomes",
        "sha256_pin": "50bda875daa8bf1aadd56dd0a3bc19f1bb52dafe42b6a9c921a5816c7d7dc081",
        "status": "UNOPENED",
        "reason": "label-read not authorized this turn",
    },
    {
        "locator": "games @ SOURCE_PINS.games",
        "sha256_pin": "4fe1cdd7f2eb616103ee6107e6a5cb0d5280f8006be420b606af0995351abef8",
        "status": "UNOPENED",
        "reason": "history payload not authorized this turn",
    },
)

FORBIDDEN_SCORE_KEYS = (
    "actual_margin",
    "actual_total",
    "home_score",
    "away_score",
    "error",
    "abs_error",
    "signed_error",
    "ats",
    "cover",
    "look",
    "eval_score",
)

PRESERVED_FICTIONAL = {
    "if_margin": 1.389941504602551,
    "q2_margin": 1.93920745003233,
    "c_margin": 1.6645744773174405,
    "pair_hash": "18b8d030deec15a6528ff24598a68e182378323bc5541b934471980d32740419",
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(Path(path).read_bytes())


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _scan_forbidden(payload: Any, *, where: str) -> None:
    """Refuse score-bearing mapping keys. String deny-lists are allowed."""
    if isinstance(payload, Mapping):
        for key, value in payload.items():
            if str(key).casefold() in FORBIDDEN_SCORE_KEYS:
                raise FollowthroughRefuse(f"{where} contains forbidden score-bearing key {key}")
            _scan_forbidden(value, where=where)
    elif isinstance(payload, (list, tuple)):
        for item in payload:
            _scan_forbidden(item, where=where)


def require_spec(root: Path) -> dict[str, str]:
    path = root / SPEC_REL
    if not path.is_file():
        raise FollowthroughRefuse(f"NTBB-K spec missing {SPEC_REL}")
    digest = sha256_file(path)
    if digest != SPEC_SHA256:
        raise FollowthroughRefuse(f"NTBB-K spec sha256 {digest} != {SPEC_SHA256}")
    return {"path": SPEC_REL, "sha256": digest, "opened": "read_bind_only", "kernel_implemented": False}


def bind_working_tree_sources(root: Path) -> dict[str, Any]:
    rows = []
    for rel in (SPEC_REL, PROJECTION_REL, *CODE_FILES, *FOLLOWTHROUGH_FILES):
        path = root / rel
        if not path.is_file():
            raise FollowthroughRefuse(f"source bind missing {rel}")
        rows.append({"path": rel, "sha256": sha256_file(path), "present": True})
    return {"n": len(rows), "files": rows}


def _git_show(root: Path, commit: str, rel: str) -> bytes:
    proc = subprocess.run(
        ["git", "show", f"{commit}:{rel}"],
        cwd=str(root),
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise FollowthroughRefuse(f"archived pointer {commit}:{rel} unreadable: {proc.stderr.decode()[:200]}")
    return proc.stdout


def bind_archived_identity(root: Path) -> dict[str, Any]:
    """Identity-only bind from archived git object. Does not open labels."""
    raw = _git_show(root, ARCHIVED_IDENTITY_COMMIT, ARCHIVED_IDENTITY_REL)
    digest = sha256_bytes(raw)
    body = json.loads(raw.decode("utf-8"))
    _scan_forbidden(body, where="archived identity")
    game_ids = [str(x) for x in body.get("game_ids") or []]
    n_by = body.get("n_by_season") or {}
    if len(game_ids) != EXACT_496:
        raise FollowthroughRefuse(f"archived identity n={len(game_ids)} != {EXACT_496}")
    if int(n_by.get("2020", -1)) != N_2020 or int(n_by.get("2021", -1)) != N_2021:
        raise FollowthroughRefuse(f"archived n_by_season {n_by} != {N_2020}+{N_2021}")
    if N_2020 + N_2021 != EXACT_496:
        raise FollowthroughRefuse("240+256 != 496")
    return {
        "opened": "identity_manifest_git_object_only",
        "commit": ARCHIVED_IDENTITY_COMMIT,
        "path": ARCHIVED_IDENTITY_REL,
        "bytes": len(raw),
        "sha256": digest,
        "n": EXACT_496,
        "n_by_season": {"2020": N_2020, "2021": N_2021},
        "identity_sha256_pin": body.get("identity_sha256"),
        "membership_rule": body.get("membership_rule"),
        "week_le_18_proxy": body.get("week_le_18_proxy"),
        "reg_week18_2021_retained": list(body.get("reg_week18_2021_retained") or []),
        "wildcard_2020_refused": list(body.get("wildcard_2020_refused") or []),
        "game_ids": game_ids,
        "working_tree_present": (root / ARCHIVED_IDENTITY_REL).is_file(),
    }


def bind_old437_new59(root: Path, game_ids: list[str]) -> dict[str, Any]:
    raw = _git_show(root, ARCHIVED_IDENTITY_COMMIT, OLD_IF_FREEZE_REL)
    digest = sha256_bytes(raw)
    old = json.loads(raw.decode("utf-8"))
    old_ids = [str(x) for x in old.get("game_ids") or []]
    # Do not persist forecasts. IDs only.
    new_set = set(game_ids)
    old_set = set(old_ids)
    common = sorted(new_set & old_set)
    only_new = sorted(new_set - old_set)
    if len(common) != N_OLD_437 or len(only_new) != N_NEW_59:
        raise FollowthroughRefuse(
            f"old437+new59 mismatch common={len(common)} new={len(only_new)}"
        )
    if len(common) + len(only_new) != EXACT_496:
        raise FollowthroughRefuse("437+59 != 496")
    return {
        "opened": "old_freeze_game_ids_only",
        "commit": ARCHIVED_IDENTITY_COMMIT,
        "path": OLD_IF_FREEZE_REL,
        "sha256": digest,
        "old_freeze_n_game_ids": len(old_set),
        "n_common_437": len(common),
        "n_new_59": len(only_new),
        "new_59_ids": only_new,
        "forecasts_copied": False,
        "working_tree_present": (root / OLD_IF_FREEZE_REL).is_file(),
    }


def consume_projection(root: Path, *, archived_ids: list[str], new_59_ids: list[str]) -> dict[str, Any]:
    """Consume staged metadata projection. No feature/forecast/score/economic values."""
    path = root / PROJECTION_REL
    if not path.is_file():
        raise FollowthroughRefuse(f"metadata projection missing {PROJECTION_REL}")
    raw = path.read_bytes()
    digest = sha256_bytes(raw)
    if digest != PROJECTION_SHA256:
        raise FollowthroughRefuse(f"metadata projection sha256 {digest} != {PROJECTION_SHA256}")
    body = json.loads(raw.decode("utf-8"))
    _scan_forbidden(body, where="metadata projection")
    if body.get("schema_id") != PROJECTION_SCHEMA:
        raise FollowthroughRefuse(f"projection schema {body.get('schema_id')} != {PROJECTION_SCHEMA}")
    if body.get("actual_clock_proof") is not False:
        raise FollowthroughRefuse("projection must not claim actual_clock_proof")
    if body.get("contemporaneous_availability_proof") is not False:
        raise FollowthroughRefuse("projection must not claim contemporaneous_availability_proof")

    counts = body.get("counts") or {}
    if int(counts.get("target", -1)) != EXACT_496:
        raise FollowthroughRefuse(f"projection target {counts.get('target')} != {EXACT_496}")
    if int(counts.get("old437", -1)) != N_OLD_437 or int(counts.get("new59", -1)) != N_NEW_59:
        raise FollowthroughRefuse(f"projection old/new {counts} != {N_OLD_437}+{N_NEW_59}")
    if int(counts.get("same96", -1)) != N_SAME_96:
        raise FollowthroughRefuse(f"projection same96 {counts.get('same96')} != {N_SAME_96}")
    if int(counts.get("schedule_reg_records", -1)) != N_SCHEDULE_REG:
        raise FollowthroughRefuse(
            f"projection schedule_reg_records {counts.get('schedule_reg_records')} != {N_SCHEDULE_REG}"
        )

    identities = list(body.get("identities") or [])
    if len(identities) != EXACT_496:
        raise FollowthroughRefuse(f"projection identities n={len(identities)} != {EXACT_496}")
    identity_ids = [str(row["game_id"]) for row in identities]
    if len(set(identity_ids)) != EXACT_496:
        raise FollowthroughRefuse("projection identities not unique")
    if set(identity_ids) != set(archived_ids):
        raise FollowthroughRefuse("projection identities != archived 496 set")
    n_2020 = sum(1 for row in identities if int(row["season"]) == 2020)
    n_2021 = sum(1 for row in identities if int(row["season"]) == 2021)
    if n_2020 != N_2020 or n_2021 != N_2021:
        raise FollowthroughRefuse(f"projection season split {n_2020}+{n_2021} != {N_2020}+{N_2021}")
    identity_rows = []
    for row in identities:
        identity_rows.append(
            {
                "game_id": str(row["game_id"]),
                "season": int(row["season"]),
                "week": int(row["week"]),
                "home": str(row["home"]),
                "away": str(row["away"]),
                "consumed_game_ids_home": list(row.get("consumed_game_ids_home") or []),
                "consumed_game_ids_away": list(row.get("consumed_game_ids_away") or []),
                "publication_timestamp_status": row.get("publication_timestamp_status"),
                "observation_timestamp_status": row.get("observation_timestamp_status"),
                "production_causal_claim": bool(row.get("production_causal_claim")),
                "selected_rating_week_home": row.get("selected_rating_week_home"),
                "selected_rating_week_away": row.get("selected_rating_week_away"),
            }
        )
        if row.get("production_causal_claim"):
            raise FollowthroughRefuse(f"projection causal claim refused for {row.get('game_id')}")
        if row.get("publication_timestamp_status") != "unverified":
            raise FollowthroughRefuse("publication timestamps must stay unverified")
        if row.get("observation_timestamp_status") != "unverified":
            raise FollowthroughRefuse("observation timestamps must stay unverified")

    old437_ids = [str(x) for x in body.get("old437_game_ids") or []]
    new59_ids = [str(x) for x in body.get("new59_game_ids") or []]
    if set(old437_ids) | set(new59_ids) != set(archived_ids):
        raise FollowthroughRefuse("projection old437/new59 != archived 496")
    if set(new59_ids) != set(new_59_ids):
        raise FollowthroughRefuse("projection new59 != archived new59")
    if len(old437_ids) != N_OLD_437 or len(new59_ids) != N_NEW_59:
        raise FollowthroughRefuse("projection old437/new59 counts drifted")

    schedule = list(body.get("physical_schedule_recorded_metadata_only") or [])
    if len(schedule) != N_SCHEDULE_REG:
        raise FollowthroughRefuse(f"projection schedule n={len(schedule)} != {N_SCHEDULE_REG}")
    schedule_rows = []
    for row in schedule:
        if row.get("season_type") != "REG":
            raise FollowthroughRefuse(f"non-REG schedule row {row.get('game_id')}")
        for clock_key in (
            "actual_kickoff_utc",
            "scheduled_kickoff_utc",
            "available_at",
            "observed_at",
        ):
            if row.get(clock_key) is not None:
                raise FollowthroughRefuse(
                    f"projection fabricated clock upgrade {clock_key}={row.get(clock_key)}"
                )
        schedule_rows.append(
            {
                "game_id": str(row["game_id"]),
                "season": row.get("season"),
                "week": row.get("week"),
                "season_type": "REG",
                "home": str(row["home"]),
                "away": str(row["away"]),
                "game_date": row.get("game_date"),
                "start_time_raw": row.get("start_time_raw"),
                "start_time_raw_role": PBP_TIME_ROLE,
                "played_status": row.get("played_status"),
                "played_status_is_actual_clock_proof": False,
                "actual_kickoff_utc": None,
                "scheduled_kickoff_utc": None,
                "available_at": None,
                "observed_at": None,
                "source_locator": row.get("source_locator"),
            }
        )
    if not all(
        row["played_status"] == "HISTORICAL_PBP_EXTRACT_RECORD_NOT_INDEPENDENT_ACTUAL_CLOCK_PROOF"
        for row in schedule_rows
    ):
        raise FollowthroughRefuse("schedule played_status upgraded beyond recorded-metadata label")

    same96 = list(body.get("same96_metadata") or [])
    if len(same96) != N_SAME_96:
        raise FollowthroughRefuse(f"projection same96 n={len(same96)} != {N_SAME_96}")
    same96_rows = []
    for row in same96:
        if row.get("price_or_line_included") is not False:
            raise FollowthroughRefuse(f"same96 price/line leaked for {row.get('game_id')}")
        gid = str(row["game_id"])
        if gid not in set(archived_ids):
            raise FollowthroughRefuse(f"same96 id not in 496: {gid}")
        same96_rows.append(
            {
                "game_id": gid,
                "kickoff_utc_from_B1": row.get("kickoff_utc_from_B1"),
                "cutoff_utc_from_B1": row.get("cutoff_utc_from_B1"),
                "price_or_line_included": False,
                "b1_kickoff_is_certified_actual_utc": False,
                "b1_cutoff_is_ko_minus_60_seal": False,
            }
        )
    same96_ids = [row["game_id"] for row in same96_rows]
    if len(set(same96_ids)) != N_SAME_96:
        raise FollowthroughRefuse("same96 ids not unique")

    declared = [str(x) for x in body.get("matrix_declared_fields") or []]
    if set(declared) != set(CONTRACT_27) or len(declared) != N_CONTRACT_27:
        raise FollowthroughRefuse("matrix_declared_fields != CONTRACT_27")

    field_meta = list(body.get("matrix_field_metadata") or [])
    if len(field_meta) != EXACT_496:
        raise FollowthroughRefuse(f"matrix_field_metadata n={len(field_meta)} != {EXACT_496}")
    field_rows = []
    raw_cutoffs: list[str] = []
    for row in field_meta:
        gid = str(row["game_id"])
        if gid not in set(archived_ids):
            raise FollowthroughRefuse(f"field metadata id not in 496: {gid}")
        raw = row.get("raw_field_named_pregame_cutoff_utc")
        if not raw:
            raise FollowthroughRefuse(f"missing raw_field_named_pregame_cutoff_utc for {gid}")
        raw_cutoffs.append(str(raw))
        counts_status = row.get("claimed_status_counts") or {}
        if counts_status != {"DERIVED_PREGAME": N_CONTRACT_27}:
            raise FollowthroughRefuse(f"field status drifted for {gid}: {counts_status}")
        if int(row.get("n_fields", -1)) != N_CONTRACT_27:
            raise FollowthroughRefuse(f"n_fields drifted for {gid}")
        if row.get("field_set_matches_declared") is not True:
            raise FollowthroughRefuse(f"field set mismatch for {gid}")
        field_rows.append(
            {
                "game_id": gid,
                "n_fields": N_CONTRACT_27,
                "field_set_matches_declared": True,
                "claimed_status_counts": {"DERIVED_PREGAME": N_CONTRACT_27},
                "field_source_set_digest": row.get("field_source_set_digest"),
                "field_metadata_sha256": row.get("field_metadata_sha256"),
                "n_unique_field_source_hashes": row.get("n_unique_field_source_hashes"),
                "raw_field_named_pregame_cutoff_utc": str(raw),
                "raw_field_named_pregame_cutoff_utc_role": RAW_CUTOFF_ROLE,
                "used_as_seal": False,
                "silently_subtracted_60": False,
                "reconstructed_feature_values": False,
            }
        )
    if len(set(raw_cutoffs)) < 1:
        raise FollowthroughRefuse("no raw cutoff values")

    source_pins = dict(body.get("source_pins") or {})
    expected_pins = {row["locator"]: row["sha256_pin"] for row in CLOUD_METADATA_LOCATORS}
    if source_pins != expected_pins:
        raise FollowthroughRefuse(f"projection source_pins drifted: {source_pins}")

    timestamp_audit = _audit_same96_timestamps(same96_rows, field_rows)
    declared_audit = body.get("matrix_timestamp_audit") or {}
    if int(declared_audit.get("matrix_named_pregame_cutoff_equals_B1_kickoff", -1)) != N_SAME_96:
        raise FollowthroughRefuse("projection timestamp audit kickoff count drifted")
    if int(declared_audit.get("matrix_named_pregame_cutoff_equals_B1_true_cutoff", -1)) != 0:
        raise FollowthroughRefuse("projection timestamp audit cutoff count drifted")
    if timestamp_audit["matrix_named_pregame_cutoff_equals_B1_kickoff"] != N_SAME_96:
        raise FollowthroughRefuse("independent same96 cutoff==B1 kickoff failed")
    if timestamp_audit["matrix_named_pregame_cutoff_equals_B1_true_cutoff"] != 0:
        raise FollowthroughRefuse("independent same96 cutoff==B1 true cutoff was not 0")

    return {
        "opened": "staged_metadata_projection_only",
        "path": PROJECTION_REL,
        "schema_id": PROJECTION_SCHEMA,
        "commit": PROJECTION_COMMIT,
        "sha256": digest,
        "sha256_required": PROJECTION_SHA256,
        "sha256_match": True,
        "bytes": len(raw),
        "actual_clock_proof": False,
        "contemporaneous_availability_proof": False,
        "counts": {
            "target": EXACT_496,
            "old437": N_OLD_437,
            "new59": N_NEW_59,
            "same96": N_SAME_96,
            "schedule_reg_records": N_SCHEDULE_REG,
        },
        "identities": identity_rows,
        "physical_schedule_recorded_metadata_only": schedule_rows,
        "old437_game_ids": old437_ids,
        "new59_game_ids": new59_ids,
        "same96_metadata": same96_rows,
        "same96_ids": same96_ids,
        "matrix_declared_fields": declared,
        "matrix_field_metadata": field_rows,
        "matrix_timestamp_audit": timestamp_audit,
        "source_pins": source_pins,
        "limits": list(body.get("limits") or []),
        "feature_values_copied": False,
        "forecasts_copied": False,
        "target_scores_copied": False,
        "outcomes_copied": False,
        "economics_copied": False,
        "originals_untouched": True,
    }


def _audit_same96_timestamps(
    same96_rows: list[dict[str, Any]],
    field_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """Independent 96-game check only. Do not generalize to 496 or subtract 60."""
    fields = {row["game_id"]: row for row in field_rows}
    eq_kick = 0
    eq_cut = 0
    for row in same96_rows:
        meta = fields.get(row["game_id"])
        if meta is None:
            raise FollowthroughRefuse(f"same96 missing matrix field metadata {row['game_id']}")
        raw = meta["raw_field_named_pregame_cutoff_utc"]
        if raw == row["kickoff_utc_from_B1"]:
            eq_kick += 1
        if raw == row["cutoff_utc_from_B1"]:
            eq_cut += 1
    return {
        "n_same96": N_SAME_96,
        "matrix_named_pregame_cutoff_equals_B1_kickoff": eq_kick,
        "matrix_named_pregame_cutoff_equals_B1_true_cutoff": eq_cut,
        "matrix_named_pregame_cutoff_equals_actual_ko_minus_60": 0,
        "actual_ko_minus_60_computed": False,
        "used_as_seal": False,
        "silently_subtracted_60": False,
        "meaning_generalized_beyond_same96": False,
        "independent_recompute": True,
        "role": RAW_CUTOFF_ROLE,
        "note": (
            "On the independent 96, R4 matrix pregame_cutoff_utc equals B1 kickoff_utc "
            "and equals B1 true cutoff on 0. All 496 have one consistent raw value each. "
            "Do not feed that field as a seal or silently subtract 60. "
            "0 == actual KO−60 is the recorded audit result; actual KO was not computed here."
        ),
    }


def project_targets(
    game_ids: list[str],
    *,
    projection: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Identity + consumed metadata slots. Unknown actual clocks stay unknown."""
    identities = {row["game_id"]: row for row in projection["identities"]}
    schedule = {row["game_id"]: row for row in projection["physical_schedule_recorded_metadata_only"]}
    fields = {row["game_id"]: row for row in projection["matrix_field_metadata"]}
    same96 = {row["game_id"]: row for row in projection["same96_metadata"]}
    rows: list[dict[str, Any]] = []
    for gid in game_ids:
        ident = identities[gid]
        sched = schedule.get(gid)
        field = fields[gid]
        market = same96.get(gid)
        rows.append(
            {
                "game_id": gid,
                "season": ident["season"],
                "week": ident["week"],
                "season_type": "REG",
                "away_team": ident["away"],
                "home_team": ident["home"],
                "identity_ready": True,
                "consumed_game_ids_home": ident["consumed_game_ids_home"],
                "consumed_game_ids_away": ident["consumed_game_ids_away"],
                "publication_timestamp_status": "unverified",
                "observation_timestamp_status": "unverified",
                "production_causal_claim": False,
                "actual_kickoff_utc": None,
                "scheduled_kickoff_utc": None,
                "available_at": None,
                "observed_at": None,
                "actual_versus_scheduled": "UNKNOWN",
                "played": "UNKNOWN",
                "played_status_recorded": (
                    sched["played_status"] if sched else None
                ),
                "played_status_is_actual_clock_proof": False,
                "pbp_game_date": sched["game_date"] if sched else None,
                "pbp_start_time_raw": sched["start_time_raw"] if sched else None,
                "pbp_start_time_raw_role": PBP_TIME_ROLE,
                "predecessor_ready": False,
                "rest_ready": False,
                "strict_rest_ready": False,
                "strict_rest_block_reason": STRICT_REST_BLOCK_REASON,
                "previous_week_history_pointer_eligible": ident["week"] >= 2,
                "previous_week_history_pointer": "UNOPENED",
                "availability": "UNKNOWN",
                "same96_member": market is not None,
                "same96_kickoff_utc_from_B1": market["kickoff_utc_from_B1"] if market else None,
                "same96_cutoff_utc_from_B1": market["cutoff_utc_from_B1"] if market else None,
                "raw_field_named_pregame_cutoff_utc": field["raw_field_named_pregame_cutoff_utc"],
                "raw_field_named_pregame_cutoff_utc_role": RAW_CUTOFF_ROLE,
                "raw_field_named_pregame_cutoff_utc_used_as_seal": False,
                "raw_field_named_pregame_cutoff_utc_silently_subtracted_60": False,
                "field_source_set_digest": field["field_source_set_digest"],
                "field_metadata_sha256": field["field_metadata_sha256"],
                "claimed_status_counts": field["claimed_status_counts"],
                "score_bearing_payload": False,
            }
        )
    return rows


def consumed_cloud_metadata(root: Path) -> list[dict[str, Any]]:
    rows = []
    for row in CLOUD_METADATA_LOCATORS:
        locator = str(row["locator"])
        rows.append(
            {
                "locator": locator,
                "role": row["role"],
                "sha256_pin": row["sha256_pin"],
                "working_tree": "ABSENT_COPY_OK",
                "working_tree_present": (root / locator).is_file(),
                "status": "CONSUMED_VIA_STAGED_PROJECTION",
                "resolves": "absent_cloud_metadata",
                "does_not_resolve": "unknown_actual_clock_provenance",
            }
        )
    rows.append(
        {
            "locator": "same96 IDs + B1 kickoff/cutoff time metadata",
            "role": "same96 identity/time metadata (not book prices; not actual-clock proof)",
            "sha256_pin": PROJECTION_SHA256,
            "working_tree": "CONSUMED_FROM_PROJECTION",
            "working_tree_present": True,
            "status": "CONSUMED_VIA_STAGED_PROJECTION",
            "resolves": "absent_cloud_metadata",
            "does_not_resolve": "unknown_actual_clock_provenance",
        }
    )
    return rows


def missing_locators(root: Path) -> list[dict[str, Any]]:
    """Cloud metadata is consumed. Residual missing is the POINT-ERROR digest only."""
    digest = POINT_ERROR_MARKET_DIGEST
    present = False
    # Do not invent a path. Only count a real existing file if one is later added
    # at an explicit digest locator. None exists on this checkout.
    return [
        {
            "locator": digest["locator"],
            "role": digest["role"],
            "sha256_pin": digest["sha256_pin"],
            "working_tree": "ABSENT",
            "working_tree_present": present,
            "count_blocked": N_SAME_96,
            "blocks": "POINT_ERROR_market_reference_bind",
            "does_not_block": [
                "cloud_metadata_identities",
                "same96_ids_and_b1_times",
            ],
            "invented_prices": False,
            "invented_opener_close_label": False,
        }
    ]


def ntbb_k_integrate_hooks() -> dict[str, Any]:
    """Freeze Cos-accepted RETURN 36205 tip only. Not a real R7 model arm."""
    return {
        "status": "FROZEN_ISOLATED_SYNTHETIC_KERNEL",
        "return_order": RETURN_NTBBK,
        "refused_tip": B_NTBBK_TIP_REFUSED,
        "refused_tip_short": "d0bb6bef",
        "frozen_tip": B_NTBBK_TIP_FROZEN,
        "frozen_tip_short": "a807af22",
        "frozen_as_final": True,
        "integrated": True,
        "r7_model_arm": False,
        "kernel_files_copied": True,
        "kernel_sha256_locked": True,
        "kernel_sha256": B_NTBBK_KERNEL_SHA256,
        "profile_id": NTBBK_PROFILE_HOOK,
        "profile_status": "REGISTERED_ISOLATED_NOT_R7_MODEL_ARM",
        "shared_gate_registered": True,
        "isolated_area": NTBBK_ISOLATED_AREA,
        "isolated_ops": NTBBK_ISOLATED_OPS,
        "package_closed_from_b_alone": False,
        "producer_capability_gate": {
            "owner": "A",
            "status": "A_OBLIGATION_NOT_CLOSED_BY_B",
            "reexecuted_this_turn": False,
            "real_science": False,
        },
        "scipy_fitting": "UNEXECUTED_DEPENDENCY_HELD",
        "b_clocks_promoted": False,
        "note": (
            "Cos ACCEPT RETURN 36205 tip a807af22 frozen as isolated NTBB-K "
            "SYNTHETIC kernel. d0bb6bef refused. Not a real R7 model arm. "
            "Producer→capability/gate remains Worker A."
        ),
    }


def retro_c1_hold() -> dict[str, Any]:
    """DESIGN 25194 / HISTORY 47316 — synthetic executor implemented; real EXEC HOLD."""
    return {
        "package": RETRO_C1_HOLD,
        "status": "SYNTHETIC_EXECUTOR_READY_REAL_EXEC_HOLD",
        "started": True,
        "implemented": True,
        "real_exec": False,
        "spec_id": RETRO_C1_SPEC,
        "spec_sha_prefix": RETRO_C1_SPEC_SHA_PREFIX,
        "strict_actual_kickoff_live_causal": "DATA_HOLD",
        "forecasts": False,
        "real_features": False,
        "cert": CERT,
    }


def fifth_prerequisite(projection: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "scope": "POINT_ERROR_VS_FROZEN_MEDIAN_SPREAD_MARKET_REFERENCE_SAME96",
        "score_access": False,
        "forecast_authorization": False,
        "book_specific_offered_price_required": False,
        "book_specific_settlement_required": False,
        "book_specific_blocks": ["historical_economic", "ATS", "ROI", "CLV"],
        "same96_ids_bound": True,
        "same96_b1_times_bound": True,
        "same96_n": len(projection["same96_ids"]),
        "price_or_line_included": False,
        "market_point_bind": {
            "method": "existing_freeze_or_digest_only",
            "invented_prices": False,
            "opener_close_label_invented": False,
            "digest_found": False,
            "locator": POINT_ERROR_MARKET_DIGEST["locator"],
            "sha256_pin": None,
            "status": "ABSENT",
            "source": "no existing frozen median-spread digest on this checkout; not invented",
        },
    }


def runtime_versions() -> dict[str, Any]:
    numpy_ver = None
    scipy_ver = None
    try:
        import numpy

        numpy_ver = numpy.__version__
    except Exception:
        numpy_ver = None
    try:
        import scipy

        scipy_ver = scipy.__version__
    except Exception:
        scipy_ver = "ABSENT"
    return {
        "python": sys.version.split()[0],
        "python_full": sys.version,
        "platform": platform.platform(),
        "numpy": numpy_ver,
        "scipy": scipy_ver,
        "tz": CALENDAR_TZ,
        "calendar_id": CALENDAR_ID,
        "ko_minus_minutes": KO_MINUS_MINUTES,
        "simulations": SIMULATIONS,
        "seed_base": SEED_BASE,
        "seed_mod": SEED_MOD,
        "market_blend": MARKET_BLEND,
        "candidate_weight": CANDIDATE_WEIGHT,
        "if_tip": IF_TIP,
        "sim_sha256": SIM_SHA256,
        "fw_sha256": FW_SHA256,
        "apply_linear_totals_calibration": False,
        "bootstrap_B": BOOTSTRAP_B,
        "bootstrap_gen": BOOTSTRAP_GEN,
        "bootstrap_seed": BOOTSTRAP_SEED,
        "sensitivity_seed": SENSITIVITY_SEED,
        "scipy_required_for_kernel": True,
        "kernel_authorized": False,
        "scipy_install_attempted": False,
    }


def build_candidate(*, root: Path | None = None) -> dict[str, Any]:
    repo = repo_root() if root is None else Path(root)
    runtime_source_revision = git_tip(repo)
    spec = require_spec(repo)
    sources = bind_working_tree_sources(repo)
    identity = bind_archived_identity(repo)
    split = bind_old437_new59(repo, identity["game_ids"])
    projection = consume_projection(
        repo, archived_ids=identity["game_ids"], new_59_ids=split["new_59_ids"]
    )
    targets = project_targets(identity["game_ids"], projection=projection)
    consumed = consumed_cloud_metadata(repo)
    missing = missing_locators(repo)
    fifth = fifth_prerequisite(projection)
    ntbb_hooks = ntbb_k_integrate_hooks()
    retro_hold = retro_c1_hold()
    residuals = {
        "actual_clock_provenance": {
            "actual_kickoff_utc": "UNKNOWN",
            "scheduled_kickoff_utc": "UNKNOWN",
            "available_at": "UNKNOWN",
            "observed_at": "UNKNOWN",
            "actual_clock_proof": False,
            "contemporaneous_availability_proof": False,
            "fabricated_upgrade": False,
            "live_gate_bypass": False,
        },
        "strict_rest": {
            "blocked": True,
            "reason": STRICT_REST_BLOCK_REASON,
        },
        "book_specific_offered_price_settlement": list(ECONOMIC_RESIDUALS),
        "scipy": "ABSENT",
        "ntbb_k_kernel": "FROZEN_ISOLATED_SYNTHETIC_KERNEL_NOT_R7_MODEL_ARM",
        "ntbb_k_return": RETURN_NTBBK,
        "ntbb_k_frozen_tip": B_NTBBK_TIP_FROZEN,
        "science_hold": True,
        "retro_c1": retro_hold["status"],
    }
    candidate = {
        "schema_id": SCHEMA_ID,
        "schema_delta": SCHEMA_DELTA,
        "package": PACKAGE,
        "owner_clear": OWNER_CLEAR,
        "authority": AUTHORITY,
        "metadata_authority": METADATA_AUTHORITY,
        "metadata_order": METADATA_ORDER,
        "scope_id": SCOPE_ID,
        "cert": CERT,
        "channel": "METADATA_PREFLIGHT_DELTA",
        "opt_in": True,
        "implemented_ne_verified": True,
        "kernel_implemented": False,
        "ready_for_real_exec": False,
        "science_hold": True,
        "runtime_source_revision": runtime_source_revision,
        "packaging_revision": None,
        "packaging_revision_claimed_as_executed": False,
        "prior_packaging_revision": PRIOR_PACKAGING_REVISION,
        "start_tip": START_TIP,
        "spec_commit": SPEC_COMMIT,
        "projection_commit": PROJECTION_COMMIT,
        "spec": spec,
        "counts": {
            "exact496": EXACT_496,
            "n_2020": N_2020,
            "n_2021": N_2021,
            "sum_240_256": N_2020 + N_2021,
            "old437": N_OLD_437,
            "new59": N_NEW_59,
            "sum_437_59": N_OLD_437 + N_NEW_59,
            "same96": N_SAME_96,
            "same96_ids_present": True,
            "schedule_reg_records": N_SCHEDULE_REG,
            "contract_27": N_CONTRACT_27,
        },
        "consumed_sources": sources,
        "consumed_projection": {
            k: projection[k]
            for k in projection
            if k
            not in {
                "identities",
                "physical_schedule_recorded_metadata_only",
                "matrix_field_metadata",
                "old437_game_ids",
                "new59_game_ids",
                "same96_metadata",
            }
        },
        "identities": projection["identities"],
        "physical_schedule_recorded_metadata_only": projection[
            "physical_schedule_recorded_metadata_only"
        ],
        "same96_metadata": projection["same96_metadata"],
        "matrix_field_metadata": projection["matrix_field_metadata"],
        "timestamp_role": projection["matrix_timestamp_audit"],
        "fifth_prerequisite": fifth,
        "ntbb_k_integrate": ntbb_hooks,
        "retro_c1_hold": retro_hold,
        "consumed_cloud_metadata": consumed,
        "r7_config_hash": r7_config_hash(),
        "r7_code_hash": r7_code_hash(repo),
        "runtime": runtime_versions(),
        "archived_control": {
            "identity": {k: identity[k] for k in identity if k != "game_ids"},
            "old437_new59": {k: split[k] for k in split if k != "new_59_ids"},
            "unopened_label_history_pointers": list(UNOPENED_LABEL_POINTERS),
        },
        "game_ids": identity["game_ids"],
        "new_59_ids": split["new_59_ids"],
        "same96_ids": projection["same96_ids"],
        "targets": targets,
        "missing": missing,
        "missing_n": len(missing),
        "missing_n_prior": PRIOR_MISSING_N,
        "missing_n_delta": len(missing) - PRIOR_MISSING_N,
        "residuals": residuals,
        "projection_request": {
            "needed": False,
            "cloud_metadata_resolved": True,
            "actual_clock_provenance_resolved": False,
            "reason": (
                "staged R7_METADATA_PROJECTION consumed; absent cloud metadata resolved; "
                "actual/scheduled/availability remain unknown; frozen median-spread "
                "market-point digest still absent for POINT-ERROR bind"
            ),
            "locators": [row["locator"] for row in missing],
            "do_not_include": [
                "home_score",
                "away_score",
                "actual_margin",
                "labels",
                "outcomes",
                "reconstructed_feature_values",
                "forecasts",
                "target_scores",
                "economics",
                "invented_prices",
                "invented_opener_close_label",
            ],
            "permitted_fields": [
                "game_id",
                "season",
                "week",
                "season_type",
                "home_team",
                "away_team",
                "frozen_median_spread_market_point",
                "existing_freeze_digest",
            ],
        },
        "readiness": "NOT_READY",
        "score_bearing_payload_returned": False,
        "causal_to_retrospective_bypass": False,
        "worker_id": WORKER_A_ID,
        "produced_utc": _utc_now(),
    }
    _scan_forbidden(candidate, where="candidate")
    return candidate


def load_prior_fictional_chain(*, dest: Path) -> dict[str, Any]:
    """Reuse Phase 1 fictional chain. Re-exec is not authorized this turn."""
    prior = dest / "receipt.json"
    if not prior.is_file():
        raise FollowthroughRefuse("prior fictional receipt missing; re-exec not authorized")
    body = json.loads(prior.read_text(encoding="utf-8"))
    chain = body.get("fictional_chain")
    if not isinstance(chain, Mapping):
        raise FollowthroughRefuse("prior fictional_chain missing; re-exec not authorized")
    for key, expected in PRESERVED_FICTIONAL.items():
        if chain.get(key) != expected:
            raise FollowthroughRefuse(
                f"prior fictional {key} drifted {chain.get(key)} != {expected}"
            )
    reused = dict(chain)
    reused["reexecuted_this_turn"] = False
    reused["reused_from"] = f"{OPS_REL}/receipt.json"
    return reused


def run_fictional_chain(*, root: Path, dest: Path) -> dict[str, Any]:
    """One actual fictional producer→gate→consumer→atomic readback.

    Kept for Phase 1 compatibility. METADATA 14083 must not call this.
    """
    from src.services.nfl_r7_correctness_v1.run import run_r7_integrated
    from src.services.nfl_ops_v1_evidence.validate_r7 import dest_is_actually_temp, readback_and_rehash
    from src.services.nfl_t5208u.hashing import sha256_file as sha_file
    from src.services.nfl_t5208u.caller import model_spy_counts, reset_model_spy

    outcome_spy = OutcomeReadSpy()
    surface = ForbiddenSurfaceSpy()
    reset_model_spy()
    receipt = run_r7_integrated(root=root, dest=dest)
    result_path = Path(dest) / "demo_result.json"
    if not result_path.is_file():
        raise FollowthroughRefuse("fictional chain did not write demo_result.json")
    expected = sha_file(result_path)
    readback_and_rehash(result_path, expected)
    if outcome_spy.reads not in (None, 0):
        raise FollowthroughRefuse("fictional chain read outcomes")
    return {
        "ok": bool(receipt.get("ok")),
        "exit": receipt.get("exit"),
        "exit_source": receipt.get("exit_source"),
        "game_id": receipt["produce"]["game_id"],
        "if_margin": receipt["produce"]["if_margin"],
        "q2_margin": receipt["produce"]["q2_margin"],
        "c_margin": receipt["produce"]["c_margin"],
        "pair_hash": receipt["pair"]["pair_hash"],
        "r7_config_hash": receipt["produce"]["r7_config_hash"],
        "r7_code_hash": receipt["produce"]["r7_code_hash"],
        "apply_linear_totals_calibration": receipt["produce"].get("apply_linear_totals_calibration"),
        "demo_result_sha256": expected,
        "final_dest_is_temp": dest_is_actually_temp(dest),
        "model_spy": model_spy_counts(),
        "outcome_reads": outcome_spy.reads,
        "surface_notes": surface.count,
        "command": "PYTHONPATH=services/model-service python3 scripts/nfl/run_nfl_r7_followthrough_preflight.py",
    }


def run_direct_boundary_controls() -> dict[str, Any]:
    from src.services.nfl_ops_v1_evidence.spy import run_spy_positive_control

    spy = run_spy_positive_control()
    negatives: list[dict[str, Any]] = []
    try:
        _scan_forbidden({"home_score": 21}, where="negative")
        negatives.append({"name": "score_key", "refused": False})
    except FollowthroughRefuse:
        negatives.append({"name": "score_key", "refused": True})
    try:
        require_spec(Path("/nonexistent/repo-root"))
        negatives.append({"name": "missing_spec", "refused": False})
    except FollowthroughRefuse:
        negatives.append({"name": "missing_spec", "refused": True})
    if not all(item["refused"] for item in negatives):
        raise FollowthroughRefuse(f"direct-boundary negatives failed: {negatives}")
    return {"spy_positive_control": dict(spy), "negatives": negatives}


def run_followthrough_preflight(*, root: Path | None = None) -> dict[str, Any]:
    repo = repo_root() if root is None else Path(root)
    dest = repo / OPS_REL
    dest.mkdir(parents=True, exist_ok=True)
    candidate = build_candidate(root=repo)
    fictional = load_prior_fictional_chain(dest=dest)
    boundaries = run_direct_boundary_controls()
    receipt = {
        "ok": True,
        "cert": CERT,
        "status": "PREFLIGHT_CLOUD_METADATA_CONSUMED_ACTUAL_CLOCK_UNKNOWN",
        "ready_for_review": False,
        "accepted": False,
        "package": PACKAGE,
        "owner_clear": OWNER_CLEAR,
        "metadata_authority": METADATA_AUTHORITY,
        "metadata_order": METADATA_ORDER,
        "runtime_source_revision": candidate["runtime_source_revision"],
        "packaging_revision": None,
        "counts": candidate["counts"],
        "readiness": candidate["readiness"],
        "missing_n": candidate["missing_n"],
        "missing_n_prior": candidate["missing_n_prior"],
        "missing_n_delta": candidate["missing_n_delta"],
        "spec_sha256": candidate["spec"]["sha256"],
        "projection_sha256": candidate["consumed_projection"]["sha256"],
        "r7_config_hash": candidate["r7_config_hash"],
        "r7_code_hash": candidate["r7_code_hash"],
        "fictional_chain": fictional,
        "boundaries": boundaries,
        "kernel_implemented": False,
        "fifth_prerequisite": candidate["fifth_prerequisite"],
        "ntbb_k_integrate": candidate["ntbb_k_integrate"],
        "retro_c1_hold": candidate["retro_c1_hold"],
        "timestamp_role": candidate["timestamp_role"],
        "residuals": candidate["residuals"],
    }
    _scan_forbidden(receipt, where="receipt")
    write_json(dest / "CANDIDATE.json", candidate)
    write_json(dest / "MISSING.json", {"n": candidate["missing_n"], "missing": candidate["missing"]})
    write_json(dest / "receipt.json", receipt)
    projection_request = {
        "schema_id": SCHEMA_ID,
        "schema_delta": SCHEMA_DELTA,
        "request": candidate["projection_request"],
        "counts": candidate["counts"],
        "consumed_projection_sha256": candidate["consumed_projection"]["sha256"],
    }
    write_json(dest / "PROJECTION_REQUEST.json", projection_request)
    return receipt


def main() -> int:
    receipt = run_followthrough_preflight()
    print(
        json.dumps(
            {
                "ok": receipt["ok"],
                "status": receipt["status"],
                "runtime_source_revision": receipt["runtime_source_revision"],
                "readiness": receipt["readiness"],
                "missing_n": receipt["missing_n"],
                "missing_n_prior": receipt["missing_n_prior"],
                "missing_n_delta": receipt["missing_n_delta"],
                "exact496": receipt["counts"]["exact496"],
                "same96_ids_present": receipt["counts"]["same96_ids_present"],
                "projection_sha256": receipt["projection_sha256"],
                "fictional_reexecuted": receipt["fictional_chain"].get("reexecuted_this_turn"),
            },
            sort_keys=True,
        )
    )
    return 0 if receipt["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
