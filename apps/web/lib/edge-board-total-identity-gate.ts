/**
 * INC-2026-09-10 — Edge Board totals identity kill switch.
 *
 * Smoking gun: live MLB `totals` (e.g. 3.5) compared to full-game KEI/fairTotal
 * (~9) → painted PLAY Over. Odds `totals` key had no period; commence was past.
 *
 * Canonical: T ≡ Q_target BEFORE Edge = f(Model, Market).
 *   Q = (event, sport, market, period, side, line, price, book, timestamp)
 *   T = (event, sport, market, period, side)
 *
 * #517 short-term: fail-close when identity cannot be certified.
 * This follow-on honors stamped Odds/KEI identity:
 *   - Certified FG pregame (`fg` / `fg_pregame` / …) + T.period ≡ Q.period → compare
 *   - Missing / live (`fg_live`) / non-FG (`1st5`) → FAIL CLOSED
 *   - In-play still fails even if someone stamps `fg` (live FG ≠ pregame T)
 *
 * Do not clamp because a number "looks low". No JSX. Do not invent period
 * from the Odds `totals` key here — ingest stamps via Odds rules.
 *
 * TRUTH RECERT RED check #8: fail-closed / unavailable ≠ PASS. Strip
 * publishTag / actionLabel / edgeMagnitude (including nested decision).
 */

import {
  booksEquivalent,
  isFullGameLivePeriod,
  isFullGamePregamePeriod,
  isOddsInPlayEvent,
  quoteAsOfCompatibleWithModelTarget,
  quoteTargetEqualsModel,
} from "@/lib/edge-board-market-identity";

export { FULL_GAME_PREGAME_PERIODS as FULL_GAME_TOTAL_PERIODS } from "@/lib/edge-board-market-identity";
export {
  isFullGamePregamePeriod as isFullGameTotalPeriod,
  isOddsInPlayEvent,
  MODEL_TOTAL_PERIOD_FG,
} from "@/lib/edge-board-market-identity";

export type TotalIdentityReason =
  | "ok"
  | "missing_period_identity"
  | "in_play"
  | "in_play_missing_period"
  | "period_not_fg"
  | "target_mismatch"
  | "book_mismatch"
  | "quote_asof_incompatible"
  | "compare_ineligible";

export type TotalIdentityVerdict = {
  failClosed: boolean;
  reason: TotalIdentityReason;
  inPlay: boolean;
};

export type TotalIdentityGateInput = {
  sport?: string | null;
  market?: string | null;
  /** Q.period — explicit period identity (fg / fg_live / 1st5 / …). Absent = unknown. */
  period?: string | null;
  /** T.period — model/KEI target. KEI totals are FG pregame when stamped. */
  modelPeriod?: string | null;
  event?: string | null;
  modelEvent?: string | null;
  side?: string | null;
  modelSide?: string | null;
  commenceTime?: string | null;
  /** Quote vintage (book/market last_update). */
  linesAsOf?: string | null;
  /** Model/KEI vintage when stamped — stale vs quote is fail-closed. */
  modelAsOf?: string | null;
  modelValidUntil?: string | null;
  edgeCalcAsOf?: string | null;
  quoteAsOfCompatible?: boolean | null;
  /** Displayed decision book. */
  book?: string | null;
  /** Book of the quote used for Edge = f(Model, Market). */
  decisionBook?: string | null;
  /** Assemble already stamped ineligible. */
  compareEligible?: boolean | null;
  /** Injected clock for Odds in-play fallback (MLB only). */
  nowMs?: number;
};

export type TotalIdentityRowFields = {
  market?: string;
  period?: string | null;
  modelPeriod?: string | null;
  game?: string | null;
  modelEvent?: string | null;
  commenceTime?: string | null;
  linesAsOf?: string | null;
  modelAsOf?: string | null;
  modelValidUntil?: string | null;
  edgeCalcAsOf?: string | null;
  quoteAsOfCompatible?: boolean | null;
  book?: string | null;
  bookKey?: string | null;
  decisionBook?: string | null;
  edgeCalcBook?: string | null;
  totalCompareEligible?: boolean;
  totalIdentityReason?: TotalIdentityReason;
  /** Quote is live / commenced — not compared to FG fair. */
  totalQuoteLive?: boolean;
  publishTag?: unknown;
  publish_tag?: unknown;
  actionLabel?: unknown;
  action_label?: unknown;
  edgeMagnitude?: unknown;
  edge_magnitude?: unknown;
  decision?: unknown;
};

const FAIL_CLOSED_DECISION_KEYS = [
  "actionLabel",
  "action_label",
  "edgeMagnitude",
  "edge_magnitude",
  "numericalEdge",
  "numerical_edge",
  "playTo",
  "play_to",
] as const;

/**
 * Unavailable / fail-closed ≠ PASS. Strip publish + action + edge chrome
 * (top-level and nested decision). Does not invent a stand-in tag.
 */
export function stripFailClosedTotalDecisionChrome<
  T extends TotalIdentityRowFields,
>(row: T): T {
  const next: T = { ...row };
  delete next.publishTag;
  delete next.publish_tag;
  delete next.actionLabel;
  delete next.action_label;
  delete next.edgeMagnitude;
  delete next.edge_magnitude;
  const decision = next.decision;
  if (decision && typeof decision === "object" && !Array.isArray(decision)) {
    const d: Record<string, unknown> = {
      ...(decision as Record<string, unknown>),
    };
    for (const key of FAIL_CLOSED_DECISION_KEYS) {
      delete d[key];
    }
    next.decision = d;
  }
  return next;
}

export function isEdgeBoardTotalMarket(
  market: string | null | undefined,
): boolean {
  const m = String(market ?? "").trim();
  return m === "Total" || /^total$/i.test(m);
}

/**
 * Fail-closed verdict for a totals comparison (KEI/fair vs sportsbook).
 * Kill switch is not weakened: MLB still requires certified FG pregame
 * identity and rejects in-play even when period says `fg`.
 */
export function evaluateTotalIdentityGate(
  args: TotalIdentityGateInput,
): TotalIdentityVerdict {
  if (!isEdgeBoardTotalMarket(args.market)) {
    return { failClosed: false, reason: "ok", inPlay: false };
  }

  const sport = String(args.sport ?? "")
    .trim()
    .toLowerCase();
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

  const period = args.period;
  const hasPeriod = period != null && String(period).trim() !== "";
  const isFg = isFullGamePregamePeriod(period);
  const isLivePeriod = isFullGameLivePeriod(period);

  if (isLivePeriod) {
    return { failClosed: true, reason: "in_play", inPlay: true };
  }

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
  } else if (!hasPeriod && inPlay) {
    // Other sports: same hole only when period is missing and the event is live.
    return { failClosed: true, reason: "in_play_missing_period", inPlay: true };
  } else if (inPlay && isFg) {
    // Live remaining of a featured FG quote is not pregame T, any sport.
    return { failClosed: true, reason: "in_play", inPlay: true };
  }

  // T ≡ Q_target when both periods are certified. Missing Q.period on
  // non-MLB pregame keeps the #517 hole (compare); MLB already failed above.
  if (
    hasPeriod &&
    args.modelPeriod != null &&
    String(args.modelPeriod).trim() !== ""
  ) {
    const compatible = quoteTargetEqualsModel(
      {
        event: args.modelEvent,
        sport: args.sport,
        market: args.market,
        period: args.modelPeriod,
        side: args.modelSide,
      },
      {
        event: args.event,
        sport: args.sport,
        market: args.market,
        period: args.period,
        side: args.side,
      },
    );
    if (!compatible) {
      return { failClosed: true, reason: "target_mismatch", inPlay };
    }
  }

  const bookMatch = booksEquivalent(args.book, args.decisionBook);
  if (bookMatch === false) {
    return { failClosed: true, reason: "book_mismatch", inPlay };
  }

  if (
    !quoteAsOfCompatibleWithModelTarget({
      linesAsOf: args.linesAsOf,
      modelAsOf: args.modelAsOf,
      commenceTime: args.commenceTime,
      modelValidUntil: args.modelValidUntil,
      edgeCalcAsOf: args.edgeCalcAsOf,
      quoteAsOfCompatible: args.quoteAsOfCompatible,
    })
  ) {
    return { failClosed: true, reason: "quote_asof_incompatible", inPlay };
  }

  return { failClosed: false, reason: "ok", inPlay: false };
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
  const sport = String(sportKey ?? "")
    .trim()
    .toLowerCase();
  return rows.map((row) => {
    if (!isEdgeBoardTotalMarket(row.market)) return row;
    const verdict = evaluateTotalIdentityGate({
      sport,
      market: row.market,
      period: row.period,
      modelPeriod: row.modelPeriod,
      event: row.game,
      modelEvent: row.modelEvent ?? row.game,
      commenceTime: row.commenceTime,
      linesAsOf: row.linesAsOf,
      modelAsOf: row.modelAsOf,
      modelValidUntil: row.modelValidUntil,
      edgeCalcAsOf: row.edgeCalcAsOf,
      quoteAsOfCompatible: row.quoteAsOfCompatible,
      book: row.book ?? row.bookKey,
      decisionBook: row.decisionBook ?? row.edgeCalcBook,
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

    const next = stripFailClosedTotalDecisionChrome(row);
    next.totalCompareEligible = false;
    next.totalIdentityReason = verdict.reason;
    if (verdict.inPlay) next.totalQuoteLive = true;
    return next;
  });
}
