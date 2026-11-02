"""Gated Odds fetch + provenance envelope. No default live HTTP.

After a 200 transport result and BEFORE json.loads, persist exact body
bytes to raw/odds/<game_id>.body (IMV 91ead2d8 §A). Hash-only retention
is a defect for NEW dests. First-seal CAR@GB dest is not written here.

Key is read from env only and never persisted. refuse_odds_fetch remains
the fail-closed default until the paper KEEP-ack (2539d916):
R1 NFL_W8_H1_AUTH_CITE=89fdd45f plus R2 KEEP STATEMENT
(CREDENTIAL_POLICY=KEEP_EXISTING KEEP_AUTH_SHA8=a9ae5ae6
VERIFY_PASS_SHA8=e64e73ac H1C_AUTH_SHA8=89fdd45f T4500U_SHA8=20325274
ROTATION_ASSERTED=false).
NFL_W8_PR_ROTATE_CONFIRM is rejected as a KEEP path.

Library default (transport=None) still refuses to open a socket. Production
HTTP lives in http_transport.OddsHttpTransport and is injected by the
one-shot CLI. Celery tick must not use that transport.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Optional, Protocol

from src.services.nfl_w8_capture.alerts import control_alert, deliver_alert
from src.services.nfl_w8_capture.books import ENV_ODDS_API_KEY, build_w8_odds_request_params
from src.services.nfl_w8_capture.credits import (
    CreditCeilingError,
    CreditEstimateError,
    CreditHeaderError,
    CreditReconcileError,
    assert_t0_ready,
    estimate_request_credits,
    ledger_closed,
    ledger_overrun,
    pre_call_check,
    read_cumulative,
    record_credit_use,
    write_reservation,
)
from src.services.nfl_w8_capture.hold import OddsApiHoldError, odds_api_hold_is_on, refuse_odds_fetch
from src.services.nfl_w8_capture.redact import redact_secrets
from src.services.nfl_w8_capture.store import BundleStore

ODDS_ENDPOINT = "sports/americanfootball_nfl/odds"


class OddsFetchError(RuntimeError):
    """Fetch refused or failed without a live network call succeeding."""


@dataclass
class OddsTransportResult:
    status_code: int
    headers: dict[str, str]
    body: bytes
    provider_server_ts: Optional[str] = None


class OddsTransport(Protocol):
    def __call__(
        self,
        *,
        endpoint: str,
        params: Mapping[str, str],
        headers: Mapping[str, str],
    ) -> OddsTransportResult: ...


def raw_body_sha256(body: bytes | str) -> str:
    raw = body if isinstance(body, (bytes, bytearray)) else str(body).encode("utf-8")
    return hashlib.sha256(bytes(raw)).hexdigest()


def build_provenance_envelope(
    *,
    endpoint: str,
    params: Mapping[str, Any],
    request_headers: Mapping[str, Any],
    response_headers: Mapping[str, Any],
    raw_body: bytes | str,
    provider_server_ts: Optional[str] = None,
    client_received_at: Optional[str] = None,
) -> dict[str, Any]:
    received = client_received_at or datetime.now(timezone.utc).isoformat().replace(
        "+00:00", "Z"
    )
    return {
        "endpoint": endpoint,
        "params": redact_secrets(dict(params)),
        "request_headers": redact_secrets(dict(request_headers)),
        "response_headers": redact_secrets(dict(response_headers)),
        "raw_body_sha256": raw_body_sha256(raw_body),
        "provider_server_ts": provider_server_ts,
        "client_received_at": received,
        "client_receive_is_not_a_close": True,
        "transport": "injected",
    }


def _env_key(env: Mapping[str, str]) -> str:
    key = str(env.get(ENV_ODDS_API_KEY) or "").strip()
    if not key:
        raise OddsFetchError(f"{ENV_ODDS_API_KEY} missing from env; key is never hardcoded")
    return key


def _alert(
    store: Optional[BundleStore],
    *,
    kind: str,
    detail: str,
    env: Optional[Mapping[str, str]],
    game_id: str = "",
    market: str = "control",
) -> None:
    if store is None:
        return
    deliver_alert(
        control_alert(kind=kind, detail=detail, game_id=game_id, market=market),
        store,
        env=env,
    )


def _tip_sha(env: Mapping[str, str]) -> str:
    """Recorded tip only. Empty is UNSET — do not invent a commit."""
    for key in ("NFL_W8_TIP_SHA", "GITHUB_SHA", "RAILWAY_GIT_COMMIT_SHA", "GIT_COMMIT"):
        value = str(env.get(key) or "").strip()
        if value:
            return value
    return ""


def fetch_odds_with_provenance(
    *,
    store: BundleStore,
    env: Optional[Mapping[str, str]] = None,
    transport: Optional[OddsTransport] = None,
    params: Optional[Mapping[str, str]] = None,
    game_id: str = "",
    capture_receipt_id: str = "",
    tip_sha: str = "",
) -> dict[str, Any]:
    """Hold-gated fetch. Requires an injected transport. Never defaults to HTTP.

    Production path: inject OddsHttpTransport (oneshot CLI). Tests inject fakes.
    """
    source = env if env is not None else os.environ
    request_params = dict(params or build_w8_odds_request_params())
    if odds_api_hold_is_on(source):
        _alert(
            store,
            kind="hold",
            detail=(
                "Odds hold on: refuse_odds_fetch "
                "(R1 NFL_W8_H1_AUTH_CITE=89fdd45f + R2 KEEP-ack; "
                "R3 NFL_W8_PR_ROTATE_CONFIRM is not a lift)"
            ),
            env=source,
            game_id=game_id,
            market="hold",
        )
        refuse_odds_fetch(endpoint=ODDS_ENDPOINT, params=request_params, env=source)
        raise OddsApiHoldError("hold refuse")  # unreachable; refuse always raises here

    try:
        if ledger_closed(store):
            raise CreditCeilingError(
                "H-1c ledger closed (ceiling, overrun, or used-header mismatch); "
                "subsequent calls refuse"
            )
        estimate = estimate_request_credits(request_params)
        pre_call_check(
            read_cumulative(store),
            estimate,
            overrun=ledger_overrun(store),
        )
        # t4520u / t4523u Option A: T-0 + worst-case reserve before any transport.
        assert_t0_ready(store)
        write_reservation(store, estimate)
    except (CreditCeilingError, CreditEstimateError, CreditReconcileError) as exc:
        kind = "ceiling" if isinstance(exc, CreditCeilingError) else "fetch_fail"
        _alert(store, kind=kind, detail=str(exc), env=source, game_id=game_id, market="credits")
        raise
    key = _env_key(source)
    request_headers = {"x-api-key": key}

    if transport is None:
        _alert(
            store,
            kind="fetch_fail",
            detail="no transport injected; live HTTP is not the default path",
            env=source,
            game_id=game_id,
            market="fetch",
        )
        raise OddsFetchError(
            "no transport; library default does not open a socket. "
            "Inject OddsHttpTransport (python -m src.services.nfl_w8_capture) "
            "or a test fake. Do not call The Odds API from tick."
        )

    try:
        result = transport(
            endpoint=ODDS_ENDPOINT,
            params=request_params,
            headers=request_headers,
        )
    except Exception as exc:  # noqa: BLE001 — surface as fetch_fail, never leak key
        _alert(
            store,
            kind="fetch_fail",
            detail=f"transport error: {type(exc).__name__}",
            env=source,
            game_id=game_id,
            market="fetch",
        )
        raise OddsFetchError("transport failed") from exc

    if int(result.status_code) != 200:
        _alert(
            store,
            kind="fetch_fail",
            detail=f"transport status {result.status_code}",
            env=source,
            game_id=game_id,
            market="fetch",
        )
        raise OddsFetchError(f"transport status {result.status_code}")

    # IMV 91ead2d8 §A: hash + persist EXACT body bytes BEFORE json.loads/parse.
    # Lazy import avoids a fetch↔raw_body cycle; H uses this module's function.
    from src.services.nfl_w8_capture.raw_body import persist_raw_odds_body

    body_bytes = bytes(result.body)
    body_h = raw_body_sha256(body_bytes)
    received = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    raw_persist = persist_raw_odds_body(
        store,
        game_id=game_id,
        body_bytes=body_bytes,
        expected_h=body_h,
        response_headers=result.headers,
        request_params=request_params,
        endpoint=ODDS_ENDPOINT,
        provider_server_ts=result.provider_server_ts,
        client_received_at=received,
        tip_sha=str(tip_sha or "").strip() or _tip_sha(source),
        capture_receipt_id=capture_receipt_id,
    )

    try:
        ledger = record_credit_use(
            store,
            result.headers,
            note="odds-fetch",
            require_t0=True,
            expected_charge=estimate,
        )
    except (CreditHeaderError, CreditCeilingError, CreditReconcileError) as exc:
        kind = "ceiling" if isinstance(exc, CreditCeilingError) else "fetch_fail"
        _alert(store, kind=kind, detail=str(exc), env=source, game_id=game_id, market="credits")
        raise

    envelope = build_provenance_envelope(
        endpoint=ODDS_ENDPOINT,
        params=request_params,
        request_headers=request_headers,
        response_headers=result.headers,
        raw_body=body_bytes,
        provider_server_ts=result.provider_server_ts,
        client_received_at=received,
    )
    if str(envelope.get("raw_body_sha256") or "") != body_h:
        from src.services.nfl_w8_capture.raw_body import RawBodyRetentionError

        raise RawBodyRetentionError("envelope.raw_body_sha256 != H; refuse provenance")
    if str(raw_persist.get("raw_body_sha256") or "") != body_h:
        from src.services.nfl_w8_capture.raw_body import RawBodyRetentionError

        raise RawBodyRetentionError("persisted raw_body_sha256 != H; refuse provenance")
    dumped = str(envelope)
    if key and key in dumped:
        raise OddsFetchError("refusing to persist provenance that still contains the env key")
    store.append_chained_jsonl(
        "provenance.jsonl",
        envelope,
        actor="nfl_w8_capture",
        note=f"provenance:{game_id or 'slate'}",
    )
    payload: Any = None
    try:
        payload = json.loads(body_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
        payload = None
    return {
        "envelope": envelope,
        "credits": ledger,
        "payload": payload,
        "raw_body": raw_persist,
    }
