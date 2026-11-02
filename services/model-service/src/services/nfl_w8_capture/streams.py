"""AC-2 / AC-6: per-input as-of proofs and two isolated streams."""

from __future__ import annotations

from typing import Any, Iterable, Mapping, Optional

from src.services.nfl_w8_capture.constants import (
    FORBIDDEN_INDEPENDENT_KEYS,
    FORBIDDEN_INDEPENDENT_PREFIXES,
    STREAM_INDEPENDENT,
)
from src.services.nfl_w8_capture.timeutil import is_late, parse_utc


class StreamError(ValueError):
    """Stream or as-of contract violation."""


def is_forbidden_independent_key(key: str) -> bool:
    name = key.lower()
    if name in FORBIDDEN_INDEPENDENT_KEYS:
        return True
    return any(name.startswith(prefix) for prefix in FORBIDDEN_INDEPENDENT_PREFIXES)


def forbidden_independent_keys(row: Mapping[str, Any]) -> tuple[str, ...]:
    return tuple(sorted(k for k in row if is_forbidden_independent_key(str(k))))


def assert_independent_has_no_market(rows: Iterable[Mapping[str, Any]]) -> None:
    for row in rows:
        banned = forbidden_independent_keys(row)
        if banned:
            raise StreamError(
                f"AC-6: independent stream contains forbidden market input(s) {list(banned)}"
            )


def validate_input_proof(
    proof: Mapping[str, Any],
    *,
    min_lead_minutes: int,
) -> Optional[str]:
    """Per-input as-of. Week-number matching is not accepted (AC-2)."""
    if proof.get("proof_kind") == "week_number" or (
        proof.get("as_of_utc") in (None, "")
        and proof.get("feature_week") is not None
    ):
        return "week_number_matching_not_accepted"
    as_of = parse_utc(proof.get("as_of_utc"))
    source = parse_utc(proof.get("source_captured_at_utc"))
    kickoff = parse_utc(proof.get("kickoff_utc"))
    if as_of is None:
        return "missing_as_of_utc"
    if source is None:
        return "missing_source_captured_at_utc"
    if kickoff is None:
        return "missing_kickoff_utc"
    if as_of != source:
        return "as_of_does_not_match_source_capture"
    if as_of >= kickoff:
        return "as_of_not_before_kickoff"
    if is_late(as_of, kickoff, min_lead_minutes=min_lead_minutes):
        return "late_as_of"
    if not proof.get("input_name"):
        return "missing_input_name"
    return None


def check_stream_proofs(
    proofs: Iterable[Mapping[str, Any]],
    *,
    stream: str,
    min_lead_minutes: int,
) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    for proof in proofs:
        if stream == STREAM_INDEPENDENT:
            banned = forbidden_independent_keys(proof)
            if banned:
                failures.append(
                    {
                        "game_id": proof.get("game_id"),
                        "input_name": proof.get("input_name"),
                        "reason": "forbidden_market_input",
                        "keys": list(banned),
                    }
                )
                continue
        reason = validate_input_proof(proof, min_lead_minutes=min_lead_minutes)
        if reason:
            failures.append(
                {
                    "game_id": proof.get("game_id"),
                    "input_name": proof.get("input_name"),
                    "reason": reason,
                }
            )
    return failures
