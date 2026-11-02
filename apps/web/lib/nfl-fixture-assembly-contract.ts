/**
 * t5178u M0 — TS mirror of the shared fixture-assembly contract.
 * SoT: services/model-service/src/services/nfl_fixture_assembly/contract.py
 *
 * OPT-IN INTERNAL FIXTURE-ONLY. CERT=0.
 * ALLOW_FIXTURE is fixture-channel-only (Alex X1) — never subscriber/betting.
 * NFL is not in FAIR_LINES_HONESTY_SPORTS — do not copy honesty-empty here.
 */

export const FIXTURE_CHANNEL = "FIXTURE" as const;
export const FIXTURE_CONTRACT_ID = "t5178u-nfl-fixture-assembly-v0";
export const FIXTURE_CONTRACT_SCHEMA_VERSION = "nfl-fixture-assembly-v0";
/** Additive A→B chain (t5194u). Does not rewrite v0 evidence. */
export const CHAIN_CONTRACT_ID = "t5194u-nfl-fixture-chain-v1";
export const CHAIN_SCHEMA_VERSION = "nfl-fixture-chain-v1";
export const SYNTHETIC_ADJUSTMENT_POLICY =
  "TRANSPORT_ONLY_NOT_INJURY_POLICY" as const;
export const AMERICAN_PRICE_MIN_ABS = 100;

/** Must be present on consume_fixture_eligibility input — no truthiness defaults. */
export const ELIGIBILITY_REQUIRED_KEYS = [
  "result",
  "reason",
  "contract_id",
  "schema_version",
  "channel",
  "fixture",
  "subscriber_consumable",
  "betting_consumable",
  "production_consumable",
  "env_bypass_honored",
  "cacheable",
] as const;

export const FORECAST_CAPABILITIES = ["POINT_MARGIN", "JOINT_SCORE"] as const;
export type ForecastCapability = (typeof FORECAST_CAPABILITIES)[number];

export const REQUESTED_OUTPUTS = [
  "POINT_MARGIN_SPREAD",
  "TOTAL",
  "MONEYLINE",
  "COVER_PROBABILITY",
  "ECONOMIC_ELIGIBILITY",
] as const;
export type RequestedOutput = (typeof REQUESTED_OUTPUTS)[number];

export const QUOTE_SIDES = ["HOME", "AWAY"] as const;
export type QuoteSide = (typeof QUOTE_SIDES)[number];

export const FIXTURE_PERIODS = ["full_game", "h1"] as const;
export type FixturePeriod = (typeof FIXTURE_PERIODS)[number];

/** ONE eligibility/refusal enum. */
export const FIXTURE_ELIGIBILITY_RESULTS = [
  "ALLOW_FIXTURE",
  "REFUSE_IDENTITY",
  "REFUSE_HASH",
  "REFUSE_VERSION",
  "REFUSE_GAME",
  "REFUSE_PERIOD",
  "REFUSE_LINE",
  "REFUSE_SIGN",
  "REFUSE_TIME",
  "REFUSE_CUTOFF",
  "REFUSE_CAPABILITY",
  "REFUSE_QUALIFICATION",
  "REFUSE_MISSING",
  "REFUSE_STALE",
  "REFUSE_PARTIAL",
  "REFUSE_CACHE",
  "REFUSE_TOTALS",
  "REFUSE_MONEYLINE",
  "REFUSE_COVER_PROBABILITY",
  "REFUSE_ECONOMIC_ELIGIBILITY",
  "REFUSE_PRODUCTION_CHANNEL",
  "REFUSE_ENV_BYPASS",
  "REFUSE_MARKET_FIELDS",
  "REFUSE_VALIDATION",
] as const;
export type FixtureEligibilityResult =
  (typeof FIXTURE_ELIGIBILITY_RESULTS)[number];

export type ForecastRecord = {
  forecast_id: string;
  game_id: string;
  period: FixturePeriod;
  side: QuoteSide;
  point_margin: number;
};

export type ProvenanceRecord = {
  source_id: string;
  source_url: string;
  source_snapshot_id: string;
  parser_version: string;
  protocol_sha: string;
  schema_version: string;
  source_published_at: string;
  captured_at: string;
  decision_ts: string;
  kickoff_ts: string;
  as_of_ts: string;
};

export type CapabilityRecord = {
  bits: readonly ForecastCapability[];
};

export type SyntheticQuote = {
  book: string;
  event_id: string;
  side: QuoteSide;
  period: FixturePeriod;
  line: number;
  price: number;
  time: string;
  fixture: true;
  transport_only: true;
  injury_policy_approved: false;
};

export type EligibilityDecision = {
  result: FixtureEligibilityResult;
  reason: string;
  fixture: true;
  channel: typeof FIXTURE_CHANNEL;
  subscriber_consumable: false;
  betting_consumable: false;
  production_consumable: false;
  env_bypass_honored: false;
  cacheable: false;
  contract_id: typeof FIXTURE_CONTRACT_ID;
  schema_version: typeof FIXTURE_CONTRACT_SCHEMA_VERSION;
};

/** t5194u additive chain record — B consumes this JSON, not v0-only to_dict. */
export type FixtureChainRecord = {
  chain_contract_id: typeof CHAIN_CONTRACT_ID;
  chain_schema_version: typeof CHAIN_SCHEMA_VERSION;
  base_contract_id: typeof FIXTURE_CONTRACT_ID;
  base_schema_version: typeof FIXTURE_CONTRACT_SCHEMA_VERSION;
  channel: typeof FIXTURE_CHANNEL;
  fixture: true;
  production_mode: false;
  cacheable: false;
  honor_env_bypass: false;
  requested_output: RequestedOutput;
  eligibility: EligibilityDecision;
  quote: SyntheticQuote;
  forecast: ForecastRecord;
  provenance: ProvenanceRecord;
  cutoff: {
    source_published_at: string;
    captured_at: string;
    decision_ts: string;
    kickoff_ts: string;
    as_of_ts: string;
  };
  capability: CapabilityRecord;
  l1_candidate: Record<string, unknown>;
  game_id: string;
  admitted_capture_id: string;
  offense_raw: number;
  defense_raw: number;
  offense_multiplier: number;
  defense_multiplier: number;
  adjustment_policy: typeof SYNTHETIC_ADJUSTMENT_POLICY;
};

/** Consumer tokens that MUST refuse ALLOW_FIXTURE (Alex X1 / props-eligibility). */
export const NON_FIXTURE_CONSUMERS = [
  "subscriber",
  "betting",
  "production",
  "fair_lines_api",
  "honesty_board",
  "props_eligibility",
] as const;
export type NonFixtureConsumer = (typeof NON_FIXTURE_CONSUMERS)[number];
