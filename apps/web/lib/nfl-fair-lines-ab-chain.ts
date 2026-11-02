/**
 * t5194u A→B chain consume. Loads A's serialized FixtureChainRecord.
 * Does not invent allow tokens. CERT=0.
 */
import { projectFixtureFairLinesApiResponse } from "@/lib/nfl-fair-lines-fixture-api";
import { projectFixtureFairLinesViewModel } from "@/lib/nfl-fair-lines-view-types";
import { keiGamesFromFixtureFairLines } from "@/lib/resolve-kei-lines";
import {
  pageDataCacheHeadersForFixture,
  readFixtureProjectionCache,
  writeFixtureProjectionCache,
} from "@/lib/page-data-cache";
import {
  CHAIN_CONTRACT_ID,
  CHAIN_SCHEMA_VERSION,
  FIXTURE_CHANNEL,
  FIXTURE_CONTRACT_ID,
  FIXTURE_CONTRACT_SCHEMA_VERSION,
  FixtureHardRefuse,
  consumeFixtureEligibility,
  type FixtureChainRecord,
  type FixtureEligibilityResult,
} from "@/lib/nfl-fixture-assembly-contract";

const HANDOFF_KEYS = [
  "eligibility",
  "quote",
  "forecast",
  "provenance",
  "cutoff",
  "capability",
  "l1_candidate",
  "game_id",
  "admitted_capture_id",
] as const;

function refuse(result: FixtureEligibilityResult, reason: string): never {
  throw new FixtureHardRefuse(result, reason);
}

function asRecord(value: unknown, label: string): Record<string, unknown> {
  if (value == null || typeof value !== "object" || Array.isArray(value)) {
    refuse("REFUSE_PARTIAL", `${label} must be an object`);
  }
  return value as Record<string, unknown>;
}

/** Validate A's serialized chain before any B projection. */
export function assertFixtureChainRecord(raw: unknown): FixtureChainRecord {
  const payload = asRecord(raw, "chain");
  if (payload.chain_contract_id !== CHAIN_CONTRACT_ID) {
    refuse(
      "REFUSE_VERSION",
      `chain_contract_id ${JSON.stringify(payload.chain_contract_id)} != ${CHAIN_CONTRACT_ID}`,
    );
  }
  if (payload.chain_schema_version !== CHAIN_SCHEMA_VERSION) {
    refuse(
      "REFUSE_VERSION",
      `chain_schema_version ${JSON.stringify(payload.chain_schema_version)} != ${CHAIN_SCHEMA_VERSION}`,
    );
  }
  if (payload.base_contract_id !== FIXTURE_CONTRACT_ID) {
    refuse("REFUSE_VERSION", "base_contract_id mismatch (not rewritten)");
  }
  if (payload.base_schema_version !== FIXTURE_CONTRACT_SCHEMA_VERSION) {
    refuse("REFUSE_VERSION", "base_schema_version mismatch");
  }
  if (payload.channel !== FIXTURE_CHANNEL) {
    refuse("REFUSE_PRODUCTION_CHANNEL", "chain channel is not FIXTURE");
  }
  if (payload.fixture !== true) {
    refuse("REFUSE_QUALIFICATION", "chain.fixture=false cannot be rewritten");
  }
  if (payload.production_mode !== false) {
    refuse("REFUSE_PRODUCTION_CHANNEL", "production_mode must be false");
  }
  if (payload.cacheable !== false) {
    refuse("REFUSE_CACHE", "chain.cacheable must be false");
  }
  if (payload.honor_env_bypass !== false) {
    refuse("REFUSE_ENV_BYPASS", "honor_env_bypass must be false");
  }

  const missing = HANDOFF_KEYS.filter((key) => !(key in payload));
  if (missing.length > 0) {
    refuse("REFUSE_PARTIAL", `chain missing ${JSON.stringify(missing)}`);
  }

  consumeFixtureEligibility(
    payload.eligibility as FixtureChainRecord["eligibility"],
    "fixture",
  );

  const forecast = asRecord(payload.forecast, "forecast");
  const quote = asRecord(payload.quote, "quote");
  const provenance = asRecord(payload.provenance, "provenance");
  const cutoff = asRecord(payload.cutoff, "cutoff");
  const capability = asRecord(payload.capability, "capability");
  const candidate = asRecord(payload.l1_candidate, "l1_candidate");

  const gameId = payload.game_id;
  if (
    typeof gameId !== "string" ||
    !gameId ||
    gameId !== forecast.game_id ||
    gameId !== quote.event_id ||
    gameId !== candidate.game_id
  ) {
    refuse("REFUSE_GAME", "game_id / forecast / quote / candidate identity mismatch");
  }
  if (payload.admitted_capture_id !== candidate.capture_id) {
    refuse("REFUSE_IDENTITY", "admitted_capture_id != l1_candidate.capture_id");
  }
  if (
    typeof forecast.forecast_id !== "string" ||
    !/^[0-9a-f]{64}$/.test(forecast.forecast_id)
  ) {
    refuse("REFUSE_HASH", "forecast_id must be sha256 hex");
  }
  if (quote.period !== "full_game" || forecast.period !== "full_game") {
    refuse("REFUSE_PERIOD", "period must be full_game");
  }
  if (quote.side !== forecast.side) {
    refuse("REFUSE_SIGN", "quote.side != forecast.side");
  }
  const pointMargin = Number(forecast.point_margin);
  const line = Number(quote.line);
  if (!Number.isFinite(line) || !Number.isFinite(pointMargin)) {
    refuse("REFUSE_LINE", "quote.line / forecast.point_margin not finite");
  }
  const expectedLine = quote.side === "HOME" ? -pointMargin : pointMargin;
  if (line !== expectedLine) {
    refuse(
      line === -expectedLine ? "REFUSE_SIGN" : "REFUSE_LINE",
      `quote.line ${line} != expected ${expectedLine}`,
    );
  }
  if (
    quote.time !== cutoff.captured_at ||
    quote.time !== provenance.captured_at ||
    cutoff.captured_at !== provenance.captured_at
  ) {
    refuse("REFUSE_TIME", "quote.time must equal captured_at");
  }
  if (
    cutoff.decision_ts !== provenance.decision_ts ||
    cutoff.kickoff_ts !== provenance.kickoff_ts
  ) {
    refuse("REFUSE_CUTOFF", "cutoff timestamps must match provenance");
  }
  if (
    typeof cutoff.as_of_ts === "string" &&
    typeof cutoff.kickoff_ts === "string" &&
    cutoff.as_of_ts > cutoff.kickoff_ts
  ) {
    refuse("REFUSE_STALE", "as_of_ts after kickoff_ts");
  }
  const bits = capability.bits;
  if (!Array.isArray(bits) || !bits.includes("POINT_MARGIN")) {
    refuse("REFUSE_CAPABILITY", "POINT_MARGIN capability bit required");
  }

  return payload as unknown as FixtureChainRecord;
}

export function projectFixtureAbChain(raw: unknown): {
  api: ReturnType<typeof projectFixtureFairLinesApiResponse>;
  view: ReturnType<typeof projectFixtureFairLinesViewModel>;
  kei: ReturnType<typeof keiGamesFromFixtureFairLines>;
  headers: Record<string, string>;
} {
  const chain = assertFixtureChainRecord(raw);
  const input = {
    eligibility: chain.eligibility,
    consumer: "fixture" as const,
    quote: chain.quote,
    requestedOutput: chain.requested_output,
  };
  const api = projectFixtureFairLinesApiResponse(input);
  const view = projectFixtureFairLinesViewModel(api.board);
  const kei = keiGamesFromFixtureFairLines(api.board);
  const headers = pageDataCacheHeadersForFixture(api.board.eligibility);
  return { api, view, kei, headers };
}

export function writeThenReadFixtureChainCache(
  key: string,
  body: unknown,
  generation: number,
) {
  writeFixtureProjectionCache(key, body, generation);
  return readFixtureProjectionCache(key, generation);
}
