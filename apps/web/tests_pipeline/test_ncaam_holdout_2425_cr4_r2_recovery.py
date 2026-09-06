"""Phase 2.6F CR4 — authoritative R2 disaster recovery tests.

Mock R2 only (no credentials / no real upload). Documents real hydrate entrypoint:
  scripts/ncaam/recover_2425_sealed_holdout_from_r2.py
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

WEB_ROOT = Path(__file__).resolve().parents[1]
SRC = WEB_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ncaam_lab.holdout_2425.locked_identity import (  # noqa: E402
    LOCKED_CANONICAL_PACK_SHA256,
    LOCKED_FEATURE_CONTENT_SHA256,
    LOCKED_LABEL_CONTENT_SHA256,
    LOCKED_REJECTED_SHA256,
    SEALED_V1_1_CONTENT_FETCH_REF,
    SEALED_V1_1_CONTENT_GIT_SHA,
    locked_expected_hashes,
)
from ncaam_lab.holdout_2425.path_b_promote import (  # noqa: E402
    PromoteVerificationError,
    sha256_file,
)
from ncaam_lab.holdout_2425.path_b_r2_recovery import (  # noqa: E402
    RecoveryError,
    recover_from_r2,
)
from ncaam_lab.holdout_2425.r2_hydrate import (  # noqa: E402
    AccessRole,
    HydrateError,
    LabelVaultAccessDenied,
    MockR2Store,
    hydrate_features_objects,
    hydrate_label_vault_objects,
    seed_mock_store_from_bytes,
    sha256_bytes,
)
from ncaam_lab.holdout_2425.r2_storage_contract import (  # noqa: E402
    FEATURES_BUCKET,
    LABEL_VAULT_BUCKET,
    ROLE_STAGING_RELPATH,
)
from ncaam_lab.holdout_2425.seal_package import reseal_from_content_packages  # noqa: E402

REPO = WEB_ROOT.parent.parent

TIP_PATHS = {
    "feature_content": "data/ops/lab/ncaam/holdout_2024_25/feature_package/features.json",
    "label_content": "data/ops/lab/ncaam/holdout_2024_25/label_package/labels.json",
    "rejected": "data/ops/lab/ncaam/holdout_2024_25/rejected/rejected_events.json",
    "canonical_pack": (
        "services/model-service/src/services/ncaam_schedule/data/"
        "ncaam_official_schedule_2024_25.json"
    ),
}


def _ensure_sealed_content_commit() -> str:
    probe = subprocess.run(
        ["git", "cat-file", "-e", f"{SEALED_V1_1_CONTENT_GIT_SHA}^{{commit}}"],
        cwd=REPO,
        capture_output=True,
    )
    if probe.returncode == 0:
        return SEALED_V1_1_CONTENT_GIT_SHA
    fetched = subprocess.run(
        ["git", "fetch", "--no-tags", "origin", SEALED_V1_1_CONTENT_FETCH_REF],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    if fetched.returncode != 0:
        pytest.fail(
            "CR4 requires sealed v1.1 tip content commit "
            f"{SEALED_V1_1_CONTENT_GIT_SHA} (or fetchable {SEALED_V1_1_CONTENT_FETCH_REF}). "
            f"fetch_stderr={fetched.stderr.strip()}"
        )
    return SEALED_V1_1_CONTENT_GIT_SHA


def _git_blob(sha: str, rel: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{sha}:{rel}"], cwd=REPO)


def _materialize_locked_role_bytes(tmp_path: Path) -> dict[str, bytes]:
    """Exact frozen content + resealed manifests/seal for mock R2 seeding."""
    content_sha = _ensure_sealed_content_commit()
    role_bytes: dict[str, bytes] = {}
    work = tmp_path / "_materialize"
    feat = work / "feature_package"
    lab = work / "label_package"
    rej = work / "rejected"
    feat.mkdir(parents=True)
    lab.mkdir(parents=True)
    rej.mkdir(parents=True)

    feat_b = _git_blob(content_sha, TIP_PATHS["feature_content"])
    lab_b = _git_blob(content_sha, TIP_PATHS["label_content"])
    rej_b = _git_blob(content_sha, TIP_PATHS["rejected"])
    pack_b = _git_blob(content_sha, TIP_PATHS["canonical_pack"])

    assert hashlib.sha256(feat_b).hexdigest() == LOCKED_FEATURE_CONTENT_SHA256
    assert hashlib.sha256(lab_b).hexdigest() == LOCKED_LABEL_CONTENT_SHA256
    assert hashlib.sha256(rej_b).hexdigest() == LOCKED_REJECTED_SHA256
    assert hashlib.sha256(pack_b).hexdigest() == LOCKED_CANONICAL_PACK_SHA256

    (feat / "features.json").write_bytes(feat_b)
    (lab / "labels.json").write_bytes(lab_b)
    (rej / "rejected_events.json").write_bytes(rej_b)
    (work / "ncaam_official_schedule_2024_25.json").write_bytes(pack_b)

    seal = reseal_from_content_packages(out_root=work)
    locked = locked_expected_hashes()
    assert seal["seal_payload_sha256"] == locked["seal_payload_sha256"]
    assert seal["seal_file_sha256"] == locked["seal_file_sha256"]

    role_bytes["feature_content"] = feat_b
    role_bytes["label_content"] = lab_b
    role_bytes["rejected"] = rej_b
    role_bytes["canonical_pack"] = pack_b
    role_bytes["feature_manifest"] = (
        work / "feature_package" / "feature_manifest.json"
    ).read_bytes()
    role_bytes["label_manifest"] = (
        work / "label_package" / "label_manifest.json"
    ).read_bytes()
    role_bytes["seal_receipt"] = (work / "seal" / "seal_receipt.json").read_bytes()
    sidecar = (work / "seal" / "seal_receipt.file_sha256").read_bytes()
    role_bytes["seal_file_sidecar"] = sidecar
    return role_bytes


def _seed_store(tmp_path: Path) -> tuple[MockR2Store, list[dict]]:
    role_bytes = _materialize_locked_role_bytes(tmp_path)
    store = MockR2Store()
    inventory = seed_mock_store_from_bytes(store, role_bytes=role_bytes)
    return store, inventory


def _run_recovery(tmp_path: Path, store: MockR2Store, inventory: list, *, run_id: str, **kwargs):
    live = tmp_path / f"live_{run_id}"
    live.mkdir(parents=True)
    seal_dir = live / "seal"
    seal_dir.mkdir()
    pack = live / "pack.json"
    # Pre-existing live package that must be preserved on failure.
    prev_seal = {"holdout_id": "prev", "note": "previous-known-good"}
    (seal_dir / "seal_receipt.json").write_text(
        json.dumps(prev_seal, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (seal_dir / "seal_receipt.file_sha256").write_text("prevfilehash\n", encoding="utf-8")
    pack.write_text('{"previous": true}\n', encoding="utf-8")
    (live / "feature_package").mkdir()
    (live / "feature_package" / "features.json").write_text('{"previous": true}\n')
    (live / "label_package").mkdir()
    (live / "label_package" / "labels.json").write_text('{"previous": true}\n')

    defaults = dict(
        features_store=store,
        label_store=store,
        inventory_objects=inventory,
        live_root=live,
        live_pack_path=pack,
        live_seal_dir=seal_dir,
        staging_root=tmp_path / f"staging_{run_id}",
        access_role=AccessRole.GOVERNED_EVALUATOR,
        authorize_unseal=True,
    )
    defaults.update(kwargs)
    receipt = recover_from_r2(**defaults)
    return live, pack, seal_dir, receipt


# ---------------------------------------------------------------------------
# CR4 required cases
# ---------------------------------------------------------------------------


def test_cr4_two_identical_recoveries_byte_identical(tmp_path):
    store, inventory = _seed_store(tmp_path)
    digests = []
    for i in range(2):
        live, pack, seal_dir, receipt = _run_recovery(
            tmp_path, store, inventory, run_id=f"ident{i}"
        )
        assert receipt["status"] == "RECOVERED_VERIFIED_PROMOTED"
        assert receipt["credentials_included"] is False
        assert receipt["odds_api_calls_made"] is False
        digests.append(
            {
                "features": (live / "feature_package" / "features.json").read_bytes(),
                "labels": (live / "label_package" / "labels.json").read_bytes(),
                "rejected": (live / "rejected" / "rejected_events.json").read_bytes(),
                "pack": pack.read_bytes(),
                "feature_manifest": (
                    live / "feature_package" / "feature_manifest.json"
                ).read_bytes(),
                "label_manifest": (
                    live / "label_package" / "label_manifest.json"
                ).read_bytes(),
                "seal": (seal_dir / "seal_receipt.json").read_bytes(),
                "sidecar": (seal_dir / "seal_receipt.file_sha256").read_bytes(),
                "hashes": receipt["staging_hashes"],
            }
        )
    assert digests[0] == digests[1]


def test_cr4_restored_package_matches_every_locked_hash(tmp_path):
    store, inventory = _seed_store(tmp_path)
    live, pack, seal_dir, receipt = _run_recovery(
        tmp_path, store, inventory, run_id="locked"
    )
    assert receipt["status"] == "RECOVERED_VERIFIED_PROMOTED"
    assert receipt["staging_hashes"] == locked_expected_hashes()
    assert sha256_file(live / "feature_package" / "features.json") == LOCKED_FEATURE_CONTENT_SHA256
    assert sha256_file(live / "label_package" / "labels.json") == LOCKED_LABEL_CONTENT_SHA256
    assert sha256_file(live / "rejected" / "rejected_events.json") == LOCKED_REJECTED_SHA256
    assert sha256_file(pack) == LOCKED_CANONICAL_PACK_SHA256


def test_cr4_missing_feature_object_fails_closed(tmp_path):
    store, inventory = _seed_store(tmp_path)
    # Drop feature content from store.
    feat = next(o for o in inventory if o["role"] == "feature_content")
    del store.objects[(feat["bucket"], feat["cas_key"])]
    live = tmp_path / "live_miss_feat"
    live.mkdir()
    seal_dir = live / "seal"
    seal_dir.mkdir()
    prev = b'{"previous":"seal"}\n'
    (seal_dir / "seal_receipt.json").write_bytes(prev)
    pack = live / "pack.json"
    pack.write_bytes(b'{"previous":true}\n')
    with pytest.raises(HydrateError, match="missing object"):
        recover_from_r2(
            features_store=store,
            label_store=store,
            inventory_objects=inventory,
            live_root=live,
            live_pack_path=pack,
            live_seal_dir=seal_dir,
            staging_root=tmp_path / "st_miss_feat",
            access_role=AccessRole.GOVERNED_EVALUATOR,
            authorize_unseal=True,
        )
    assert (seal_dir / "seal_receipt.json").read_bytes() == prev
    assert pack.read_bytes() == b'{"previous":true}\n'


def test_cr4_missing_restricted_label_fails_closed_no_leak(tmp_path):
    store, inventory = _seed_store(tmp_path)
    lab = next(o for o in inventory if o["role"] == "label_content")
    # Restrict rather than delete — AccessDenied style.
    store.restrict(bucket=lab["bucket"], key=lab["cas_key"])
    live = tmp_path / "live_lab"
    live.mkdir()
    seal_dir = live / "seal"
    seal_dir.mkdir()
    prev = b'{"previous":"seal"}\n'
    (seal_dir / "seal_receipt.json").write_bytes(prev)
    pack = live / "pack.json"
    pack.write_bytes(b'{"previous":true}\n')
    with pytest.raises(HydrateError) as ei:
        recover_from_r2(
            features_store=store,
            label_store=store,
            inventory_objects=inventory,
            live_root=live,
            live_pack_path=pack,
            live_seal_dir=seal_dir,
            staging_root=tmp_path / "st_lab",
            access_role=AccessRole.GOVERNED_EVALUATOR,
            authorize_unseal=True,
        )
    err = str(ei.value)
    # Must not leak label JSON contents.
    assert "home_score" not in err
    assert "away_score" not in err
    assert "[" not in err or "role=" in err
    assert (seal_dir / "seal_receipt.json").read_bytes() == prev


def test_cr4_corrupted_object_fails_closed(tmp_path):
    store, inventory = _seed_store(tmp_path)
    feat = next(o for o in inventory if o["role"] == "feature_content")
    store.put(bucket=feat["bucket"], key=feat["cas_key"], body=b"corrupted-not-features")
    live = tmp_path / "live_corrupt"
    live.mkdir()
    seal_dir = live / "seal"
    seal_dir.mkdir()
    prev = b'{"previous":"seal"}\n'
    (seal_dir / "seal_receipt.json").write_bytes(prev)
    pack = live / "pack.json"
    pack.write_bytes(b'{"previous":true}\n')
    with pytest.raises(HydrateError, match="corrupted|mismatched"):
        recover_from_r2(
            features_store=store,
            label_store=store,
            inventory_objects=inventory,
            live_root=live,
            live_pack_path=pack,
            live_seal_dir=seal_dir,
            staging_root=tmp_path / "st_corrupt",
            access_role=AccessRole.GOVERNED_EVALUATOR,
            authorize_unseal=True,
        )
    assert (seal_dir / "seal_receipt.json").read_bytes() == prev


def test_cr4_wrong_manifest_or_seal_hash_fails_closed(tmp_path):
    store, inventory = _seed_store(tmp_path)
    # Corrupt feature manifest bytes but keep cas_key pointing at wrong body.
    fm = next(o for o in inventory if o["role"] == "feature_manifest")
    bad = b'{"content_sha256": "' + b"0" * 64 + b'"}\n'
    store.put(bucket=fm["bucket"], key=fm["cas_key"], body=bad)
    # Inventory still expects original sha — hydrate fails closed.
    live = tmp_path / "live_bad_manifest"
    live.mkdir()
    seal_dir = live / "seal"
    seal_dir.mkdir()
    prev = b'{"previous":"seal"}\n'
    (seal_dir / "seal_receipt.json").write_bytes(prev)
    pack = live / "pack.json"
    pack.write_bytes(b'{"previous":true}\n')
    with pytest.raises((HydrateError, PromoteVerificationError)):
        recover_from_r2(
            features_store=store,
            label_store=store,
            inventory_objects=inventory,
            live_root=live,
            live_pack_path=pack,
            live_seal_dir=seal_dir,
            staging_root=tmp_path / "st_bad_manifest",
            access_role=AccessRole.GOVERNED_EVALUATOR,
            authorize_unseal=True,
        )
    assert (seal_dir / "seal_receipt.json").read_bytes() == prev

    # Wrong seal hash path: mutate expected in inventory for seal after content OK.
    store2, inventory2 = _seed_store(tmp_path / "seed2")
    for obj in inventory2:
        if obj["role"] == "seal_receipt":
            obj["expected_content_sha256"] = "f" * 64
    live2 = tmp_path / "live_bad_seal"
    live2.mkdir()
    seal_dir2 = live2 / "seal"
    seal_dir2.mkdir()
    prev2 = b'{"previous":"seal2"}\n'
    (seal_dir2 / "seal_receipt.json").write_bytes(prev2)
    pack2 = live2 / "pack2.json"
    pack2.write_bytes(b'{"previous":true}\n')
    with pytest.raises((HydrateError, PromoteVerificationError)):
        recover_from_r2(
            features_store=store2,
            label_store=store2,
            inventory_objects=inventory2,
            live_root=live2,
            live_pack_path=pack2,
            live_seal_dir=seal_dir2,
            staging_root=tmp_path / "st_bad_seal",
            access_role=AccessRole.GOVERNED_EVALUATOR,
            authorize_unseal=True,
        )
    assert (seal_dir2 / "seal_receipt.json").read_bytes() == prev2


def test_cr4_interrupted_recovery_preserves_previous_package(tmp_path):
    store, inventory = _seed_store(tmp_path)
    live, pack, seal_dir, receipt = _run_recovery(
        tmp_path,
        store,
        inventory,
        run_id="interrupt",
        interrupt_after_hydrate=True,
    )
    assert receipt["status"] == "INTERRUPTED_AFTER_HYDRATE"
    assert receipt["live_package_preserved"] is True
    assert json.loads((seal_dir / "seal_receipt.json").read_text())["note"] == (
        "previous-known-good"
    )
    assert pack.read_text().startswith('{"previous"')


def test_cr4_failed_atomic_promotion_preserves_previous_package(tmp_path):
    store, inventory = _seed_store(tmp_path)
    live = tmp_path / "live_fail_promote"
    live.mkdir()
    seal_dir = live / "seal"
    seal_dir.mkdir()
    prev = b'{"note":"previous-known-good"}\n'
    (seal_dir / "seal_receipt.json").write_bytes(prev)
    (seal_dir / "seal_receipt.file_sha256").write_text("prevfilehash\n")
    pack = live / "pack.json"
    pack.write_bytes(b'{"previous":true}\n')
    with pytest.raises(RecoveryError, match="injected promote failure"):
        recover_from_r2(
            features_store=store,
            label_store=store,
            inventory_objects=inventory,
            live_root=live,
            live_pack_path=pack,
            live_seal_dir=seal_dir,
            staging_root=tmp_path / "st_fail_promote",
            access_role=AccessRole.GOVERNED_EVALUATOR,
            authorize_unseal=True,
            fail_promote=True,
        )
    assert (seal_dir / "seal_receipt.json").read_bytes() == prev
    assert pack.read_bytes() == b'{"previous":true}\n'


def test_cr4_builders_cannot_access_label_vault(tmp_path):
    store, inventory = _seed_store(tmp_path)
    staging = tmp_path / "builder_staging"
    with pytest.raises(LabelVaultAccessDenied, match="builders cannot access"):
        hydrate_label_vault_objects(
            role=AccessRole.BUILDER,
            store=store,
            staging_root=staging,
            inventory_objects=inventory,
            authorize_unseal=True,
        )
    # Even governed role without unseal auth fails closed.
    with pytest.raises(LabelVaultAccessDenied, match="authorize_unseal"):
        hydrate_label_vault_objects(
            role=AccessRole.GOVERNED_EVALUATOR,
            store=store,
            staging_root=staging,
            inventory_objects=inventory,
            authorize_unseal=False,
        )
    # Full recovery as builder preserves live and refuses.
    live = tmp_path / "live_builder"
    live.mkdir()
    seal_dir = live / "seal"
    seal_dir.mkdir()
    prev = b'{"previous":"seal"}\n'
    (seal_dir / "seal_receipt.json").write_bytes(prev)
    pack = live / "pack.json"
    pack.write_bytes(b'{"previous":true}\n')
    with pytest.raises(LabelVaultAccessDenied):
        recover_from_r2(
            features_store=store,
            label_store=store,
            inventory_objects=inventory,
            live_root=live,
            live_pack_path=pack,
            live_seal_dir=seal_dir,
            staging_root=tmp_path / "st_builder",
            access_role=AccessRole.BUILDER,
            authorize_unseal=True,
        )
    assert (seal_dir / "seal_receipt.json").read_bytes() == prev
    # Features hydrate still works for builders (no label vault).
    feat_only = [o for o in inventory if o["role"] not in ("label_content", "label_manifest")]
    receipt = hydrate_features_objects(
        store=store,
        staging_root=tmp_path / "feat_only",
        inventory_objects=feat_only,
    )
    assert receipt["label_vault_touched"] is False
    assert receipt["status"] == "HYDRATED"


def test_cr4_no_preseeded_seal_silently_reused(tmp_path):
    store, inventory = _seed_store(tmp_path)
    live, pack, seal_dir, receipt = _run_recovery(
        tmp_path, store, inventory, run_id="noseed"
    )
    assert receipt["reseal"]["preseeded_seal_silently_reused"] is False
    # Promoted seal must be resealed identity, not the previous-known-good stub.
    seal = json.loads((seal_dir / "seal_receipt.json").read_text(encoding="utf-8"))
    assert seal.get("note") != "previous-known-good"
    assert seal["seal_payload_sha256"] == locked_expected_hashes()["seal_payload_sha256"]


def test_cr4_no_odds_api_or_live_data_fallback(tmp_path):
    store, inventory = _seed_store(tmp_path)
    _, _, _, receipt = _run_recovery(tmp_path, store, inventory, run_id="noodds")
    assert receipt["odds_api_calls_made"] is False
    assert receipt["live_data_fallback"] is False
    assert receipt["forensic_raw_kenpom_odds_path"] is False
    # Source modules must not reference Odds API as recovery fallback.
    recovery_src = (
        SRC / "ncaam_lab" / "holdout_2425" / "path_b_r2_recovery.py"
    ).read_text(encoding="utf-8")
    assert "the-odds-api" not in recovery_src.lower()
    assert "ODDS_API" not in recovery_src


def test_cr4_clean_checkout_recovery_from_exact_r2_refs_mock(tmp_path):
    """Clean checkout: no pre-seeded seal; mock R2 refs → full recovery."""
    store, inventory = _seed_store(tmp_path)
    live = tmp_path / "clean"
    live.mkdir()
    # No seal dir / no pack — clean.
    pack = live / "ncaam_official_schedule_2024_25.json"
    seal_dir = live / "seal"
    assert not seal_dir.exists()
    assert not pack.exists()
    receipt = recover_from_r2(
        features_store=store,
        label_store=store,
        inventory_objects=inventory,
        live_root=live,
        live_pack_path=pack,
        live_seal_dir=seal_dir,
        staging_root=tmp_path / "st_clean",
        access_role=AccessRole.GOVERNED_EVALUATOR,
        authorize_unseal=True,
    )
    assert receipt["status"] == "RECOVERED_VERIFIED_PROMOTED"
    assert receipt["live_seal_existed_before"] is False
    assert (seal_dir / "seal_receipt.json").exists()
    assert pack.exists()
    assert sha256_file(pack) == LOCKED_CANONICAL_PACK_SHA256
    # Documented real entrypoint exists.
    assert (REPO / "scripts" / "ncaam" / "recover_2425_sealed_holdout_from_r2.py").exists()


def test_cr4_forensic_script_cannot_promote_live(tmp_path):
    import importlib.util

    path = REPO / "scripts" / "ncaam" / "forensic_rebuild_2425_from_raw_kenpom_odds.py"
    spec = importlib.util.spec_from_file_location("forensic_cr4", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    # Targeting live root must refuse.
    with pytest.raises(SystemExit, match="FORENSIC REFUSED"):
        mod.forensic_rebuild(
            out_root=Path(mod.C.OUT_ROOT),
            pack_path=tmp_path / "x.json",
            dry_run=True,
        )
    # Isolated dry-run OK.
    receipt = mod.forensic_rebuild(
        out_root=tmp_path / "forensic_out",
        pack_path=tmp_path / "forensic_out" / "pack.json",
        dry_run=True,
    )
    assert receipt["may_promote_to_live_seal"] is False
    assert receipt["may_redefine_frozen_holdout"] is False


def test_cr4_storage_contract_buckets_and_no_secrets():
    from ncaam_lab.holdout_2425.r2_storage_contract import (
        storage_contract_summary,
        default_package_inventory,
    )

    summary = storage_contract_summary()
    assert summary["features_bucket"] == FEATURES_BUCKET
    assert summary["label_vault_bucket"] == LABEL_VAULT_BUCKET
    assert summary["credentials_in_git"] is False
    assert summary["cloud_agent_upload_attempted"] is False
    inv = default_package_inventory()
    assert inv["builders_receive_label_vault_credentials"] is False
    assert inv["public_access"] == "disabled"
    assert inv["r2_dev_access"] == "disabled"
    text = json.dumps(summary) + json.dumps(inv)
    assert "AKIA" not in text
    assert "SECRET" not in text or "SECRET_ACCESS_KEY" in text  # env var *names* ok
    # Ensure no secret *values*
    assert "aws_secret_access_key\": \"" not in text.lower()
