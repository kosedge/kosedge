"""NHL fetcher — raw snapshot gates (no prior / no KEINHL)."""

from __future__ import annotations

import json
from pathlib import Path

from src.services.nhl_data import (
    FETCHER_VERSION,
    NHL_TEAM_ABBREVS,
    SEASON_SCHEDULE,
    SEASON_TEAM_BOX,
    TALENT_SEASONS,
    documentation,
    load_goalie_box_pack,
    load_schedule_pack,
    load_skater_box_pack,
    load_team_box_pack,
    opening_night_has_fla_at_car,
)

ROOT = Path(__file__).resolve().parents[3]
CFB_KEI = ROOT / "services/model-service/src/services/cfb_season_engine/data/cfb_kei_w0_w1_2026.json"
NBA_FANTASY = (
    ROOT / "services/model-service/src/services/nba_season_engine/nba_fantasy.py"
)
WNBA_FANTASY = (
    ROOT / "services/model-service/src/services/wnba_season_engine/wnba_fantasy.py"
)
EDGE_KEI_AVAIL = ROOT / "apps/web/lib/edge-board-kei-availability.ts"


def test_documentation_names_official_vendor() -> None:
    doc = documentation()
    assert doc["vendor"] == "nhl"
    assert "api-web.nhle.com" in doc["api_web"]
    assert "api.nhle.com/stats/rest" in doc["stats_rest"]
    assert doc["refresh"] == "python3 scripts/nhl/fetch_raw.py"
    assert FETCHER_VERSION == "nhl-fetcher-v1"
    assert SEASON_SCHEDULE == 20262027
    assert SEASON_TEAM_BOX == 20252026
    assert TALENT_SEASONS == (20232024, 20242025, 20252026)


def test_team_box_has_32_rows() -> None:
    pack = load_team_box_pack()
    teams = pack.get("teams") or []
    assert pack.get("n_teams") == 32
    assert len(teams) == 32
    abbrevs = {str(t.get("team") or "").upper() for t in teams}
    assert abbrevs == set(NHL_TEAM_ABBREVS)
    for t in teams:
        assert t.get("gf") is not None
        assert t.get("ga") is not None
        assert int(t.get("games_played") or 0) > 0


def test_schedule_opening_night_fla_at_car() -> None:
    pack = load_schedule_pack()
    assert pack.get("n_games") == 1344  # 32 * 84 / 2
    assert opening_night_has_fla_at_car(pack) is True
    # Every club plays 84 RS games.
    from collections import Counter

    counts: Counter[str] = Counter()
    for g in pack.get("games") or []:
        counts[str(g.get("away") or "").upper()] += 1
        counts[str(g.get("home") or "").upper()] += 1
    assert len(counts) == 32
    assert set(counts) == set(NHL_TEAM_ABBREVS)
    assert min(counts.values()) == 84
    assert max(counts.values()) == 84


def test_skater_and_goalie_talent_tables_nonempty() -> None:
    skaters = load_skater_box_pack()
    goalies = load_goalie_box_pack()
    assert int(skaters.get("n_rows") or 0) > 0
    assert int(goalies.get("n_rows") or 0) > 0
    for season in TALENT_SEASONS:
        key = str(season)
        assert len(skaters.get("by_season", {}).get(key) or []) > 100
        assert len(goalies.get("by_season", {}).get(key) or []) > 20


def test_fetcher_module_does_not_define_shrink() -> None:
    """Fetcher stays ingest-only; Ch1 owns NHL_TEAM_CARRY_SHRINK in priors.py."""
    text = (ROOT / "services/model-service/src/services/nhl_data.py").read_text(
        encoding="utf-8"
    )
    assert "NHL_TEAM_CARRY_SHRINK =" not in text
    assert "nhl_team_prior_2026" not in text or "does_not" in text


def test_edge_board_nhl_kei_source_wired() -> None:
    # Fetcher chapter does not emit KEI; Ch4 wires the source. Helper remains.
    text = EDGE_KEI_AVAIL.read_text(encoding="utf-8")
    assert "sportIsMarketsOnlyEdgeBoard" in text
    assert "sportHasKeiSource" in text
    assert '"nhl"' in text


def test_nba_wnba_cfb_untouched() -> None:
    nba = NBA_FANTASY.read_text(encoding="utf-8")
    assert 'FANTASY_VERSION = "nba-fantasy-ch7-v1"' in nba
    wnba = WNBA_FANTASY.read_text(encoding="utf-8")
    assert 'FANTASY_VERSION = "wnba-fantasy-ch7-v1"' in wnba
    kei = json.loads(CFB_KEI.read_text(encoding="utf-8"))
    game = next(
        g
        for g in kei["games"]
        if g.get("away") == "BALL" and g.get("home") == "OSU" and g.get("week") == 1
    )
    assert abs(float(game["kei"]["kei_spread_home"]) - (-40.51)) < 1e-9
