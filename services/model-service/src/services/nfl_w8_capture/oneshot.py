"""One-shot PART B W8 sealed capture: fetch → snapshot → close → seal.

Word-for-word live argv (no secrets; hold still default ON):

  cd services/model-service && PYTHONPATH=. python3 -m src.services.nfl_w8_capture --game-id <GAME_ID> --kickoff-utc <KICKOFF_UTC>

Word-for-word SYNTHETIC demo (no live Odds, no secrets):

  cd services/model-service && PYTHONPATH=. NFL_W8_H1_AUTH_CITE=89fdd45f CREDENTIAL_POLICY=KEEP_EXISTING KEEP_AUTH_SHA8=a9ae5ae6 VERIFY_PASS_SHA8=e64e73ac H1C_AUTH_SHA8=89fdd45f T4500U_SHA8=20325274 ROTATION_ASSERTED=false python3 -m src.services.nfl_w8_capture --synthetic --bundle-dir /tmp/nfl-w8-synthetic-demo

PART B is CONSTANTS, not argv: books draftkings,fanduel,betmgm,fanatics,circa;
regions us,us2; markets h2h,spreads,totals; S=10; k≥3; F-8 90m.

refuse_odds_fetch stays default ON. There is no CLI lift flag. Single-invocation
lift is process-scoped KEEP-ack only (paper 2539d916; not Railway-global):
CREDENTIAL_POLICY=KEEP_EXISTING KEEP_AUTH_SHA8=a9ae5ae6 VERIFY_PASS_SHA8=e64e73ac
H1C_AUTH_SHA8=89fdd45f T4500U_SHA8=20325274 ROTATION_ASSERTED=false.
NFL_W8_PR_ROTATE_CONFIRM is stale and is rejected as a KEEP path.

AC-12: produce_seal writes AC-1 + AC-2 custodian_receipt_id slot only.
seal_ack stays CURSOR_CANNOT_SEAL_ACK. A named custodian receipt is required
for AC-2; Cursor cannot seal-ack. Do not fake seal-ack.

Credit: operator must enforce (used−11622)+estimate ≤ 3000 from response
headers (cited baseline e64e73ac). Bundle-local ceiling remains 3000.
t4520u / t4523u Option A: T-0 snapshot + worst-case reserve before execute;
this-request last vs concurrent beat/worker after. Baseline 11622 / ceiling
14622 stay immutable. Receipt 072005fe stays immutable.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict, is_dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

from src.services.nfl_w8_capture.books import W8_ODDS_MARKETS, build_w8_odds_request_params
from src.services.nfl_w8_capture.cadence import (
    F8_CUTOFF,
    F8CutoffError,
    assert_slate_join_before_f8,
    f8_cutoff_utc,
)
from src.services.nfl_w8_capture.close import (
    CLOSE_MAX_AGE,
    PRIMARY_K_REQUIRED,
    evaluate_game_market_close,
)
from src.services.nfl_w8_capture.alerts import control_alert, deliver_alert
from src.services.nfl_w8_capture.credits import (
    ACCOUNT_REMAINING_CITED_E64E73AC,
    ACCOUNT_USED_BASELINE_E64E73AC,
    CREDIT_CEILING,
    HEADER_USED,
    CreditCeilingError,
    CreditEstimateError,
    CreditHeaderError,
    CreditReconcileError,
    assert_account_used_ceiling,
    assert_dual_credit_r5,
    assert_operator_account_budget,
    credit_headers,
    estimate_request_credits,
    parse_credit_headers,
    seed_account_baseline_note,
    seed_t0_account_snapshot,
    t0_headers_from_env,
)
from src.services.nfl_w8_capture.fetch import (
    OddsFetchError,
    OddsTransport,
    OddsTransportResult,
    fetch_odds_with_provenance,
)
from src.services.nfl_w8_capture.fixture_load import (
    cells_from_odds_shaped_event,
    load_json_fixture,
    select_odds_event,
)
from src.services.nfl_w8_capture.hold import (
    OddsApiHoldError,
    hold_lift_state,
    keep_policy_ack_record,
    odds_api_hold_is_on,
)
from src.services.nfl_w8_capture.books import ENV_ODDS_API_KEY
from src.services.nfl_w8_capture.http_transport import OddsHttpTransport
from src.services.nfl_w8_capture.redact import redact_secrets
from src.services.nfl_w8_capture.seal import SEAL_MIN_LEAD, SealWindowError, produce_seal
from src.services.nfl_w8_capture.snapshots import append_snapshot
from src.services.nfl_w8_capture.store import BundleStore
from src.services.nfl_w8_capture.streams import refuse_seal
from src.services.nfl_w8_capture.tick import ENV_BUNDLE_DIR
from src.services.nfl_w8_capture.timestamps import parse_utc

# Exact copyable argv for IMV / CoS. No secrets. PART B not in flags.
ONESHOT_ARGV = (
    "cd services/model-service && PYTHONPATH=. python3 -m src.services.nfl_w8_capture "
    "--game-id <GAME_ID> --kickoff-utc <KICKOFF_UTC>"
)
ONESHOT_SYNTHETIC_ARGV = (
    "cd services/model-service && PYTHONPATH=. "
    "NFL_W8_H1_AUTH_CITE=89fdd45f CREDENTIAL_POLICY=KEEP_EXISTING "
    "KEEP_AUTH_SHA8=a9ae5ae6 VERIFY_PASS_SHA8=e64e73ac "
    "H1C_AUTH_SHA8=89fdd45f T4500U_SHA8=20325274 ROTATION_ASSERTED=false "
    "python3 -m src.services.nfl_w8_capture --synthetic --bundle-dir /tmp/nfl-w8-synthetic-demo"
)

SEAL_ACK = "CURSOR_CANNOT_SEAL_ACK"
KEEP_ACK_NOTE = (
    "R1–R7 KEEP-ack (paper 2539d916 / IMV ACCEPT 91b13a45): "
    "NFL_W8_H1_AUTH_CITE=89fdd45f PLUS CREDENTIAL_POLICY=KEEP_EXISTING "
    "KEEP_AUTH_SHA8=a9ae5ae6 VERIFY_PASS_SHA8=e64e73ac H1C_AUTH_SHA8=89fdd45f "
    "T4500U_SHA8=20325274 ROTATION_ASSERTED=false SECRET_MATERIAL=none. "
    "R3: NFL_W8_PR_ROTATE_CONFIRM truthy is FAIL CLOSED. "
    "R4: process-scoped env= only. R7: paper ACCEPT does not authorize live Odds."
)
SYNTHETIC_DUMMY_KEY = "synthetic-not-a-key"


def synthetic_fixture_transport(event: Mapping[str, Any]) -> OddsTransport:
    """In-process fixture transport. Opens no socket. Not The Odds API."""
    body = json.dumps(dict(event), sort_keys=True).encode("utf-8")
    provider_ts = str(event.get("provider_server_ts") or "")

    def _transport(
        *,
        endpoint: str,
        params: Mapping[str, str],
        headers: Mapping[str, str],
    ) -> OddsTransportResult:
        del endpoint, params, headers
        return OddsTransportResult(
            status_code=200,
            headers={
                "x-requests-last": "30",
                "x-requests-used": "11652",
                "x-requests-remaining": "8348",
                "Date": "Wed, 28 Oct 2026 21:15:00 GMT",
            },
            body=body,
            provider_server_ts=provider_ts or None,
        )

    return _transport


class OneshotError(RuntimeError):
    """One-shot capture refused or failed before a seal-ack (which never happens)."""


def _aware(value: Any, *, field: str) -> datetime:
    parsed = parse_utc(value)
    if parsed is None:
        raise OneshotError(f"{field} must be a parseable UTC timestamp")
    return parsed


def _jsonable(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    if is_dataclass(value):
        return {key: _jsonable(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def _resolve_t0_headers(
    args: Any,
    env: Mapping[str, str],
    *,
    synthetic: bool,
) -> Optional[dict[str, str]]:
    """CLI / env T-0, or synthetic default 11622/8378/last=0 (matches fixture 11652/30)."""
    used = str(getattr(args, "t0_used", "") or env.get("NFL_W8_T0_USED") or "").strip()
    remaining = str(getattr(args, "t0_remaining", "") or env.get("NFL_W8_T0_REMAINING") or "").strip()
    last = str(getattr(args, "t0_last", "") or env.get("NFL_W8_T0_LAST") or "0").strip() or "0"
    if used and remaining:
        return credit_headers(last=last, used=used, remaining=remaining)
    if synthetic:
        return credit_headers(
            last=0,
            used=ACCOUNT_USED_BASELINE_E64E73AC,
            remaining=ACCOUNT_REMAINING_CITED_E64E73AC,
        )
    return None


def run_oneshot_sealed_capture(
    *,
    game_id: str,
    kickoff_utc: datetime | str,
    store: BundleStore,
    env: Optional[Mapping[str, str]] = None,
    transport: Optional[OddsTransport] = None,
    now_utc: Optional[datetime | str] = None,
    custodian_receipt_id: str = "",
    odds_event_id: str = "",
    registered_at: Optional[datetime | str] = None,
    t0_headers: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    """Fetch → snapshot → close → seal for ONE PART B W8 game.

    Does not lift hold. Does not seal-ack. Does not call refuse_seal as success.
    """
    source = env if env is not None else os.environ
    kickoff = _aware(kickoff_utc, field="kickoff_utc")
    now = _aware(now_utc, field="now_utc") if now_utc is not None else datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    lift_state = hold_lift_state(source)
    if lift_state.get("rotate_rejected"):
        deliver_alert(
            control_alert(
                kind="hold",
                detail=(
                    "R3: NFL_W8_PR_ROTATE_CONFIRM truthy on KEEP path — "
                    "FAIL CLOSED (stale/conflicting; not a lift)"
                ),
                game_id=game_id,
                market="hold",
            ),
            store,
            env=source,
        )
    if odds_api_hold_is_on(source):
        raise OddsApiHoldError(
            "refuse_odds_fetch default ON. R1+R2 process-scoped KEEP-ack only "
            "(no CLI flag, not Railway-global). R3 rotate-confirm is not a lift. "
            "R7: paper ACCEPT does not authorize live Odds. "
            f"{KEEP_ACK_NOTE}"
        )

    if registered_at is not None:
        assert_slate_join_before_f8(_aware(registered_at, field="registered_at"), kickoff)

    lead = kickoff - now
    if lead < SEAL_MIN_LEAD:
        raise OneshotError(
            f"AC-1 seal requires >=60 minutes before kickoff; lead={lead.total_seconds():.0f}s"
        )

    seed_account_baseline_note(store)
    params = build_w8_odds_request_params()
    estimate = estimate_request_credits(params)
    t0 = dict(t0_headers) if t0_headers is not None else t0_headers_from_env(source)
    if t0 is None:
        raise CreditReconcileError(
            "need T-0 snapshot immediately before request "
            "(--t0-used/--t0-remaining or NFL_W8_T0_USED/NFL_W8_T0_REMAINING)"
        )
    seed_t0_account_snapshot(store, t0)
    t0_used = int(parse_credit_headers(t0)[HEADER_USED])
    # Reserve against T-0 used, not the VERIFY 11622 cite.
    assert_operator_account_budget(t0_used, estimate)

    live_transport = transport if transport is not None else OddsHttpTransport()
    fetched = fetch_odds_with_provenance(
        store=store,
        env=source,
        transport=live_transport,
        params=params,
        game_id=game_id,
    )
    credits = fetched.get("credits") or {}
    headers = (credits.get("headers") or {}) if isinstance(credits, dict) else {}
    used_now = headers.get(HEADER_USED)
    if used_now is None:
        raise CreditReconcileError("R5: x-requests-used missing; ledger+account dual-check required")
    # R5: (a) bundle ledger cumulative ≤ 3000 AND (b) account used ≤ 14622
    dual = assert_dual_credit_r5(store, int(used_now))
    assert_account_used_ceiling(int(used_now))

    envelope = fetched.get("envelope") or {}
    payload = fetched.get("payload")
    event = select_odds_event(
        payload,
        game_id=game_id,
        kickoff_utc=kickoff,
        odds_event_id=odds_event_id,
    )
    provider_ts = envelope.get("provider_server_ts")
    received = envelope.get("client_received_at")

    snapshot_payload = {
        "game_id": game_id,
        "kickoff_utc": kickoff.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "part_b_books": params["bookmakers"],
        "part_b_markets": params["markets"],
        "part_b_regions": params["regions"],
        "S_minutes": int(CLOSE_MAX_AGE.total_seconds() // 60),
        "k_required": PRIMARY_K_REQUIRED,
        "f8_cutoff_minutes": int(F8_CUTOFF.total_seconds() // 60),
        "raw_body_sha256": envelope.get("raw_body_sha256"),
        "provider_server_ts": provider_ts,
        "client_received_at": received,
        "event": event,
    }
    snapshot = append_snapshot(store.root, snapshot_payload, captured_at=now)

    markets = [part for part in W8_ODDS_MARKETS.split(",") if part.strip()]
    close_by_market: dict[str, Any] = {}
    for market in markets:
        cells = cells_from_odds_shaped_event(
            event,
            market=market,
            game_id=game_id,
            provider_server_ts=provider_ts,
            client_received_at=received,
        )
        verdict = evaluate_game_market_close(
            game_id=game_id,
            market=market,
            kickoff_utc=kickoff,
            cells=cells,
        )
        close_by_market[market] = _jsonable(verdict)

    close_relpath = (
        "closes/"
        + "".join(ch if ch.isalnum() or ch in "-_@" else "_" for ch in game_id)
        + ".close.json"
    )
    close_written = store.write_new_file(
        close_relpath,
        {
            "game_id": game_id,
            "kickoff_utc": kickoff.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
            "S_minutes": int(CLOSE_MAX_AGE.total_seconds() // 60),
            "k_required": PRIMARY_K_REQUIRED,
            "f8_cutoff_utc": f8_cutoff_utc(kickoff)
            .astimezone(timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
            "books": params["bookmakers"],
            "markets": close_by_market,
            "note": "Close verdict only. Missing PRIMARY is never imputed. Not a seal-ack.",
        },
        actor="nfl_w8_capture",
        note=f"close:{game_id}",
    )

    receipt_id = str(custodian_receipt_id or "").strip()
    seal = produce_seal(
        store,
        game_id=game_id,
        kickoff_utc=kickoff,
        now_utc=now,
        artifact_shas={
            "snapshot_content_sha256": str(snapshot.get("content_sha256") or ""),
            "snapshot_entry_sha": str(snapshot.get("entry_sha") or ""),
            "close": str(close_written.get("artifact_sha") or ""),
            "provenance_raw_body_sha256": str(envelope.get("raw_body_sha256") or ""),
        },
        custodian_receipt_id=receipt_id,
    )
    # AC-12: never treat produce_seal as seal-ack. refuse_seal always raises.
    try:
        refuse_seal([])
    except PermissionError:
        pass
    else:
        raise OneshotError("AC-12 broken: refuse_seal did not raise")

    statement = keep_policy_ack_record()
    keep_receipt = store.write_new_file(
        "keep_ack_statement.json",
        statement,
        actor="nfl_w8_capture",
        note="r6-keep-statement",
    )

    summary = {
        "ok": True,
        "entrypoint": ONESHOT_ARGV,
        "game_id": game_id,
        "kickoff_utc": kickoff.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "now_utc": now.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "lead_seconds": int(lead.total_seconds()),
        "part_b": {
            "books": params["bookmakers"],
            "markets": params["markets"],
            "regions": params["regions"],
            "S_minutes": int(CLOSE_MAX_AGE.total_seconds() // 60),
            "k_required": PRIMARY_K_REQUIRED,
            "f8_cutoff_minutes": int(F8_CUTOFF.total_seconds() // 60),
            "estimate_credits": estimate,
        },
        "credits": credits,
        "r5_dual_credit": {
            **dual,
            "rule_a": "bundle ledger cumulative <= 3000",
            "rule_b": "(used-11622) <= 3000 i.e. used <= 14622",
            "ledger_not_optional": True,
        },
        "operator_budget": {
            "baseline_used": ACCOUNT_USED_BASELINE_E64E73AC,
            "cite": "e64e73ac",
            "rule": "R5 (a) ledger cumulative<=3000 AND (b) used<=14622",
            "ceiling": CREDIT_CEILING,
            "used_now": used_now,
            "t0_used": t0_used,
        },
        "t0": {
            "used": t0_used,
            "rule": "fresh account reading immediately before request; not VERIFY 11622 seed",
        },
        "t4523u_option_a": {
            "beat_worker_left_running": True,
            "this_request_charge": (credits.get("oneshot_delta") if isinstance(credits, dict) else None),
            "concurrent": (credits.get("concurrent") if isinstance(credits, dict) else None),
            "concurrent_attribution": (
                credits.get("concurrent_attribution") if isinstance(credits, dict) else None
            ),
        },
        "snapshot_entry_sha": snapshot.get("entry_sha"),
        "close_relpath": close_relpath,
        "close_sha": close_written.get("artifact_sha"),
        "close_by_market": {name: body.get("status") for name, body in close_by_market.items()},
        "seal_relpath": seal.get("relpath"),
        "custodian_receipt": seal.get("custodian_receipt"),
        "seal_ack": SEAL_ACK,
        "ac_2_note": (
            "AC-2 requires a named custodian receipt_id. Slot is UNSET until the "
            "custodian fills it. Cursor cannot seal-ack (AC-12)."
        ),
        "hold_lift": lift_state,
        "keep_ack": statement,
        "keep_ack_note": KEEP_ACK_NOTE,
        "keep_ack_receipt": keep_receipt.get("relpath"),
        "r7_live_not_authorized": True,
        "nfl_no_go": True,
        "coming_soon": True,
        "sealed_count_claim": 0,
    }
    dumped = json.dumps(redact_secrets(summary), sort_keys=True)
    key = str(source.get("ODDS_API_KEY") or "").strip()
    if key and key in dumped:
        raise OddsFetchError("refusing to emit oneshot summary that still contains the env key")
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python3 -m src.services.nfl_w8_capture",
        description=(
            "One-shot PART B W8 sealed capture (fetch→snapshot→close→seal). "
            "Draft path only. No merge, no deploy. --synthetic uses fixture "
            "transport only (zero live Odds). No CLI hold-lift flag."
        ),
        epilog=(
            f"Live argv: {ONESHOT_ARGV}\n"
            f"Synthetic demo: {ONESHOT_SYNTHETIC_ARGV}\n"
            "Optional: --bundle-dir <DIR> --custodian-receipt-id <ID> "
            "--now-utc <ISO> --odds-event-id <ID> --registered-at <ISO>\n"
            "PART B constants (not flags): draftkings,fanduel,betmgm,fanatics,circa; "
            "S=10; k>=3; 90m.\n"
            f"Lift (process-scoped env, not Railway-global): {KEEP_ACK_NOTE}\n"
            "ODDS_API_KEY from env only on the live path — never argv, never logs.\n"
            "AC-12: seal_ack=CURSOR_CANNOT_SEAL_ACK. Custodian receipt required for AC-2.\n"
            "Credit: (used-11622)+estimate <= 3000 from response headers."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--game-id", default="", help="Capture game id (required unless --synthetic)")
    parser.add_argument("--kickoff-utc", default="", help="Kickoff UTC ISO-8601 (required unless --synthetic)")
    parser.add_argument(
        "--synthetic",
        action="store_true",
        help="Fixture-only demo: no socket, no The Odds API. Uses package synthetic W8 REG event.",
    )
    parser.add_argument(
        "--bundle-dir",
        default="",
        help="Evidence bundle directory (default NFL_W8_EVIDENCE_DIR or data/ops/nfl-w8-capture-bundle)",
    )
    parser.add_argument(
        "--custodian-receipt-id",
        default="",
        help="AC-2 custodian receipt id. Leave empty for UNSET slot. Does not seal-ack.",
    )
    parser.add_argument("--now-utc", default="", help="Override now (tests / replay). UTC ISO-8601")
    parser.add_argument("--odds-event-id", default="", help="Optional Odds event id filter")
    parser.add_argument(
        "--registered-at",
        default="",
        help="Optional slate-join timestamp; if set, F-8 T=90m cutoff is enforced",
    )
    parser.add_argument(
        "--t0-used",
        default="",
        help="T-0 x-requests-used immediately before the request (or NFL_W8_T0_USED)",
    )
    parser.add_argument(
        "--t0-remaining",
        default="",
        help="T-0 x-requests-remaining immediately before the request (or NFL_W8_T0_REMAINING)",
    )
    parser.add_argument(
        "--t0-last",
        default="",
        help="T-0 x-requests-last (must be 0). Default 0. Or NFL_W8_T0_LAST.",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None, *, env: Optional[Mapping[str, str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    source: Mapping[str, str] = env if env is not None else os.environ
    env_map = {str(key): str(value) for key, value in source.items()}
    transport: Optional[OddsTransport] = None
    game_id = str(args.game_id or "").strip()
    kickoff_utc = str(args.kickoff_utc or "").strip()
    now_utc = str(args.now_utc or "").strip() or None
    if args.synthetic:
        event = load_json_fixture()
        game_id = game_id or str(event.get("game_id") or "")
        kickoff_utc = kickoff_utc or str(event.get("kickoff_utc") or "")
        if now_utc is None:
            kickoff = _aware(kickoff_utc, field="kickoff_utc")
            now_utc = (kickoff - timedelta(hours=2)).isoformat().replace("+00:00", "Z")
        transport = synthetic_fixture_transport(event)
        env_map.setdefault(ENV_ODDS_API_KEY, SYNTHETIC_DUMMY_KEY)
    elif not game_id or not kickoff_utc:
        parser.error("--game-id and --kickoff-utc are required unless --synthetic")
    t0_headers = _resolve_t0_headers(args, env_map, synthetic=bool(args.synthetic))
    root = Path(
        args.bundle_dir
        or env_map.get(ENV_BUNDLE_DIR)
        or (Path.cwd() / "data" / "ops" / "nfl-w8-capture-bundle")
    )
    try:
        summary = run_oneshot_sealed_capture(
            game_id=game_id,
            kickoff_utc=kickoff_utc,
            store=BundleStore(root),
            env=env_map,
            transport=transport,
            now_utc=now_utc,
            custodian_receipt_id=str(args.custodian_receipt_id or ""),
            odds_event_id=str(args.odds_event_id or ""),
            registered_at=str(args.registered_at) or None,
            t0_headers=t0_headers,
        )
        if args.synthetic:
            summary["synthetic"] = True
            summary["live_odds"] = False
            summary["entrypoint"] = ONESHOT_SYNTHETIC_ARGV
    except (
        OddsApiHoldError,
        OddsFetchError,
        OneshotError,
        CreditCeilingError,
        CreditEstimateError,
        CreditHeaderError,
        CreditReconcileError,
        F8CutoffError,
        SealWindowError,
        ValueError,
    ) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001 — never dump env/key
        print(f"oneshot failed: {type(exc).__name__}", file=sys.stderr)
        return 1
    print(json.dumps(redact_secrets(summary), indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
