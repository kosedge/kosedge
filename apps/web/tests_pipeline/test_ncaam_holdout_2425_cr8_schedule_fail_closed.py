"""Phase 2.6F CR8 — fail-closed schedule loader when CURRENT is set.

When CURRENT exists, the model-service official schedule loader must resolve
only CURRENT/<canonical-pack>. A missing active-release pack or a broken
CURRENT symlink must return present=false with zero games — never the stale
static DATA_DIR pack.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

WEB_ROOT = Path(__file__).resolve().parents[1]
REPO = WEB_ROOT.parent.parent

STALE_STATIC_BLOB = {
    "season": "2024-25",
    "season_end_year": 2025,
    "official": True,
    "source": "stale_static_should_not_load",
    "slate_complete": False,
    "games": [
        {
            "game_id": "stale-401",
            "espn_game_id": "stale-401",
            "tipoff": "2024-11-12T00:00Z",
            "date": "2024-11-12",
            "home": "duke",
            "away": "north carolina",
            "map_status": "b7_both",
        }
    ],
}


def _load_script(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_schedule_mod():
    sched_path = (
        REPO
        / "services"
        / "model-service"
        / "src"
        / "services"
        / "ncaam_schedule"
        / "official_schedule.py"
    )
    return _load_script("ncaam_official_schedule_cr8", sched_path)


def _seed_stale_static(data_dir: Path) -> Path:
    data_dir.mkdir(parents=True, exist_ok=True)
    stale = data_dir / "ncaam_official_schedule_2024_25.json"
    stale.write_text(json.dumps(STALE_STATIC_BLOB), encoding="utf-8")
    assert stale.is_file()
    assert len(STALE_STATIC_BLOB["games"]) > 0
    return stale


def test_cr8_refuses_stale_static_when_current_set_but_pack_missing(
    tmp_path, monkeypatch
):
    """CURRENT → release without pack + stale static with games → refuse static."""
    live = tmp_path / "live"
    live.mkdir()
    release = live / "releases" / "r-no-pack"
    release.mkdir(parents=True)
    (live / "CURRENT").symlink_to(release)
    assert not (release / "ncaam_official_schedule_2024_25.json").exists()

    data_dir = tmp_path / "static_data_dir"
    stale = _seed_stale_static(data_dir)

    sched = _load_schedule_mod()
    monkeypatch.setattr(sched, "_holdout_live_root", lambda: live)
    monkeypatch.setattr(sched, "DATA_DIR", data_dir)

    path = sched.schedule_path_for_season("2024-25")
    assert path.resolve() == (release / sched.HOLDOUT_PACK_BASENAME).resolve()
    assert path.resolve() != stale.resolve()

    blob = sched.load_official_schedule_blob("2024-25")
    assert blob["present"] is False
    assert blob["source"] == "missing_active_release_pack"
    assert blob.get("games") == []
    assert blob.get("active_release_current_set") is True
    assert Path(blob["resolved_path"]).resolve() != stale.resolve()
    assert Path(blob["resolved_path"]).name == sched.HOLDOUT_PACK_BASENAME


def test_cr8_broken_current_symlink_fail_closed(tmp_path, monkeypatch):
    """Broken CURRENT symlink must fail closed — never load stale static."""
    live = tmp_path / "live_broken"
    live.mkdir()
    (live / "CURRENT").symlink_to(live / "releases" / "does-not-exist")
    assert (live / "CURRENT").is_symlink()
    assert not (live / "CURRENT").exists()

    data_dir = tmp_path / "static_data_dir_broken"
    stale = _seed_stale_static(data_dir)

    sched = _load_schedule_mod()
    monkeypatch.setattr(sched, "_holdout_live_root", lambda: live)
    monkeypatch.setattr(sched, "DATA_DIR", data_dir)

    state = sched.inspect_holdout_current(live_root=live)
    assert state["current_set"] is True
    assert state["broken_current"] is True

    blob = sched.load_official_schedule_blob("2024-25")
    assert blob["present"] is False
    assert blob["source"] == "broken_current_pointer"
    assert blob.get("games") == []
    assert blob.get("active_release_current_set") is True
    assert Path(blob["resolved_path"]).resolve() != stale.resolve()


def test_cr8_static_fallback_only_when_current_absent(tmp_path, monkeypatch):
    """Static DATA_DIR remains permitted only when CURRENT does not exist."""
    live = tmp_path / "live_no_current"
    live.mkdir()
    assert not (live / "CURRENT").exists()

    data_dir = tmp_path / "static_ok"
    stale = _seed_stale_static(data_dir)

    sched = _load_schedule_mod()
    monkeypatch.setattr(sched, "_holdout_live_root", lambda: live)
    monkeypatch.setattr(sched, "DATA_DIR", data_dir)

    blob = sched.load_official_schedule_blob("2024-25")
    assert blob["present"] is True
    assert blob.get("authority") == "static_DATA_DIR_or_flat"
    assert blob.get("active_release_current_set") is False
    assert len(blob.get("games") or []) == 1
    assert Path(blob["resolved_path"]).resolve() == stale.resolve()
