"""H-1c credit ledger: hash-chained cumulative spend, hard ceiling 3000.

Credits come from Odds API response headers. Missing headers fail closed.
There is no purchase / top-up path.
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


class CreditPurchaseError(RuntimeError):
    """H-1c: no automatic purchase or credit top-up."""


def _header_map(headers: Mapping[str, Any]) -> dict[str, str]:
    return {str(key).strip().lower(): str(value).strip() for key, value in headers.items()}


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


def read_cumulative(store: BundleStore) -> int:
    path = store.root / CREDITS_NAME
    if not path.exists():
        return 0
    last = 0
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        entry = json.loads(raw)
        record = entry.get("record") or {}
        last = int(record.get("cumulative") or 0)
    return last


def pre_call_check(cumulative: int, next_credits: int = 1) -> None:
    """Hard stop at ≤3000. 2999+1 allowed; 3000 and 3001 refuse."""
    if next_credits < 0:
        raise CreditHeaderError("next_credits must be >= 0")
    if cumulative > CREDIT_CEILING:
        raise CreditCeilingError(
            f"H-1c credit ceiling: cumulative {cumulative} already > {CREDIT_CEILING}"
        )
    if cumulative >= CREDIT_CEILING:
        raise CreditCeilingError(
            f"H-1c credit ceiling: cumulative {cumulative} >= {CREDIT_CEILING}; hard stop"
        )
    if cumulative + next_credits > CREDIT_CEILING:
        raise CreditCeilingError(
            f"H-1c credit ceiling: {cumulative}+{next_credits} > {CREDIT_CEILING}; hard stop"
        )


def record_credit_use(
    store: BundleStore,
    headers: Mapping[str, Any],
    *,
    actor: str = "nfl_w8_capture",
    note: str = "credit-use",
) -> dict[str, Any]:
    parsed = parse_credit_headers(headers)
    delta = parsed[HEADER_LAST]
    current = read_cumulative(store)
    pre_call_check(current, delta)
    cumulative = current + delta
    record = {
        "delta": delta,
        "cumulative": cumulative,
        "ceiling": CREDIT_CEILING,
        "headers": {
            HEADER_LAST: parsed[HEADER_LAST],
            HEADER_USED: parsed[HEADER_USED],
            HEADER_REMAINING: parsed[HEADER_REMAINING],
        },
        "purchase": False,
    }
    committed = store.append_chained_jsonl(
        CREDITS_NAME,
        record,
        actor=actor,
        note=note,
    )
    return {
        "delta": delta,
        "cumulative": cumulative,
        "entry_sha": committed["entry_sha"],
        "headers": record["headers"],
    }


def refuse_credit_purchase() -> None:
    raise CreditPurchaseError(
        "H-1c: additional credit purchases / plan top-up are not authorized. "
        "No purchase path exists in nfl_w8_capture."
    )
