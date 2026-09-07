"""Phase 2.6F CR7 — real consumer wiring after clean Path B recovery.

Recover from a clean checkout (mock R2), then invoke **actual consumer
entrypoints** — not ``resolve_live_artifacts()`` alone — and prove they all
read locked hashes from one CURRENT release. Official schedule loader must
return the restored 2024–25 package.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

WEB_ROOT = Path(__file__).resolve().parents[1]
SRC = WEB_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ncaam_lab.holdout_2425.active_release import (  # noqa: E402
    ActiveReleaseError,
    load_canonical_pack,
    load_evaluator_inputs,
    load_feature_content,
    load_label_content,
    load_rejected_events,
    load_seal_receipt,
)
from ncaam_lab.holdout_2425.locked_identity import (  # noqa: E402
    LOCKED_CANONICAL_PACK_SHA256,
    LOCKED_FEATURE_CONTENT_SHA256,
    LOCKED_FEATURE_MANIFEST_SHA256,
    LOCKED_LABEL_CONTENT_SHA256,
    LOCKED_LABEL_MANIFEST_SHA256,
    LOCKED_REJECTED_SHA256,
    locked_expected_hashes,
)
from ncaam_lab.holdout_2425.path_b_promote import (  # noqa: E402
    resolve_current_release,
    sha256_file,
)
from ncaam_lab.holdout_2425.path_b_r2_recovery import recover_from_r2  # noqa: E402
from ncaam_lab.holdout_2425.r2_hydrate import AccessRole  # noqa: E402
from ncaam_lab.holdout_2425.seal_package import reseal_from_content_packages  # noqa: E402

# Reuse CR4 tip materialization helpers.
from test_ncaam_holdout_2425_cr4_r2_recovery import _seed_store  # noqa: E402

REPO = WEB_ROOT.parent.parent


def _load_script(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _clean_recover(tmp_path: Path):
    store, inventory = _seed_store(tmp_path)
    live = tmp_path / "clean_live"
    live.mkdir()
    # Declared flat pack path (model-service-shaped) — intentionally absent.
    pack = live / "ncaam_official_schedule_2024_25.json"
    seal_dir = live / "seal"
    assert not pack.exists()
    assert not seal_dir.exists()
    receipt = recover_from_r2(
        features_store=store,
        label_store=store,
        inventory_objects=inventory,
        live_root=live,
        live_pack_path=pack,
        live_seal_dir=seal_dir,
        staging_root=tmp_path / "st_cr7_clean",
        access_role=AccessRole.GOVERNED_EVALUATOR,
        authorize_unseal=True,
    )
    assert receipt["status"] == "RECOVERED_VERIFIED_PROMOTED"
    assert resolve_current_release(live) is not None
    # Dual-reality bug shape: CURRENT pack present; declared flat pack absent.
    assert not pack.exists()
    release = resolve_current_release(live)
    assert release is not None
    assert (release / pack.name).exists()
    assert not (live / "feature_package" / "features.json").exists()
    assert (release / "feature_package" / "features.json").exists()
    return live, pack, seal_dir, receipt


def test_cr7_verifier_fails_when_authoritative_pack_unavailable(tmp_path):
    """Verifier must FAIL — not pass with a note — when pack is missing."""
    live = tmp_path / "no_pack"
    live.mkdir()
    # CURRENT pointing at empty release (pack absent).
    release = live / "releases" / "r-empty"
    release.mkdir(parents=True)
    (live / "CURRENT").symlink_to(release)
    verify_mod = _load_script(
        "verify_cr7_fail",
        REPO / "scripts" / "ncaam" / "verify_2425_sealed_artifacts.py",
    )
    result = verify_mod.verify(live_root=live)
    assert result["ok"] is False
    assert any("canonical pack unavailable" in e for e in result["errors"])


def test_cr7_clean_recovery_real_consumers_one_release(tmp_path, monkeypatch):
    live, pack, seal_dir, receipt = _clean_recover(tmp_path)
    release = resolve_current_release(live)
    assert release is not None
    locked = locked_expected_hashes()

    # Point active_release defaults at the recovered live root.
    import ncaam_lab.holdout_2425.constants as constants

    monkeypatch.setattr(constants, "OUT_ROOT", live)
    monkeypatch.setattr(constants, "FEATURE_DIR", live / "feature_package")
    monkeypatch.setattr(constants, "LABEL_DIR", live / "label_package")
    monkeypatch.setattr(constants, "SEAL_DIR", seal_dir)
    monkeypatch.setattr(constants, "REJECTED_DIR", live / "rejected")
    monkeypatch.setattr(constants, "CANONICAL_PACK_PATH", pack)

    # --- Shared API consumers ---
    feat = load_feature_content()
    lab = load_label_content()
    rej = load_rejected_events()
    seal = load_seal_receipt()
    canon = load_canonical_pack()
    assert isinstance(feat, list) and len(feat) > 0
    assert isinstance(lab, list) and len(lab) > 0
    assert isinstance(rej, list)
    assert isinstance(canon, dict) and len(canon.get("games") or []) > 0
    assert sha256_file(release / "feature_package" / "features.json") == (
        LOCKED_FEATURE_CONTENT_SHA256
    )
    assert sha256_file(release / pack.name) == LOCKED_CANONICAL_PACK_SHA256
    assert seal["seal_payload_sha256"] == locked["seal_payload_sha256"]
    assert sha256_file(release / "seal" / "seal_receipt.json") == locked[
        "seal_file_sha256"
    ]
    assert sha256_file(release / "feature_package" / "feature_manifest.json") == (
        LOCKED_FEATURE_MANIFEST_SHA256
    )
    assert sha256_file(release / "label_package" / "label_manifest.json") == (
        LOCKED_LABEL_MANIFEST_SHA256
    )
    assert sha256_file(release / "label_package" / "labels.json") == (
        LOCKED_LABEL_CONTENT_SHA256
    )
    assert sha256_file(release / "rejected" / "rejected_events.json") == (
        LOCKED_REJECTED_SHA256
    )

    ev = load_evaluator_inputs()
    assert ev["current_set"] is True
    assert Path(ev["release_dir"]).resolve() == release.resolve()
    assert ev["sha256"]["feature_content"] == LOCKED_FEATURE_CONTENT_SHA256
    assert ev["sha256"]["pack_path"] == LOCKED_CANONICAL_PACK_SHA256
    assert ev["scoring_authorized"] is False

    # --- Actual verifier entrypoint ---
    verify_mod = _load_script(
        "verify_cr7_ok",
        REPO / "scripts" / "ncaam" / "verify_2425_sealed_artifacts.py",
    )
    result = verify_mod.verify(live_root=live)
    assert result["ok"] is True, result.get("errors")
    assert result["seal"]["canonical_pack_sha256"] == LOCKED_CANONICAL_PACK_SHA256
    assert result["seal"]["current_set"] is True
    assert result["authority"] == "active_release_CURRENT"

    # Flat declared pack still absent — consumers must not need it.
    assert not pack.exists()
    assert not constants.CANONICAL_PACK_PATH.exists()

    # --- Model-service schedule loader is a holdout consumer ---
    sched_path = (
        REPO
        / "services"
        / "model-service"
        / "src"
        / "services"
        / "ncaam_schedule"
        / "official_schedule.py"
    )
    sched = _load_script("ncaam_official_schedule_cr7", sched_path)
    monkeypatch.setattr(sched, "_holdout_live_root", lambda: live)
    blob = sched.load_official_schedule_blob("2024-25")
    assert blob["present"] is True
    assert blob.get("authority") == "holdout_CURRENT_release"
    assert blob.get("active_release_current_set") is True
    assert len(blob.get("games") or []) > 0
    assert Path(blob["resolved_path"]).resolve() == (release / pack.name).resolve()
    assert (
        hashlib.sha256(Path(blob["resolved_path"]).read_bytes()).hexdigest()
        == LOCKED_CANONICAL_PACK_SHA256
    )
    # Static DATA_DIR pack remains absent / non-authoritative.
    static = sched.DATA_DIR / "ncaam_official_schedule_2024_25.json"
    assert not static.exists() or static.resolve() != Path(blob["resolved_path"]).resolve()


def test_cr7_ci_flat_forbid_script_passes():
    script = REPO / "scripts" / "ncaam" / "check_active_release_flat_forbid.py"
    proc = subprocess.run(
        [sys.executable, str(script)],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout


def test_cr7_reseal_refuses_default_flat_when_current_set(tmp_path, monkeypatch):
    live, pack, seal_dir, _ = _clean_recover(tmp_path)
    import ncaam_lab.holdout_2425.constants as constants

    monkeypatch.setattr(constants, "OUT_ROOT", live)
    monkeypatch.setattr(constants, "FEATURE_DIR", live / "feature_package")
    monkeypatch.setattr(constants, "LABEL_DIR", live / "label_package")
    monkeypatch.setattr(constants, "SEAL_DIR", seal_dir)
    monkeypatch.setattr(constants, "REJECTED_DIR", live / "rejected")
    with pytest.raises(ActiveReleaseError, match="CURRENT is set"):
        reseal_from_content_packages()
