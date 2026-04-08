/**
 * Centralized paths for file-based data (power ratings, KEI lines).
 * Works in dev (apps/web as cwd) and Vercel (app root as cwd).
 */

import { join } from "node:path";

const DATA_PROCESSED = "data/processed";

/** Resolved path to data/processed (same dir as package.json when run from apps/web). */
export function getDataProcessedDir(): string {
  return join(process.cwd(), DATA_PROCESSED);
}

export function getPowerRatingsPath(sportKey: string): string {
  return join(getDataProcessedDir(), `power_ratings_${sportKey}.json`);
}

export function getKeiLinesPath(sportKey: string): string {
  return join(getDataProcessedDir(), `kei_lines_${sportKey}.json`);
}
