"""bash-3.2 builder pin. Synthetic only. No Mac / no parity evidence."""

from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
IMV = ROOT / "scripts" / "nfl" / "imv"
import sys

sys.path.insert(0, str(IMV))

import nfl_imv_v26 as v26  # noqa: E402
import nfl_imv_v27 as v27  # noqa: E402


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_v26_frozen() -> None:
    assert _sha(IMV / "nfl_imv_v26.py") == v27.V26_PIN
    assert _sha(IMV / "nfl-imv-feature-build-v2.4.sh") == v26.SHELL_PINS["nfl-imv-feature-build-v2.4.sh"]


def test_builder_241_safe_expansion() -> None:
    text = (IMV / "nfl-imv-feature-build-v2.4.1.sh").read_text(encoding="utf-8")
    assert '${PACK_ARG[@]+"${PACK_ARG[@]}"}' in text
    assert text.count('"${PACK_ARG[@]}"') == text.count('${PACK_ARG[@]+"${PACK_ARG[@]}"}')
    assert _sha(IMV / "nfl-imv-feature-build-v2.4.1.sh") == v27.BUILD_241_PIN


def test_check_pins_includes_241() -> None:
    rec = v27.stamp_helper_shas(IMV, sums_v25=IMV / "SHA256SUMS.v2.5")
    assert rec["ok"] is True
    assert rec["shell_pins"]["nfl-imv-feature-build-v2.4.1.sh"] == v27.BUILD_241_PIN
    assert rec["shells"]["nfl-imv-feature-build-v2.4.1.sh"] == v27.BUILD_241_PIN
    assert rec["v26"] == v27.V26_PIN
