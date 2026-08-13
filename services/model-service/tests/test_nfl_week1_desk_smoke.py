"""Week 1 desk smoke — go-mode checklist (automated)."""

from __future__ import annotations

import json
from pathlib import Path

from src.services.nfl_kei_week1_reprice import load_week1_pack, week1_slate_reprice_table

SCHEDULE = (
    Path(__file__).resolve().parents[1]
    / "src/services/nfl_season_engine/data/nfl_regular_schedule_2026.json"
)


def test_week1_desk_smoke_gate_a_b() -> None:
    payload = json.loads(SCHEDULE.read_text(encoding="utf-8"))
    games = [g for g in payload["games"] if int(g["week"]) == 1]
    assert len(games) == 16
    assert all(str(g.get("game_type") or "REG").upper() == "REG" for g in games)
    assert not any(str(g.get("game_type") or "").upper() == "PRE" for g in games)

    pack = load_week1_pack(2026)
    assert pack.loaded
    rows = week1_slate_reprice_table(games, pack=pack)
    assert len(rows) == 16
    diverged = [r for r in rows if r["spread_delta"] or r["total_delta"]]
    assert len(diverged) > 0

    by_game = {r["game"]: r for r in rows}
    atl = " ".join(by_game["ATL @PIT"]["factors"] + by_game["ATL @PIT"]["not_applied"])
    assert "open_competition" in atl
    mia = " ".join(by_game["MIA @LV"]["factors"])
    assert "Willis" in mia or "named_starter" in mia
    minn = " ".join(by_game["GB @MIN"]["factors"])
    assert "Kyler" in minn or "Murray" in minn
    cle = " ".join(by_game["CLE @JAX"]["factors"] + by_game["CLE @JAX"]["not_applied"])
    assert "open_competition" in cle
