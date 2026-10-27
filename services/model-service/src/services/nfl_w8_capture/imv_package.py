"""Build a custodian-ready IMV inventory. Not a seal-ack."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Sequence

from src.services.nfl_w8_capture.hold import refuse_odds_fetch
from src.services.nfl_w8_capture.store import BundleStore
from src.services.nfl_w8_capture.streams import refuse_seal

REPO_RELATIVE_INVENTORY = (
    "services/model-service/src/services/nfl_w8_capture/__init__.py",
    "services/model-service/src/services/nfl_w8_capture/alerts.py",
    "services/model-service/src/services/nfl_w8_capture/archive.py",
    "services/model-service/src/services/nfl_w8_capture/books.py",
    "services/model-service/src/services/nfl_w8_capture/cadence.py",
    "services/model-service/src/services/nfl_w8_capture/carveouts.py",
    "services/model-service/src/services/nfl_w8_capture/close.py",
    "services/model-service/src/services/nfl_w8_capture/credits.py",
    "services/model-service/src/services/nfl_w8_capture/fetch.py",
    "services/model-service/src/services/nfl_w8_capture/evidence.py",
    "services/model-service/src/services/nfl_w8_capture/fixture_load.py",
    "services/model-service/src/services/nfl_w8_capture/fixtures/synthetic_w8_reg_game.json",
    "services/model-service/src/services/nfl_w8_capture/hold.py",
    "services/model-service/src/services/nfl_w8_capture/http_transport.py",
    "services/model-service/src/services/nfl_w8_capture/imv_package.py",
    "services/model-service/src/services/nfl_w8_capture/oneshot.py",
    "services/model-service/src/services/nfl_w8_capture/__main__.py",
    "services/model-service/src/services/nfl_w8_capture/pin.py",
    "services/model-service/src/services/nfl_w8_capture/redact.py",
    "services/model-service/src/services/nfl_w8_capture/restore.py",
    "services/model-service/src/services/nfl_w8_capture/seal.py",
    "services/model-service/src/services/nfl_w8_capture/snapshots.py",
    "services/model-service/src/services/nfl_w8_capture/store.py",
    "services/model-service/src/services/nfl_w8_capture/streams.py",
    "services/model-service/src/services/nfl_w8_capture/tick.py",
    "services/model-service/src/services/nfl_w8_capture/timestamps.py",
    "services/model-service/tests/test_nfl_w8_capture.py",
    "services/model-service/src/celerybeat_schedule.py",
    "services/model-service/src/celery_app.py",
    ".github/workflows/pr-check.yml",
    "data/ops/nfl-w8-prospective-capture-spec-to-code-t4445u.md",
    "data/ops/nfl-w8-t4520u-t4523u-t0-reserve-reconcile.md",
    "scripts/ci/run-nfl-w8-capture-tests.sh",
)

HARD_STOPS = (
    "refuse_odds_fetch default ON. R1: NFL_W8_H1_AUTH_CITE=89fdd45f PLUS KEEP fields. R2: CREDENTIAL_POLICY=KEEP_EXISTING KEEP_AUTH_SHA8=a9ae5ae6 VERIFY_PASS_SHA8=e64e73ac H1C_AUTH_SHA8=89fdd45f T4500U_SHA8=20325274 ROTATION_ASSERTED=false. R3: rotate-confirm FAIL CLOSED. R4: process-scoped only. R7: paper ACCEPT ≠ live GO. Tick never fetches.",
    "refuse_seal ALWAYS raises (AC-12). Cursor cannot seal-ack. produce_seal is AC-1/AC-2 only. Custodian receipt required for AC-2.",
    "Draft only. No merge. No deploy. Coming Soon ON. NFL NO-GO stays.",
    "Production NFL_ODDS_API_CARRIED_BOOKMAKERS is not edited.",
    "Synthetic argv: cd services/model-service && PYTHONPATH=. NFL_W8_H1_AUTH_CITE=89fdd45f CREDENTIAL_POLICY=KEEP_EXISTING KEEP_AUTH_SHA8=a9ae5ae6 VERIFY_PASS_SHA8=e64e73ac H1C_AUTH_SHA8=89fdd45f T4500U_SHA8=20325274 ROTATION_ASSERTED=false python3 -m src.services.nfl_w8_capture --synthetic --bundle-dir /tmp/nfl-w8-synthetic-demo",
)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inventory_rows(
    repo_root: str | Path,
    paths: Sequence[str] = REPO_RELATIVE_INVENTORY,
) -> list[tuple[str, str]]:
    root = Path(repo_root)
    rows: list[tuple[str, str]] = []
    for rel in paths:
        path = root / rel
        if not path.is_file():
            raise FileNotFoundError(rel)
        rows.append((_sha256_file(path), rel))
    return rows


def prove_hard_stops() -> dict[str, str]:
    odds = "ok"
    seal = "ok"
    try:
        refuse_odds_fetch()
        odds = "FAILED_TO_RAISE"
    except Exception as exc:  # noqa: BLE001 — proof only
        odds = type(exc).__name__
    try:
        refuse_seal([])
        seal = "FAILED_TO_RAISE"
    except Exception as exc:  # noqa: BLE001 — proof only
        seal = type(exc).__name__
    if odds == "FAILED_TO_RAISE" or seal == "FAILED_TO_RAISE":
        raise RuntimeError(f"hard stops not intact odds={odds} seal={seal}")
    return {"refuse_odds_fetch": odds, "refuse_seal": seal}


def write_imv_package(
    repo_root: str | Path,
    dest: str | Path,
    *,
    tip_sha: str = "",
    actor: str = "nfl_w8_capture",
) -> dict[str, object]:
    """Write FILELIST + SHA256SUMS + hard-stop proof. Does not seal-ack."""
    hard = prove_hard_stops()
    rows = inventory_rows(repo_root)
    store = BundleStore(dest)
    filelist = "".join(f"{rel}\n" for _, rel in rows)
    sums = "".join(f"{sha}  {rel}\n" for sha, rel in rows)
    store.write_new_file("FILELIST.txt", filelist.encode("utf-8"), actor=actor, note="imv-filelist")
    store.write_new_file(
        "INVENTORY.SHA256SUMS",
        sums.encode("utf-8"),
        actor=actor,
        note="imv-inventory-sha256sums",
    )
    proof = {
        "package": "nfl-w8-imv-package-t4450u",
        "authority": "Ryan t4450u",
        "decision_sha8": "20ea635f",
        "tip_sha": tip_sha,
        "seal_ack": "CURSOR_CANNOT_SEAL_ACK",
        "odds_api_hold": True,
        "nfl_no_go": True,
        "coming_soon": True,
        "hard_stops": list(HARD_STOPS),
        "hard_stop_proof": hard,
        "file_count": len(rows),
    }
    store.write_new_file(
        "HARD_STOPS.json",
        (json.dumps(proof, indent=2, sort_keys=True) + "\n").encode("utf-8"),
        actor=actor,
        note="imv-hard-stops",
    )
    store.verify()
    return {
        "dest": str(Path(dest)),
        "file_count": len(rows),
        "hard_stop_proof": hard,
        "seal_ack": "CURSOR_CANNOT_SEAL_ACK",
        "head_sha": store.verify()["head_sha"],
    }
