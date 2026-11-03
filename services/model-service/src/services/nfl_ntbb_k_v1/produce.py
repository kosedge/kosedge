"""Produce SYNTHETIC NTBB-K kernel metadata. CERT=0. No fit. No SciPy."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from src.services.nfl_ntbb_k_v1.cases import run_root_nine
from src.services.nfl_ntbb_k_v1.constants import (
    ALEX_PASS_SPEC,
    CERT,
    CHANNEL,
    CLEAR,
    DATA_LABEL,
    EVIDENCE_ID,
    FAMILY,
    METADATA_14083,
    METADATA_TICKET,
    NO_INSTALL,
    ORACLE_MAX_ENUMERATED_TOTAL,
    OUTPUT_LABEL,
    OWNER,
    PACKAGE,
    PIN_JSONL_143_PROJECTION_SHA256,
    PIN_LEDGER_81759_SHA256,
    PIN_LEDGER_92861_SHA256,
    PROFILE,
    QUALIFICATION,
    SCIPY_FITTING_ALGORITHM,
    SCIPY_STATUS,
    SPEC_BYTES,
    SPEC_COMMIT,
    SPEC_PATH,
    SPEC_SHA256,
    TICKET,
    WORKER,
)
from src.services.nfl_ntbb_k_v1.refuse import NtbbKRefuse
from src.services.nfl_ntbb_k_v1.table import (
    enumerate_joint,
    refuse_unknown_settlement,
    summarize_spread,
    summarize_total,
)

OPS_REL = Path("data/ops/nfl_ntbb_k_v1")


def _sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _write_atomic(path: Path, payload: Any) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    raw = text.encode("utf-8")
    fd, tmp = tempfile.mkstemp(prefix="ntbbk_", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(raw)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
    readback = path.read_bytes()
    if readback != raw:
        raise NtbbKRefuse("atomic readback mismatch")
    return _sha256_bytes(readback)


def verify_spec_blob(repo_root: Path) -> dict[str, Any]:
    import subprocess

    proc = subprocess.run(
        ["git", "-C", str(repo_root), "show", f"{SPEC_COMMIT}:{SPEC_PATH}"],
        check=False,
        capture_output=True,
    )
    if proc.returncode != 0:
        raise NtbbKRefuse(f"git show {SPEC_COMMIT}:{SPEC_PATH} failed")
    digest = _sha256_bytes(proc.stdout)
    if digest != SPEC_SHA256:
        raise NtbbKRefuse(f"spec sha256 {digest} != {SPEC_SHA256}")
    if len(proc.stdout) != SPEC_BYTES:
        raise NtbbKRefuse(f"spec bytes {len(proc.stdout)} != {SPEC_BYTES}")
    return {
        "bytes": SPEC_BYTES,
        "commit": SPEC_COMMIT,
        "path": SPEC_PATH,
        "sha256": digest,
        "sha256_match": True,
    }


def verify_market_partial_preserved(repo_root: Path) -> dict[str, Any]:
    proj = repo_root / "data/ops/nfl_owned_market_v1/codex_staged/JSONL_SELECTED_143_SOURCE_VALUE_PROJECTION.json"
    led92861 = repo_root / "data/ops/nfl_owned_market_v1/CLOCK_LINEAGE_LEDGER_92861.json"
    led81759 = repo_root / "data/ops/nfl_owned_market_v1/CLOCK_LINEAGE_LEDGER_81759.json"
    rows = {
        "jsonl_143": _sha256_bytes(proj.read_bytes()),
        "ledger_92861": _sha256_bytes(led92861.read_bytes()),
        "ledger_81759": _sha256_bytes(led81759.read_bytes()),
    }
    if rows["jsonl_143"] != PIN_JSONL_143_PROJECTION_SHA256:
        raise NtbbKRefuse("143 projection sha drifted")
    if rows["ledger_92861"] != PIN_LEDGER_92861_SHA256:
        raise NtbbKRefuse("92861 ledger sha drifted")
    if rows["ledger_81759"] != PIN_LEDGER_81759_SHA256:
        raise NtbbKRefuse("81759 ledger sha drifted")
    doc = json.loads(proj.read_text())
    clock_false = all(r.get("clock_semantics_verified") is False for r in doc.get("rows") or [])
    return {
        "clocks_status": "SOURCE_VALUE_MATCH_NOT_VERIFIED",
        "clock_semantics_verified_any": not clock_false,
        "preserved": True,
        "sha256": rows,
    }


def build_kernel_document(repo_root: Path) -> dict[str, Any]:
    spec = verify_spec_blob(repo_root)
    market = verify_market_partial_preserved(repo_root)
    nine = run_root_nine()
    demo = enumerate_joint(mu=8.0, r=20.0, p=0.5, c=12.0, k0=0.0, k3=0.0, k7=0.0)
    spread = summarize_spread(demo, "-3")
    total = summarize_total(demo, "44.5")
    return {
        "cert": CERT,
        "channel": CHANNEL,
        "clocks_143": "SOURCE_VALUE_MATCH_NOT_VERIFIED",
        "data_label": DATA_LABEL,
        "demo_summaries": {"spread": spread, "total": total},
        "evidence_id": EVIDENCE_ID,
        "family": FAMILY,
        "fitting_algorithm": SCIPY_FITTING_ALGORITHM,
        "historical_economic_calculation": False,
        "kernel_implemented": True,
        "market_partial_preserved": market,
        "metadata_14083": METADATA_14083,
        "metadata_ticket": METADATA_TICKET,
        "no_install": NO_INSTALL,
        "oracle_max_enumerated_total": ORACLE_MAX_ENUMERATED_TOTAL,
        "owned_completion_claimed": False,
        "owner": OWNER,
        "package": PACKAGE,
        "pass_spec": ALEX_PASS_SPEC,
        "profile": PROFILE,
        "qualification": QUALIFICATION,
        "root_nine": {
            "max_enumerated_total": nine["max_enumerated_total"],
            "n_cases": nine["n_cases"],
            "oracle_max_enumerated_total": nine["oracle_max_enumerated_total"],
            "results": [
                {k: v for k, v in row.items() if k != "extras"}
                | {"extras": {ek: ev for ek, ev in row["extras"].items() if ek != "log_pmf_00"}}
                for row in nine["results"]
            ],
            "status": nine["status"],
        },
        "scientific_hold": [
            "no outcomes",
            "no forecast",
            "no fit",
            "no historical ATS/ROI",
            "SciPy fitting algorithm unexecuted / dependency-held",
            "143 clocks remain SOURCE_VALUE_MATCH not verified",
        ],
        "scipy_status": SCIPY_STATUS,
        "spec": spec,
        "ticket": TICKET,
        "use_label": OUTPUT_LABEL,
        "worker": WORKER,
    }


def produce_kernel(*, repo_root: Path | None = None) -> dict[str, Any]:
    root = Path(repo_root) if repo_root is not None else Path.cwd()
    # walk to git root if needed
    here = root
    for path in (here, *here.parents):
        if (path / ".git").exists():
            root = path
            break
    doc = build_kernel_document(root)
    out = root / OPS_REL / "KERNEL_SYNTHETIC_92861.json"
    sha = _write_atomic(out, doc)
    receipt = {
        "cert": CERT,
        "clear": CLEAR,
        "clocks_143": "SOURCE_VALUE_MATCH_NOT_VERIFIED",
        "fitting_algorithm": SCIPY_FITTING_ALGORITHM,
        "kernel_implemented": True,
        "kernel_sha256": sha,
        "max_enumerated_total": doc["root_nine"]["max_enumerated_total"],
        "metadata_14083": METADATA_14083,
        "oracle_max_enumerated_total": ORACLE_MAX_ENUMERATED_TOTAL,
        "owned_completion_claimed": False,
        "path": str(out.relative_to(root)),
        "root_nine_status": doc["root_nine"]["status"],
        "scipy_status": SCIPY_STATUS,
        "spec_sha256_match": doc["spec"]["sha256_match"],
        "ticket": TICKET,
    }
    rec_path = root / OPS_REL / "receipt.json"
    rec_sha = _write_atomic(rec_path, receipt)
    return {
        "document": doc,
        "path": str(out.relative_to(root)),
        "receipt_path": str(rec_path.relative_to(root)),
        "receipt_sha256": rec_sha,
        "sha256": sha,
    }


def refuse_settled_if_unknown() -> None:
    refuse_unknown_settlement(period=None)
