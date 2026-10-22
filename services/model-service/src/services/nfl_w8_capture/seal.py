"""Build, seal, verify, and custodian-receipt a W8 capture bundle."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional, Sequence

from src.services.nfl_w8_capture.chain import (
    append_event,
    open_log,
    sha256_hex,
    verify_chain,
)
from src.services.nfl_w8_capture.constants import (
    BLIND_GRADER,
    DEFAULT_SEAL_BY_ET,
    MIN_LEAD_MINUTES,
    MISSING,
    STATUS_FAIL,
    STATUS_OFFICIAL,
    STATUS_SEALED,
    STREAM_INDEPENDENT,
    STREAM_MARKET,
)
from src.services.nfl_w8_capture.fail_closed import (
    FailClosedError,
    run_builder_guards,
    w8_build_context,
)
from src.services.nfl_w8_capture.odds_ms import snapshot_record
from src.services.nfl_w8_capture.streams import (
    StreamError,
    assert_independent_has_no_market,
    check_stream_proofs,
)
from src.services.nfl_w8_capture.timeutil import et_to_utc, is_late, parse_utc, to_iso


class CaptureError(ValueError):
    """W8 capture refused the request."""


@dataclass
class CaptureResult:
    status: str
    root: str
    sha256sums: str
    official_seal_time_utc: Optional[str] = None
    failures: list[dict[str, Any]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "root": self.root,
            "sha256sums": self.sha256sums,
            "official_seal_time_utc": self.official_seal_time_utc,
            "failures": self.failures,
            "notes": self.notes,
            "published": False,
            "graded": False,
            "gate": False,
        }


def refuse_credentials(*, dry_run: bool) -> None:
    if not dry_run:
        return
    for key in ("DATABASE_URL", "ODDS_API_KEY", "THE_ODDS_API_KEY"):
        if os.environ.get(key):
            raise CaptureError(f"AC-4/MS-10 dry-run refuses {key}")


def refuse_publish(flag: Any = None) -> None:
    if flag:
        raise CaptureError("AC-11: publishing is forbidden")


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(dict(row), sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def write_sha256sums(root: Path, paths: Iterable[Path]) -> Path:
    lines: list[str] = []
    for path in sorted(paths, key=lambda p: p.relative_to(root).as_posix()):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if rel == "SHA256SUMS":
            continue
        lines.append(f"{sha256_hex(path.read_bytes())}  {rel}")
    out = root / "SHA256SUMS"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def verify_sha256sums(root: Path) -> Optional[str]:
    sums = root / "SHA256SUMS"
    if not sums.is_file():
        return "missing_sha256sums"
    listed: set[str] = set()
    for line in sums.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, rel = line.split("  ", 1)
        listed.add(rel)
        target = root / rel
        if not target.is_file():
            return f"sha256_missing_file:{rel}"
        if sha256_hex(target.read_bytes()) != digest:
            return f"sha256_mismatch:{rel}"
    return None


def _pins(
    *,
    model_version: str,
    code_sha: str,
    input_shas: Mapping[str, str],
    extra: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    payload = {
        "model_version": model_version,
        "code_sha": code_sha,
        "criteria": ["4f832c91", "132ee26c"],
        "protocol": "6a3aa3d9",
        "input_shas": dict(input_shas),
    }
    if extra:
        payload.update(dict(extra))
    return payload


def build_and_seal(
    root: Path | str,
    *,
    games: Sequence[Mapping[str, Any]],
    market_predictions: Sequence[Mapping[str, Any]],
    independent_predictions: Sequence[Mapping[str, Any]],
    market_inputs: Sequence[Mapping[str, Any]],
    independent_inputs: Sequence[Mapping[str, Any]],
    market_proofs: Sequence[Mapping[str, Any]],
    independent_proofs: Sequence[Mapping[str, Any]],
    odds_snapshots: Sequence[Mapping[str, Any]],
    model_version: str,
    code_sha: str,
    now_utc: datetime,
    dry_run: bool = True,
    publish: bool = False,
    min_lead_minutes: int = MIN_LEAD_MINUTES,
    default_seal_by_et: datetime = DEFAULT_SEAL_BY_ET,
) -> CaptureResult:
    """Write two streams, checksum, chain, and seal. Does not grade or publish."""
    with w8_build_context():
        return _build_and_seal_impl(
            root,
            games=games,
            market_predictions=market_predictions,
            independent_predictions=independent_predictions,
            market_inputs=market_inputs,
            independent_inputs=independent_inputs,
            market_proofs=market_proofs,
            independent_proofs=independent_proofs,
            odds_snapshots=odds_snapshots,
            model_version=model_version,
            code_sha=code_sha,
            now_utc=now_utc,
            dry_run=dry_run,
            publish=publish,
            min_lead_minutes=min_lead_minutes,
            default_seal_by_et=default_seal_by_et,
        )


def _build_and_seal_impl(
    root: Path | str,
    *,
    games: Sequence[Mapping[str, Any]],
    market_predictions: Sequence[Mapping[str, Any]],
    independent_predictions: Sequence[Mapping[str, Any]],
    market_inputs: Sequence[Mapping[str, Any]],
    independent_inputs: Sequence[Mapping[str, Any]],
    market_proofs: Sequence[Mapping[str, Any]],
    independent_proofs: Sequence[Mapping[str, Any]],
    odds_snapshots: Sequence[Mapping[str, Any]],
    model_version: str,
    code_sha: str,
    now_utc: datetime,
    dry_run: bool,
    publish: bool,
    min_lead_minutes: int,
    default_seal_by_et: datetime,
) -> CaptureResult:
    try:
        guards = run_builder_guards()
    except FailClosedError as exc:
        raise CaptureError(str(exc)) from exc
    refuse_credentials(dry_run=dry_run)
    refuse_publish(publish)
    base = Path(root)
    if base.exists() and any(base.iterdir()):
        raise CaptureError("capture root must be empty")
    base.mkdir(parents=True, exist_ok=True)

    failures: list[dict[str, Any]] = []
    now = now_utc if now_utc.tzinfo else now_utc.replace(tzinfo=timezone.utc)
    default_by = et_to_utc(default_seal_by_et)
    if now > default_by:
        failures.append({"reason": "late_vs_default_seal_by"})

    try:
        assert_independent_has_no_market(independent_inputs)
        assert_independent_has_no_market(independent_predictions)
        assert_independent_has_no_market(independent_proofs)
    except StreamError as exc:
        failures.append({"reason": str(exc)})

    failures.extend(
        check_stream_proofs(
            market_proofs, stream=STREAM_MARKET, min_lead_minutes=min_lead_minutes
        )
    )
    failures.extend(
        check_stream_proofs(
            independent_proofs,
            stream=STREAM_INDEPENDENT,
            min_lead_minutes=min_lead_minutes,
        )
    )

    snap_rows = [
        snapshot_record(
            game_id=str(row.get("game_id") or ""),
            book=row.get("book"),
            captured_at_utc=row.get("captured_at_utc"),
            market=row.get("market"),
            price=row.get("price"),
            source_captured_at_utc=row.get("source_captured_at_utc"),
            kickoff_utc=row.get("kickoff_utc"),
            mint_wall_clock=bool(row.get("mint_wall_clock")),
        )
        for row in odds_snapshots
    ]
    required_games = {str(g.get("game_id") or "") for g in games if g.get("game_id")}
    present_games = {
        str(r["game_id"])
        for r in snap_rows
        if r.get("status") == "PRESENT" or r.get("status") == MISSING
    }
    # A game with no snapshot row at all is FAIL (AC-8), even a MISSING row counts as recorded.
    for gid in sorted(required_games - present_games):
        failures.append({"game_id": gid, "reason": "missing_snapshot"})

    for game in games:
        kick = parse_utc(game.get("kickoff_utc"))
        if kick is None:
            failures.append({"game_id": game.get("game_id"), "reason": "missing_kickoff_utc"})
            continue
        if is_late(now, kick, min_lead_minutes=min_lead_minutes):
            failures.append({"game_id": game.get("game_id"), "reason": "late_seal"})

    market_dir = base / STREAM_MARKET
    ind_dir = base / STREAM_INDEPENDENT
    _write_jsonl(market_dir / "predictions.jsonl", market_predictions)
    _write_jsonl(market_dir / "inputs.jsonl", market_inputs)
    _write_jsonl(market_dir / "asof_proofs.jsonl", market_proofs)
    _write_jsonl(market_dir / "odds_snapshots.jsonl", snap_rows)
    _write_jsonl(ind_dir / "predictions.jsonl", independent_predictions)
    _write_jsonl(ind_dir / "inputs.jsonl", independent_inputs)
    _write_jsonl(ind_dir / "asof_proofs.jsonl", independent_proofs)

    input_shas = {
        "market_informed/inputs.jsonl": sha256_hex((market_dir / "inputs.jsonl").read_bytes()),
        "market_informed/odds_snapshots.jsonl": sha256_hex(
            (market_dir / "odds_snapshots.jsonl").read_bytes()
        ),
        "independent/inputs.jsonl": sha256_hex((ind_dir / "inputs.jsonl").read_bytes()),
    }
    pins = _pins(
        model_version=model_version,
        code_sha=code_sha,
        input_shas=input_shas,
        extra={"stream_pair": [STREAM_MARKET, STREAM_INDEPENDENT], "dry_run": dry_run},
    )
    _write_json(market_dir / "pins.json", pins)
    _write_json(
        ind_dir / "pins.json",
        {**pins, "stream": STREAM_INDEPENDENT, "market_inputs": "forbidden"},
    )

    log = open_log(base / "evidence_log.jsonl")
    ts = to_iso(now)
    append_event(log, event="STREAM_WRITE", ts_utc=ts, payload={"streams": [STREAM_MARKET, STREAM_INDEPENDENT]})
    append_event(log, event="PINS", ts_utc=ts, payload={"code_sha": code_sha, "model_version": model_version})

    status = STATUS_FAIL if failures else STATUS_SEALED
    handoff = {
        "grader": BLIND_GRADER,
        "note": "AC-9: capture builder must not grade. Outcomes are omitted.",
        "streams": [STREAM_MARKET, STREAM_INDEPENDENT],
        "code_sha": code_sha,
        "model_version": model_version,
        "outcomes": None,
        "publish": False,
    }
    _write_json(base / "blind_grade_handoff.json", handoff)
    _write_json(
        base / "manifest.json",
        {
            "status": status,
            "sealed_at_build_utc": ts,
            "official_seal_time_utc": None,
            "official_seal_rule": "custodian receipt of sha",
            "default_seal_by_et": default_seal_by_et.isoformat(),
            "min_lead_minutes": min_lead_minutes,
            "dry_run": dry_run,
            "publish": False,
            "nfl_env_overrides": guards["nfl_env_overrides"],
            "src_root": guards["src_root"],
            "fail_closed": ["F-0", "F-1", "F-2", "F-3", "F-4", "F-5", "F-6"],
        },
    )
    # Evidence log is verified by the hash chain, not SHA256SUMS, so SEAL/receipt
    # appends do not invalidate the sealed artifact checksums (AC-5 / AC-7).
    sealed_files = [
        market_dir / "predictions.jsonl",
        market_dir / "inputs.jsonl",
        market_dir / "asof_proofs.jsonl",
        market_dir / "odds_snapshots.jsonl",
        market_dir / "pins.json",
        ind_dir / "predictions.jsonl",
        ind_dir / "inputs.jsonl",
        ind_dir / "asof_proofs.jsonl",
        ind_dir / "pins.json",
        base / "blind_grade_handoff.json",
        base / "manifest.json",
    ]
    write_sha256sums(base, sealed_files)
    sums_digest = sha256_hex((base / "SHA256SUMS").read_bytes())
    append_event(
        log,
        event="FAIL" if failures else "SEAL",
        ts_utc=ts,
        payload={"sha256sums": sums_digest, "failures": failures, "official_seal_time": "pending_custodian_receipt"},
    )
    notes = [
        "Official seal time is when the custodian receives the sha (AC-1).",
        "AC-7: no edits after the seal.",
        "AC-9: grader is not the capture builder.",
        "AC-11: not published.",
    ]
    if failures:
        notes.insert(0, "AC-8: missing or late counts as FAIL.")
    return CaptureResult(
        status=status,
        root=str(base),
        sha256sums=sums_digest,
        failures=failures,
        notes=notes,
    )


def record_custodian_receipt(
    root: Path | str,
    *,
    received_sha256sums: str,
    received_at_utc: datetime,
    custodian_id: str,
    min_lead_minutes: int = MIN_LEAD_MINUTES,
    games: Optional[Sequence[Mapping[str, Any]]] = None,
) -> CaptureResult:
    """AC-1: official seal time is custodian receipt of the sha."""
    base = Path(root)
    sums = sha256_hex((base / "SHA256SUMS").read_bytes())
    failures: list[dict[str, Any]] = []
    if sums != received_sha256sums:
        failures.append({"reason": "custodian_sha_mismatch"})
    chain_err = verify_chain(open_log(base / "evidence_log.jsonl"))
    if chain_err:
        failures.append({"reason": chain_err})
    sha_err = verify_sha256sums(base)
    if sha_err:
        failures.append({"reason": sha_err})
    if games:
        recv = received_at_utc if received_at_utc.tzinfo else received_at_utc.replace(tzinfo=timezone.utc)
        for game in games:
            kick = parse_utc(game.get("kickoff_utc"))
            if kick is None:
                continue
            if is_late(recv, kick, min_lead_minutes=min_lead_minutes):
                failures.append({"game_id": game.get("game_id"), "reason": "late_custodian_receipt"})
    log = open_log(base / "evidence_log.jsonl")
    ts = to_iso(received_at_utc if received_at_utc.tzinfo else received_at_utc)
    append_event(
        log,
        event="CUSTODIAN_RECEIPT",
        ts_utc=ts,
        payload={
            "custodian_id": custodian_id,
            "received_sha256sums": received_sha256sums,
            "official_seal_time_utc": ts,
        },
    )
    status = STATUS_FAIL if failures else STATUS_OFFICIAL
    receipt = {
        "custodian_id": custodian_id,
        "official_seal_time_utc": ts,
        "received_sha256sums": received_sha256sums,
        "status": status,
    }
    _write_json(base / "custodian_receipt.json", receipt)
    return CaptureResult(
        status=status,
        root=str(base),
        sha256sums=sums,
        official_seal_time_utc=ts if not failures else None,
        failures=failures,
        notes=["Official seal time is the custodian receipt (AC-1)."],
    )


def verify_sealed_bundle(root: Path | str) -> CaptureResult:
    base = Path(root)
    failures: list[dict[str, Any]] = []
    sha_err = verify_sha256sums(base)
    if sha_err:
        failures.append({"reason": sha_err})
    chain_err = verify_chain(open_log(base / "evidence_log.jsonl"))
    if chain_err:
        failures.append({"reason": chain_err})
    if (base / STREAM_INDEPENDENT / "inputs.jsonl").is_file():
        rows = [
            json.loads(line)
            for line in (base / STREAM_INDEPENDENT / "inputs.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        try:
            assert_independent_has_no_market(rows)
        except StreamError as exc:
            failures.append({"reason": str(exc)})
    status = STATUS_FAIL if failures else (
        STATUS_OFFICIAL if (base / "custodian_receipt.json").is_file() else STATUS_SEALED
    )
    return CaptureResult(
        status=status,
        root=str(base),
        sha256sums=sha256_hex((base / "SHA256SUMS").read_bytes()) if (base / "SHA256SUMS").is_file() else "",
        failures=failures,
        notes=["verify only; no grade; no publish"],
    )


def detect_post_seal_edit(root: Path | str) -> Optional[str]:
    result = verify_sealed_bundle(root)
    if result.failures:
        return str(result.failures[0]["reason"])
    return None
