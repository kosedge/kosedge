/**
 * P0 2026-09-11 — CFB Edge Board public visibility kill switch.
 * Ryan 2026-09-15 — extend the same fail-closed pattern to NFL public
 * number surfaces (Edge Board, edges, KEI/fair, power, week-stale slates).
 *
 * Visibility / publishing only. Does not change model math, KEI, odds,
 * assemble research libs, or other sports.
 *
 * Flip `CFB_EDGE_BOARD_PUBLIC_ENABLED` / `NFL_EDGE_BOARD_PUBLIC_ENABLED`
 * to `true` only after CoS CLEAR / re-enable (validated current market coverage,
 * trustworthy source status, market as_of, canonical game joins, and
 * sanity checks on extreme model-vs-market gaps).
 *
 * Product 2026-09-17 — NFL Fair Lines PRODUCTION-CERT harness (not a CLEAR):
 * independent spread / ML / total gates default false; PLAY / Kelly stay
 * suppressed; certified `run_id` + `sha256` slot stays unbound. Public paint
 * fail-closes on missing / mismatched / stale / rejected-practice cert.
 * `pe_drive_poss_v1` sha `b5ee9d80…` is a rejected practice SHA only.
 * Production target is `pe_drive_poss_v2` (pending freeze). No remat, no
 * invented numbers, no DFS / Line Curve / CFB work from this harness.
 *
 * Internal QA / research:
 *   - `/api/edge-board/{sport}/today` stays secret-gated
 *   - set `CFB_EDGE_BOARD_INTERNAL=1` or `NFL_EDGE_BOARD_INTERNAL=1`
 *     (server) to serve the public board for QA without flipping the
 *     public constant
 *   - `NEXT_PUBLIC_CFB_EDGE_BOARD_INTERNAL=1` /
 *     `NEXT_PUBLIC_NFL_EDGE_BOARD_INTERNAL=1` also restores chrome
 */

export const CFB_EDGE_BOARD_PUBLIC_ENABLED = false;
export const NFL_EDGE_BOARD_PUBLIC_ENABLED = false;

/** Independent NFL Fair Lines market gates. Not a public CLEAR. */
export const NFL_FAIR_LINES_PUBLIC_SPREAD_ENABLED = false;
export const NFL_FAIR_LINES_PUBLIC_ML_ENABLED = false;
export const NFL_FAIR_LINES_PUBLIC_TOTAL_ENABLED = false;

/** Stake chrome — stays suppressed until a separate Ryan / CoS authorization. */
export const NFL_FAIR_LINES_PLAY_ENABLED = false;
export const NFL_FAIR_LINES_KELLY_ENABLED = false;

/**
 * Certified public Fair Lines run. Unbound until CoS / Ryan stamp a real
 * `run_id` + sha256. Do not invent a production hash here.
 * Do **not** bind this slot to `pe_drive_poss_v1` (rejected practice SHA).
 * Production target is `pe_drive_poss_v2` pending freeze.
 */
export const NFL_FAIR_LINES_CERTIFIED_RUN_ID: string | null = null;
export const NFL_FAIR_LINES_CERTIFIED_SHA256: string | null = null;
export const NFL_FAIR_LINES_CERTIFIED_AT: string | null = null;
export const NFL_FAIR_LINES_CERT_MAX_AGE_HOURS = 168;

/**
 * War-room practice artifact (Alex 2026-09-17). All five gates FAIL.
 * Recorded for fail-closed / provenance smoke only. Not a production bind.
 */
export const NFL_FAIR_LINES_WARROOM_ARTIFACT_ID = "pe_drive_poss_v1";
export const NFL_FAIR_LINES_WARROOM_ARTIFACT_VERSION =
  "1.0.0-warroom-20260917";
export const NFL_FAIR_LINES_WARROOM_ARTIFACT_SHA256 =
  "b5ee9d80494bbc13b989174af0676afb1831a4cb11e678f2f243ac469b92d36b";
export const NFL_FAIR_LINES_WARROOM_ARTIFACT_STATUS =
  "REJECTED_NO_CLEAR" as const;

/** Authorized production target once v2 freezes with a new checksum. */
export const NFL_FAIR_LINES_PRODUCTION_ARTIFACT_ID = "pe_drive_poss_v2";
export const NFL_FAIR_LINES_PRODUCTION_ARTIFACT_SHA256: string | null = null;
export const NFL_FAIR_LINES_PRODUCTION_ARTIFACT_STATUS =
  "PENDING_FREEZE" as const;

export type NflFairLinesMarket = "spread" | "ml" | "total";

export type NflFairLinesCertBindReason =
  | "ok"
  | "unbound_certified_slot"
  | "missing_run_id"
  | "missing_sha256"
  | "invalid_sha256"
  | "run_id_mismatch"
  | "sha256_mismatch"
  | "rejected_practice_sha"
  | "missing_certified_at"
  | "stale";

export type NflFairLinesCertifiedBinding = {
  runId: string | null;
  sha256: string | null;
  certifiedAt: string | null;
  maxAgeHours: number;
};

export type NflFairLinesCertObserved = {
  runId?: string | null;
  sha256?: string | null;
  at?: Date | string | null;
};

export type NflFairLinesCertBindResult = {
  ok: boolean;
  reason: NflFairLinesCertBindReason;
  expectedRunId: string | null;
  expectedSha256: string | null;
  observedRunId: string | null;
  observedSha256: string | null;
};

const SHA256_HEX = /^[a-f0-9]{64}$/;

/** Customer heading on parked NFL/CFB number surfaces. */
export const FOOTBALL_PUBLIC_NUMBERS_HEADING = "Coming soon";

export const CFB_EDGE_BOARD_UNAVAILABLE_MESSAGE =
  "CFB Edge Board temporarily unavailable while market coverage is being validated.";

export const NFL_EDGE_BOARD_UNAVAILABLE_MESSAGE =
  "NFL numbers temporarily unavailable while market coverage is being validated.";

export const CFB_EDGE_BOARD_UNAVAILABLE_CODE = "cfb_edge_board_unavailable";
export const NFL_EDGE_BOARD_UNAVAILABLE_CODE = "nfl_edge_board_unavailable";

const FOOTBALL_CUSTOMER_TAG_KEYS = [
  "publishTag",
  "actionLabel",
  "tag",
  "tagLine",
  "tagOU",
  "actionLabelLine",
  "actionLabelOU",
  "playLine",
  "playOU",
  "publishTagSpread",
  "publishTagTotal",
  "publishTagMl",
] as const;

function envFlagTrue(name: string): boolean {
  const v = process.env[name];
  if (typeof v !== "string") return false;
  const n = v.trim().toLowerCase();
  return n === "1" || n === "true" || n === "yes";
}

function sportKey(sport: string | null | undefined): string {
  return String(sport ?? "")
    .trim()
    .toLowerCase();
}

/** Server/QA override — never on in production unless explicitly set. */
export function isCfbEdgeBoardInternalOverride(): boolean {
  return (
    envFlagTrue("CFB_EDGE_BOARD_INTERNAL") ||
    envFlagTrue("NEXT_PUBLIC_CFB_EDGE_BOARD_INTERNAL")
  );
}

export function isNflEdgeBoardInternalOverride(): boolean {
  return (
    envFlagTrue("NFL_EDGE_BOARD_INTERNAL") ||
    envFlagTrue("NEXT_PUBLIC_NFL_EDGE_BOARD_INTERNAL")
  );
}

/** Customer chrome + assemble + tag publish. */
export function isCfbEdgeBoardCustomerEnabled(): boolean {
  return CFB_EDGE_BOARD_PUBLIC_ENABLED || isCfbEdgeBoardInternalOverride();
}

export function isNflEdgeBoardCustomerEnabled(): boolean {
  return NFL_EDGE_BOARD_PUBLIC_ENABLED || isNflEdgeBoardInternalOverride();
}

export function isCfbSportKey(sport: string | null | undefined): boolean {
  return sportKey(sport) === "cfb";
}

export function isNflSportKey(sport: string | null | undefined): boolean {
  return sportKey(sport) === "nfl";
}

export function isFootballSportKey(sport: string | null | undefined): boolean {
  return isCfbSportKey(sport) || isNflSportKey(sport);
}

export function isCfbEdgeBoardCustomerDisabled(sport?: string | null): boolean {
  return isCfbSportKey(sport) && !isCfbEdgeBoardCustomerEnabled();
}

export function isNflEdgeBoardCustomerDisabled(sport?: string | null): boolean {
  return isNflSportKey(sport) && !isNflEdgeBoardCustomerEnabled();
}

/** NFL or CFB public number surface is fail-closed. */
export function isFootballPublicNumbersDisabled(
  sport?: string | null,
): boolean {
  return (
    isCfbEdgeBoardCustomerDisabled(sport) ||
    isNflEdgeBoardCustomerDisabled(sport)
  );
}

export function isCfbEdgeBoardHref(href: string | null | undefined): boolean {
  if (!href) return false;
  return /(?:^|\/)edge-board\/cfb(?:[/?#]|$)/.test(href);
}

export function isNflEdgeBoardHref(href: string | null | undefined): boolean {
  if (!href) return false;
  return /(?:^|\/)edge-board\/nfl(?:[/?#]|$)/.test(href);
}

export function isFootballEdgeBoardHref(
  href: string | null | undefined,
): boolean {
  return isCfbEdgeBoardHref(href) || isNflEdgeBoardHref(href);
}

/**
 * Customer hrefs that mint house KEI / fair / PLAY / edge / power numbers
 * for NFL or CFB. Used to drop chrome while the kill switch is off.
 */
export function isFootballPublicNumberHref(
  href: string | null | undefined,
): boolean {
  if (!href) return false;
  if (isFootballEdgeBoardHref(href)) return true;
  return (
    /(?:^|\/)pro\/(?:nfl|cfb)\/(?:edges|fair-lines|slate)(?:[/?#]|$)/.test(
      href,
    ) ||
    /(?:^|\/)pro\/power-ratings\/(?:nfl|cfb)(?:[/?#]|$)/.test(href) ||
    /(?:^|\/)pro\/kei-lines\/(?:nfl|cfb)(?:[/?#]|$)/.test(href) ||
    /(?:^|\/)pro\/nfl\/fantasy\/pickem(?:[/?#]|$)/.test(href) ||
    /(?:^|\/)pro\/cfb\/teams(?:[/?#]|$)/.test(href)
  );
}

function footballCustomerEnabledForKey(key: string): boolean {
  if (key === "cfb") return isCfbEdgeBoardCustomerEnabled();
  if (key === "nfl") return isNflEdgeBoardCustomerEnabled();
  return true;
}

/** Sports shown on the public/pro Edge Board selector. */
export function publicEdgeBoardSports<T extends { key: string }>(
  sports: readonly T[],
): T[] {
  return sports.filter((s) => footballCustomerEnabledForKey(s.key));
}

/** Public Edge Board sport keys (infrastructure list may still include cfb/nfl). */
export function publicEdgeBoardSportKeys(keys: readonly string[]): string[] {
  return keys.filter((k) => footballCustomerEnabledForKey(k));
}

/**
 * Customer Edge Board href, or null when that football sport is public-disabled.
 * Use to hide CTAs; the canonical `/edge-board/{sport}` URL still fail-closes.
 */
export function publicEdgeBoardHref(
  sport: string | null | undefined,
): string | null {
  const key = sportKey(sport);
  if (!key) return null;
  if (isFootballPublicNumbersDisabled(key)) return null;
  if (key === "cfb") return "/edge-board/cfb?week=1";
  return `/edge-board/${key}`;
}

/** Drop football Edge Board links from customer chrome while the kill switch is off. */
export function withoutCfbEdgeBoardHrefs<T extends { href?: string | null }>(
  items: readonly T[],
): T[] {
  return items.filter((item) => {
    const href = item.href;
    if (isCfbEdgeBoardHref(href) && !isCfbEdgeBoardCustomerEnabled()) {
      return false;
    }
    if (isNflEdgeBoardHref(href) && !isNflEdgeBoardCustomerEnabled()) {
      return false;
    }
    return true;
  });
}

/** Drop NFL/CFB house-number chrome (board, edges, KEI, power, stale slates). */
export function withoutFootballPublicNumberHrefs<
  T extends { href?: string | null },
>(items: readonly T[]): T[] {
  return items.filter((item) => {
    const href = item.href;
    if (!isFootballPublicNumberHref(href)) return true;
    if (isCfbEdgeBoardHref(href) || /(?:^|\/)pro\/cfb\//.test(href ?? "")) {
      return isCfbEdgeBoardCustomerEnabled();
    }
    if (
      isNflEdgeBoardHref(href) ||
      /(?:^|\/)pro\/(?:nfl|power-ratings\/nfl)/.test(href ?? "")
    ) {
      return isNflEdgeBoardCustomerEnabled();
    }
    return !isFootballPublicNumbersDisabled(
      /\/cfb(?:\/|$)/.test(href ?? "") ? "cfb" : "nfl",
    );
  });
}

export function customerCtaHref(
  href: string | null | undefined,
): string | null | undefined {
  if (href == null || href === "") return href;
  if (isCfbEdgeBoardHref(href) && !isCfbEdgeBoardCustomerEnabled()) {
    return null;
  }
  if (isNflEdgeBoardHref(href) && !isNflEdgeBoardCustomerEnabled()) {
    return null;
  }
  return href;
}

export type CfbCustomerPublishTag = "PLAY" | "LEAN" | "PASS";

/**
 * Customer publish vocabulary. Returns undefined while public-disabled
 * (zero PLAY/LEAN/PASS). Does not change `cfbEdgeTag` math.
 */
export function cfbCustomerPublishTag(
  absEdge: number | null | undefined,
  tagger: (
    absEdge: number | null | undefined,
    market?: "spread" | "total",
  ) => CfbCustomerPublishTag,
  market: "spread" | "total" = "spread",
): CfbCustomerPublishTag | undefined {
  if (!isCfbEdgeBoardCustomerEnabled()) return undefined;
  return tagger(absEdge, market);
}

/** Strip PLAY/LEAN/PASS/value tag fields from a customer assemble/paint row. */
export function stripCfbCustomerEdgeTags<T extends Record<string, unknown>>(
  row: T,
): T {
  const out: Record<string, unknown> = { ...row };
  for (const key of FOOTBALL_CUSTOMER_TAG_KEYS) {
    delete out[key];
  }
  if (
    out.decision &&
    typeof out.decision === "object" &&
    !Array.isArray(out.decision)
  ) {
    const decision = { ...(out.decision as Record<string, unknown>) };
    delete decision.publishTag;
    delete decision.actionLabel;
    delete decision.tag;
    out.decision = decision;
  }
  return out as T;
}

export function stripCfbCustomerEdgeTagRows<T extends Record<string, unknown>>(
  rows: readonly T[],
): T[] {
  return rows.map((row) => stripCfbCustomerEdgeTags(row));
}

export function footballPublicNumbersUnavailableMessage(
  sport?: string | null,
): string {
  if (isNflSportKey(sport)) return NFL_EDGE_BOARD_UNAVAILABLE_MESSAGE;
  return CFB_EDGE_BOARD_UNAVAILABLE_MESSAGE;
}

export function footballPublicNumbersUnavailableCode(
  sport?: string | null,
): string {
  if (isNflSportKey(sport)) return NFL_EDGE_BOARD_UNAVAILABLE_CODE;
  return CFB_EDGE_BOARD_UNAVAILABLE_CODE;
}

type AssembleUnavailablePayload = {
  error: string;
  message: string;
  rows: [];
  games: 0;
  week0Count: 0;
  week1Count: 0;
  week2Count: 0;
  requestedWeek: null;
  requestedWeekCount: 0;
  fullCount: 0;
  weeks: [];
  linesAsOf: null;
};

export function footballPublicNumbersAssembleUnavailablePayload(
  sport?: string | null,
): AssembleUnavailablePayload {
  return {
    error: footballPublicNumbersUnavailableCode(sport),
    message: footballPublicNumbersUnavailableMessage(sport),
    rows: [],
    games: 0,
    week0Count: 0,
    week1Count: 0,
    week2Count: 0,
    requestedWeek: null,
    requestedWeekCount: 0,
    fullCount: 0,
    weeks: [],
    linesAsOf: null,
  };
}

export function cfbEdgeBoardAssembleUnavailablePayload(): AssembleUnavailablePayload {
  return footballPublicNumbersAssembleUnavailablePayload("cfb");
}

export function nflEdgeBoardAssembleUnavailablePayload(): AssembleUnavailablePayload {
  return footballPublicNumbersAssembleUnavailablePayload("nfl");
}

function normalizeCertToken(
  value: string | null | undefined,
): string | null {
  if (typeof value !== "string") return null;
  const n = value.trim();
  return n ? n : null;
}

function normalizeSha256Hex(
  value: string | null | undefined,
): string | null {
  const n = normalizeCertToken(value);
  return n ? n.toLowerCase() : null;
}

export function isNflFairLinesRejectedPracticeSha(
  sha256: string | null | undefined,
): boolean {
  return normalizeSha256Hex(sha256) === NFL_FAIR_LINES_WARROOM_ARTIFACT_SHA256;
}

export function nflFairLinesWarroomPracticeArtifact() {
  return {
    artifactId: NFL_FAIR_LINES_WARROOM_ARTIFACT_ID,
    version: NFL_FAIR_LINES_WARROOM_ARTIFACT_VERSION,
    sha256: NFL_FAIR_LINES_WARROOM_ARTIFACT_SHA256,
    status: NFL_FAIR_LINES_WARROOM_ARTIFACT_STATUS,
    alex: "NO_CLEAR" as const,
  };
}

export function nflFairLinesCertifiedBinding(): NflFairLinesCertifiedBinding {
  return {
    runId: NFL_FAIR_LINES_CERTIFIED_RUN_ID,
    sha256: NFL_FAIR_LINES_CERTIFIED_SHA256,
    certifiedAt: NFL_FAIR_LINES_CERTIFIED_AT,
    maxAgeHours: NFL_FAIR_LINES_CERT_MAX_AGE_HOURS,
  };
}

export function isNflFairLinesMarketPublicEnabled(
  market: NflFairLinesMarket,
): boolean {
  if (market === "spread") return NFL_FAIR_LINES_PUBLIC_SPREAD_ENABLED;
  if (market === "ml") return NFL_FAIR_LINES_PUBLIC_ML_ENABLED;
  return NFL_FAIR_LINES_PUBLIC_TOTAL_ENABLED;
}

export function nflFairLinesPublicEnabledMarkets(): NflFairLinesMarket[] {
  return (["spread", "ml", "total"] as const).filter((market) =>
    isNflFairLinesMarketPublicEnabled(market),
  );
}

export function isNflFairLinesAnyMarketPublicEnabled(): boolean {
  return nflFairLinesPublicEnabledMarkets().length > 0;
}

export function isNflFairLinesPlayEnabled(): boolean {
  return NFL_FAIR_LINES_PLAY_ENABLED;
}

export function isNflFairLinesKellyEnabled(): boolean {
  return NFL_FAIR_LINES_KELLY_ENABLED;
}

function certBindResult(
  reason: NflFairLinesCertBindReason,
  expected: NflFairLinesCertifiedBinding,
  observed: NflFairLinesCertObserved,
): NflFairLinesCertBindResult {
  return {
    ok: reason === "ok",
    reason,
    expectedRunId: normalizeCertToken(expected.runId),
    expectedSha256: normalizeSha256Hex(expected.sha256),
    observedRunId: normalizeCertToken(observed.runId),
    observedSha256: normalizeSha256Hex(observed.sha256),
  };
}

/**
 * Bind an observed Fair Lines run to the certified `run_id` + sha256.
 * Fail-closed on unbound / missing / mismatched / stale. Does not invent
 * a certified hash and does not rematerialize numbers.
 */
export function bindNflFairLinesCertifiedRun(
  observed: NflFairLinesCertObserved = {},
  expected: NflFairLinesCertifiedBinding = nflFairLinesCertifiedBinding(),
): NflFairLinesCertBindResult {
  const expectedRunId = normalizeCertToken(expected.runId);
  const expectedSha256 = normalizeSha256Hex(expected.sha256);
  if (!expectedRunId || !expectedSha256) {
    return certBindResult("unbound_certified_slot", expected, observed);
  }
  if (!SHA256_HEX.test(expectedSha256)) {
    return certBindResult("invalid_sha256", expected, observed);
  }
  if (expectedSha256 === NFL_FAIR_LINES_WARROOM_ARTIFACT_SHA256) {
    return certBindResult("rejected_practice_sha", expected, observed);
  }

  const observedRunId = normalizeCertToken(observed.runId);
  const observedSha256 = normalizeSha256Hex(observed.sha256);
  if (!observedRunId) {
    return certBindResult("missing_run_id", expected, observed);
  }
  if (!observedSha256) {
    return certBindResult("missing_sha256", expected, observed);
  }
  if (!SHA256_HEX.test(observedSha256)) {
    return certBindResult("invalid_sha256", expected, observed);
  }
  if (observedSha256 === NFL_FAIR_LINES_WARROOM_ARTIFACT_SHA256) {
    return certBindResult("rejected_practice_sha", expected, observed);
  }
  if (observedRunId !== expectedRunId) {
    return certBindResult("run_id_mismatch", expected, observed);
  }
  if (observedSha256 !== expectedSha256) {
    return certBindResult("sha256_mismatch", expected, observed);
  }

  const certifiedAtMs = expected.certifiedAt
    ? Date.parse(expected.certifiedAt)
    : Number.NaN;
  if (!Number.isFinite(certifiedAtMs)) {
    return certBindResult("missing_certified_at", expected, observed);
  }

  const atMs =
    observed.at instanceof Date
      ? observed.at.getTime()
      : observed.at
        ? Date.parse(String(observed.at))
        : Date.now();
  if (!Number.isFinite(atMs)) {
    return certBindResult("stale", expected, observed);
  }

  const maxAgeHours = Number.isFinite(expected.maxAgeHours)
    ? expected.maxAgeHours
    : NFL_FAIR_LINES_CERT_MAX_AGE_HOURS;
  const maxAgeMs = Math.max(0, maxAgeHours) * 60 * 60 * 1000;
  if (atMs - certifiedAtMs > maxAgeMs) {
    return certBindResult("stale", expected, observed);
  }

  return certBindResult("ok", expected, observed);
}

/**
 * Public certified paint — requires the master NFL public flag, at least one
 * independent market gate, and a valid cert bind. INTERNAL is not a CLEAR.
 */
export function isNflFairLinesCertifiedPublicPaintAllowed(
  observed: NflFairLinesCertObserved = {},
  market?: NflFairLinesMarket,
): boolean {
  if (!NFL_EDGE_BOARD_PUBLIC_ENABLED) return false;
  if (market) {
    if (!isNflFairLinesMarketPublicEnabled(market)) return false;
  } else if (!isNflFairLinesAnyMarketPublicEnabled()) {
    return false;
  }
  return bindNflFairLinesCertifiedRun(observed).ok;
}

/**
 * NFL Fair Lines customer page / API. Coming soon stays on while the public
 * flag is off. INTERNAL QA may inspect the research board without a CLEAR.
 * A later public flip still fail-closes without market gates + cert bind.
 */
export function isNflFairLinesCustomerSurfaceClosed(
  observed: NflFairLinesCertObserved = {},
): boolean {
  if (isFootballPublicNumbersDisabled("nfl")) return true;
  if (isNflEdgeBoardInternalOverride()) return false;
  return !isNflFairLinesCertifiedPublicPaintAllowed(observed);
}
