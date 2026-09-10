/**
 * INC-2026-09-10 — Edge Board totals identity kill switch (short-term).
 *
 * Smoking gun: live MLB `totals` (e.g. 3.5) compared to full-game KEI/fairTotal
 * (~9) → painted PLAY Over. Odds `totals` key has no period; commence was past.
 *
 * Invariant (follow-on, not this module): T ≡ Q_target.
 * This PR only fail-closes when we cannot certify that identity:
 *   - MLB totals: missing period/identity OR event in-play
 *   - Other sports totals: missing period AND in-play (same hole, narrower)
 *   - Any sport: period present but not full-game
 *
 * Do not clamp because a number "looks low". No JSX. Canonical Q/T schema
 * is a follow-on — do not invent period=fg from the Odds `totals` key here.
 */

export const FULL_GAME_TOTAL_PERIODS = [
  "fg",
  "full",
  "full_game",
  "full-game",
  "regulation",
  "game",
] as const;

export type TotalIdentityReason =
  | "ok"
  | "missing_period_identity"
  | "in_play"
  | "in_play_missing_period"
  | "period_not_fg"
  | "compare_ineligible";

export type TotalIdentityVerdict = {
  failClosed: boolean;
  reason: TotalIdentityReason;
  inPlay: boolean;
};

export type TotalIdentityGateInput = {
  sport?: string | null;
  market?: string | null;
  /** Explicit period identity (fg / 1st5 / live / …). Absent = unknown. */
  period?: string | null;
  commenceTime?: string | null;
  /** Quote vintage (book/market last_update). */
  linesAsOf?: string | null;
  /** Assemble already stamped ineligible. */
  compareEligible?: boolean | null;
  /** Injected clock for Odds in-play fallback (MLB only). */
  nowMs?: number;
};

export type TotalIdentityRowFields = {
  market?: string;
  period?: string | null;
  commenceTime?: string | null;
  linesAsOf?: string | null;
  totalCompareEligible?: boolean;
  totalIdentityReason?: TotalIdentityReason;
  /** Quote is live / commenced — not compared to FG fair. */
  totalQuoteLive?: boolean;
  publishTag?: unknown;
  actionLabel?: unknown;
  edgeMagnitude?: unknown;
};

function parseTimeMs(raw: string | null | undefined): number | null {
  if (raw == null || !String(raw).trim()) return null;
  const ms = Date.parse(String(raw).trim());
  return Number.isFinite(ms) ? ms : null;
}

function normalizePeriod(raw: string | null | undefined): string | null {
  if (raw == null) return null;
  const p = String(raw).trim().toLowerCase();
  return p || null;
}

export function isFullGameTotalPeriod(
  period: string | null | undefined,
): boolean {
  const p = normalizePeriod(period);
  if (!p) return false;
  return (FULL_GAME_TOTAL_PERIODS as readonly string[]).includes(p);
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

export function isEdgeBoardTotalMarket(
  market: string | null | undefined,
): boolean {
  const m = String(market ?? "").trim();
  return m === "Total" || /^total$/i.test(m);
}

/**
 * Fail-closed verdict for a totals comparison (KEI/fair vs sportsbook).
 */
export function evaluateTotalIdentityGate(
  args: TotalIdentityGateInput,
): TotalIdentityVerdict {
  if (!isEdgeBoardTotalMarket(args.market)) {
    return { failClosed: false, reason: "ok", inPlay: false };
  }

  const sport = String(args.sport ?? "").trim().toLowerCase();
  const isMlb = sport === "mlb";
  const inPlay = isOddsInPlayEvent({
    commenceTime: args.commenceTime,
    linesAsOf: args.linesAsOf,
    nowMs: args.nowMs,
    allowWallClockOddsRule: isMlb,
  });

  if (args.compareEligible === false) {
    return {
      failClosed: true,
      reason: "compare_ineligible",
      inPlay,
    };
  }

  const period = normalizePeriod(args.period);
  const hasPeriod = period != null;
  const isFg = isFullGameTotalPeriod(period);

  if (hasPeriod && !isFg) {
    return { failClosed: true, reason: "period_not_fg", inPlay };
  }

  if (isMlb) {
    if (!hasPeriod) {
      return { failClosed: true, reason: "missing_period_identity", inPlay };
    }
    if (inPlay) {
      return { failClosed: true, reason: "in_play", inPlay: true };
    }
    return { failClosed: false, reason: "ok", inPlay: false };
  }

  // Other sports: same hole only when period is missing and the event is live.
  if (!hasPeriod && inPlay) {
    return { failClosed: true, reason: "in_play_missing_period", inPlay: true };
  }
  return { failClosed: false, reason: "ok", inPlay };
}

/**
 * Assemble-path stamp: keep book quote + KEI display; strip comparison paint.
 * Idempotent. Does not invent period=fg.
 */
export function applyTotalIdentityGateToRows<T extends TotalIdentityRowFields>(
  rows: T[],
  sportKey: string,
  nowMs?: number,
): T[] {
  const sport = String(sportKey ?? "").trim().toLowerCase();
  return rows.map((row) => {
    if (!isEdgeBoardTotalMarket(row.market)) return row;
    const verdict = evaluateTotalIdentityGate({
      sport,
      market: row.market,
      period: row.period,
      commenceTime: row.commenceTime,
      linesAsOf: row.linesAsOf,
      compareEligible: row.totalCompareEligible,
      nowMs,
    });
    if (!verdict.failClosed) {
      if (row.totalCompareEligible === true && row.totalIdentityReason) {
        return row;
      }
      return {
        ...row,
        totalCompareEligible: true,
        totalIdentityReason: "ok" as const,
      };
    }

    const next: T = { ...row };
    next.totalCompareEligible = false;
    next.totalIdentityReason = verdict.reason;
    if (verdict.inPlay) next.totalQuoteLive = true;
    delete next.publishTag;
    delete next.actionLabel;
    delete next.edgeMagnitude;
    return next;
  });
}
