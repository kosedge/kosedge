"""t4862u D2 provenance add-only. Does not rewrite sealed v1/v2 packets."""

from __future__ import annotations

from src.services.nfl_offline_if_caller import sha256_file
from src.services.nfl_offline_if_eval_w8_v2 import V1_DIR, V2_DIR

D2 = V2_DIR.parent / "eval_w8_t4850u_v2_d2"


def test_d2_note_binds_tips_and_v2_py_diff():
    note = (D2 / "D2_PROVENANCE.md").read_text(encoding="utf-8")
    assert "6ca03716" in note
    assert "1d8b089b" in note
    assert "426bd1d9" in note
    assert "b6d019b0" in note
    assert "HEAD=426bd1d9e7d3eed4e9bf1166caa2b558862e7551" in note
    names = (D2 / "DIFF_b6d019b0_to_6ca03716.name-only.txt").read_text(encoding="utf-8")
    assert "services/model-service/src/services/nfl_offline_if_eval_w8_v2.py" in names
    assert "scripts/nfl/run_offline_if_eval_w8_t4850u_v2.py" in names
    bind = (D2 / "SCRIPT_BIND_6ca03716.json").read_text(encoding="utf-8")
    assert "d1582231a014f717bc85e8bba634410bcb70a862776b2db0b9929106948d3314" in bind
    assert "a6ccb178b5c5c136e5aae8bc5ee0d31c1fe3ebe91268b8e6b51f59a828a989a3" in bind


def test_sealed_packets_untouched_by_d2():
    for folder in (V1_DIR, V2_DIR):
        for line in (folder / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
            digest, rel = line.split("  ", 1)
            assert sha256_file(folder / rel) == digest
    stdout = (V2_DIR / "INVOKE_STDOUT.txt").read_text(encoding="utf-8")
    assert "HEAD=426bd1d9e7d3eed4e9bf1166caa2b558862e7551" in stdout
    for line in (D2 / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
        digest, rel = line.split("  ", 1)
        assert sha256_file(D2 / rel) == digest
