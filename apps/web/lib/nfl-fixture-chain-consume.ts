/**
 * t5194u / t5201u consume of a serialized FixtureChainRecord.
 * Mirrors services/model-service/.../consume_chain.py (A assemble semantics).
 * Canonical forecast_id vs trusted identity fields; parsed UTC + kickoff−90m;
 * exact numeric/enum + American price. CERT=0.
 */
import {
  AMERICAN_PRICE_MIN_ABS,
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

export const DECISION_OFFSET_BEFORE_KICKOFF_MINUTES = 90;

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

const TIME_FIELDS = [
  "source_published_at",
  "captured_at",
  "decision_ts",
  "kickoff_ts",
  "as_of_ts",
] as const;

const SHA256_HEX = /^[0-9a-f]{64}$/;
const HAS_TZ = /(?:Z|[+-]\d{2}:\d{2})$/;

function refuse(result: FixtureEligibilityResult, reason: string): never {
  throw new FixtureHardRefuse(result, reason);
}

function asRecord(value: unknown, label: string): Record<string, unknown> {
  if (value == null || typeof value !== "object" || Array.isArray(value)) {
    refuse("REFUSE_PARTIAL", `${label} must be an object`);
  }
  return value as Record<string, unknown>;
}

/** Python hashlib.sha256(utf-8).hexdigest() — browser-safe (no node:crypto). */
export function sha256Hex(message: string): string {
  const bytes = new TextEncoder().encode(message);
  return bytesToHex(sha256Bytes(bytes));
}

const K = new Uint32Array([
  0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1,
  0x923f82a4, 0xab1c5ed5, 0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3,
  0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174, 0xe49b69c1, 0xefbe4786,
  0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
  0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147,
  0x06ca6351, 0x14292967, 0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13,
  0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85, 0xa2bfe8a1, 0xa81a664b,
  0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
  0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a,
  0x5b9cca4f, 0x682e6ff3, 0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208,
  0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
]);

function rrot(n: number, b: number): number {
  return (n >>> b) | (n << (32 - b));
}

function sha256Bytes(bytes: Uint8Array): Uint8Array {
  const bitLen = bytes.length * 8;
  const withOne = bytes.length + 1;
  const padLen = (56 - (withOne % 64) + 64) % 64;
  const total = withOne + padLen + 8;
  const buf = new Uint8Array(total);
  buf.set(bytes);
  buf[bytes.length] = 0x80;
  const view = new DataView(buf.buffer);
  view.setUint32(total - 8, Math.floor(bitLen / 0x100000000));
  view.setUint32(total - 4, bitLen >>> 0);

  let h0 = 0x6a09e667;
  let h1 = 0xbb67ae85;
  let h2 = 0x3c6ef372;
  let h3 = 0xa54ff53a;
  let h4 = 0x510e527f;
  let h5 = 0x9b05688c;
  let h6 = 0x1f83d9ab;
  let h7 = 0x5be0cd19;
  const w = new Uint32Array(64);

  for (let i = 0; i < total; i += 64) {
    for (let j = 0; j < 16; j += 1) w[j] = view.getUint32(i + j * 4);
    for (let j = 16; j < 64; j += 1) {
      const s0 = rrot(w[j - 15], 7) ^ rrot(w[j - 15], 18) ^ (w[j - 15] >>> 3);
      const s1 = rrot(w[j - 2], 17) ^ rrot(w[j - 2], 19) ^ (w[j - 2] >>> 10);
      w[j] = (w[j - 16] + s0 + w[j - 7] + s1) >>> 0;
    }
    let a = h0;
    let b = h1;
    let c = h2;
    let d = h3;
    let e = h4;
    let f = h5;
    let g = h6;
    let h = h7;
    for (let j = 0; j < 64; j += 1) {
      const S1 = rrot(e, 6) ^ rrot(e, 11) ^ rrot(e, 25);
      const ch = (e & f) ^ (~e & g);
      const t1 = (h + S1 + ch + K[j] + w[j]) >>> 0;
      const S0 = rrot(a, 2) ^ rrot(a, 13) ^ rrot(a, 22);
      const maj = (a & b) ^ (a & c) ^ (b & c);
      const t2 = (S0 + maj) >>> 0;
      h = g;
      g = f;
      f = e;
      e = (d + t1) >>> 0;
      d = c;
      c = b;
      b = a;
      a = (t1 + t2) >>> 0;
    }
    h0 = (h0 + a) >>> 0;
    h1 = (h1 + b) >>> 0;
    h2 = (h2 + c) >>> 0;
    h3 = (h3 + d) >>> 0;
    h4 = (h4 + e) >>> 0;
    h5 = (h5 + f) >>> 0;
    h6 = (h6 + g) >>> 0;
    h7 = (h7 + h) >>> 0;
  }

  const out = new Uint8Array(32);
  const ov = new DataView(out.buffer);
  ov.setUint32(0, h0);
  ov.setUint32(4, h1);
  ov.setUint32(8, h2);
  ov.setUint32(12, h3);
  ov.setUint32(16, h4);
  ov.setUint32(20, h5);
  ov.setUint32(24, h6);
  ov.setUint32(28, h7);
  return out;
}

function bytesToHex(bytes: Uint8Array): string {
  return Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
}

/** Python json.dumps(float(n)) token — integers stay "3.0", not "3". */
function pythonFloatToken(n: number): string {
  if (!Number.isFinite(n)) {
    refuse("REFUSE_LINE", "point_margin is not finite");
  }
  if (Number.isInteger(n)) return `${n}.0`;
  return String(n);
}

/** A's synth.make_forecast_id — sha256(canonical_json({game_id,period,point_margin,side})). */
export function makeForecastId(opts: {
  game_id: string;
  period: string;
  side: string;
  point_margin: number;
}): string {
  const blob =
    `{"game_id":${JSON.stringify(opts.game_id)},` +
    `"period":${JSON.stringify(opts.period)},` +
    `"point_margin":${pythonFloatToken(opts.point_margin)},` +
    `"side":${JSON.stringify(opts.side)}}`;
  return sha256Hex(blob);
}

function requireFiniteNumber(value: unknown, field: string): number {
  if (typeof value === "boolean" || typeof value !== "number" || !Number.isFinite(value)) {
    refuse("REFUSE_LINE", `${field} is not a finite number (got ${typeof value})`);
  }
  return value;
}

function assertAmericanPrice(value: unknown): number {
  if (typeof value === "boolean" || typeof value !== "number" || !Number.isInteger(value)) {
    refuse("REFUSE_LINE", "quote.price must be an int American price");
  }
  if (value === 0 || Math.abs(value) < AMERICAN_PRICE_MIN_ABS) {
    refuse("REFUSE_LINE", `quote.price ${value} is not a valid American price`);
  }
  return value;
}

function parseUtc(
  value: unknown,
  field: string,
  result: FixtureEligibilityResult,
): Date {
  if (value == null || (typeof value === "string" && !value.trim())) {
    refuse(result, `${field} missing (no impute)`);
  }
  if (typeof value !== "string") {
    refuse(result, `${field} is not a valid UTC timestamp`);
  }
  const raw = value.trim();
  if (!HAS_TZ.test(raw)) {
    refuse(result, `${field} naive timestamp rejected (no impute to UTC)`);
  }
  const dt = new Date(raw);
  if (Number.isNaN(dt.getTime())) {
    refuse(result, `${field} is not a valid UTC timestamp`);
  }
  return dt;
}

function canonicalizeUtc(
  value: unknown,
  field: string,
  result: FixtureEligibilityResult,
): string {
  return parseUtc(value, field, result).toISOString().replace(/\.\d{3}Z$/, "Z");
}

export function expectedDecisionTs(kickoffTs: unknown): string {
  const kickoff = parseUtc(kickoffTs, "kickoff_ts", "REFUSE_CUTOFF");
  const decision = new Date(
    kickoff.getTime() - DECISION_OFFSET_BEFORE_KICKOFF_MINUTES * 60 * 1000,
  );
  return decision.toISOString().replace(/\.\d{3}Z$/, "Z");
}

function isSha256Hex(value: unknown): value is string {
  return typeof value === "string" && SHA256_HEX.test(value);
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

  const period = forecast.period;
  const side = forecast.side;
  if (period !== "full_game" || quote.period !== "full_game") {
    refuse("REFUSE_PERIOD", "period must be full_game");
  }
  if (side !== "HOME" && side !== "AWAY") {
    refuse("REFUSE_SIGN", "forecast.side must be HOME or AWAY");
  }
  if (quote.side !== side) {
    refuse("REFUSE_SIGN", "quote.side != forecast.side");
  }
  if (quote.side !== "HOME" && quote.side !== "AWAY") {
    refuse("REFUSE_SIGN", "quote.side must be HOME or AWAY");
  }

  const pointMargin = requireFiniteNumber(forecast.point_margin, "forecast.point_margin");
  const line = requireFiniteNumber(quote.line, "quote.line");
  const expectedLine = side === "HOME" ? -pointMargin : pointMargin;
  if (line !== expectedLine) {
    refuse(
      line === -expectedLine ? "REFUSE_SIGN" : "REFUSE_LINE",
      `quote.line ${line} != expected ${expectedLine}`,
    );
  }
  assertAmericanPrice(quote.price);

  if (!isSha256Hex(forecast.forecast_id)) {
    refuse("REFUSE_HASH", "forecast_id must be sha256 hex");
  }
  const derivedId = makeForecastId({
    game_id: gameId,
    period: String(period),
    side: String(side),
    point_margin: pointMargin,
  });
  if (forecast.forecast_id !== derivedId) {
    refuse(
      "REFUSE_HASH",
      "forecast_id does not match canonical digest of trusted identity fields",
    );
  }

  for (const field of TIME_FIELDS) {
    const cutoffMissing = !(field in cutoff) || cutoff[field] == null || cutoff[field] === "";
    const provMissing =
      !(field in provenance) || provenance[field] == null || provenance[field] === "";
    const result: FixtureEligibilityResult =
      field === "decision_ts" || field === "kickoff_ts" ? "REFUSE_CUTOFF" : "REFUSE_TIME";
    if (cutoffMissing) refuse(result, `cutoff.${field} missing`);
    if (provMissing) refuse(result, `provenance.${field} missing`);
  }

  const kickoffCut = canonicalizeUtc(cutoff.kickoff_ts, "cutoff.kickoff_ts", "REFUSE_CUTOFF");
  const kickoffProv = canonicalizeUtc(
    provenance.kickoff_ts,
    "provenance.kickoff_ts",
    "REFUSE_CUTOFF",
  );
  if (kickoffCut !== kickoffProv) {
    refuse("REFUSE_CUTOFF", "cutoff.kickoff_ts != provenance.kickoff_ts");
  }
  const expectedCut = expectedDecisionTs(kickoffProv);
  const decisionCut = canonicalizeUtc(
    cutoff.decision_ts,
    "cutoff.decision_ts",
    "REFUSE_CUTOFF",
  );
  const decisionProv = canonicalizeUtc(
    provenance.decision_ts,
    "provenance.decision_ts",
    "REFUSE_CUTOFF",
  );
  if (decisionCut !== decisionProv) {
    refuse("REFUSE_CUTOFF", "cutoff.decision_ts != provenance.decision_ts");
  }
  if (decisionCut !== expectedCut || decisionProv !== expectedCut) {
    refuse("REFUSE_CUTOFF", `decision_ts must be kickoff−90m (${expectedCut})`);
  }

  const capturedCut = canonicalizeUtc(cutoff.captured_at, "cutoff.captured_at", "REFUSE_TIME");
  const capturedProv = canonicalizeUtc(
    provenance.captured_at,
    "provenance.captured_at",
    "REFUSE_TIME",
  );
  const quoteTime = canonicalizeUtc(quote.time, "quote.time", "REFUSE_TIME");
  if (quoteTime !== capturedCut || quoteTime !== capturedProv) {
    refuse("REFUSE_TIME", "quote.time must equal captured_at");
  }

  const asOfCut = parseUtc(cutoff.as_of_ts, "cutoff.as_of_ts", "REFUSE_TIME");
  const asOfProv = parseUtc(provenance.as_of_ts, "provenance.as_of_ts", "REFUSE_TIME");
  const kickoffDt = parseUtc(kickoffProv, "kickoff_ts", "REFUSE_CUTOFF");
  if (asOfCut.getTime() > kickoffDt.getTime() || asOfProv.getTime() > kickoffDt.getTime()) {
    refuse("REFUSE_STALE", "as_of_ts after kickoff_ts");
  }
  if (asOfCut.getTime() !== asOfProv.getTime()) {
    refuse("REFUSE_TIME", "cutoff.as_of_ts != provenance.as_of_ts");
  }

  const bits = capability.bits;
  if (!Array.isArray(bits) || !bits.includes("POINT_MARGIN")) {
    refuse("REFUSE_CAPABILITY", "POINT_MARGIN capability bit required");
  }

  return payload as unknown as FixtureChainRecord;
}
