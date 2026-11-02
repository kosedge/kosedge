"""OPT-IN INTERNAL FIXTURE-ONLY assembly (t5178u W-FIX-A).

Binds the shared typed contract. Assembly is implemented in assemble.py.
Does not import simulator, produce_mu, outcome loaders, network, DB, or jobs.
"""

from src.services.nfl_fixture_assembly.assemble import (
    NON_FIXTURE_CONSUMERS,
    assemble_fixture_batch,
    assemble_fixture_only,
    consume_eligibility,
    forbidden_import_names,
)
from src.services.nfl_fixture_assembly.contract import (
    CONTRACT_ID,
    CONTRACT_SCHEMA_VERSION,
    FIXTURE_CHANNEL,
    FIXTURE_ENV_BYPASS_KEYS,
    SYNTHETIC_ADJUSTMENT_POLICY,
    AssemblyResult,
    CapabilityRecord,
    EligibilityDecision,
    FixtureEligibilityResult,
    FixtureEnvelope,
    FixtureHardRefuse,
    FixturePeriod,
    ForecastCapability,
    ForecastRecord,
    ProvenanceRecord,
    QuoteSide,
    RequestedOutput,
    SyntheticQuote,
    SyntheticQuoteSpec,
    expected_quote_line,
    home_spread_from_point_margin,
)

__all__ = [
    "NON_FIXTURE_CONSUMERS",
    "assemble_fixture_batch",
    "assemble_fixture_only",
    "consume_eligibility",
    "forbidden_import_names",
    "CONTRACT_ID",
    "CONTRACT_SCHEMA_VERSION",
    "FIXTURE_CHANNEL",
    "FIXTURE_ENV_BYPASS_KEYS",
    "SYNTHETIC_ADJUSTMENT_POLICY",
    "AssemblyResult",
    "CapabilityRecord",
    "EligibilityDecision",
    "FixtureEligibilityResult",
    "FixtureEnvelope",
    "FixtureHardRefuse",
    "FixturePeriod",
    "ForecastCapability",
    "ForecastRecord",
    "ProvenanceRecord",
    "QuoteSide",
    "RequestedOutput",
    "SyntheticQuote",
    "SyntheticQuoteSpec",
    "expected_quote_line",
    "home_spread_from_point_margin",
]
