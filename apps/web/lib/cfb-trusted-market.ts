/**
 * CFB trusted-market guard.
 * Edge / Tag may only fire against a quality book number — never a lone
 * junk or wrong-game line (e.g. TCU KEI −20 vs a +8.5 stray).
 *
 * Thresholds live here and in data/ops/cfb-kei-rules-2026.md.
 */

export const CFB_PLAY_EDGE_PTS = 4.0;
export const CFB_LEAN_EDGE_PTS = 2.5;
/** |best − open| at/above this → reject best (use open if it is trusted). */
export const CFB_OUTLIER_VS_OPEN_PTS = 3.5;
/** |market − KEI| at/above this → wrong game / junk. No Edge. */
export const CFB_ABSURD_VS_KEI_PTS = 12;
/** Single-book (open missing or same as best) + |market − KEI| ≥ this → untrusted. */
export const CFB_SINGLE_BOOK_ABSURD_PTS = 8;

export type CfbTrustedMarket = {
  trusted: boolean;
  market: number | null;
  reason: string;
};

function num(v: unknown): number | null {
  if (v == null || v === "" || v === "—") return null;
  const n = parseFloat(String(v).replace(/[^+\-\d.]/g, ""));
  return Number.isFinite(n) ? n : null;
}

export function trustCfbMarket(input: {
  kei?: unknown;
  best?: unknown;
  open?: unknown;
  bookCount?: number;
}): CfbTrustedMarket {
  const kei = num(input.kei);
  const best = num(input.best);
  const open = num(input.open);
  const books = input.bookCount ?? (best != null && open != null && best !== open ? 2 : 1);

  if (kei == null) {
    return { trusted: false, market: null, reason: "no_kei" };
  }
  if (best == null && open == null) {
    return { trusted: false, market: null, reason: "no_market" };
  }

  let candidate = best ?? open;
  let reason = "best";

  if (best != null && open != null && Math.abs(best - open) >= CFB_OUTLIER_VS_OPEN_PTS) {
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
>(rows: T[]): T[] {
  return rows.map((row) => {
    if (String(row.market || "") !== "Spread") return row;
    const verdict = trustCfbMarket({
      kei: row.kei,
      best: row.best,
      open: row.open,
    });
    if (verdict.trusted) return row;
    return {
      ...row,
      best: undefined,
      book: verdict.reason === "no_market" ? row.book : "untrusted",
      bookKey: verdict.reason === "no_market" ? row.bookKey : "",
    };
  });
}

export function cfbEdgeTag(
  absEdge: number | null | undefined,
): "PLAY" | "LEAN" | "PASS" {
  if (absEdge == null || !Number.isFinite(absEdge)) return "PASS";
  if (absEdge >= CFB_PLAY_EDGE_PTS) return "PLAY";
  if (absEdge >= CFB_LEAN_EDGE_PTS) return "LEAN";
  return "PASS";
}
