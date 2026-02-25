/**
 * Power ratings: team strength / rankings per sport.
 * Data is read from data/processed/power_ratings_{sport}.json (exported by pipeline script).
 */

import { readFileSync } from "node:fs";
import { join } from "node:path";
import { getSport } from "@/lib/sports";

export type PowerRatingRow = {
  rank: number;
  team: string;
  teamNorm?: string;
  rating: number;
  adjem?: number;
  torvik?: number;
  barthag?: number;
  year?: number;
};

export function getPowerRatings(sportKey: string): PowerRatingRow[] {
  if (!getSport(sportKey)) return [];

  const p = join(
    process.cwd(),
    "data",
    "processed",
    `power_ratings_${sportKey}.json`
  );
  try {
    const raw = readFileSync(p, "utf-8");
    const data = JSON.parse(raw) as { ratings?: PowerRatingRow[] };
    return Array.isArray(data.ratings) ? data.ratings : [];
  } catch {
    return [];
  }
}
