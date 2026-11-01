#!/usr/bin/env python3
"""t5035u tamper / refusal guards (Alex RETURN 404a4ab2 M1).

CERT=0 · DEV_RESEARCH. No outcome comparison. No ΔMAE rewrite.
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from compare_appendix_o import LookRefuse, main  # noqa: E402
from q2s.freeze_guard import (  # noqa: E402
    SEALED_ROWS_SHA,
    FreezeGuardRefuse,
    assert_freeze_and_rows,
    sha256_file,
    verify_protocol_freeze,
    verify_rows_addendum,
)

EXECUTED_PROTOCOL_FREEZE = (
    "0bd9993a48bf305acbf1a2576e4f89ac3605169f73ec94a1bf2a6e7031b3727b"
)
EXECUTED_APPENDIX_O = (
    "be7013251a45206d5ac21da58dd35636d941d02309ddd10a3c5100b86cc0bdae"
)
EXECUTED_APPENDIX_O_MD = (
    "058b6a9c66393ed7344b1a05fc7ba44734d96948ff6d315c5f6700018b7fc44e"
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


class TestTamperPinnedFileRefuses(unittest.TestCase):
    def test_mutated_pinned_file_refuses(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pinned = root / "pins" / "note.txt"
            _write(pinned, "sealed\n")
            freeze = {
                "files": {"pins/note.txt": sha256_file(pinned)},
            }
            freeze_path = root / "artifacts" / "PROTOCOL_FREEZE.json"
            _write(freeze_path, json.dumps(freeze))
            verify_protocol_freeze(root, freeze_path)
            pinned.write_text("tampered\n")
            with self.assertRaises(FreezeGuardRefuse) as ctx:
                verify_protocol_freeze(root, freeze_path)
            self.assertIn("re-hash mismatch", str(ctx.exception))
            self.assertIn("pins/note.txt", str(ctx.exception))


class TestTamperRowsRefuses(unittest.TestCase):
    def test_mutated_rows_refuses(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rows = root / "artifacts" / "q2s_rows_t5033u.json"
            rows.parent.mkdir(parents=True, exist_ok=True)
            # Bind the sealed live rows bytes, then mutate the copy.
            shutil.copy2(ROOT / "artifacts" / "q2s_rows_t5033u.json", rows)
            self.assertEqual(sha256_file(rows), SEALED_ROWS_SHA)
            addendum = {
                "emitted_rows": {
                    "path": "artifacts/q2s_rows_t5033u.json",
                    "sha256": SEALED_ROWS_SHA,
                }
            }
            addendum_path = root / "artifacts" / "FREEZE_ADDENDUM.json"
            _write(addendum_path, json.dumps(addendum))
            verify_rows_addendum(root, addendum_path, rows)
            payload = json.loads(rows.read_text())
            payload["n_emitted"] = 69
            rows.write_text(json.dumps(payload))
            with self.assertRaises(FreezeGuardRefuse) as ctx:
                verify_rows_addendum(root, addendum_path, rows)
            self.assertIn("q2s rows sha", str(ctx.exception))
            self.assertNotEqual(sha256_file(rows), SEALED_ROWS_SHA)


class TestAlreadyConsumedLookRefuses(unittest.TestCase):
    def test_already_consumed_look_refuses(self) -> None:
        self.assertTrue((ROOT / "artifacts" / "LOOK_CONSUMED.json").exists())
        self.assertTrue((ROOT / "artifacts" / "APPENDIX_O.json").exists())
        with self.assertRaises(LookRefuse) as ctx:
            main()
        self.assertIn("already consumed", str(ctx.exception))


class TestLivePinsPreserved(unittest.TestCase):
    def test_live_rows_still_0d6a5e14(self) -> None:
        rows = ROOT / "artifacts" / "q2s_rows_t5033u.json"
        self.assertTrue(sha256_file(rows).startswith("0d6a5e14"))
        self.assertEqual(sha256_file(rows), SEALED_ROWS_SHA)

    def test_executed_freeze_and_appendix_o_bytes_untouched(self) -> None:
        self.assertEqual(
            sha256_file(ROOT / "artifacts" / "PROTOCOL_FREEZE.json"),
            EXECUTED_PROTOCOL_FREEZE,
        )
        self.assertEqual(
            sha256_file(ROOT / "artifacts" / "APPENDIX_O.json"),
            EXECUTED_APPENDIX_O,
        )
        self.assertEqual(
            sha256_file(ROOT / "APPENDIX_O_COMPARISON.md"),
            EXECUTED_APPENDIX_O_MD,
        )

    def test_live_rehash_green_with_addendum(self) -> None:
        addendum = assert_freeze_and_rows(ROOT)
        self.assertEqual(addendum["emitted_rows"]["sha256"], SEALED_ROWS_SHA)
        self.assertFalse(addendum.get("rewrote_protocol_freeze"))
        self.assertFalse(addendum.get("second_look"))


if __name__ == "__main__":
    unittest.main()
