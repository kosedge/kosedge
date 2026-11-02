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
export const SYNTHETIC_ADJUSTMENT_POLICY =
  "TRANSPORT_ONLY_NOT_INJURY_POLICY" as const;

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

/** Mirrors contract.py OUTPUT_REFUSE — point-margin hard-refuses these channels. */
export const OUTPUT_REFUSE = {
  TOTAL: "REFUSE_TOTALS",
  MONEYLINE: "REFUSE_MONEYLINE",
  COVER_PROBABILITY: "REFUSE_COVER_PROBABILITY",
  ECONOMIC_ELIGIBILITY: "REFUSE_ECONOMIC_ELIGIBILITY",
} as const;

export const FIXTURE_ENV_BYPASS_KEYS = [
  "NFL_EDGE_BOARD_INTERNAL",
  "NEXT_PUBLIC_NFL_EDGE_BOARD_INTERNAL",
  "NFL_EDGE_BOARD_PUBLIC_ENABLED",
  "NFL_FAIR_LINES_PUBLIC_SPREAD_ENABLED",
  "NFL_FAIR_LINES_PUBLIC_ML_ENABLED",
  "NFL_FAIR_LINES_PUBLIC_TOTAL_ENABLED",
  "NFL_FIXTURE_ALLOW_PRODUCTION",
  "NFL_FIXTURE_ENV_BYPASS",
  "HHL1_LIVE_CAPTURE",
  "HHL1_NOWCAST_ENABLED",
  "HHL1_SCORING",
  "HHL1_PUBLISH",
] as const;

/** Loose input so refuse rows can share the same consume gate. */
export type EligibilityDecisionInput = {
  result: FixtureEligibilityResult;
  reason: string;
  fixture?: boolean;
  channel?: string;
  subscriber_consumable?: boolean;
  betting_consumable?: boolean;
  production_consumable?: boolean;
  env_bypass_honored?: boolean;
  cacheable?: boolean;
  contract_id?: string;
};

export class FixtureHardRefuse extends Error {
  readonly result: FixtureEligibilityResult;
  readonly reason: string;
  readonly partial = false as const;

  constructor(result: FixtureEligibilityResult, reason: string) {
    super(`FIXTURE HARD REFUSE [${result}] ${reason}`);
    this.name = "FixtureHardRefuse";
    this.result = result;
    this.reason = reason;
  }

  toDict() {
    return {
      result: this.result,
      reason: this.reason,
      partial: false as const,
      fixture: true as const,
      subscriber_consumable: false as const,
      betting_consumable: false as const,
      production_consumable: false as const,
      env_bypass_honored: false as const,
      cacheable: false as const,
      contract_id: FIXTURE_CONTRACT_ID,
    };
  }
}

export function allowFixtureEligibility(
  reason = "fixture-channel transport admitted; not a production/betting allow",
): EligibilityDecision {
  return {
    result: "ALLOW_FIXTURE",
    reason,
    fixture: true,
    channel: FIXTURE_CHANNEL,
    subscriber_consumable: false,
    betting_consumable: false,
    production_consumable: false,
    env_bypass_honored: false,
    cacheable: false,
    contract_id: FIXTURE_CONTRACT_ID,
  };
}

/**
 * Alex X1 — ALLOW_FIXTURE cannot be consumed by subscriber/betting/production.
 * Mirrors assemble.consume_eligibility against the same contract enum.
 */
export function consumeFixtureEligibility(
  decision: EligibilityDecision | EligibilityDecisionInput,
  consumer: string,
): EligibilityDecision {
  const token = String(consumer ?? "")
    .trim()
    .toLowerCase();
  if ((NON_FIXTURE_CONSUMERS as readonly string[]).includes(token)) {
    throw new FixtureHardRefuse(
      "REFUSE_PRODUCTION_CHANNEL",
      `consumer=${JSON.stringify(token)} cannot consume ALLOW_FIXTURE (fixture-channel-only)`,
    );
  }
  if (token !== "fixture") {
    throw new FixtureHardRefuse(
      "REFUSE_QUALIFICATION",
      `unknown consumer ${JSON.stringify(consumer)}; only consumer='fixture' is qualified`,
    );
  }
  if (decision.result !== "ALLOW_FIXTURE") {
    throw new FixtureHardRefuse(decision.result, "eligibility is not ALLOW_FIXTURE");
  }
  if (
    decision.subscriber_consumable ||
    decision.betting_consumable ||
    decision.production_consumable ||
    decision.env_bypass_honored ||
    decision.cacheable
  ) {
    throw new FixtureHardRefuse(
      "REFUSE_PRODUCTION_CHANNEL",
      "ALLOW_FIXTURE payload illegally set a production/cache consumable bit",
    );
  }
  return {
    result: "ALLOW_FIXTURE",
    reason: decision.reason,
    fixture: true,
    channel: FIXTURE_CHANNEL,
    subscriber_consumable: false,
    betting_consumable: false,
    production_consumable: false,
    env_bypass_honored: false,
    cacheable: false,
    contract_id: FIXTURE_CONTRACT_ID,
  };
}

export function homeSpreadFromPointMargin(pointMargin: number): number {
  return -pointMargin;
}

export function expectedQuoteLine(opts: {
  pointMargin: number;
  side: QuoteSide;
}): number {
  const homeSpread = homeSpreadFromPointMargin(opts.pointMargin);
  return opts.side === "HOME" ? homeSpread : opts.pointMargin;
}
