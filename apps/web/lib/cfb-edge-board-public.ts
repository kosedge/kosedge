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
