/** American → implied win probability (with vig). */
export function americanImpliedProb(price: number): number | null {
  if (!isValidAmericanOdds(price)) return null;
  if (price > 0) return 100 / (price + 100);
  return Math.abs(price) / (Math.abs(price) + 100);
}

/**
 * Standard American moneyline/juice: finite, non-zero, |price| >= 100.
 * Rejects corrupt mid-range values like -66 that are almost always bad ingest.
 */
export function isValidAmericanOdds(price: unknown): price is number {
  if (typeof price !== "number" || !Number.isFinite(price) || price === 0) {
    return false;
  }
  return Math.abs(price) >= 100;
}

/** Display helper — blank / invalid books render as em dash. */
export function formatAmericanOdds(price: unknown): string {
  if (!isValidAmericanOdds(price)) return "—";
  const n = Math.round(price);
  return n > 0 ? `+${n}` : String(n);
}

/** Two-way no-vig home win probability from a book's home/away Americans. */
export function noVigHomeProb(
  homePrice: number,
  awayPrice: number,
): number | null {
  const home = americanImpliedProb(homePrice);
  const away = americanImpliedProb(awayPrice);
  if (home == null || away == null) return null;
  const total = home + away;
  if (total <= 0) return null;
  return home / total;
}
