/**
 * Price normalization for Line Curve.
 * Implied probability (with vig) is not true market probability.
 * Hold is tracked separately when both sides of a line are posted.
 */

import { americanImpliedProb, isValidAmericanOdds } from "@/lib/american-odds";

export { americanImpliedProb, isValidAmericanOdds };

/** Decimal payout including stake (e.g. -110 → 1.909…). */
export function americanToDecimal(american: number): number {
  if (!isValidAmericanOdds(american)) return Number.NaN;
  if (american > 0) return 1 + american / 100;
  return 1 + 100 / Math.abs(american);
}

/**
 * Fair American from a no-push win probability (cover | not push).
 * Push mass is priced separately in EV, not stuffed into this quote.
 */
export function fairAmericanFromProb(winProb: number): number {
  const p = Number(winProb);
  if (!Number.isFinite(p) || p <= 0) return 10000;
  if (p >= 1) return -10000;
  if (p >= 0.5) return Math.round((-100 * p) / (1 - p));
  return Math.round((100 * (1 - p)) / p);
}

/**
 * EV per $1 risked with ATS push = stake returned (0 P/L).
 * Do not treat push as a loss.
 */
export function evPerDollarRisked(args: {
  cover: number;
  push: number;
  loss: number;
  americanOdds: number;
}): number | null {
  if (!isValidAmericanOdds(args.americanOdds)) return null;
  const cover = clampProb(args.cover);
  const push = clampProb(args.push);
  const loss = clampProb(args.loss);
  const profitIfWin = americanToDecimal(args.americanOdds) - 1;
  return cover * profitIfWin + push * 0 + loss * -1;
}

/** Two-way bookmaker hold. Null if either price is invalid. */
export function bookmakerHold(
  sideAmerican: number,
  opposingAmerican: number,
): number | null {
  const a = americanImpliedProb(sideAmerican);
  const b = americanImpliedProb(opposingAmerican);
  if (a == null || b == null) return null;
  return a + b - 1;
}

/** Standard independent 2-leg parlay American from two posted singles. */
export function multiplicativeParlayAmerican(
  americanA: number,
  americanB: number,
): number | null {
  const dA = americanToDecimal(americanA);
  const dB = americanToDecimal(americanB);
  if (!Number.isFinite(dA) || !Number.isFinite(dB)) return null;
  return decimalToAmerican(dA * dB);
}

export function decimalToAmerican(decimal: number): number {
  if (!Number.isFinite(decimal) || decimal <= 1) return 10000;
  if (decimal >= 2) return Math.round((decimal - 1) * 100);
  return Math.round(-100 / (decimal - 1));
}

function clampProb(p: number): number {
  if (!Number.isFinite(p)) return 0;
  return Math.max(0, Math.min(1, p));
}
