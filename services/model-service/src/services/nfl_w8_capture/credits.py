"""H-1c credit ledger: hash-chained cumulative spend, hard ceiling 3000.

Actual spend is always recorded (overrun-marked) before raise+alert.
Pre-call estimate is books×markets×regions (five-book PART B = 30), never 1.
Missing headers and used-header mismatch fail closed. No purchase path.
"""

from __future__ import annotations

import json
from typing import Any, Mapping, Optional

from src.services.nfl_w8_capture.store import CREDITS_NAME, BundleStore

CREDIT_CEILING = 3000

HEADER_LAST = "x-requests-last"
HEADER_USED = "x-requests-used"
HEADER_REMAINING = "x-requests-remaining"
REQUIRED_CREDIT_HEADERS = (HEADER_LAST, HEADER_USED, HEADER_REMAINING)


class CreditCeilingError(RuntimeError):
    """Raised when the 3,000-credit cumulative ceiling would be breached."""


class CreditHeaderError(RuntimeError):
    """Raised when required credit headers are missing or unparseable."""


class CreditEstimateError(ValueError):
    """Raised when the pre-call estimate is missing or < 1."""


class CreditReconcileError(RuntimeError):
    """Raised when ledger delta does not match the account used-credits header."""


class CreditPurchaseError(RuntimeError):
    """H-1c: no automatic purchase or credit top-up."""


def _header_map(headers: Mapping[str, Any]) -> dict[str, str]:
    return {str(key).strip().lower(): str(value).strip() for key, value in headers.items()}


def _csv_count(raw: Any) -> int:
    return len([part for part in str(raw or "").split(",") if part.strip()])


def estimate_request_credits(params: Mapping[str, Any]) -> int:
    """Real request cost: bookmakers × markets × regions. Never default 1."""
    n_books = _csv_count(params.get("bookmakers"))
    n_markets = _csv_count(params.get("markets"))
    n_regions = _csv_count(params.get("regions"))
    cost = n_books * n_markets * n_regions
    if cost < 1:
        raise CreditEstimateError(
            "pre-call estimate must be >= 1 (books×markets×regions); never default 1"
        )
    return cost


def parse_credit_headers(headers: Mapping[str, Any]) -> dict[str, int]:
    """Require last/used/remaining. Missing any header stops."""
    normalized = _header_map(headers)
    parsed: dict[str, int] = {}
    missing = [name for name in REQUIRED_CREDIT_HEADERS if name not in normalized or normalized[name] == ""]
    if missing:
        raise CreditHeaderError(f"missing credit headers: {','.join(missing)}")
    for name in REQUIRED_CREDIT_HEADERS:
        try:
            parsed[name] = int(normalized[name])
        except ValueError as exc:
            raise CreditHeaderError(f"unparseable credit header {name}") from exc
        if parsed[name] < 0:
            raise CreditHeaderError(f"negative credit header {name}")
    return parsed


def read_last_credit_record(store: BundleStore) -> Optional[dict[str, Any]]:
    path = store.root / CREDITS_NAME
    if not path.exists():
        return None
    last: Optional[dict[str, Any]] = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        entry = json.loads(raw)
        record = entry.get("record") or {}
        if isinstance(record, dict):
            last = record
    return last


def read_cumulative(store: BundleStore) -> int:
    record = read_last_credit_record(store)
    if record is None:
        return 0
    return int(record.get("cumulative") or 0)


def ledger_overrun(store: BundleStore) -> bool:
    record = read_last_credit_record(store)
    if record is None:
        return False
    if record.get("overrun") is True:
        return True
    return int(record.get("cumulative") or 0) > CREDIT_CEILING


def ledger_closed(store: BundleStore) -> bool:
    """After ceiling, overrun, or reconcile fail, every subsequent pre-call refuses."""
    record = read_last_credit_record(store)
    if record is None:
        return False
    if record.get("overrun") is True:
        return True
    if record.get("reconcile_ok") is False:
        return True
    return int(record.get("cumulative") or 0) >= CREDIT_CEILING


def pre_call_check(
    cumulative: int,
    next_credits: int,
    *,
    overrun: bool = False,
) -> None:
    """Hard stop at ≤3000. Estimate must be the real request cost (>= 1)."""
    if next_credits < 1:
        raise CreditEstimateError(
            "pre-call estimate must be >= 1 (books×markets×regions); never default 1"
        )
    if overrun or cumulative > CREDIT_CEILING:
        raise CreditCeilingError(
            f"H-1c credit ceiling: ledger already overrun (cumulative={cumulative})"
        )
    if cumulative >= CREDIT_CEILING:
        raise CreditCeilingError(
            f"H-1c credit ceiling: cumulative {cumulative} >= {CREDIT_CEILING}; hard stop"
        )
    if cumulative + next_credits > CREDIT_CEILING:
        raise CreditCeilingError(
            f"H-1c credit ceiling: {cumulative}+{next_credits} > {CREDIT_CEILING}; hard stop"
        )


def _reconcile_account_used(
    prior: Optional[Mapping[str, Any]],
    parsed: Mapping[str, int],
) -> Optional[str]:
    if prior is None:
        return None
    headers = prior.get("headers") or {}
    if not isinstance(headers, dict) or HEADER_USED not in headers:
        return None
    try:
        prev_used = int(headers[HEADER_USED])
    except (TypeError, ValueError):
        raise CreditReconcileError("prior x-requests-used unparseable")
    account_delta = parsed[HEADER_USED] - prev_used
    if account_delta != parsed[HEADER_LAST]:
        return (
            f"used-header mismatch: {prev_used}+{parsed[HEADER_LAST]} "
            f"!= {parsed[HEADER_USED]}"
        )
    return None


def record_credit_use(
    store: BundleStore,
    headers: Mapping[str, Any],
    *,
    actor: str = "nfl_w8_capture",
    note: str = "credit-use",
) -> dict[str, Any]:
    """Record actual spend first. Overrun/mismatch are marked, then raised."""
    parsed = parse_credit_headers(headers)
    delta = parsed[HEADER_LAST]
    prior = read_last_credit_record(store)
    current = int((prior or {}).get("cumulative") or 0)
    mismatch = _reconcile_account_used(prior, parsed)
    cumulative = current + delta
    overrun = cumulative > CREDIT_CEILING
    record = {
        "delta": delta,
        "cumulative": cumulative,
        "ceiling": CREDIT_CEILING,
        "overrun": overrun,
        "reconcile_ok": mismatch is None,
        "headers": {
            HEADER_LAST: parsed[HEADER_LAST],
            HEADER_USED: parsed[HEADER_USED],
            HEADER_REMAINING: parsed[HEADER_REMAINING],
        },
        "purchase": False,
    }
    if mismatch:
        record["reconcile_error"] = mismatch
    committed = store.append_chained_jsonl(
        CREDITS_NAME,
        record,
        actor=actor,
        note=note if not overrun else f"{note}:overrun",
    )
    out = {
        "delta": delta,
        "cumulative": cumulative,
        "overrun": overrun,
        "entry_sha": committed["entry_sha"],
        "headers": record["headers"],
    }
    if mismatch:
        raise CreditReconcileError(mismatch)
    if overrun:
        raise CreditCeilingError(
            f"H-1c credit ceiling: recorded actual spend {current}+{delta}={cumulative} "
            f"> {CREDIT_CEILING}; ledger closed"
        )
    return out


def refuse_credit_purchase() -> None:
    raise CreditPurchaseError(
        "H-1c: additional credit purchases / plan top-up are not authorized. "
        "No purchase path exists in nfl_w8_capture."
    )
