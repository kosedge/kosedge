import type { FantasyDeskRow } from "@/lib/fantasy/types";

/** High floor — stay-alive names for weekly elimination formats. */
export function selectGuillotineSafeFloor(
  rows: FantasyDeskRow[],
  limit = 8,
): FantasyDeskRow[] {
  return [...rows]
    .filter((r) => !["K", "DST"].includes(r.position.toUpperCase()))
    .filter((r) => r.rankOverall <= 60)
    .sort((a, b) => {
      const floorGap = b.floorPoints - a.floorPoints;
      if (Math.abs(floorGap) > 0.5) return floorGap;
      return a.rankOverall - b.rankOverall;
    })
    .slice(0, limit);
}

/** High upside — waiver / add targets when chasing ceiling weeks. */
export function selectGuillotineHighUpside(
  rows: FantasyDeskRow[],
  limit = 8,
): FantasyDeskRow[] {
  return [...rows]
    .filter((r) => !["K", "DST"].includes(r.position.toUpperCase()))
    .filter((r) => r.rankOverall >= 24 && r.rankOverall <= 120)
    .sort((a, b) => {
      const ceilGap =
        b.ceilingPoints - b.medianPoints - (a.ceilingPoints - a.medianPoints);
      if (Math.abs(ceilGap) > 0.5) return ceilGap;
      return (b.valueDelta ?? -999) - (a.valueDelta ?? -999);
    })
    .slice(0, limit);
}
