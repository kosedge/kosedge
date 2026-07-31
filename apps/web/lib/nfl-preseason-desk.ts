import "server-only";
import { loadLatestNflPreseasonBundle2026 } from "@/lib/nfl-preseason-artifacts";

/**
 * Preseason desk reference — enterprise path while PRE game sims are absent.
 *
 * Regular-season fair-lines / sims remain REG-only. For PRE boards we publish:
 * 1) ESPN (or book) market numbers when posted
 * 2) A camp strength reference derived from the latest REG preseason sim
 *    expected-wins table (relative team strength → rough home spread)
 *
 * This is intentionally labeled informational: PRE rotations invalidate
 * season PLAY tags, and the reference is not a PRE-game simulation.
 */

const PRE_POINTS_PER_WIN_DIFF = 1.15;
const PRE_HOME_FIELD_POINTS = 1.0;

/** Map common schedule/sim aliases onto Kos Edge team codes. */
const ABBR_ALIASES: Record<string, string> = {
  LA: "LAR",
  LAR: "LAR",
  WSH: "WAS",
  WAS: "WAS",
  JAC: "JAX",
  JAX: "JAX",
  ARZ: "ARI",
  NOR: "NO",
  GNB: "GB",
  KAN: "KC",
  SFO: "SF",
  TAM: "TB",
  NWE: "NE",
  SD: "LAC",
  OAK: "LV",
  STL: "LAR",
};

export function normalizeNflAbbr(value: string | null | undefined): string {
  const raw = (value ?? "").trim().toUpperCase();
  if (!raw) return "";
  return ABBR_ALIASES[raw] ?? raw;
}

export type PreseasonStrengthMap = {
  bundleDirName: string;
  byTeam: Map<string, number>;
  leagueMeanWins: number;
};

export function loadPreseasonStrengthMap(): PreseasonStrengthMap | null {
  const bundle = loadLatestNflPreseasonBundle2026();
  if (!bundle?.teamRows?.length) return null;
  const byTeam = new Map<string, number>();
  let sum = 0;
  for (const row of bundle.teamRows) {
    const abbr = normalizeNflAbbr(row.team);
    if (!abbr) continue;
    byTeam.set(abbr, row.expectedWins);
    sum += row.expectedWins;
  }
  if (byTeam.size === 0) return null;
  return {
    bundleDirName: bundle.bundleDirName,
    byTeam,
    leagueMeanWins: sum / byTeam.size,
  };
}

function roundHalf(value: number): number {
  return Math.round(value * 2) / 2;
}

/**
 * Convert relative REG expected-wins into a PRE informational home spread.
 * Negative = home favored (same convention as fair-lines / ESPN).
 */
export function campReferenceSpreadHome(
  homeAbbr: string,
  awayAbbr: string,
  strength?: PreseasonStrengthMap | null,
): number | null {
  const map = strength ?? loadPreseasonStrengthMap();
  if (!map) return null;
  const home = map.byTeam.get(normalizeNflAbbr(homeAbbr));
  const away = map.byTeam.get(normalizeNflAbbr(awayAbbr));
  if (home == null || away == null) return null;
  const raw =
    -((home - away) * PRE_POINTS_PER_WIN_DIFF) - PRE_HOME_FIELD_POINTS;
  return roundHalf(raw);
}

export function campReferenceContextNote(options: {
  hasMarket: boolean;
  hasCampRef: boolean;
  bundleDirName?: string | null;
}): string {
  if (options.hasCampRef && options.hasMarket) {
    return "PRE info desk — ESPN market + camp strength ref from REG expected-wins (not a PRE-game sim; season PLAY tags blocked).";
  }
  if (options.hasCampRef) {
    return "PRE info desk — camp strength ref from REG expected-wins until books post a market (not a PRE-game sim).";
  }
  if (options.hasMarket) {
    return "PRE info desk — ESPN/market board only; camp strength ref unavailable for this matchup.";
  }
  return "PRE schedule card — waiting on market posts and camp strength join.";
}
