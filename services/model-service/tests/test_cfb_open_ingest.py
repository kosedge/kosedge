"""CFB open-ingest scaffold — map, store, join. No KEI. No forced matches."""

from __future__ import annotations

import json
import os
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src.services.cfb_warehouse.market_diagnostic import (  # noqa: E402
    INSUFFICIENT_MARKET_ROWS,
    diagnose_live_2026,
)
from src.services.cfb_warehouse.open_ingest import (  # noqa: E402
    USED_IN_SPREAD,
    flatten_event,
    ingest_events,
    inventory_from_mapped,
    load_mapped,
    load_official_slate_games,
    map_rows_to_slate,
    reduce_mapped_games,
    resolve_odds_team_name,
    snapshot_key,
)


def _event(*, home: str, away: str, commence: str, event_id: str, point: float = -3.5) -> dict:
    return {
        "id": event_id,
        "home_team": home,
        "away_team": away,
        "commence_time": commence,
        "bookmakers": [
            {
                "key": "draftkings",
                "markets": [
                    {
                        "key": "spreads",
                        "outcomes": [
                            {"name": home, "point": point, "price": -110},
                            {"name": away, "point": -point, "price": -110},
                        ],
                    },
                    {
                        "key": "player_pass_yds",
                        "outcomes": [{"name": "Someone", "point": 250.5}],
                    },
                ],
            }
        ],
    }


def test_flatten_drops_props_and_sets_research_flags() -> None:
    rows = flatten_event(
        _event(
            home="Ohio State Buckeyes",
            away="Ball State Cardinals",
            commence="2026-09-05T16:00:00Z",
            event_id="evt-1",
        ),
        pulled_at="2026-08-14T12:00:00Z",
    )
    assert len(rows) == 1
    assert rows[0]["market"] == "spread"
    assert rows[0]["spread_home"] == -3.5
    assert rows[0]["used_in_spread"] is False
    assert rows[0]["kei"] is False
    assert rows[0]["snapshot_key"] == snapshot_key(rows[0])


def test_unmatched_names_are_logged_not_forced() -> None:
    slate = load_official_slate_games(2026)
    rows = flatten_event(
        _event(
            home="Findlay Oilers",
            away="Some FCS Team",
            commence="2026-08-29T16:00:00Z",
            event_id="evt-fcs",
        ),
        pulled_at="2026-08-14T12:00:00Z",
    )
    mapped = map_rows_to_slate(rows, slate)
    assert mapped[0]["matched"] is False
    assert mapped[0]["slate_game_id"] is None
    assert mapped[0]["unmatched_reason"] in {"unresolved_team", "no_slate_pair"}
    assert resolve_odds_team_name("Findlay Oilers") is None
    assert resolve_odds_team_name("Sam Houston State Bearkats") == "SHSU"
    assert resolve_odds_team_name("Southern Mississippi Golden Eagles") == "USM"


def test_official_slate_match_unc_tcu_week0() -> None:
    slate = load_official_slate_games(2026)
    rows = flatten_event(
        _event(
            home="TCU Horned Frogs",
            away="North Carolina Tar Heels",
            commence="2026-08-29T16:00:00Z",
            event_id="evt-tcu",
            point=-14.5,
        ),
        pulled_at="2026-08-14T12:00:00Z",
    )
    mapped = map_rows_to_slate(rows, slate)
    assert mapped[0]["matched"] is True
    assert mapped[0]["slate_game_id"] == "401856766"
    assert mapped[0]["week"] == 0
    assert mapped[0]["home_team_id"] == "TCU"
    assert mapped[0]["away_team_id"] == "UNC"
    assert mapped[0]["used_in_spread"] is False


def test_write_attempt_is_idempotent(tmp_path: Path) -> None:
    slate = load_official_slate_games(2026)
    events = [
        _event(
            home="TCU Horned Frogs",
            away="North Carolina Tar Heels",
            commence="2026-08-29T16:00:00Z",
            event_id="evt-tcu",
        )
    ]
    first = ingest_events(
        events,
        slate,
        pulled_at="2026-08-14T18:00:00Z",
        weeks=(0, 1, 2),
        prefer_hd=False,
        root=tmp_path,
    )
    second = ingest_events(
        events,
        slate,
        pulled_at="2026-08-14T18:00:00Z",
        weeks=(0, 1, 2),
        prefer_hd=False,
        root=tmp_path,
    )
    assert first["inventory"]["n_opens"] >= 1
    assert first["inventory"]["used_in_spread"] is False
    assert first["inventory"]["kei"] is False
    assert second["status"] == "idempotent"
    loaded = load_mapped(root=tmp_path)
    keys = [r["snapshot_key"] for r in loaded]
    assert len(keys) == len(set(keys))


def test_empty_attempt_is_recorded_honestly(tmp_path: Path) -> None:
    slate = load_official_slate_games(2026)
    written = ingest_events(
        [],
        slate,
        pulled_at="2026-08-14T19:00:00Z",
        weeks=(0, 1, 2),
        prefer_hd=False,
        root=tmp_path,
        note="Honest empty",
    )
    inv = written["inventory"]
    assert inv["n_opens"] == 0
    assert inv["n_closes"] == 0
    assert inv["n_events"] == 0
    assert inv["status"] == "empty"
    assert inv["used_in_spread"] is False
    assert (tmp_path / "inventory.json").is_file()
    assert (tmp_path / "attempts.jsonl").is_file()


def test_join_n0_and_n_positive(tmp_path: Path) -> None:
    empty = diagnose_live_2026(reduce_mapped_games([]))
    assert empty["status"] == INSUFFICIENT_MARKET_ROWS
    assert empty["used_in_spread"] is False

    slate = load_official_slate_games(2026)
    events = [
        _event(
            home="TCU Horned Frogs",
            away="North Carolina Tar Heels",
            commence="2026-08-29T16:00:00Z",
            event_id="evt-tcu",
            point=-13.5,
        )
    ]
    ingest_events(
        events,
        slate,
        pulled_at="2026-08-14T20:00:00Z",
        weeks=(0, 1, 2),
        prefer_hd=False,
        root=tmp_path,
    )
    reduced = reduce_mapped_games(load_mapped(root=tmp_path), weeks=(0, 1, 2))
    assert reduced
    assert reduced[0]["open_spread_home"] == -13.5
    assert reduced[0]["close_spread_home"] is None  # kickoff still in the future
    assert reduced[0]["used_in_spread"] is False
    assert USED_IN_SPREAD is False


def test_inventory_never_sets_kei() -> None:
    inv = inventory_from_mapped(
        [],
        pulled_at="2026-08-14T00:00:00Z",
        n_events=0,
        weeks=(0, 1, 2),
    )
    assert inv["kei"] is False
    assert inv["blend"] is False
    assert inv["used_in_spread"] is False
