/**
 * CFB trusted-market guard.
 * Edge / Tag may only fire against a quality book number — never a lone
 * junk or wrong-game line (e.g. TCU KEI −20 vs a +8.5 stray, or
 * FIU@USF KEI total 72.5 vs book 52.5).
 *
 * Thresholds live here and in data/ops/cfb-kei-rules-2026.md.
 * Applies to **Spread and Total** rows. Moneyline is untouched.
 *
 * Sign convention (spreads only): KEI is home-signed (`kei_spread_home`).
 * Odds-API board rows store Open/Best away-signed (`awayOutcome.point`).
 * Convert book → home at this boundary via `cfbAwayBookToHome` before
 * trust/edge. Totals are unsigned levels — compare KEI total vs book total
 * with no flip. Do not rewrite the odds cache; do not flip the Python
 * ledger `spread_home` path.
 *
 * Display vs trust: Open/Best feed prices always stay on the row. Trust only
 * sets `cfbMarketTrusted` / `cfbTrustReason`. Edge/Tag use trusted Best only.
 */

export const CFB_PLAY_EDGE_PTS = 4.0;
export const CFB_LEAN_EDGE_PTS = 2.5;
/** |best − open| at/above this → reject best (use open if it is trusted). */
export const CFB_OUTLIER_VS_OPEN_PTS = 3.5;
/** |market − KEI| at/above this → wrong game / junk. No Edge. */
export const CFB_ABSURD_VS_KEI_PTS = 12;
/** Single-book (open missing or same as best) + |market − KEI| ≥ this → untrusted. */
export const CFB_SINGLE_BOOK_ABSURD_PTS = 8;

/**
 * Totals PLAY sits until an unused close holdout greens and Ryan/CoS flips.
 * LEAN ≥2.5 still fires. Doctrine: `docs/CFB_TOTALS_PLAY_SIT.md`
 */
export const CFB_TOTALS_PLAY_ELIGIBLE = false;

/**
 * Spread PLAY sits until an unused close holdout greens and Ryan/CoS flips.
 * PLAY-band edges → PASS (not demoted to LEAN). LEAN ≥2.5 still fires.
 * Doctrine: `docs/CFB_SPREAD_PLAY_SIT.md`
 */
export const CFB_SPREAD_PLAY_ELIGIBLE = false;

export type CfbEdgeMarket = "spread" | "total";
export type CfbEdgeTag = "PLAY" | "LEAN" | "PASS";

export type CfbTrustedMarket = {
  trusted: boolean;
  /** Home-signed trusted market when trusted; else null. */
  market: number | null;
  reason: string;
};

export type CfbTrustRowFields = {
  cfbMarketTrusted?: boolean;
  cfbTrustReason?: string;
  /** Desk footnote: `untrusted` | `no book` | undefined when trusted. */
  cfbTrustLabel?: string;
};

function num(v: unknown): number | null {
  if (v == null || v === "" || v === "—") return null;
  const n = parseFloat(String(v).replace(/[^+\-\d.]/g, ""));
  return Number.isFinite(n) ? n : null;
}

/**
 * Flip Odds-API away-signed CFB spread → home (KEI convention).
 * home = −away. Null/blank passthrough.
 */
export function cfbAwayBookToHome(awaySigned: unknown): number | null {
  const n = num(awaySigned);
  return n == null ? null : -n;
}

export function cfbTrustLabelForReason(reason: string): string | undefined {
  if (reason === "best" || reason === "best_outlier_vs_open") return undefined;
  if (
    reason === "no_market" ||
    reason === "no_kei" ||
    reason === "no_candidate"
  ) {
    return "no book";
  }
  return "untrusted";
}

/**
 * Trust gate. `best` / `open` must already be **home-signed**
 * (callers convert with `cfbAwayBookToHome` when reading board rows).
 */
export function trustCfbMarket(input: {
  kei?: unknown;
  best?: unknown;
  open?: unknown;
  bookCount?: number;
}): CfbTrustedMarket {
  const kei = num(input.kei);
  const best = num(input.best);
  const open = num(input.open);
  const books =
    input.bookCount ?? (best != null && open != null && best !== open ? 2 : 1);

  if (kei == null) {
    return { trusted: false, market: null, reason: "no_kei" };
  }
  if (best == null && open == null) {
    return { trusted: false, market: null, reason: "no_market" };
  }

  let candidate = best ?? open;
  let reason = "best";

  if (
    best != null &&
    open != null &&
    Math.abs(best - open) >= CFB_OUTLIER_VS_OPEN_PTS
  ) {
    candidate = open;
    reason = "best_outlier_vs_open";
  }

  if (candidate == null) {
    return { trusted: false, market: null, reason: "no_candidate" };
  }

  const gap = Math.abs(candidate - kei);
  if (gap >= CFB_ABSURD_VS_KEI_PTS) {
    return {
      trusted: false,
      market: null,
      reason: "absurd_vs_kei",
    };
  }
  if (books < 2 && gap >= CFB_SINGLE_BOOK_ABSURD_PTS) {
    return {
      trusted: false,
      market: null,
      reason: "single_book_outlier",
    };
  }

  return { trusted: true, market: candidate, reason };
}

export function applyCfbTrustedMarketToRows<
  T extends {
    market?: string;
    kei?: string;
    best?: string;
    open?: string;
    book?: string;
    bookKey?: string;
  },
>(rows: T[]): (T & CfbTrustRowFields)[] {
  return rows.map((row) => {
    const market = String(row.market || "");
    if (market !== "Spread" && market !== "Total") return row;

    // Spreads: board Open/Best are away-signed; KEI is home → flip.
    // Totals: unsigned levels; compare KEI total vs book total as-is.
    const openNum =
      market === "Spread" ? cfbAwayBookToHome(row.open) : num(row.open);
    const bestNum =
      market === "Spread" ? cfbAwayBookToHome(row.best) : num(row.best);
    // Rows do not carry n_books (odds cache untouched). When both Open and
    // Best are posted, do not treat open===best as a lone-book feed — that
    // false-clears cupcakes (BALL@OSU ss 8.3) under SINGLE_BOOK=8.
    const bookCount = openNum != null && bestNum != null ? 2 : 1;
    const verdict = trustCfbMarket({
      kei: row.kei,
      best: bestNum,
      open: openNum,
      bookCount,
    });
    // Never blank feed Best/Open. Trust is a flag for Edge/Tag only.
    return {
      ...row,
      cfbMarketTrusted: verdict.trusted,
      cfbTrustReason: verdict.reason,
      cfbTrustLabel: verdict.trusted
        ? undefined
        : cfbTrustLabelForReason(verdict.reason),
    };
  });
}

/**
 * CFB Edge / Tag O/U SoT. One tagger for board + publish/display.
 * Totals never emit PLAY while `CFB_TOTALS_PLAY_ELIGIBLE` is false
 * (PLAY-band edges become PASS; LEAN band still LEAN).
 * Spreads never emit PLAY while `CFB_SPREAD_PLAY_ELIGIBLE` is false
 * (same remap: PLAY-band → PASS; LEAN ≥2.5 stays).
 */
export function cfbEdgeTag(
  absEdge: number | null | undefined,
  market: CfbEdgeMarket = "spread",
): CfbEdgeTag {
  if (absEdge == null || !Number.isFinite(absEdge)) return "PASS";
  const e = Math.abs(Number(absEdge));
  if (e >= CFB_PLAY_EDGE_PTS) {
    if (market === "total" && !CFB_TOTALS_PLAY_ELIGIBLE) return "PASS";
    if (market === "spread" && !CFB_SPREAD_PLAY_ELIGIBLE) return "PASS";
    return "PLAY";
  }
  if (e >= CFB_LEAN_EDGE_PTS) return "LEAN";
  return "PASS";
}

/**
 * Publish vocabulary ≡ display tag after PLAY sit remap.
 * CFB has no dead-tier chrome; identity is the tagger output itself.
 */
export function cfbPublishTagFromEdge(
  absEdge: number | null | undefined,
  market: CfbEdgeMarket = "spread",
): CfbEdgeTag {
  return cfbEdgeTag(absEdge, market);
}
