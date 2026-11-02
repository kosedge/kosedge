"""t5155u N1 — pytest elapsed timing is non-semantic for output_sha256."""

from __future__ import annotations

from pathlib import Path

from src.services.nfl_t5107u.eval_result_contract import (
    PROFILE_DEV_IF437,
    PROFILE_DEV_MARKET72,
    PROFILE_FEATURE_RECON_REG496,
)
from src.services.nfl_t5107u.verify_integrate import (
    B1_UNIVERSE_PATH,
    DEV437_RESULT_PATH,
    build_receipt,
    hash_file_list,
    semantic_tests_payload,
    strip_pytest_elapsed,
)

ROOT = Path(__file__).resolve().parents[3]


def _profiles() -> dict:
    return {
        PROFILE_FEATURE_RECON_REG496: {
            "ok": True,
            "feature_gate": {"identity_sha256": "aa"},
            "numerical": {"joined_row_sha256": "bb", "n": 496},
        },
        PROFILE_DEV_IF437: {
            "ok": True,
            "feature_gate": {"identity_sha256": "cc"},
            "numerical": {"joined_row_sha256": "dd", "n": 437},
        },
        PROFILE_DEV_MARKET72: {
            "ok": True,
            "feature_gate": {"identity_sha256": "ee"},
            "numerical": {"joined_row_sha256": "ff", "n": 72},
        },
    }


def _timed(elapsed: str) -> dict:
    return {
        "ok": True,
        "commands": [
            {
                "command": "python -m pytest services/model-service/tests/test_nfl_t5151u_verify_integrate.py -q --tb=line",
                "ok": True,
                "returncode": 0,
                "stdout_tail": f"..................                                                       [100%]\n18 passed in {elapsed}",
                "stderr_tail": "",
            }
        ],
        "tests": ["services/model-service/tests/test_nfl_t5151u_verify_integrate.py"],
    }


def test_strip_pytest_elapsed_keeps_count():
    assert strip_pytest_elapsed("18 passed in 4.86s") == "18 passed"
    assert strip_pytest_elapsed("8 passed in 21.95s") == "8 passed"
    assert "in 4.86s" not in semantic_tests_payload(_timed("4.86s"))["commands"][0]["stdout_tail"]


def test_output_hash_excludes_pytest_elapsed_timing():
    one = build_receipt(
        root=ROOT,
        pins={"ok": True, "checks": [], "errors": []},
        profiles=_profiles(),
        tests=_timed("2.07s"),
        errors=[],
        interpreter="/abs/venv-one/bin/python",
    )
    two = build_receipt(
        root=ROOT,
        pins={"ok": True, "checks": [], "errors": []},
        profiles=_profiles(),
        tests=_timed("21.95s"),
        errors=[],
        interpreter="/other/root/bin/python",
    )
    assert one["hashes"]["output_sha256"] == two["hashes"]["output_sha256"]
    assert one["side_metadata"]["pytest_elapsed"] == ["2.07"]
    assert two["side_metadata"]["pytest_elapsed"] == ["21.95"]
    assert one["runtime"]["pytest_elapsed"] != two["runtime"]["pytest_elapsed"]
    assert "in 2.07s" not in one["tests"]["commands"][0]["stdout_tail"]
    assert "in 21.95s" not in two["tests"]["commands"][0]["stdout_tail"]
    assert one["alex_return_sha8"] == "7057e5a9"
    assert one["closed_700_tip"].startswith("12ccc482")


def test_output_hash_stable_across_rerun_and_cross_root(tmp_path):
    tests = _timed("3.14s")
    root_a = tmp_path / "a"
    root_b = tmp_path / "b"
    rel = "data/ops/pin.txt"
    for root in (root_a, root_b):
        dest = root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text("same-bytes\n", encoding="utf-8")
    hashed_a = hash_file_list(root_a, [root_a / rel])
    hashed_b = hash_file_list(root_b, [root_b / rel])
    assert hashed_a["sha256"] == hashed_b["sha256"]
    first = build_receipt(
        root=ROOT, pins={"ok": True, "checks": [], "errors": []}, profiles=_profiles(), tests=tests, errors=[]
    )
    second = build_receipt(
        root=ROOT,
        pins={"ok": True, "checks": [], "errors": []},
        profiles=_profiles(),
        tests=_timed("9.99s"),
        errors=[],
    )
    assert first["hashes"]["output_sha256"] == second["hashes"]["output_sha256"]
    input_paths = [row["path"] for row in first["hashes"]["input"]["files"]]
    assert B1_UNIVERSE_PATH in input_paths
    assert DEV437_RESULT_PATH in input_paths
