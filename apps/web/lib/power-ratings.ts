/**
 * Power ratings: team strength / rankings per sport.
 * Data is read from data/processed/power_ratings_{sport}.json (exported by pipeline script).
 * NFL falls back to the latest 2026 preseason simulation expected-wins table.
 */

import { readFileSync, existsSync } from "node:fs";
import { getSport } from "@/lib/sports";
import { getPowerRatingsPath } from "@/lib/data-paths";
import { loadLatestNflPreseasonBundle2026 } from "@/lib/nfl-preseason-artifacts";
import { teamDisplayName } from "@/lib/nfl-team-intel";

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

function nflRatingsFromPreseasonBundle(): PowerRatingRow[] {
  const bundle = loadLatestNflPreseasonBundle2026();
  if (!bundle?.teamRows?.length) return [];
  return bundle.teamRows
    .slice()
    .sort(
      (a, b) =>
        b.expectedWins - a.expectedWins ||
        b.playoffProb - a.playoffProb,
    )
    .map((row, index) => ({
      rank: index + 1,
      team: teamDisplayName(row.team),
      teamNorm: row.team,
      // Rating = expected wins from the active preseason sim bundle.
      rating: Number(row.expectedWins.toFixed(2)),
      year: row.season,
    }));
}

export function getPowerRatings(sportKey: string): PowerRatingRow[] {
  if (!getSport(sportKey)) return [];

  const p = getPowerRatingsPath(sportKey);
  if (existsSync(p)) {
    try {
      const raw = readFileSync(p, "utf-8");
      const data = JSON.parse(raw) as { ratings?: PowerRatingRow[] };
      if (Array.isArray(data.ratings) && data.ratings.length > 0) {
        return data.ratings;
      }
    } catch {
      // fall through
    }
  }

  if (sportKey === "nfl") return nflRatingsFromPreseasonBundle();
  return [];
}
