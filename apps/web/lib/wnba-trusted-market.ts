/**
 * WNBA trusted-market gate (Chapter 4).
 * Tag = KEI vs trusted Best only. LEAN ≥ 2.5 / PLAY ≥ 4.0.
 * PASS if Best missing, untrusted, or already final.
 * Open + Current (Best) stay on the row for display (like CFB/NBA).
 * Trust flags drive Edge/Tag only — do not invent KEI from the book.
 *
 * Sport key: basketball_wnba via odds SPORT_KEY_MAP.wnba.
 */

export const WNBA_PLAY_EDGE_PTS = 4.0;
export const WNBA_LEAN_EDGE_PTS = 2.5;
export const WNBA_OUTLIER_VS_OPEN_PTS = 3.5;
export const WNBA_ABSURD_VS_KEI_PTS = 12;
export const WNBA_SINGLE_BOOK_ABSURD_PTS = 8;

export const WNBA_FORBIDDEN_LEFTOVER_GAME_IDS = [
  "401857105",
  "401857106",
] as const;

export type WnbaTrustedMarket = {
  trusted: boolean;
  market: number | null;
  reason: string;
};

export type WnbaTrustRowFields = {
  wnbaMarketTrusted?: boolean;
  wnbaTrustReason?: string;
  wnbaTrustLabel?: string;
  /** Cleared for tagging when untrusted (display Best may remain). */
  best?: string;
};

function num(v: unknown): number | null {
  if (v == null || v === "" || v === "—") return null;
  const n = parseFloat(String(v).replace(/[^+\-\d.]/g, ""));
  return Number.isFinite(n) ? n : null;
}

/** Odds-API board spreads are away-signed; KEI is home-signed. */
export function wnbaAwayBookToHome(awaySigned: unknown): number | null {
  const n = num(awaySigned);
  return n == null ? null : -n;
}

export function wnbaTrustLabelForReason(reason: string): string | undefined {
  if (reason === "best" || reason === "best_outlier_vs_open") return undefined;
  if (
    reason === "no_market" ||
    reason === "no_kei" ||
    reason === "no_candidate" ||
    reason === "already_final"
  ) {
    return "no book";
  }
  return "untrusted";
}

/** RS window May–Oct. Outside → treat as off-slate (PASS posture). */
export function isWnbaOffWindow(d = new Date()): boolean {
  const m = d.getUTCMonth() + 1;
  return !(m >= 5 && m <= 10);
}

export function trustWnbaMarket(input: {
  kei?: unknown;
  best?: unknown;
  open?: unknown;
  bookCount?: number;
  alreadyFinal?: boolean;
}): WnbaTrustedMarket {
  if (input.alreadyFinal) {
    return { trusted: false, market: null, reason: "already_final" };
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
    Math.abs(best - open) >= WNBA_OUTLIER_VS_OPEN_PTS
  ) {
    candidate = open;
    reason = "best_outlier_vs_open";
  }
  if (candidate == null) {
    return { trusted: false, market: null, reason: "no_candidate" };
  }

  const gap = Math.abs(candidate - kei);
  if (gap >= WNBA_ABSURD_VS_KEI_PTS) {
    return { trusted: false, market: null, reason: "absurd_vs_kei" };
  }
  if (books < 2 && gap >= WNBA_SINGLE_BOOK_ABSURD_PTS) {
    return { trusted: false, market: null, reason: "single_book_outlier" };
  }
  return { trusted: true, market: candidate, reason };
}

export function applyWnbaTrustedMarketToRows<
  T extends {
    id?: string;
    market?: string;
    kei?: string;
    best?: string;
    open?: string;
    status?: string;
  },
>(rows: T[], opts?: { alreadyFinal?: boolean }): (T & WnbaTrustRowFields)[] {
  return rows.map((row) => {
    const market = String(row.market || "");
    if (market !== "Spread" && market !== "Total") return row;

    const id = String(row.id || "");
    const leftover = WNBA_FORBIDDEN_LEFTOVER_GAME_IDS.some((gid) =>
      id.includes(gid),
    );
    const alreadyFinal =
      opts?.alreadyFinal === true ||
      leftover ||
      String(row.status || "").toLowerCase() === "final";

    const openNum =
      market === "Spread" ? wnbaAwayBookToHome(row.open) : num(row.open);
    const bestNum =
      market === "Spread" ? wnbaAwayBookToHome(row.best) : num(row.best);
    const bookCount = openNum != null && bestNum != null ? 2 : 1;
    const verdict = trustWnbaMarket({
      kei: row.kei,
      best: bestNum,
      open: openNum,
      bookCount,
      alreadyFinal,
    });
    return {
      ...row,
      // Keep Open + Current for display. Trust flags drive tags only.
      best: row.best ?? "—",
      open: row.open ?? "—",
      wnbaMarketTrusted: verdict.trusted,
      wnbaTrustReason: verdict.reason,
      wnbaTrustLabel: verdict.trusted
        ? undefined
        : wnbaTrustLabelForReason(verdict.reason),
    };
  });
}

export function wnbaEdgeTag(
  absEdge: number | null | undefined,
  opts?: { trusted?: boolean; alreadyFinal?: boolean },
): "PLAY" | "LEAN" | "PASS" {
  if (opts?.alreadyFinal || opts?.trusted === false) return "PASS";
  if (absEdge == null || !Number.isFinite(absEdge)) return "PASS";
  if (absEdge >= WNBA_PLAY_EDGE_PTS) return "PLAY";
  if (absEdge >= WNBA_LEAN_EDGE_PTS) return "LEAN";
  return "PASS";
}
