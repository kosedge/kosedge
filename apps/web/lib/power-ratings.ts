/**
 * Power ratings: team strength / rankings per sport.
 * Data is read from data/processed/power_ratings_{sport}.json (exported by pipeline script).
 */

import { readFileSync, existsSync } from "node:fs";
import { getSport } from "@/lib/sports";
import { getPowerRatingsPath } from "@/lib/data-paths";

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

  const p = getPowerRatingsPath(sportKey);
  if (!existsSync(p)) return [];

  try {
    const raw = readFileSync(p, "utf-8");
    const data = JSON.parse(raw) as { ratings?: PowerRatingRow[] };
    return Array.isArray(data.ratings) ? data.ratings : [];
  } catch {
    return [];
  }
}
