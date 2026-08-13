"""Tests for CFB warehouse identity spine (alias stability)."""

from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src.services.cfb_warehouse.identity import (
    alias_rows,
    canonical_code,
    known_engine_codes,
    resolve_team_code,
)


def test_florida_gators_not_findlay() -> None:
    known = known_engine_codes()
    assert resolve_team_code(name="Florida Gators", abbr="FLA", known_codes=known) == "UF"
    assert resolve_team_code(name="Florida Gators", abbr="UF", known_codes=known) == "UF"
    assert resolve_team_code(name="Findlay Oilers", abbr="UF", known_codes=known) is None


def test_tamu_and_packaged_aliases() -> None:
    known = known_engine_codes()
    assert resolve_team_code(name="Texas A&M Aggies", abbr="TA&M", known_codes=known) == "TAMU"
    assert canonical_code("TA&M") == "TAMU"
    assert canonical_code("TXAM") == "TAMU"
    assert canonical_code("OLE") == "MISS"


def test_missouri_is_not_ole_miss() -> None:
    known = known_engine_codes()
    assert resolve_team_code(name="Missouri Tigers", abbr="MIZ", known_codes=known) == "MIZZ"
    assert resolve_team_code(name="Ole Miss Rebels", abbr="MISS", known_codes=known) == "MISS"
    assert resolve_team_code(name="Missouri Tigers", abbr="MIZ", known_codes=known) != "MISS"


def test_fcs_unknown_stays_unmapped() -> None:
    known = known_engine_codes()
    assert resolve_team_code(name="Montana Grizzlies", abbr="MONT", known_codes=known) is None


def test_alias_inventory_covers_florida_and_tamu() -> None:
    rows = alias_rows()
    by_alias = {(r["alias"], r["kind"]): r["team_id"] for r in rows}
    assert by_alias[("Florida Gators", "espn_name")] == "UF"
    assert by_alias[("FLA", "espn_abbr")] == "UF"
    assert by_alias[("TA&M", "espn_abbr")] == "TAMU"
    assert by_alias[("TA&M", "packaged_code")] == "TAMU"
