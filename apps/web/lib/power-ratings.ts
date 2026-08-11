/**
 * Power ratings: team strength / rankings per sport.
 * NFL uses the existing preseason simulation engine (expected wins) — not a new formula.
 * Off/Def columns are filled from owned intel EPA when available (same model stack).
 */

import { readFileSync, existsSync } from "node:fs";
import { getSport } from "@/lib/sports";
import { getPowerRatingsPath } from "@/lib/data-paths";
import { canonicalizeNflTeam } from "@/lib/nfl-canonical-teams";
import {
  loadLatestNflPreseasonBundle2026,
  loadNflPreseasonBundleById2026,
  loadNflPreseasonBundles2026,
  listNflPreseasonBundleIds2026,
  type NflPreseasonBundle,
} from "@/lib/nfl-preseason-artifacts";
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
  /** Offense EPA/play (intel) or model offense index when available */
  offense?: number | null;
  /** Defense EPA allowed/play (intel) or model defense index when available */
  defense?: number | null;
  weeklyDelta?: number | null;
  rankDelta?: number | null;
  record?: string | null;
  playoffProb?: number | null;
};

export type NflPowerIntelRow = {
  team?: unknown;
  wins?: unknown;
  losses?: unknown;
  ties?: unknown;
  epa_per_play_offense?: unknown;
  epa_per_play_defense_allowed?: unknown;
};

/**
 * Join Power Ratings board rows to intel standings/stats on canonical team ids.
 * Bundle rows are product-canonical (LAR); nflverse intel often still emits LA.
 */
export function enrichNflPowerRatingsWithIntel(
  rows: PowerRatingRow[],
  standingsRows: NflPowerIntelRow[],
  statsRows: NflPowerIntelRow[],
): PowerRatingRow[] {
  const standingsByTeam = indexIntelRowsByCanonicalTeam(standingsRows);
  const statsByTeam = indexIntelRowsByCanonicalTeam(statsRows);

  return rows.map((row) => {
    const code =
      canonicalizeNflTeam(row.teamNorm ?? row.team) ?? row.teamNorm ?? "";
    const st = standingsByTeam.get(code);
    const stat = statsByTeam.get(code);
    const wins = typeof st?.wins === "number" ? st.wins : null;
    const losses = typeof st?.losses === "number" ? st.losses : null;
    const ties = typeof st?.ties === "number" ? st.ties : null;
    const record =
      wins != null && losses != null
        ? ties && ties > 0
          ? `${wins}-${losses}-${ties}`
          : `${wins}-${losses}`
        : null;
    const offense =
      typeof stat?.epa_per_play_offense === "number"
        ? Number(stat.epa_per_play_offense.toFixed(3))
        : null;
    const defense =
      typeof stat?.epa_per_play_defense_allowed === "number"
        ? Number(stat.epa_per_play_defense_allowed.toFixed(3))
        : null;
    return { ...row, record, offense, defense };
  });
}

function indexIntelRowsByCanonicalTeam(
  rows: NflPowerIntelRow[],
): Map<string, NflPowerIntelRow> {
  const map = new Map<string, NflPowerIntelRow>();
  for (const row of rows) {
    if (typeof row.team !== "string") continue;
    const code = canonicalizeNflTeam(row.team) ?? row.team;
    // First write wins; prefer already-canonical LAR over a later LA duplicate.
    if (!map.has(code)) map.set(code, row);
  }
  return map;
}

export type NflPowerRatingsBoard = {
  rows: PowerRatingRow[];
  bundleId: string | null;
  previousBundleId: string | null;
  availableBundles: string[];
  generatedAtUtc: string | null;
  engineVersion?: string | null;
  nTeamSims?: number | null;
  launchIdentity?: string | null;
  activeRunId?: string | null;
  lineage?: NflPreseasonBundle["lineage"];
};

function rankByExpectedWins(
  teamRows: NflPreseasonBundle["teamRows"],
): Map<string, { rank: number; wins: number }> {
  const sorted = teamRows
    .slice()
    .sort(
      (a, b) =>
        b.expectedWins - a.expectedWins || b.playoffProb - a.playoffProb,
    );
  const map = new Map<string, { rank: number; wins: number }>();
  sorted.forEach((row, index) => {
    map.set(row.team, { rank: index + 1, wins: row.expectedWins });
  });
  return map;
}

function nflBoardFromBundles(
  current: NflPreseasonBundle,
  previous: NflPreseasonBundle | null,
  availableBundles: string[],
): NflPowerRatingsBoard {
  const prevRanks = previous ? rankByExpectedWins(previous.teamRows) : null;
  const rows: PowerRatingRow[] = current.teamRows
    .slice()
    .sort(
      (a, b) =>
        b.expectedWins - a.expectedWins || b.playoffProb - a.playoffProb,
    )
    .map((row, index) => {
      const rank = index + 1;
      const prev = prevRanks?.get(row.team);
      return {
        rank,
        team: teamDisplayName(row.team),
        teamNorm: row.team,
        // Rating = expected wins from the active preseason sim bundle (existing engine).
        rating: Number(row.expectedWins.toFixed(2)),
        year: row.season,
        offense: null,
        defense: null,
        weeklyDelta:
          prev != null
            ? Number((row.expectedWins - prev.wins).toFixed(2))
            : null,
        rankDelta: prev != null ? prev.rank - rank : null,
        record: null,
        playoffProb: row.playoffProb,
      };
    });

  return {
    rows,
    bundleId: current.bundleDirName,
    previousBundleId: previous?.bundleDirName ?? null,
    availableBundles,
    generatedAtUtc: current.generatedAtUtc,
    engineVersion: current.engineVersion ?? null,
    nTeamSims: current.nTeamSims ?? null,
    launchIdentity: current.launchIdentity ?? null,
    activeRunId: current.activeRunId ?? current.bundleDirName,
    lineage: current.lineage ?? null,
  };
}

function nflRatingsFromPreseasonBundle(): PowerRatingRow[] {
  return getNflPowerRatingsBoard().rows;
}

export function getNflPowerRatingsBoard(options?: {
  bundleId?: string | null;
}): NflPowerRatingsBoard {
  const available = listNflPreseasonBundleIds2026();
  const current =
    (options?.bundleId
      ? loadNflPreseasonBundleById2026(options.bundleId)
      : null) ?? loadLatestNflPreseasonBundle2026();
  if (!current) {
    return {
      rows: [],
      bundleId: null,
      engineVersion: null,
      nTeamSims: null,
      launchIdentity: null,
      previousBundleId: null,
      availableBundles: available,
      generatedAtUtc: null,
      activeRunId: null,
      lineage: null,
    };
  }
  const history = loadNflPreseasonBundles2026(8);
  const currentIdx = history.findIndex(
    (b) => b.bundleDirName === current.bundleDirName,
  );
  const previous =
    currentIdx >= 0 && currentIdx + 1 < history.length
      ? history[currentIdx + 1]!
      : (history.find((b) => b.bundleDirName !== current.bundleDirName) ?? null);
  return nflBoardFromBundles(current, previous, available);
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
