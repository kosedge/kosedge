"""One-shot PART B W8 sealed capture: fetch → snapshot → close → seal.

Word-for-word argv (no secrets):

  cd services/model-service && PYTHONPATH=. python -m src.services.nfl_w8_capture --game-id <GAME_ID> --kickoff-utc <KICKOFF_UTC>

PART B is CONSTANTS, not argv: books draftkings,fanduel,betmgm,fanatics,circa;
regions us,us2; markets h2h,spreads,totals; S=10; k≥3; F-8 90m.

refuse_odds_fetch stays default ON. There is no CLI lift flag. Single-invocation
lift is process-scoped env only (not Railway-global). Celery tick is not this
path and still never fetches or seals.

TODO(S2): NFL_W8_PR_ROTATE_CONFIRM vs KEEP existing key (decision a9ae5ae6;
VERIFY PASS e64e73ac) is pending Ryan. Do not set rotate-confirm unless Ryan
rules — that would assert a rotation that did not happen. hold.py lift policy
is unchanged.

AC-12: produce_seal writes AC-1 + AC-2 custodian_receipt_id slot only.
seal_ack stays CURSOR_CANNOT_SEAL_ACK. A named custodian receipt is required
for AC-2; Cursor cannot seal-ack. Do not fake seal-ack.

Credit: operator must enforce (used−11622)+estimate ≤ 3000 from response
headers (cited baseline e64e73ac). Bundle-local ceiling remains 3000.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
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
from src.services.nfl_w8_capture.credits import (
    ACCOUNT_USED_BASELINE_E64E73AC,
    CREDIT_CEILING,
    HEADER_USED,
    CreditCeilingError,
    CreditEstimateError,
    CreditReconcileError,
    assert_operator_account_budget,
    estimate_request_credits,
    read_last_credit_record,
    seed_account_baseline_note,
)
from src.services.nfl_w8_capture.fetch import (
    OddsFetchError,
    OddsTransport,
    fetch_odds_with_provenance,
)
from src.services.nfl_w8_capture.fixture_load import cells_from_odds_shaped_event, select_odds_event
from src.services.nfl_w8_capture.hold import OddsApiHoldError, hold_lift_state, odds_api_hold_is_on
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
    "cd services/model-service && PYTHONPATH=. python -m src.services.nfl_w8_capture "
    "--game-id <GAME_ID> --kickoff-utc <KICKOFF_UTC>"
)

SEAL_ACK = "CURSOR_CANNOT_SEAL_ACK"
S2_PENDING = (
    "S2 PENDING RYAN: NFL_W8_PR_ROTATE_CONFIRM vs KEEP existing key "
    "(a9ae5ae6 / VERIFY e64e73ac). Do not set rotate-confirm unless Ryan rules. "
    "hold.py lift policy is unchanged."
)


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


def _prior_used(store: BundleStore) -> Optional[int]:
    record = read_last_credit_record(store)
    if record is None:
        return None
    headers = record.get("headers") or {}
    if not isinstance(headers, dict) or HEADER_USED not in headers:
        return None
    try:
        return int(headers[HEADER_USED])
    except (TypeError, ValueError):
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
) -> dict[str, Any]:
    """Fetch → snapshot → close → seal for ONE PART B W8 game.

    Does not lift hold. Does not seal-ack. Does not call refuse_seal as success.
    """
    source = env if env is not None else os.environ
    kickoff = _aware(kickoff_utc, field="kickoff_utc")
    now = _aware(now_utc, field="now_utc") if now_utc is not None else datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    if odds_api_hold_is_on(source):
        raise OddsApiHoldError(
            "refuse_odds_fetch default ON. Lift is process-scoped env only "
            "(NFL_W8_H1_AUTH_CITE + NFL_W8_PR_ROTATE_CONFIRM) — no CLI flag, "
            f"not Railway-global. {S2_PENDING}"
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
    prior_used = _prior_used(store)
    if prior_used is not None:
        assert_operator_account_budget(prior_used, estimate)

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
    if used_now is not None:
        assert_operator_account_budget(int(used_now), estimate)

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
        "operator_budget": {
            "baseline_used": ACCOUNT_USED_BASELINE_E64E73AC,
            "cite": "e64e73ac",
            "rule": "(used-11622)+estimate <= 3000 from response headers",
            "ceiling": CREDIT_CEILING,
            "used_now": used_now,
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
        "hold_lift": hold_lift_state(source),
        "s2": S2_PENDING,
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
        prog="python -m src.services.nfl_w8_capture",
        description=(
            "One-shot PART B W8 sealed capture (fetch→snapshot→close→seal). "
            "Draft path only. No merge, no deploy, no live call unless process "
            "env lifts hold. No CLI hold-lift flag."
        ),
        epilog=(
            f"Exact argv: {ONESHOT_ARGV}\n"
            "Optional: --bundle-dir <DIR> --custodian-receipt-id <ID> "
            "--now-utc <ISO> --odds-event-id <ID> --registered-at <ISO>\n"
            "PART B constants (not flags): draftkings,fanduel,betmgm,fanatics,circa; "
            "S=10; k>=3; 90m.\n"
            "Lift (process-scoped env, not argv, not Railway-global): "
            "NFL_W8_H1_AUTH_CITE=89fdd45f and NFL_W8_PR_ROTATE_CONFIRM. "
            f"{S2_PENDING}\n"
            "ODDS_API_KEY from env only — never argv, never logs.\n"
            "AC-12: seal_ack=CURSOR_CANNOT_SEAL_ACK. Custodian receipt required for AC-2.\n"
            "Credit: (used-11622)+estimate <= 3000 from response headers."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--game-id", required=True, help="Capture game id (not an Odds key)")
    parser.add_argument("--kickoff-utc", required=True, help="Kickoff UTC ISO-8601")
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
    return parser


def main(argv: Optional[Sequence[str]] = None, *, env: Optional[Mapping[str, str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    source = env if env is not None else os.environ
    root = Path(
        args.bundle_dir
        or source.get(ENV_BUNDLE_DIR)
        or (Path.cwd() / "data" / "ops" / "nfl-w8-capture-bundle")
    )
    try:
        summary = run_oneshot_sealed_capture(
            game_id=str(args.game_id),
            kickoff_utc=str(args.kickoff_utc),
            store=BundleStore(root),
            env=source,
            now_utc=str(args.now_utc) or None,
            custodian_receipt_id=str(args.custodian_receipt_id or ""),
            odds_event_id=str(args.odds_event_id or ""),
            registered_at=str(args.registered_at) or None,
        )
    except (
        OddsApiHoldError,
        OddsFetchError,
        OneshotError,
        CreditCeilingError,
        CreditEstimateError,
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
