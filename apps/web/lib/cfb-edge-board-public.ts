/**
 * P0 2026-09-11 — CFB Edge Board public visibility kill switch.
 *
 * Visibility / publishing only. Does not change CFB model math, KEI,
 * odds, assemble research libs, or other sports.
 *
 * Flip `CFB_EDGE_BOARD_PUBLIC_ENABLED` to `true` only after the re-enable
 * gate in the PR body: validated current market coverage, trustworthy
 * source status, market as_of, canonical game joins, and sanity checks on
 * extreme model-vs-market gaps.
 *
 * Internal QA / research:
 *   - `/api/edge-board/cfb/today` stays secret-gated (existing internal path)
 *   - set `CFB_EDGE_BOARD_INTERNAL=1` (server) to serve `/edge-board/cfb`
 *     and assemble for QA without flipping the public constant
 *   - `NEXT_PUBLIC_CFB_EDGE_BOARD_INTERNAL=1` also restores the public
 *     selector / chrome on that deploy
 */

export const CFB_EDGE_BOARD_PUBLIC_ENABLED = false;

export const CFB_EDGE_BOARD_UNAVAILABLE_MESSAGE =
  "CFB Edge Board temporarily unavailable while market coverage is being validated.";

export const CFB_EDGE_BOARD_UNAVAILABLE_CODE = "cfb_edge_board_unavailable";

const CFB_CUSTOMER_TAG_KEYS = [
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

/** Server/QA override — never on in production unless explicitly set. */
export function isCfbEdgeBoardInternalOverride(): boolean {
  return (
    envFlagTrue("CFB_EDGE_BOARD_INTERNAL") ||
    envFlagTrue("NEXT_PUBLIC_CFB_EDGE_BOARD_INTERNAL")
  );
}

/** Customer chrome + assemble + tag publish. */
export function isCfbEdgeBoardCustomerEnabled(): boolean {
  return CFB_EDGE_BOARD_PUBLIC_ENABLED || isCfbEdgeBoardInternalOverride();
}

export function isCfbSportKey(sport: string | null | undefined): boolean {
  return (
    String(sport ?? "")
      .trim()
      .toLowerCase() === "cfb"
  );
}

export function isCfbEdgeBoardCustomerDisabled(sport?: string | null): boolean {
  return isCfbSportKey(sport) && !isCfbEdgeBoardCustomerEnabled();
}

export function isCfbEdgeBoardHref(href: string | null | undefined): boolean {
  if (!href) return false;
  return /(?:^|\/)edge-board\/cfb(?:[/?#]|$)/.test(href);
}

/** Sports shown on the public/pro Edge Board selector. */
export function publicEdgeBoardSports<T extends { key: string }>(
  sports: readonly T[],
): T[] {
  if (isCfbEdgeBoardCustomerEnabled()) return [...sports];
  return sports.filter((s) => s.key !== "cfb");
}

/** Public Edge Board sport keys (infrastructure list may still include cfb). */
export function publicEdgeBoardSportKeys(keys: readonly string[]): string[] {
  if (isCfbEdgeBoardCustomerEnabled()) return [...keys];
  return keys.filter((k) => k !== "cfb");
}

/**
 * Customer Edge Board href, or null when CFB is public-disabled.
 * Use to hide CTAs; the canonical `/edge-board/cfb` URL still fail-closes.
 */
export function publicEdgeBoardHref(
  sport: string | null | undefined,
): string | null {
  const key = String(sport ?? "")
    .trim()
    .toLowerCase();
  if (!key) return null;
  if (isCfbEdgeBoardCustomerDisabled(key)) return null;
  if (key === "cfb") return "/edge-board/cfb?week=1";
  return `/edge-board/${key}`;
}

/** Drop CFB Edge Board links from customer chrome while the kill switch is off. */
export function withoutCfbEdgeBoardHrefs<T extends { href?: string | null }>(
  items: readonly T[],
): T[] {
  if (isCfbEdgeBoardCustomerEnabled()) return [...items];
  return items.filter((item) => !isCfbEdgeBoardHref(item.href));
}

export function customerCtaHref(
  href: string | null | undefined,
): string | null | undefined {
  if (href == null || href === "") return href;
  if (isCfbEdgeBoardHref(href) && !isCfbEdgeBoardCustomerEnabled()) {
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
  for (const key of CFB_CUSTOMER_TAG_KEYS) {
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

export function cfbEdgeBoardAssembleUnavailablePayload(): {
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
} {
  return {
    error: CFB_EDGE_BOARD_UNAVAILABLE_CODE,
    message: CFB_EDGE_BOARD_UNAVAILABLE_MESSAGE,
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
