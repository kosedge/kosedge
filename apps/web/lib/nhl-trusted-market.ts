/**
 * NHL trusted-market gate (Chapter 4).
 * Tag = KEI vs trusted Best only. LEAN ≥ 2.5 / PLAY ≥ 4.0 (goal units).
 * PASS if Best missing, untrusted, or preseason.
 * Open + Current (Best) stay on the row for display.
 * Trust flags drive Edge/Tag only — do not blank book columns.
 *
 * Sport key: icehockey_nhl via odds SPORT_KEY_MAP.nhl.
 */

export const NHL_PLAY_EDGE_PTS = 4.0;
export const NHL_LEAN_EDGE_PTS = 2.5;
/** Goal-unit trust thresholds (not basketball point copies). */
export const NHL_OUTLIER_VS_OPEN_PTS = 1.5;
export const NHL_ABSURD_VS_KEI_PTS = 3.5;
export const NHL_SINGLE_BOOK_ABSURD_PTS = 2.5;

export type NhlTrustedMarket = {
  trusted: boolean;
  market: number | null;
  reason: string;
};

export type NhlTrustRowFields = {
  nhlMarketTrusted?: boolean;
  nhlTrustReason?: string;
  nhlTrustLabel?: string;
  best?: string;
};

function num(v: unknown): number | null {
  if (v == null || v === "" || v === "—") return null;
  const n = parseFloat(String(v).replace(/[^+\-\d.]/g, ""));
  return Number.isFinite(n) ? n : null;
}

/** Odds-API board spreads are away-signed; KEI puck is home-signed. */
export function nhlAwayBookToHome(awaySigned: unknown): number | null {
  const n = num(awaySigned);
  return n == null ? null : -n;
}

export function nhlTrustLabelForReason(reason: string): string | undefined {
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

/** RS ≈ Sep 29–Jun 30; else preseason / offseason → PASS posture. */
export function isNhlPreseason(d = new Date()): boolean {
  const m = d.getUTCMonth() + 1;
  const day = d.getUTCDate();
  if (m === 10 || m === 11 || m === 12 || m <= 6) return false;
  if (m === 9 && day >= 29) return false;
  return true;
}

export function trustNhlMarket(input: {
  kei?: unknown;
  best?: unknown;
  open?: unknown;
  bookCount?: number;
  preseason?: boolean;
}): NhlTrustedMarket {
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
    Math.abs(best - open) >= NHL_OUTLIER_VS_OPEN_PTS
  ) {
    candidate = open;
    reason = "best_outlier_vs_open";
  }
  if (candidate == null) {
    return { trusted: false, market: null, reason: "no_candidate" };
  }

  const gap = Math.abs(candidate - kei);
  if (gap >= NHL_ABSURD_VS_KEI_PTS) {
    return { trusted: false, market: null, reason: "absurd_vs_kei" };
  }
  if (books < 2 && gap >= NHL_SINGLE_BOOK_ABSURD_PTS) {
    return { trusted: false, market: null, reason: "single_book_outlier" };
  }
  return { trusted: true, market: candidate, reason };
}

export function applyNhlTrustedMarketToRows<
  T extends {
    market?: string;
    kei?: string;
    best?: string;
    open?: string;
  },
>(rows: T[], opts?: { preseason?: boolean }): (T & NhlTrustRowFields)[] {
  const preseason = opts?.preseason ?? isNhlPreseason();
  return rows.map((row) => {
    const market = String(row.market || "");
    if (market !== "Spread" && market !== "Total") return row;

    const openNum =
      market === "Spread" ? nhlAwayBookToHome(row.open) : num(row.open);
    const bestNum =
      market === "Spread" ? nhlAwayBookToHome(row.best) : num(row.best);
    const bookCount = openNum != null && bestNum != null ? 2 : 1;
    const verdict = trustNhlMarket({
      kei: row.kei,
      best: bestNum,
      open: openNum,
      bookCount,
      preseason,
    });
    return {
      ...row,
      best: row.best ?? "—",
      open: row.open ?? "—",
      nhlMarketTrusted: verdict.trusted,
      nhlTrustReason: verdict.reason,
      nhlTrustLabel: verdict.trusted
        ? undefined
        : nhlTrustLabelForReason(verdict.reason),
    };
  });
}

export function nhlEdgeTag(
  absEdge: number | null | undefined,
  opts?: { trusted?: boolean; preseason?: boolean },
): "PLAY" | "LEAN" | "PASS" {
  if (opts?.preseason || opts?.trusted === false) return "PASS";
  if (absEdge == null || !Number.isFinite(absEdge)) return "PASS";
  if (absEdge >= NHL_PLAY_EDGE_PTS) return "PLAY";
  if (absEdge >= NHL_LEAN_EDGE_PTS) return "LEAN";
  return "PASS";
}
