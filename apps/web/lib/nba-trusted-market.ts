/**
 * NBA trusted-market gate (Chapter 4).
 * Tag = KEI vs trusted Best only. LEAN ≥ 2.5 / PLAY ≥ 4.0.
 * PASS if Best missing, untrusted, or preseason.
 * Best is cleared on the row when untrusted (unlike CFB display-keep).
 *
 * Sport key: basketball_nba via odds SPORT_KEY_MAP.nba.
 */

export const NBA_PLAY_EDGE_PTS = 4.0;
export const NBA_LEAN_EDGE_PTS = 2.5;
export const NBA_OUTLIER_VS_OPEN_PTS = 3.5;
export const NBA_ABSURD_VS_KEI_PTS = 12;
export const NBA_SINGLE_BOOK_ABSURD_PTS = 8;

export type NbaTrustedMarket = {
  trusted: boolean;
  market: number | null;
  reason: string;
};

export type NbaTrustRowFields = {
  nbaMarketTrusted?: boolean;
  nbaTrustReason?: string;
  nbaTrustLabel?: string;
  /** Cleared when untrusted. */
  best?: string;
};

function num(v: unknown): number | null {
  if (v == null || v === "" || v === "—") return null;
  const n = parseFloat(String(v).replace(/[^+\-\d.]/g, ""));
  return Number.isFinite(n) ? n : null;
}

/** Odds-API board spreads are away-signed; KEI is home-signed. */
export function nbaAwayBookToHome(awaySigned: unknown): number | null {
  const n = num(awaySigned);
  return n == null ? null : -n;
}

export function nbaTrustLabelForReason(reason: string): string | undefined {
  if (reason === "best" || reason === "best_outlier_vs_open") return undefined;
  if (
    reason === "no_market" ||
    reason === "no_kei" ||
    reason === "no_candidate" ||
    reason === "preseason"
  ) {
    return "no book";
  }
  return "untrusted";
}

export function isNbaPreseason(d = new Date()): boolean {
  const m = d.getUTCMonth() + 1;
  return !(m === 10 || m === 11 || m === 12 || m <= 6);
}

export function trustNbaMarket(input: {
  kei?: unknown;
  best?: unknown;
  open?: unknown;
  bookCount?: number;
  preseason?: boolean;
}): NbaTrustedMarket {
  if (input.preseason) {
    return { trusted: false, market: null, reason: "preseason" };
  }
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
    Math.abs(best - open) >= NBA_OUTLIER_VS_OPEN_PTS
  ) {
    candidate = open;
    reason = "best_outlier_vs_open";
  }
  if (candidate == null) {
    return { trusted: false, market: null, reason: "no_candidate" };
  }

  const gap = Math.abs(candidate - kei);
  if (gap >= NBA_ABSURD_VS_KEI_PTS) {
    return { trusted: false, market: null, reason: "absurd_vs_kei" };
  }
  if (books < 2 && gap >= NBA_SINGLE_BOOK_ABSURD_PTS) {
    return { trusted: false, market: null, reason: "single_book_outlier" };
  }
  return { trusted: true, market: candidate, reason };
}

export function applyNbaTrustedMarketToRows<
  T extends {
    market?: string;
    kei?: string;
    best?: string;
    open?: string;
  },
>(rows: T[], opts?: { preseason?: boolean }): (T & NbaTrustRowFields)[] {
  const preseason = opts?.preseason ?? isNbaPreseason();
  return rows.map((row) => {
    const market = String(row.market || "");
    if (market !== "Spread" && market !== "Total") return row;

    const openNum =
      market === "Spread" ? nbaAwayBookToHome(row.open) : num(row.open);
    const bestNum =
      market === "Spread" ? nbaAwayBookToHome(row.best) : num(row.best);
    const bookCount = openNum != null && bestNum != null ? 2 : 1;
    const verdict = trustNbaMarket({
      kei: row.kei,
      best: bestNum,
      open: openNum,
      bookCount,
      preseason,
    });
    return {
      ...row,
      // Clear Best when untrusted (Ch4 gate).
      best: verdict.trusted ? row.best : "—",
      nbaMarketTrusted: verdict.trusted,
      nbaTrustReason: verdict.reason,
      nbaTrustLabel: verdict.trusted
        ? undefined
        : nbaTrustLabelForReason(verdict.reason),
    };
  });
}

export function nbaEdgeTag(
  absEdge: number | null | undefined,
  opts?: { trusted?: boolean; preseason?: boolean },
): "PLAY" | "LEAN" | "PASS" {
  if (opts?.preseason || opts?.trusted === false) return "PASS";
  if (absEdge == null || !Number.isFinite(absEdge)) return "PASS";
  if (absEdge >= NBA_PLAY_EDGE_PTS) return "PLAY";
  if (absEdge >= NBA_LEAN_EDGE_PTS) return "LEAN";
  return "PASS";
}
