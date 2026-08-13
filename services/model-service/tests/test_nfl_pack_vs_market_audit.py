"""Pack vs FantasyPros identity audit — smoke + classifier."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts/nfl/audit_nfl_pack_vs_market.py"


def _load():
    spec = importlib.util.spec_from_file_location("audit_nfl_pack_vs_market", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_suffix_norm_mahomes() -> None:
    mod = _load()
    assert mod._norm("Patrick Mahomes") == mod._norm("Patrick Mahomes II")
    assert mod._norm("Oronde Gadsden") == mod._norm("Oronde Gadsden II")
    assert mod._norm("Kenneth Walker III") == "kennethwalker"


def test_classify_walker_same_team_ok() -> None:
    mod = _load()
    assert (
        mod.classify("KC", "KC", 18.0, 1, "high", "kennethwalker") == "OK"
    )


def test_classify_clear_error_unique_star() -> None:
    mod = _load()
    # Walker is documented SoT KC; pack SEA vs FP KC means pack drifted.
    assert mod.classify("SEA", "KC", 18.0, 1, "high", "kennethwalker") == "CLEAR_ERROR"
    # Pack already on documented SoT, FP elsewhere → hold
    assert mod.classify("KC", "SEA", 18.0, 1, "high", "kennethwalker") == "STALE_FP"


def test_classify_weak_not_bulk_moved() -> None:
    mod = _load()
    assert mod.classify("CHI", "NYJ", 80.0, 2, "weak", "johnsmith") == "NAME_MATCH_WEAK"


def test_live_pack_audit_clean_after_walker_hotfix() -> None:
    mod = _load()
    report = mod.audit()
    assert report["smoke"]["kennethwalker"]["ok"] is True
    assert report["smoke"]["zachcharbonnet"]["ok"] is True
    assert report["smoke"]["mikeevans"]["ok"] is True
    assert report["smoke"]["emekaegbuka"]["ok"] is True
    assert report["counts"]["CLEAR_ERROR"] == 0
    assert report["counts"]["csv_vs_fp_adp150"] == 0
