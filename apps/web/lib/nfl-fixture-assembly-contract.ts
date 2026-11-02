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

/** Must be present on consumeFixtureEligibility input — no truthiness defaults. */
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

export const ELIGIBILITY_REQUIRED_FALSE_BOOLS = [
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
  result?: unknown;
  reason?: unknown;
  fixture?: unknown;
  channel?: unknown;
  subscriber_consumable?: unknown;
  betting_consumable?: unknown;
  production_consumable?: unknown;
  env_bypass_honored?: unknown;
  cacheable?: unknown;
  contract_id?: unknown;
  schema_version?: unknown;
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
    schema_version: FIXTURE_CONTRACT_SCHEMA_VERSION,
  };
}

function envTruthy(name: string): boolean {
  const raw = (typeof process !== "undefined" ? process.env?.[name] : "") ?? "";
  return ["1", "true", "yes", "y", "on"].includes(raw.trim().toLowerCase());
}

/**
 * t5194u — same gate as assemble.consume_fixture_eligibility.
 * Exact contract_id / schema_version / channel / fixture + explicit false
 * flags BEFORE normalize. No truthiness defaults. Does not accept bare
 * {result:"ALLOW_FIXTURE"} or rewrite fixture=false / PRODUCTION / wrong
 * contract_id into allow.
 */
export function consumeFixtureEligibility(
  decision: EligibilityDecision | EligibilityDecisionInput,
  consumer: string,
): EligibilityDecision {
  if (decision == null || typeof decision !== "object") {
    throw new FixtureHardRefuse("REFUSE_PARTIAL", "eligibility must be an object");
  }
  const raw = decision as Record<string, unknown>;
  const missing = ELIGIBILITY_REQUIRED_KEYS.filter((key) => !(key in raw));
  if (missing.length > 0) {
    throw new FixtureHardRefuse(
      "REFUSE_MISSING",
      `eligibility missing required fields ${JSON.stringify(missing)} (no default / no normalize)`,
    );
  }

  if (raw.contract_id !== FIXTURE_CONTRACT_ID) {
    throw new FixtureHardRefuse(
      "REFUSE_VERSION",
      `contract_id ${JSON.stringify(raw.contract_id)} != ${FIXTURE_CONTRACT_ID} (not rewritten)`,
    );
  }
  if (raw.schema_version !== FIXTURE_CONTRACT_SCHEMA_VERSION) {
    throw new FixtureHardRefuse(
      "REFUSE_VERSION",
      `schema_version ${JSON.stringify(raw.schema_version)} != ${FIXTURE_CONTRACT_SCHEMA_VERSION}`,
    );
  }
  if (raw.channel !== FIXTURE_CHANNEL) {
    throw new FixtureHardRefuse(
      "REFUSE_PRODUCTION_CHANNEL",
      `channel=${JSON.stringify(raw.channel)} is not ${FIXTURE_CHANNEL} (not rewritten)`,
    );
  }
  if (raw.fixture !== true) {
    if (raw.fixture === false) {
      throw new FixtureHardRefuse(
        "REFUSE_QUALIFICATION",
        "fixture=false cannot be rewritten into ALLOW_FIXTURE",
      );
    }
    throw new FixtureHardRefuse(
      "REFUSE_PARTIAL",
      `fixture must be boolean true (got ${JSON.stringify(raw.fixture)})`,
    );
  }
  for (const key of ELIGIBILITY_REQUIRED_FALSE_BOOLS) {
    const value = raw[key];
    if (value !== false) {
      if (typeof value !== "boolean") {
        throw new FixtureHardRefuse(
          "REFUSE_PARTIAL",
          `${key} must be boolean false (got ${typeof value})`,
        );
      }
      throw new FixtureHardRefuse(
        "REFUSE_PRODUCTION_CHANNEL",
        `${key}=${JSON.stringify(value)} must be false (no rewrite)`,
      );
    }
  }

  const resultRaw = raw.result;
  if (
    typeof resultRaw !== "string" ||
    !(FIXTURE_ELIGIBILITY_RESULTS as readonly string[]).includes(resultRaw)
  ) {
    throw new FixtureHardRefuse(
      "REFUSE_VALIDATION",
      `result ${JSON.stringify(resultRaw)} is not a FixtureEligibilityResult`,
    );
  }
  const result = resultRaw as FixtureEligibilityResult;
  if (result !== "ALLOW_FIXTURE") {
    throw new FixtureHardRefuse(result, "eligibility is not ALLOW_FIXTURE");
  }
  if (typeof raw.reason !== "string" || !raw.reason) {
    throw new FixtureHardRefuse("REFUSE_PARTIAL", "reason must be a non-empty string");
  }

  const token = typeof consumer === "string" ? consumer.trim().toLowerCase() : "";
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

  const bypassHit = FIXTURE_ENV_BYPASS_KEYS.filter((name) => envTruthy(name));
  if (bypassHit.length > 0 && raw.env_bypass_honored !== false) {
    throw new FixtureHardRefuse(
      "REFUSE_ENV_BYPASS",
      `env ${bypassHit.join(",")} must not be honored for ALLOW_FIXTURE`,
    );
  }

  return {
    result: "ALLOW_FIXTURE",
    reason: raw.reason,
    fixture: true,
    channel: FIXTURE_CHANNEL,
    subscriber_consumable: false,
    betting_consumable: false,
    production_consumable: false,
    env_bypass_honored: false,
    cacheable: false,
    contract_id: FIXTURE_CONTRACT_ID,
    schema_version: FIXTURE_CONTRACT_SCHEMA_VERSION,
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
