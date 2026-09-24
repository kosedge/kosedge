from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from src.services.nfl_clock_play_simulator import pre_entry_pass_rz_state_key

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts" / "nfl" / "build_clock_play_pre_entry_pass_rz_priors.py"


def _load_script():
    spec = importlib.util.spec_from_file_location("pre_entry_pass_rz_priors", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _row(
    *,
    game_id: str,
    drive: int,
    play_type: str,
    yardline_100: int,
    down: int,
    ydstogo: int,
    yards_gained: int,
    **extra: object,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "season": 2021,
        "season_type": "REG",
        "game_id": game_id,
        "fixed_drive": drive,
        "play_type": play_type,
        "yardline_100": yardline_100,
        "down": down,
        "ydstogo": ydstogo,
        "yards_gained": yards_gained,
        "posteam": "SYN",
        "goal_to_go": 0,
        "touchdown": 0,
        "interception": 0,
        "fumble_lost": 0,
        "incomplete_pass": 0,
        "first_down": 0,
    }
    payload.update(extra)
    return {"object_type": "pbp_play", "payload": payload}


def test_builder_owns_one_non_fourth_continuation_per_eligible_crossing(
    tmp_path: Path, monkeypatch
) -> None:
    module = _load_script()
    rows = [
        _row(
            game_id="SYN_A",
            drive=1,
            play_type="pass",
            yardline_100=25,
            down=1,
            ydstogo=10,
            yards_gained=8,
            first_down=1,
        ),
        _row(
            game_id="SYN_A",
            drive=1,
            play_type="pass",
            yardline_100=17,
            down=1,
            ydstogo=10,
            yards_gained=0,
            incomplete_pass=1,
        ),
        _row(
            game_id="SYN_A",
            drive=1,
            play_type="run",
            yardline_100=17,
            down=2,
            ydstogo=10,
            yards_gained=4,
        ),
        _row(
            game_id="SYN_A",
            drive=2,
            play_type="pass",
            yardline_100=29,
            down=1,
            ydstogo=10,
            yards_gained=10,
            first_down=1,
        ),
        _row(
            game_id="SYN_A",
            drive=2,
            play_type="run",
            yardline_100=19,
            down=1,
            ydstogo=5,
            yards_gained=5,
            first_down=1,
        ),
        _row(
            game_id="SYN_A",
            drive=3,
            play_type="pass",
            yardline_100=22,
            down=3,
            ydstogo=8,
            yards_gained=5,
        ),
        _row(
            game_id="SYN_A",
            drive=3,
            play_type="field_goal",
            yardline_100=17,
            down=4,
            ydstogo=3,
            yards_gained=0,
        ),
    ]
    pbp = tmp_path / "pbp.ndjson"
    pbp.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"

    monkeypatch.setattr(
        "sys.argv",
        [SCRIPT.name, "--pbp", str(pbp), "--output", str(first)],
    )
    module.main()
    monkeypatch.setattr(
        "sys.argv",
        [SCRIPT.name, "--pbp", str(pbp), "--output", str(second)],
    )
    module.main()

    payload = json.loads(first.read_text(encoding="utf-8"))
    accounting = payload["accounting"]
    default = payload["priors"]["default"]["sample"]
    key = pre_entry_pass_rz_state_key(
        pre_entry_yardline=75,
        yardline=83,
        down=1,
        distance=10,
        goal_to_go=False,
    )

    assert first.read_bytes() == second.read_bytes()
    assert accounting["eligible_pass_starts_70_79"] == 3
    assert accounting["pass_crossings_to_rz"] == 3
    assert accounting["eligible_joint_continuations"] == 2
    assert accounting["excluded_fourth_down_continuation"] == 1
    assert default["continuations"] == 2
    assert default["routes"] == {"pass": 1, "run": 1}
    assert default["outcomes"]["pass"]["incomplete"] == 1
    assert default["outcomes"]["run"]["first_down"] == 1
    assert key in payload["priors"]["buckets"]
