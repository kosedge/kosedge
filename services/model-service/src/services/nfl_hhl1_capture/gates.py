"""Fail-closed activation gates. Every live path is OFF and stays OFF.

t4791u authorizes plumbing only. Env vars cannot lift this CLEAR.
nowcast is OFF in all environments. Field names ≠ permission (R4).
"""

from __future__ import annotations

import os
from typing import Any, Iterable, Mapping, Optional

from src.services.nfl_hhl1_capture.constants import (
    ADMITTED_SOURCE_ID,
    ADMITTED_SOURCE_IDS,
    DELTA_CONSTANT_OVERRIDE_ENV_VARS,
    HHL1_ENABLE_ENV_VARS,
    NOWCAST_FIELD_NAMES,
    NOWCAST_SOURCE_IDS,
    RATING_WINDOW_DEFINITION,
    SIMULATOR_EXECUTABLE_IDENTITY,
    SIMULATOR_SHA_PROTOCOL_PIN,
    SIMULATOR_SHA_TIP_BYTES,
    TRUTHY_ENV_VALUES,
)
from src.services.nfl_hhl1_capture.schema import (
    ExclusionRecord,
    Hhl1Reject,
    Hhl1RejectCode,
)

# Hard locks. Not read from env. Not overridable.
HHL1_LIVE_CAPTURE_AUTHORIZED = False
HHL1_EXTERNAL_ACQUISITION_AUTHORIZED = False
HHL1_NOWCAST_AUTHORIZED = False
HHL1_SCORING_AUTHORIZED = False
HHL1_PUBLICATION_AUTHORIZED = False
HHL1_HISTORICAL_RECONSTRUCTION_AUTHORIZED = False
HHL1_MODEL_EXECUTION_AUTHORIZED = False


def _env_truthy(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in TRUTHY_ENV_VALUES


def assert_activation_locked() -> None:
    """Any attempt to enable capture/score/publish — including via env — REJECTS."""
    if HHL1_LIVE_CAPTURE_AUTHORIZED or HHL1_EXTERNAL_ACQUISITION_AUTHORIZED:
        raise Hhl1Reject(
            Hhl1RejectCode.NOT_AUTHORIZED,
            "live capture / external acquisition flag was True (must stay False)",
        )
    if HHL1_NOWCAST_AUTHORIZED:
        raise Hhl1Reject(Hhl1RejectCode.NOWCAST_OFF, "nowcast flag was True (must stay False)")
    if HHL1_SCORING_AUTHORIZED or HHL1_MODEL_EXECUTION_AUTHORIZED:
        raise Hhl1Reject(
            Hhl1RejectCode.NOT_AUTHORIZED,
            "scoring / model-execution flag was True (must stay False)",
        )
    if HHL1_PUBLICATION_AUTHORIZED:
        raise Hhl1Reject(
            Hhl1RejectCode.NOT_AUTHORIZED,
            "publication flag was True (must stay False)",
        )
    if HHL1_HISTORICAL_RECONSTRUCTION_AUTHORIZED:
        raise Hhl1Reject(
            Hhl1RejectCode.NOT_AUTHORIZED,
            "historical reconstruction flag was True (must stay False)",
        )
    enabled = [name for name in HHL1_ENABLE_ENV_VARS if _env_truthy(name)]
    if enabled:
        raise Hhl1Reject(
            Hhl1RejectCode.NOT_AUTHORIZED,
            f"env attempted to enable {enabled}; t4791u cannot be lifted by env",
        )


def assert_nowcast_off() -> None:
    """nowcast OFF everywhere. Env cannot enable it."""
    if HHL1_NOWCAST_AUTHORIZED or _env_truthy("HHL1_NOWCAST_ENABLED"):
        raise Hhl1Reject(
            Hhl1RejectCode.NOWCAST_OFF,
            "nowcast is OFF in all envs; HHL1_NOWCAST_ENABLED cannot authorize it",
        )


def assert_no_delta_constant_overrides() -> None:
    """Protocol 4.4(vi): NFL_INJURY_* overrides FORBIDDEN on a scoring run.

    Exposed as a plumbing gate for a future scoring CLEAR. This CLEAR does
    not score and does not read those values as weights.
    """
    present = [name for name in DELTA_CONSTANT_OVERRIDE_ENV_VARS if os.getenv(name)]
    if present:
        raise Hhl1Reject(
            Hhl1RejectCode.NOT_AUTHORIZED,
            f"delta-constant env overrides present {present} (FORBIDDEN)",
        )


def select_admitted_source(source_id: Any) -> str:
    """Return the admitted source id or REJECT. Does not fetch."""
    assert_nowcast_off()
    raw = str(source_id or "").strip()
    if not raw:
        raise Hhl1Reject(Hhl1RejectCode.PROVENANCE_INCOMPLETE, "source_id missing (no impute)")
    lowered = raw.lower()
    if lowered in NOWCAST_SOURCE_IDS or "nowcast" in lowered:
        raise Hhl1Reject(
            Hhl1RejectCode.NOWCAST_OFF,
            f"source_id={raw!r} is a nowcast/unsupported path; nowcast OFF (R4)",
        )
    if raw not in ADMITTED_SOURCE_IDS and lowered not in ADMITTED_SOURCE_IDS:
        raise Hhl1Reject(
            Hhl1RejectCode.UNSUPPORTED_SOURCE,
            f"source_id={raw!r} is not {ADMITTED_SOURCE_ID} (fail-closed)",
        )
    return ADMITTED_SOURCE_ID


def reject_nowcast_fields(row: Mapping[str, Any]) -> None:
    """R4: injury_nowcast_* names on an L1 row are unsupported provenance."""
    keys = set(row.keys())
    payload = row.get("payload")
    if isinstance(payload, Mapping):
        keys.update(payload.keys())
    hit = sorted(keys & NOWCAST_FIELD_NAMES)
    if hit:
        raise Hhl1Reject(
            Hhl1RejectCode.NOWCAST_OFF,
            f"L1 contains nowcast field names {hit}; names ≠ nowcast auth (R4)",
        )


def acquire_official_report(*_args: Any, **_kwargs: Any) -> None:
    raise Hhl1Reject(
        Hhl1RejectCode.NOT_AUTHORIZED,
        "live capture / official-report fetch is not authorized (t4791u plumbing only)",
    )


def fetch_nowcast(*_args: Any, **_kwargs: Any) -> None:
    raise Hhl1Reject(
        Hhl1RejectCode.NOWCAST_OFF,
        "fetch_nfl_injury_nowcast / nowcast surface is OFF (O-d, R4)",
    )


def acquire_odds(*_args: Any, **_kwargs: Any) -> None:
    raise Hhl1Reject(
        Hhl1RejectCode.NOT_AUTHORIZED,
        "Odds HOLD 70c56700 — paid Odds / The Odds API calls are not authorized",
    )


def score_l1(*_args: Any, **_kwargs: Any) -> None:
    raise Hhl1Reject(
        Hhl1RejectCode.NOT_AUTHORIZED,
        "scoring / model execution is not authorized (t4791u plumbing only); "
        f"simulator identity {SIMULATOR_EXECUTABLE_IDENTITY} "
        f"(protocol pin {SIMULATOR_SHA_PROTOCOL_PIN} vs tip {SIMULATOR_SHA_TIP_BYTES})",
    )


def publish(*_args: Any, **_kwargs: Any) -> None:
    raise Hhl1Reject(
        Hhl1RejectCode.NOT_AUTHORIZED,
        "publication is not authorized (t4791u plumbing only)",
    )


def build_baseline_personnel_ref(*_args: Any, **_kwargs: Any) -> None:
    """R3: rating-window definition is UNRESOLVED. Do not invent one."""
    raise Hhl1Reject(
        Hhl1RejectCode.RATING_WINDOW_UNRESOLVED,
        "baseline_personnel_ref builder is not authorized; "
        f"rating_window={RATING_WINDOW_DEFINITION} (do not invent)",
    )


def reconstruct_historical(*_args: Any, **_kwargs: Any) -> None:
    raise Hhl1Reject(
        Hhl1RejectCode.NOT_AUTHORIZED,
        "historical reconstruction is not authorized",
    )


def handle_unavailable(
    *,
    game_id: str,
    team: str,
    missing_enum: str,
    reason: str,
) -> ExclusionRecord:
    """Fail-closed unavailable source: exclusion record, no imputed L1 row."""
    assert_activation_locked()
    if not game_id or not team:
        raise Hhl1Reject(
            Hhl1RejectCode.PROVENANCE_INCOMPLETE,
            "unavailable handler requires game_id and team (no impute)",
        )
    return ExclusionRecord(
        game_id=game_id,
        team=team,
        missing_enum=missing_enum,
        reject_code=Hhl1RejectCode.UNAVAILABLE,
        reason=reason,
    )


def verify_plumbing_inert() -> dict[str, Any]:
    """Local read-only check: plumbing does not activate live work."""
    assert_activation_locked()
    assert_nowcast_off()
    probes = (
        ("acquire_official_report", acquire_official_report),
        ("fetch_nowcast", fetch_nowcast),
        ("acquire_odds", acquire_odds),
        ("score_l1", score_l1),
        ("publish", publish),
        ("build_baseline_personnel_ref", build_baseline_personnel_ref),
        ("reconstruct_historical", reconstruct_historical),
    )
    for name, fn in probes:
        try:
            fn()
        except Hhl1Reject as exc:
            if exc.code not in {
                Hhl1RejectCode.NOT_AUTHORIZED,
                Hhl1RejectCode.NOWCAST_OFF,
                Hhl1RejectCode.RATING_WINDOW_UNRESOLVED,
            }:
                raise
        else:
            raise Hhl1Reject(
                Hhl1RejectCode.NOT_AUTHORIZED,
                f"{name} returned without reject — live path must stay closed",
            )
    return {
        "live_capture": HHL1_LIVE_CAPTURE_AUTHORIZED,
        "external_acquisition": HHL1_EXTERNAL_ACQUISITION_AUTHORIZED,
        "nowcast": HHL1_NOWCAST_AUTHORIZED,
        "scoring": HHL1_SCORING_AUTHORIZED,
        "publication": HHL1_PUBLICATION_AUTHORIZED,
        "historical_reconstruction": HHL1_HISTORICAL_RECONSTRUCTION_AUTHORIZED,
        "model_execution": HHL1_MODEL_EXECUTION_AUTHORIZED,
        "simulator_identity": SIMULATOR_EXECUTABLE_IDENTITY,
        "inert": True,
    }


def forbidden_import_names() -> frozenset[str]:
    """Modules this package must never import (acquisition / scoring / nowcast)."""
    return frozenset(
        {
            "src.services.nfl_injury_nowcast",
            "src.services.nfl_simulator",
            "src.services.nfl_injury_report_scan",
            "src.tasks",
            "requests",
            "httpx",
            "sqlalchemy",
            "psycopg",
            "celery",
        }
    )


def collect_nowcast_markers(values: Iterable[Optional[str]]) -> list[str]:
    hits: list[str] = []
    for value in values:
        if not value:
            continue
        lowered = str(value).lower()
        if "nowcast" in lowered or lowered in NOWCAST_SOURCE_IDS:
            hits.append(str(value))
    return hits
