/** American → implied win probability (with vig). */
export function americanImpliedProb(price: number): number | null {
  if (!Number.isFinite(price) || price === 0) return null;
  if (price > 0) return 100 / (price + 100);
  return Math.abs(price) / (Math.abs(price) + 100);
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
