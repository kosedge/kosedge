"""H-1c credit ledger: hash-chained cumulative spend, hard ceiling 3000.

Actual spend is always recorded (overrun-marked) before raise+alert.
Pre-call estimate is books×markets×regions (five-book PART B = 30), never 1.
Missing headers and used-header mismatch fail closed. No purchase path.

t4520u / t4523u Option A (beat/worker left running):
- H-1c constants 11622 / 14622 stay immutable (cited VERIFY, not a live prior).
- seed_account_baseline_note is note-only; it must not write used=11622 as ledger prev.
- Reconcile prior is a fresh T-0 account reading immediately before each request.
- Reserve worst-case (T-0 used + estimate) before execute; do not ignore counter
  differences (never reserve against stale 11622 when T-0 used differs).
- After: this-request charge = x-requests-last; concurrent = used_after − T-0 − last.
- Concurrent >0 is attributed to beat/worker (Option A); never zeroed or folded
  into the oneshot. Unexplained discrepancy (negative concurrent, this-request
  charge > reserved, missing attribution, missing T-0) fails closed.
"""

from __future__ import annotations

import json
from typing import Any, Mapping, Optional

from src.services.nfl_w8_capture.store import CREDITS_NAME, BundleStore

CREDIT_CEILING = 3000

# H-1 /v4/sports VERIFY PASS e64e73ac (~2026-10-27 12:38 ET):
# used=11622 remaining=8378 last=0. Bundle-local ledger is still 3000.
# Operator must enforce (used−11622)+estimate ≤ 3000 from response headers.
# Do not treat this as a live reading; it is a cited baseline only.
ACCOUNT_USED_BASELINE_E64E73AC = 11622
ACCOUNT_REMAINING_CITED_E64E73AC = 8378
ACCOUNT_BASELINE_CITE = "e64e73ac"
# R5(b): (used − 11622) ≤ 3000 ⇒ used ≤ 14622
ACCOUNT_USED_CEILING_E64E73AC = ACCOUNT_USED_BASELINE_E64E73AC + CREDIT_CEILING
BASELINE_NOTE_NAME = "credits_account_baseline.json"

HEADER_LAST = "x-requests-last"
HEADER_USED = "x-requests-used"
HEADER_REMAINING = "x-requests-remaining"
REQUIRED_CREDIT_HEADERS = (HEADER_LAST, HEADER_USED, HEADER_REMAINING)

ROLE_T0 = "t0"
ROLE_RESERVATION = "reservation"
ROLE_FETCH = "odds-fetch"
CONCURRENT_ATTRIBUTION_BEAT_WORKER = "beat_worker"

ENV_T0_USED = "NFL_W8_T0_USED"
ENV_T0_REMAINING = "NFL_W8_T0_REMAINING"
ENV_T0_LAST = "NFL_W8_T0_LAST"

# t4516u PATH A (immutable receipt 072005fe): T-0 11704 last=0; capture 11707 last=3.
T4516U_T0_USED = 11704
T4516U_CAPTURE_USED = 11707
T4516U_CAPTURE_LAST = 3


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


def credit_headers(
    *,
    last: int | str,
    used: int | str,
    remaining: int | str,
) -> dict[str, str]:
    return {
        HEADER_LAST: str(last),
        HEADER_USED: str(used),
        HEADER_REMAINING: str(remaining),
    }


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


def _prior_used(prior: Optional[Mapping[str, Any]]) -> Optional[int]:
    if prior is None:
        return None
    headers = prior.get("headers") or {}
    if not isinstance(headers, dict) or HEADER_USED not in headers:
        return None
    try:
        return int(headers[HEADER_USED])
    except (TypeError, ValueError):
        raise CreditReconcileError("prior x-requests-used unparseable")


def _is_stale_verify_seed(prior: Mapping[str, Any]) -> bool:
    """Leftover tip-3e2f643b ledger seed: used=11622 last=0, no T-0 role."""
    role = str(prior.get("role") or "")
    if role in (ROLE_T0, ROLE_RESERVATION):
        return False
    headers = prior.get("headers") or {}
    if not isinstance(headers, dict):
        return False
    try:
        used = int(headers.get(HEADER_USED, -1))
        last = int(headers.get(HEADER_LAST, -1))
    except (TypeError, ValueError):
        return False
    return (
        used == ACCOUNT_USED_BASELINE_E64E73AC
        and last == 0
        and int(prior.get("delta") or 0) == 0
    )


def concurrent_from_counters(*, t0_used: int, used_after: int, last: int) -> int:
    """Account burn that is not this request. Option A: beat/worker left running."""
    return int(used_after) - int(t0_used) - int(last)


def _reconcile_account_used(
    prior: Optional[Mapping[str, Any]],
    parsed: Mapping[str, int],
    *,
    require_t0: bool = False,
    expected_charge: Optional[int] = None,
) -> dict[str, Any]:
    """Split this-request last from concurrent beat/worker. Never ignore a gap.

    Returns a reconcile result. ``error`` set ⇒ fail closed after the row is written.
    """
    result: dict[str, Any] = {
        "error": None,
        "concurrent": 0,
        "concurrent_attribution": None,
        "oneshot_delta": parsed[HEADER_LAST],
        "t0_used": None,
        "reserved_charge": expected_charge,
    }
    if prior is None:
        if require_t0:
            result["error"] = "need T-0 snapshot immediately before request"
        return result

    if require_t0 and _is_stale_verify_seed(prior):
        result["error"] = (
            "stale-need-T-0: VERIFY/baseline seed used="
            f"{ACCOUNT_USED_BASELINE_E64E73AC} is not a T-0 snapshot; "
            f"{ACCOUNT_USED_BASELINE_E64E73AC}+{parsed[HEADER_LAST]} "
            f"!= {parsed[HEADER_USED]}"
        )
        return result

    role = str(prior.get("role") or "")
    if require_t0 and role not in (ROLE_T0, ROLE_RESERVATION):
        result["error"] = "need T-0 snapshot immediately before request; prior role is not t0"
        return result

    try:
        prev_used = int((prior.get("headers") or {})[HEADER_USED])
    except (TypeError, ValueError, KeyError):
        if HEADER_USED not in (prior.get("headers") or {}):
            return result
        raise CreditReconcileError("prior x-requests-used unparseable")

    reserved = expected_charge
    if reserved is None and prior.get("reserved_charge") is not None:
        try:
            reserved = int(prior["reserved_charge"])
        except (TypeError, ValueError):
            reserved = None
    result["reserved_charge"] = reserved
    result["t0_used"] = prev_used

    last = parsed[HEADER_LAST]
    used = parsed[HEADER_USED]
    concurrent = concurrent_from_counters(t0_used=prev_used, used_after=used, last=last)
    result["concurrent"] = concurrent
    result["oneshot_delta"] = last

    if reserved is not None and last > int(reserved):
        result["error"] = (
            f"this-request charge {last} > reserved worst-case {reserved}; "
            "reservation must not ignore counter differences"
        )
        return result

    if require_t0 and last < 1:
        result["error"] = "unexplained discrepancy: fetch last < 1 (this-request charge missing)"
        return result

    if concurrent < 0:
        result["error"] = (
            f"used-header mismatch: {prev_used}+{last} != {used} "
            f"(concurrent={concurrent}); unexplained discrepancy"
        )
        return result

    if concurrent > 0:
        # Option A: beat/worker left running. Record explicitly. Never fold into oneshot.
        result["concurrent_attribution"] = CONCURRENT_ATTRIBUTION_BEAT_WORKER
    return result


def record_credit_use(
    store: BundleStore,
    headers: Mapping[str, Any],
    *,
    actor: str = "nfl_w8_capture",
    note: str = "credit-use",
    require_t0: bool = False,
    expected_charge: Optional[int] = None,
    role: str = ROLE_FETCH,
) -> dict[str, Any]:
    """Record actual spend first. Overrun/mismatch are marked, then raised.

    Oneshot cumulative += this-request last only. Concurrent beat/worker is
    recorded on the row and is never classified as zero or as oneshot spend.
    """
    parsed = parse_credit_headers(headers)
    delta = parsed[HEADER_LAST]
    prior = read_last_credit_record(store)
    current = int((prior or {}).get("cumulative") or 0)
    recon = _reconcile_account_used(
        prior,
        parsed,
        require_t0=require_t0,
        expected_charge=expected_charge,
    )
    mismatch = recon.get("error")
    concurrent = int(recon.get("concurrent") or 0)
    attribution = recon.get("concurrent_attribution")
    if concurrent > 0 and not attribution:
        mismatch = mismatch or (
            "unexplained discrepancy: concurrent>0 with no attribution field"
        )
    # Ledger tracks this request only. Concurrent is account-side, not oneshot.
    oneshot_delta = int(recon.get("oneshot_delta") or delta)
    cumulative = current + oneshot_delta
    overrun = cumulative > CREDIT_CEILING
    record = {
        "delta": oneshot_delta,
        "cumulative": cumulative,
        "ceiling": CREDIT_CEILING,
        "overrun": overrun,
        "reconcile_ok": mismatch is None,
        "role": role,
        "oneshot_delta": oneshot_delta,
        "concurrent": concurrent,
        "concurrent_attribution": attribution,
        "t0_used": recon.get("t0_used"),
        "reserved_charge": recon.get("reserved_charge"),
        "headers": {
            HEADER_LAST: parsed[HEADER_LAST],
            HEADER_USED: parsed[HEADER_USED],
            HEADER_REMAINING: parsed[HEADER_REMAINING],
        },
        "purchase": False,
    }
    if concurrent > 0:
        record["concurrent_note"] = (
            "explicit concurrent beat/worker (t4523u Option A leave running); "
            "not attributed to oneshot"
        )
    if mismatch:
        record["reconcile_error"] = mismatch
    committed = store.append_chained_jsonl(
        CREDITS_NAME,
        record,
        actor=actor,
        note=note if not overrun else f"{note}:overrun",
    )
    out = {
        "delta": oneshot_delta,
        "cumulative": cumulative,
        "overrun": overrun,
        "concurrent": concurrent,
        "concurrent_attribution": attribution,
        "oneshot_delta": oneshot_delta,
        "t0_used": recon.get("t0_used"),
        "reserved_charge": recon.get("reserved_charge"),
        "entry_sha": committed["entry_sha"],
        "headers": record["headers"],
    }
    if mismatch:
        raise CreditReconcileError(mismatch)
    if overrun:
        raise CreditCeilingError(
            f"H-1c credit ceiling: recorded actual spend {current}+{oneshot_delta}={cumulative} "
            f"> {CREDIT_CEILING}; ledger closed"
        )
    return out


def refuse_credit_purchase() -> None:
    raise CreditPurchaseError(
        "H-1c: additional credit purchases / plan top-up are not authorized. "
        "No purchase path exists in nfl_w8_capture."
    )


def operator_account_spend(used_now: int, *, baseline: int = ACCOUNT_USED_BASELINE_E64E73AC) -> int:
    """Account credits consumed since cited baseline. Not a live call."""
    return int(used_now) - int(baseline)


def assert_account_used_ceiling(
    used_now: int,
    *,
    baseline: int = ACCOUNT_USED_BASELINE_E64E73AC,
    ceiling: int = CREDIT_CEILING,
) -> None:
    """R5(b): (used − 11622) ≤ 3000 i.e. used ≤ 14622. Ledger is separate (R5a)."""
    if int(used_now) < int(baseline):
        raise CreditReconcileError(
            f"x-requests-used {used_now} < cited baseline {baseline} ({ACCOUNT_BASELINE_CITE}); "
            "do not assume a rotation. KEEP a9ae5ae6 / t4500u 20325274; "
            "NFL_W8_PR_ROTATE_CONFIRM is stale and is rejected as a KEEP path."
        )
    spend = operator_account_spend(used_now, baseline=baseline)
    if spend > int(ceiling):
        raise CreditCeilingError(
            f"R5(b) account ceiling: (used {used_now} − baseline {baseline}) = "
            f"{spend} > {ceiling} (used must be <= {baseline + int(ceiling)})"
        )


def assert_dual_credit_r5(
    store: BundleStore,
    used_now: int,
) -> dict[str, int]:
    """R5: (a) bundle ledger cumulative ≤ 3000 AND (b) account used ≤ 14622.

    Ledger is not optional. Account-only translation is not a substitute.
    """
    cumulative = read_cumulative(store)
    if cumulative > CREDIT_CEILING:
        raise CreditCeilingError(
            f"R5(a) ledger cumulative {cumulative} > {CREDIT_CEILING}; ledger not optional"
        )
    assert_account_used_ceiling(int(used_now))
    return {
        "ledger_cumulative": cumulative,
        "ledger_ceiling": CREDIT_CEILING,
        "account_used": int(used_now),
        "account_baseline": ACCOUNT_USED_BASELINE_E64E73AC,
        "account_ceiling": ACCOUNT_USED_CEILING_E64E73AC,
    }


def assert_operator_account_budget(
    used_now: int,
    estimate: int,
    *,
    baseline: int = ACCOUNT_USED_BASELINE_E64E73AC,
    ceiling: int = CREDIT_CEILING,
) -> None:
    """Operator rule: (used−11622)+estimate ≤ 3000 from response headers.

    used_now is the Odds ``x-requests-used`` header (or a cited prior).
    estimate is books×markets×regions (PART B = 30). Never default 1.
    """
    if estimate < 1:
        raise CreditEstimateError(
            "pre-call estimate must be >= 1 (books×markets×regions); never default 1"
        )
    if int(used_now) < int(baseline):
        raise CreditReconcileError(
            f"x-requests-used {used_now} < cited baseline {baseline} ({ACCOUNT_BASELINE_CITE}); "
            "do not assume a rotation. KEEP a9ae5ae6 / t4500u 20325274; "
            "NFL_W8_PR_ROTATE_CONFIRM is stale and is rejected as a KEEP path."
        )
    spend = operator_account_spend(used_now, baseline=baseline)
    if spend + int(estimate) > int(ceiling):
        raise CreditCeilingError(
            f"operator account budget: (used {used_now} − baseline {baseline}) + "
            f"estimate {estimate} = {spend + int(estimate)} > {ceiling}"
        )


def reserve_worst_case_before_execute(
    t0_used: int,
    estimate: int,
    *,
    used_for_reserve: Optional[int] = None,
    baseline: int = ACCOUNT_USED_BASELINE_E64E73AC,
    ceiling: int = CREDIT_CEILING,
) -> dict[str, int]:
    """Reserve T-0 used + estimate before execute. Never ignore counter differences.

    ``used_for_reserve`` if provided must equal T-0 used. Passing the VERIFY
    cite 11622 while T-0 is 11704 is FAIL CLOSED (that is the t4516u defect).
    Insufficient headroom vs 14622 / (used−11622)+estimate≤3000 fails closed.
    """
    if estimate < 1:
        raise CreditEstimateError(
            "pre-call estimate must be >= 1 (books×markets×regions); never default 1"
        )
    if used_for_reserve is not None and int(used_for_reserve) != int(t0_used):
        raise CreditReconcileError(
            "reservation must not ignore counter difference: "
            f"refusing used_for_reserve={used_for_reserve} != T-0 used={t0_used}"
        )
    current = int(t0_used)
    assert_account_used_ceiling(current, baseline=baseline, ceiling=ceiling)
    spend = operator_account_spend(current, baseline=baseline)
    worst_case_used = current + int(estimate)
    account_ceiling = int(baseline) + int(ceiling)
    if spend + int(estimate) > int(ceiling) or worst_case_used > account_ceiling:
        raise CreditCeilingError(
            f"insufficient headroom: T-0 used {current} + estimate {estimate} = "
            f"{worst_case_used} > {account_ceiling} "
            f"((used−{baseline})+estimate={spend + int(estimate)} > {ceiling})"
        )
    return {
        "t0_used": current,
        "estimate": int(estimate),
        "reserved_charge": int(estimate),
        "worst_case_used": worst_case_used,
        "counter_delta_from_baseline": spend,
        "account_baseline": int(baseline),
        "account_ceiling": account_ceiling,
        "headroom": account_ceiling - current,
    }


def assert_t0_ready(store: BundleStore) -> dict[str, Any]:
    """Fresh T-0 (or armed reservation) must be the last ledger row."""
    if ledger_closed(store):
        raise CreditReconcileError(
            "ledger closed; abort recovery requires a new bundle + T-0 "
            "(do not reuse dest; 072005fe stays immutable)"
        )
    prior = read_last_credit_record(store)
    if prior is None:
        raise CreditReconcileError("need T-0 snapshot immediately before request")
    if _is_stale_verify_seed(prior):
        raise CreditReconcileError(
            "stale-need-T-0: VERIFY/baseline seed used="
            f"{ACCOUNT_USED_BASELINE_E64E73AC} is not a T-0 snapshot"
        )
    role = str(prior.get("role") or "")
    if role not in (ROLE_T0, ROLE_RESERVATION):
        raise CreditReconcileError(
            "need T-0 snapshot immediately before request; prior role is not t0"
        )
    headers = prior.get("headers") or {}
    if not isinstance(headers, dict):
        raise CreditReconcileError("T-0 snapshot missing headers")
    try:
        last = int(headers[HEADER_LAST])
        used = int(headers[HEADER_USED])
    except (TypeError, ValueError, KeyError) as exc:
        raise CreditReconcileError("T-0 snapshot headers unparseable") from exc
    if last != 0:
        raise CreditReconcileError("T-0 snapshot last must be 0 (reading, not a spend)")
    assert_account_used_ceiling(used)
    return prior


def seed_t0_account_snapshot(
    store: BundleStore,
    headers: Mapping[str, Any],
    *,
    actor: str = "nfl_w8_capture",
    note: str = "t0-account-snapshot",
) -> dict[str, Any]:
    """Write a fresh last=0 account reading as the reconcile prior.

    Not the VERIFY 11622 cite. last must be 0. Dirty/closed dest refuses.
    """
    if ledger_closed(store):
        raise CreditReconcileError(
            "ledger closed; abort recovery requires a new bundle + T-0 "
            "(do not reuse dest; 072005fe stays immutable)"
        )
    parsed = parse_credit_headers(headers)
    if parsed[HEADER_LAST] != 0:
        raise CreditReconcileError("T-0 snapshot last must be 0 (reading, not a spend)")
    assert_account_used_ceiling(parsed[HEADER_USED])
    current = read_cumulative(store)
    record = {
        "delta": 0,
        "cumulative": current,
        "ceiling": CREDIT_CEILING,
        "overrun": False,
        "reconcile_ok": True,
        "role": ROLE_T0,
        "t0": True,
        "live_call": False,
        "headers": {
            HEADER_LAST: parsed[HEADER_LAST],
            HEADER_USED: parsed[HEADER_USED],
            HEADER_REMAINING: parsed[HEADER_REMAINING],
        },
        "purchase": False,
        "account_baseline": ACCOUNT_USED_BASELINE_E64E73AC,
        "account_ceiling": ACCOUNT_USED_CEILING_E64E73AC,
        "counter_delta_from_baseline": parsed[HEADER_USED] - ACCOUNT_USED_BASELINE_E64E73AC,
        "note": (
            "T-0 fresh account reading immediately before request; "
            "not the VERIFY 11622 cite. t4520u / t4523u Option A."
        ),
    }
    committed = store.append_chained_jsonl(
        CREDITS_NAME,
        record,
        actor=actor,
        note=note,
    )
    return {
        "role": ROLE_T0,
        "t0_used": parsed[HEADER_USED],
        "t0_remaining": parsed[HEADER_REMAINING],
        "cumulative": current,
        "entry_sha": committed["entry_sha"],
        "headers": record["headers"],
    }


def write_reservation(
    store: BundleStore,
    estimate: int,
    *,
    actor: str = "nfl_w8_capture",
    note: str = "credit-reservation",
) -> dict[str, Any]:
    """Arm worst-case reservation from the T-0 row. No transport yet."""
    prior = assert_t0_ready(store)
    if str(prior.get("role") or "") == ROLE_RESERVATION:
        raise CreditReconcileError(
            "reservation already armed; abort recovery needs a fresh T-0"
        )
    t0_used = int((prior.get("headers") or {})[HEADER_USED])
    reserved = reserve_worst_case_before_execute(t0_used, estimate)
    current = read_cumulative(store)
    record = {
        "delta": 0,
        "cumulative": current,
        "ceiling": CREDIT_CEILING,
        "overrun": False,
        "reconcile_ok": True,
        "role": ROLE_RESERVATION,
        "reserved_charge": reserved["reserved_charge"],
        "t0_used": reserved["t0_used"],
        "worst_case_used": reserved["worst_case_used"],
        "counter_delta_from_baseline": reserved["counter_delta_from_baseline"],
        "account_baseline": reserved["account_baseline"],
        "account_ceiling": reserved["account_ceiling"],
        "headroom": reserved["headroom"],
        "headers": dict(prior.get("headers") or {}),
        "purchase": False,
        "option_a_beat_worker_left_running": True,
        "note": (
            "Worst-case reservation against T-0 used (not VERIFY 11622). "
            "t4523u Option A: do not ignore counter differences."
        ),
    }
    committed = store.append_chained_jsonl(
        CREDITS_NAME,
        record,
        actor=actor,
        note=note,
    )
    return {
        **reserved,
        "role": ROLE_RESERVATION,
        "entry_sha": committed["entry_sha"],
        "headers": record["headers"],
    }


def t0_headers_from_env(env: Mapping[str, str]) -> Optional[dict[str, str]]:
    used = str(env.get(ENV_T0_USED) or "").strip()
    remaining = str(env.get(ENV_T0_REMAINING) or "").strip()
    last = str(env.get(ENV_T0_LAST) or "0").strip() or "0"
    if not used or not remaining:
        return None
    return credit_headers(last=last, used=used, remaining=remaining)


def seed_account_baseline_note(
    store: BundleStore,
    *,
    actor: str = "nfl_w8_capture",
) -> Optional[dict[str, Any]]:
    """Write cited baseline 11622 without a live Odds call.

    Note-only. Does **not** seed a ledger prior of used=11622 (t4520u).
    Reconcile prior must be a later T-0 snapshot. Skips if the note exists.
    """
    note_path = store.root / BASELINE_NOTE_NAME
    if note_path.exists():
        return None
    store.write_new_file(
        BASELINE_NOTE_NAME,
        {
            "account_used_baseline": ACCOUNT_USED_BASELINE_E64E73AC,
            "account_remaining_cited": ACCOUNT_REMAINING_CITED_E64E73AC,
            "account_used_ceiling": ACCOUNT_USED_CEILING_E64E73AC,
            "cite": ACCOUNT_BASELINE_CITE,
            "source": "H-1 /v4/sports VERIFY PASS e64e73ac",
            "operator_rule": "(used-11622)+estimate <= 3000 from response headers",
            "bundle_local_ceiling": CREDIT_CEILING,
            "live_call": False,
            "ledger_seed": False,
            "t0_required": True,
            "note": (
                "Cited account baseline only. Bundle-local ledger starts at 0. "
                "Do not write used=11622 as reconcile prev. Operator must seed a "
                "T-0 x-requests-used reading immediately before each request "
                "(t4520u / t4523u Option A). S2 rotate vs KEEP is pending Ryan."
            ),
        },
        actor=actor,
        note="credit-baseline-e64e73ac",
    )
    return {"note": True, "ledger_seed": False}
