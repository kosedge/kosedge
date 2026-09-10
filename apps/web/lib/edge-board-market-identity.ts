/**
 * Canonical Edge Board market identity (INC-2026-09-10 follow-on).
 *
 * Quote:  Q = (event, sport, market, period, side, line, price, book, timestamp)
 * Model:  T = (event, sport, market, period, side)
 * Legal comparison ONLY when T ≡ Q_target BEFORE Edge = f(Model, Market).
 *
 * Book + timestamp stay attached to the selected decision quote through
 * calc/render. Missing / ambiguous identity → FAIL CLOSED.
 *
 * Certification comes from Odds market keys + commence vs quote as-of.
 * NEVER infer compatibility from line magnitude (a 3.5 total is not F5).
 */

export const FULL_GAME_PREGAME_PERIODS = [
  "fg",
  "fg_pregame",
  "full",
  "full_game",
  "full-game",
  "regulation",
  "game",
] as const;

/** In-play remaining of the featured FG family — not comparable to pregame T. */
export const FULL_GAME_LIVE_PERIODS = ["fg_live", "live"] as const;

export const FIRST_FIVE_PERIODS = ["1st5", "f5"] as const;

export const FEATURED_FULL_GAME_ODDS_KEYS = [
  "totals",
  "h2h",
  "spreads",
] as const;

export const FIRST_FIVE_INNINGS_ODDS_KEYS = [
  "totals_1st_5_innings",
  "h2h_1st_5_innings",
  "spreads_1st_5_innings",
] as const;

/** Canonical compare token after alias fold. */
export type CanonicalPeriod = "fg" | "fg_live" | "1st5" | string;

export type QuoteIdentity = {
  event?: string | null;
  sport?: string | null;
  market?: string | null;
  period?: string | null;
  side?: string | null;
  line?: string | number | null;
  price?: string | number | null;
  book?: string | null;
  timestamp?: string | null;
};

/** T — model/KEI target. No book, line, or price. */
export type ModelTargetIdentity = {
  event?: string | null;
  sport?: string | null;
  market?: string | null;
  period?: string | null;
  side?: string | null;
};

export function parseTimeMs(raw: string | null | undefined): number | null {
  if (raw == null || !String(raw).trim()) return null;
  const ms = Date.parse(String(raw).trim());
  return Number.isFinite(ms) ? ms : null;
}

export function normalizeIdentityToken(
  raw: string | null | undefined,
): string | null {
  if (raw == null) return null;
  const p = String(raw).trim().toLowerCase();
  return p || null;
}

export function isFeaturedFullGameOddsKey(
  marketKey: string | null | undefined,
): boolean {
  const k = normalizeIdentityToken(marketKey);
  return (
    k != null && (FEATURED_FULL_GAME_ODDS_KEYS as readonly string[]).includes(k)
  );
}

export function isFirstFiveInningsOddsKey(
  marketKey: string | null | undefined,
): boolean {
  const k = normalizeIdentityToken(marketKey);
  if (!k) return false;
  if ((FIRST_FIVE_INNINGS_ODDS_KEYS as readonly string[]).includes(k)) {
    return true;
  }
  return k.includes("1st_5_innings") || k.includes("first_5_innings");
}

/**
 * Featured FG slot selector. Exact `totals` / `h2h` / `spreads` only.
 * Never falls back to F5 / alternate / derivative keys by event id.
 */
export function selectFeaturedFullGameMarket<T extends { key?: string }>(
  markets: T[] | null | undefined,
  featuredKey: (typeof FEATURED_FULL_GAME_ODDS_KEYS)[number],
): T | null {
  if (!markets?.length) return null;
  return (
    markets.find((m) => normalizeIdentityToken(m.key) === featuredKey) ?? null
  );
}

export function isFullGamePregamePeriod(
  period: string | null | undefined,
): boolean {
  const p = normalizeIdentityToken(period);
  if (!p) return false;
  return (FULL_GAME_PREGAME_PERIODS as readonly string[]).includes(p);
}

export function isFullGameLivePeriod(
  period: string | null | undefined,
): boolean {
  const p = normalizeIdentityToken(period);
  if (!p) return false;
  return (FULL_GAME_LIVE_PERIODS as readonly string[]).includes(p);
}

export function isFirstFivePeriod(period: string | null | undefined): boolean {
  const p = normalizeIdentityToken(period);
  if (!p) return false;
  return (FIRST_FIVE_PERIODS as readonly string[]).includes(p);
}

/**
 * Fold aliases to a compare token. Unknown non-empty tokens stay themselves
 * so they cannot silently equal `fg`.
 */
export function canonicalComparePeriod(
  period: string | null | undefined,
): CanonicalPeriod | null {
  const p = normalizeIdentityToken(period);
  if (!p) return null;
  if (isFullGamePregamePeriod(p)) return "fg";
  if (isFullGameLivePeriod(p)) return "fg_live";
  if (isFirstFivePeriod(p)) return "1st5";
  return p;
}

/**
 * Period family from the Odds market key alone (no commence, no line size).
 * Featured keys → `fg` family (commence split happens in stampOddsMarketPeriod).
 * F5 keys → `1st5`. Other known derivatives → a non-FG token. Unknown → null.
 */
export function periodFamilyFromOddsMarketKey(
  marketKey: string | null | undefined,
): string | null {
  const k = normalizeIdentityToken(marketKey);
  if (!k) return null;
  if (isFeaturedFullGameOddsKey(k)) return "fg";
  if (isFirstFiveInningsOddsKey(k)) return "1st5";
  if (k.includes("1st_3_innings") || k.includes("first_3_innings"))
    return "1st3";
  if (k.includes("1st_7_innings") || k.includes("first_7_innings"))
    return "1st7";
  if (k.startsWith("alternate_") || k.includes("alternate")) return "alternate";
  return null;
}

/**
 * Odds in-play: event has commenced as of the quote.
 * Prefer commenceTime ≤ linesAsOf. MLB may fall back to wall/Odds clock
 * when as-of is missing (never invent as-of — only a commenced check).
 */
export function isOddsInPlayEvent(args: {
  commenceTime?: string | null;
  linesAsOf?: string | null;
  nowMs?: number;
  allowWallClockOddsRule?: boolean;
}): boolean {
  const commenceMs = parseTimeMs(args.commenceTime);
  if (commenceMs == null) return false;
  const asOfMs = parseTimeMs(args.linesAsOf);
  if (asOfMs != null) return commenceMs <= asOfMs;
  if (!args.allowWallClockOddsRule) return false;
  const clock = args.nowMs ?? Date.now();
  return commenceMs <= clock;
}

export type StampOddsPeriodArgs = {
  marketKey: string | null | undefined;
  commenceTime?: string | null;
  linesAsOf?: string | null;
  sport?: string | null;
  nowMs?: number;
};

/**
 * Stamp Q.period from Odds rules (key + commence vs quote as-of).
 *
 * - Featured `totals`/`h2h`/`spreads` + certified not commenced → `fg`
 * - Same featured key + in-play → `fg_live` (not comparable to pregame T)
 * - `totals_1st_5_innings` (etc.) → `1st5` regardless of commence
 * - Cannot certify → null (fail closed downstream)
 */
export function stampOddsMarketPeriod(
  args: StampOddsPeriodArgs,
): string | null {
  const family = periodFamilyFromOddsMarketKey(args.marketKey);
  if (!family) return null;
  if (family !== "fg") return family;

  const sport = normalizeIdentityToken(args.sport);
  const allowWall = sport === "mlb";
  const inPlay = isOddsInPlayEvent({
    commenceTime: args.commenceTime,
    linesAsOf: args.linesAsOf,
    nowMs: args.nowMs,
    allowWallClockOddsRule: allowWall,
  });
  if (inPlay) return "fg_live";

  const commenceMs = parseTimeMs(args.commenceTime);
  if (commenceMs == null) return null;
  const asOfMs = parseTimeMs(args.linesAsOf);
  if (asOfMs != null && commenceMs > asOfMs) return "fg";
  if (allowWall) {
    const clock = args.nowMs ?? Date.now();
    if (commenceMs > clock) return "fg";
  }
  // Other sports without as-of: cannot certify pregame vs live.
  return null;
}

function tokensEqual(
  a: string | null | undefined,
  b: string | null | undefined,
): boolean {
  const na = normalizeIdentityToken(a);
  const nb = normalizeIdentityToken(b);
  if (na == null || nb == null) return false;
  return na === nb;
}

function eventsEquivalent(
  a: string | null | undefined,
  b: string | null | undefined,
): boolean {
  const na = normalizeIdentityToken(a)?.replace(/\s+/g, " ");
  const nb = normalizeIdentityToken(b)?.replace(/\s+/g, " ");
  if (!na || !nb) return false;
  return na === nb;
}

function marketsEquivalent(
  a: string | null | undefined,
  b: string | null | undefined,
): boolean {
  const na = normalizeIdentityToken(a);
  const nb = normalizeIdentityToken(b);
  if (!na || !nb) return false;
  if (na === nb) return true;
  const total = (m: string) => m === "total" || m === "totals" || m === "ou";
  if (total(na) && total(nb)) return true;
  const ml = (m: string) => m === "moneyline" || m === "ml" || m === "h2h";
  if (ml(na) && ml(nb)) return true;
  const spread = (m: string) => m === "spread" || m === "spreads" || m === "rl";
  if (spread(na) && spread(nb)) return true;
  return false;
}

/**
 * T ≡ Q_target. Required: period (after alias fold). Optional event / sport /
 * market / side must match when both sides provide them. Missing period on
 * either side → not compatible (fail closed).
 */
export function quoteTargetEqualsModel(
  target: ModelTargetIdentity,
  quote: QuoteIdentity,
): boolean {
  const tPeriod = canonicalComparePeriod(target.period);
  const qPeriod = canonicalComparePeriod(quote.period);
  if (tPeriod == null || qPeriod == null) return false;
  if (tPeriod !== qPeriod) return false;

  if (target.sport && quote.sport && !tokensEqual(target.sport, quote.sport)) {
    return false;
  }
  if (
    target.market &&
    quote.market &&
    !marketsEquivalent(target.market, quote.market)
  ) {
    return false;
  }
  if (
    target.event &&
    quote.event &&
    !eventsEquivalent(target.event, quote.event)
  ) {
    return false;
  }
  if (target.side && quote.side && !tokensEqual(target.side, quote.side)) {
    return false;
  }
  return true;
}

/** KEI / fair totals are full-game pregame model targets. */
export const MODEL_TOTAL_PERIOD_FG = "fg";

const BOOK_KEY_ALIASES: Record<string, string> = {
  dk: "draftkings",
  "draft kings": "draftkings",
  fd: "fanduel",
  "fan duel": "fanduel",
  mgm: "betmgm",
  "bet mgm": "betmgm",
};

/**
 * Canonical sportsbook key for identity compare. Display names fold to keys.
 * Unknown non-empty tokens stay themselves (cannot silently equal another book).
 */
export function normalizeBookIdentity(
  raw: string | null | undefined,
): string | null {
  const p = normalizeIdentityToken(raw)?.replace(/[_-]+/g, " ");
  if (!p) return null;
  if (BOOK_KEY_ALIASES[p]) return BOOK_KEY_ALIASES[p];
  return p.replace(/\s+/g, "");
}

/**
 * Displayed decision book must equal the quote used for edge calc.
 * Missing either side → cannot certify a mismatch (null).
 */
export function booksEquivalent(
  displayed: string | null | undefined,
  edgeQuote: string | null | undefined,
): boolean | null {
  const a = normalizeBookIdentity(displayed);
  const b = normalizeBookIdentity(edgeQuote);
  if (a == null || b == null) return null;
  return a === b;
}

function presentTimestamp(raw: string | null | undefined): {
  present: boolean;
  ms: number | null;
} {
  if (raw == null || !String(raw).trim()) {
    return { present: false, ms: null };
  }
  return { present: true, ms: parseTimeMs(raw) };
}

export type QuoteAsOfCompatArgs = {
  linesAsOf?: string | null;
  modelAsOf?: string | null;
  commenceTime?: string | null;
  /** Explicit target expiry — quote after this cannot be this T. */
  modelValidUntil?: string | null;
  /** Vintage of the quote actually used for Edge = f(Model, Market). */
  edgeCalcAsOf?: string | null;
  /** Assemble already certified incompatible. */
  quoteAsOfCompatible?: boolean | null;
};

/**
 * Quote as-of vs model target — fail closed when we cannot certify the vintage.
 * Does not invent a wall-clock stale window. Missing as-of is not a mismatch.
 */
export function quoteAsOfCompatibleWithModelTarget(
  args: QuoteAsOfCompatArgs,
): boolean {
  if (args.quoteAsOfCompatible === false) return false;

  const quote = presentTimestamp(args.linesAsOf);
  if (quote.present && quote.ms == null) return false;

  const model = presentTimestamp(args.modelAsOf);
  if (model.present && model.ms == null) return false;

  const until = presentTimestamp(args.modelValidUntil);
  if (until.present && until.ms == null) return false;
  if (until.ms != null && quote.ms != null && quote.ms > until.ms) {
    return false;
  }

  const calc = presentTimestamp(args.edgeCalcAsOf);
  if (calc.present && calc.ms == null) return false;
  if (calc.ms != null && quote.ms != null && calc.ms !== quote.ms) {
    return false;
  }

  const commenceMs = parseTimeMs(args.commenceTime);
  if (model.ms != null && quote.ms != null && commenceMs != null) {
    // Pregame model vintage vs live quote — not the same target window.
    if (model.ms < commenceMs && quote.ms >= commenceMs) return false;
  }

  return true;
}
