"""CFB historical warehouse v1 — identity spine, leakage contract, ingest.

Production season-engine / project-game does **not** live-query this warehouse.
Feature builders that feed backtests must register ``available_at`` and call
``assert_available_before_kickoff``.
"""

from src.services.cfb_warehouse.identity import (
    ESPN_ABBR_TO_CODE,
    ESPN_NAME_TO_CODE,
    PACKAGED_CODE_ALIASES,
    alias_rows,
    canonical_code,
    known_engine_codes,
    resolve_team_code,
)
from src.services.cfb_warehouse.leakage import (
    ERA_TAGS,
    LEAKAGE_RULE,
    assert_available_before_kickoff,
    era_tag,
    filter_available,
    is_available_before_kickoff,
)

__all__ = [
    "ERA_TAGS",
    "ESPN_ABBR_TO_CODE",
    "ESPN_NAME_TO_CODE",
    "LEAKAGE_RULE",
    "PACKAGED_CODE_ALIASES",
    "alias_rows",
    "assert_available_before_kickoff",
    "canonical_code",
    "era_tag",
    "filter_available",
    "is_available_before_kickoff",
    "known_engine_codes",
    "resolve_team_code",
]
