from __future__ import annotations

import json
from pathlib import Path

from src.services.nfl_kdst_publish import (
    dst_overlay_for_team,
    kdst_publish_status,
    kdst_volume_overlay_for_team,
    load_kdst_publish_artifact,
    named_kickers_from_artifact,
)


def test_missing_artifact_is_honest_empty(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("NFL_KDST_PUBLISH_PATH", str(tmp_path / "none.json"))
    assert load_kdst_publish_artifact(2026) is None
    status = kdst_publish_status(2026)
    assert status["status"] == "missing"
    assert status["kickers"] == 0
    assert kdst_volume_overlay_for_team(None, "KC") is None


def test_ready_artifact_overlays_volume_without_inventing_names(
    tmp_path: Path, monkeypatch
) -> None:
    path = tmp_path / "nfl-kdst-season-2026.json"
    path.write_text(
        json.dumps(
            {
                "season": 2026,
                "source": "test-hook",
                "kickers": [{"player_id": "k1", "team": "KC", "fg_attempts": 33.0}],
                "dst": [{"team": "KC", "points_allowed_mean": 19.5}],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("NFL_KDST_PUBLISH_PATH", str(path))
    art = load_kdst_publish_artifact(2026)
    assert art is not None
    assert kdst_publish_status(2026)["status"] == "ready"
    overlay = kdst_volume_overlay_for_team(art, "KC")
    assert overlay == {"fg_attempts": 33.0}
    assert kdst_volume_overlay_for_team(art, "SEA") is None
    assert named_kickers_from_artifact(art) == [
        {"team": "KC", "player_id": "k1", "player_name": "k1"}
    ]
    assert dst_overlay_for_team(art, "KC") == {"points_allowed_mean": 19.5}
    assert dst_overlay_for_team(art, "SEA") is None


def test_artifact_xp_overlay_and_named_player(tmp_path: Path, monkeypatch) -> None:
    path = tmp_path / "nfl-kdst-season-2026.json"
    path.write_text(
        json.dumps(
            {
                "season": 2026,
                "source": "test-hook",
                "kickers": [
                    {
                        "player_id": "00-0031234",
                        "player_name": "Harrison Butker",
                        "team": "KC",
                        "fg_attempts": 32.0,
                        "xp_attempts": 47.0,
                    }
                ],
                "dst": [{"team": "LAR", "points_allowed_mean": 21.1, "sacks": 41.0}],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("NFL_KDST_PUBLISH_PATH", str(path))
    art = load_kdst_publish_artifact(2026)
    assert kdst_volume_overlay_for_team(art, "KC") == {
        "fg_attempts": 32.0,
        "xp_attempts": 47.0,
    }
    assert named_kickers_from_artifact(art)[0]["player_name"] == "Harrison Butker"
    assert dst_overlay_for_team(art, "LA") == {
        "points_allowed_mean": 21.1,
        "sacks": 41.0,
    }
