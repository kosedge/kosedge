import "server-only";
import { existsSync, readdirSync, readFileSync } from "node:fs";
import path from "node:path";

type CsvRow = Record<string, string>;

export type TeamProjectionRow = {
  season: number;
  team: string;
  conference: string;
  division: string;
  expectedWins: number;
  winsP10: number;
  winsP90: number;
  playoffProb: number;
  divisionTitleProb: number;
  superBowlWinProb: number;
};

export type PlayerProjectionTotalsRow = {
  season: number;
  playerKey: string;
  playerName: string;
  team: string;
  position: string;
  gamesProjected: number;
  passYardsTotal: number;
  rushYardsTotal: number;
  receivingYardsTotal: number;
  receptionsTotal: number;
  passTdsTotal: number;
  rushTdsTotal: number;
  recTdsTotal: number;
  anytimeTdProbTotal: number;
};

export type NflPreseasonBundle = {
  bundleDirName: string;
  bundlePath: string;
  generatedAtUtc: string | null;
  qualityChecks: {
    sumSuperBowlProb?: number;
    sumDivisionTitleProb?: number;
    sumPlayoffProb?: number;
  };
  teamRows: TeamProjectionRow[];
  playerTotalsRegular: PlayerProjectionTotalsRow[];
  playerTotalsPlayoff: PlayerProjectionTotalsRow[];
};

function toNumber(value: string | undefined): number {
  const parsed = Number(value ?? "");
  return Number.isFinite(parsed) ? parsed : 0;
}

function toInt(value: string | undefined): number {
  return Math.round(toNumber(value));
}

function parseCsvRows(input: string): CsvRow[] {
  const lines = input.trim().split(/\r?\n/);
  if (lines.length < 2) return [];
  const header = parseCsvLine(lines[0]);
  return lines.slice(1).map((line) => {
    const values = parseCsvLine(line);
    const row: CsvRow = {};
    header.forEach((key, idx) => {
      row[key] = values[idx] ?? "";
    });
    return row;
  });
}

function parseCsvLine(line: string): string[] {
  const values: string[] = [];
  let cell = "";
  let inQuotes = false;
  for (let index = 0; index < line.length; index += 1) {
    const char = line[index];
    if (char === '"') {
      const next = line[index + 1];
      if (inQuotes && next === '"') {
        cell += '"';
        index += 1;
      } else {
        inQuotes = !inQuotes;
      }
      continue;
    }
    if (char === "," && !inQuotes) {
      values.push(cell);
      cell = "";
      continue;
    }
    cell += char;
  }
  values.push(cell);
  return values;
}

function findRepoRoot(): string | null {
  let current = process.cwd();
  for (let depth = 0; depth < 6; depth += 1) {
    const dataOps = path.join(current, "data", "ops");
    if (existsSync(dataOps)) return current;
    const parent = path.dirname(current);
    if (parent === current) break;
    current = parent;
  }
  return null;
}

function list2026BundleDirectories(dataOpsPath: string): string[] {
  return readdirSync(dataOpsPath, { withFileTypes: true })
    .filter((entry) => entry.isDirectory())
    .map((entry) => entry.name)
    .filter((name) => name.startsWith("nfl-preseason-sim-2026-"))
    .sort()
    .reverse();
}

function mapTeamRows(rows: CsvRow[]): TeamProjectionRow[] {
  return rows.map((row) => ({
    season: toInt(row.season),
    team: row.team ?? "UNK",
    conference: row.conference ?? "",
    division: row.division ?? "",
    expectedWins: toNumber(row.expected_wins),
    winsP10: toInt(row.wins_p10),
    winsP90: toInt(row.wins_p90),
    playoffProb: toNumber(row.playoff_prob),
    divisionTitleProb: toNumber(row.division_title_prob),
    superBowlWinProb: toNumber(row.super_bowl_win_prob),
  }));
}

function mapPlayerTotalsRows(rows: CsvRow[]): PlayerProjectionTotalsRow[] {
  return rows.map((row) => ({
    season: toInt(row.season),
    playerKey: row.player_key ?? "",
    playerName: row.player_name ?? "Unknown",
    team: row.team ?? "UNK",
    position: row.position ?? "UNK",
    gamesProjected: toInt(row.games_projected),
    passYardsTotal: toNumber(row.pass_yards_total),
    rushYardsTotal: toNumber(row.rush_yards_total),
    receivingYardsTotal: toNumber(row.receiving_yards_total),
    receptionsTotal: toNumber(row.receptions_total),
    passTdsTotal: toNumber(row.pass_tds_total),
    rushTdsTotal: toNumber(row.rush_tds_total),
    recTdsTotal: toNumber(row.rec_tds_total),
    // CSV column is `anytime_td_prob` (not `anytime_td_prob_total`) -- see
    // player_season_totals.py for why this stays a bounded probability
    // rather than a summed total like the other columns here.
    anytimeTdProbTotal: toNumber(row.anytime_td_prob),
  }));
}

function loadBundleFromDir(
  dataOpsPath: string,
  bundleDirName: string,
): NflPreseasonBundle | null {
  const bundlePath = path.join(dataOpsPath, bundleDirName);
  const teamPath = path.join(bundlePath, "team_regular_season_outcomes.csv");
  const regularPath = path.join(bundlePath, "player_regular_season_totals.csv");
  const playoffPath = path.join(bundlePath, "player_playoff_totals.csv");
  const checksPath = path.join(bundlePath, "quality_checks.json");
  const summaryPath = path.join(bundlePath, "run_summary.json");
  if (
    !existsSync(teamPath) ||
    !existsSync(regularPath) ||
    !existsSync(playoffPath)
  ) {
    return null;
  }

  const teamRows = mapTeamRows(parseCsvRows(readFileSync(teamPath, "utf8")));
  const playerTotalsRegular = mapPlayerTotalsRows(
    parseCsvRows(readFileSync(regularPath, "utf8")),
  );
  const playerTotalsPlayoff = mapPlayerTotalsRows(
    parseCsvRows(readFileSync(playoffPath, "utf8")),
  );

  let generatedAtUtc: string | null = null;
  if (existsSync(summaryPath)) {
    try {
      const parsed = JSON.parse(readFileSync(summaryPath, "utf8")) as {
        generated_at_utc?: string;
      };
      generatedAtUtc = parsed.generated_at_utc ?? null;
    } catch {
      generatedAtUtc = null;
    }
  }

  let qualityChecks: NflPreseasonBundle["qualityChecks"] = {};
  if (existsSync(checksPath)) {
    try {
      const parsed = JSON.parse(readFileSync(checksPath, "utf8")) as {
        sanity?: {
          sum_super_bowl_prob?: number;
          sum_division_title_prob?: number;
          sum_playoff_prob?: number;
        };
      };
      qualityChecks = {
        sumSuperBowlProb: parsed.sanity?.sum_super_bowl_prob,
        sumDivisionTitleProb: parsed.sanity?.sum_division_title_prob,
        sumPlayoffProb: parsed.sanity?.sum_playoff_prob,
      };
    } catch {
      qualityChecks = {};
    }
  }

  return {
    bundleDirName,
    bundlePath,
    generatedAtUtc,
    qualityChecks,
    teamRows,
    playerTotalsRegular,
    playerTotalsPlayoff,
  };
}

export function loadLatestNflPreseasonBundle2026(): NflPreseasonBundle | null {
  const repoRoot = findRepoRoot();
  if (!repoRoot) return null;
  const dataOpsPath = path.join(repoRoot, "data", "ops");
  const bundleDirs = list2026BundleDirectories(dataOpsPath);
  for (const bundleDirName of bundleDirs) {
    const bundle = loadBundleFromDir(dataOpsPath, bundleDirName);
    if (bundle) return bundle;
  }
  return null;
}

/** Latest N valid 2026 preseason sim bundles (newest first). Used for weekly Δ. */
export function loadNflPreseasonBundles2026(
  limit = 2,
): NflPreseasonBundle[] {
  const repoRoot = findRepoRoot();
  if (!repoRoot) return [];
  const dataOpsPath = path.join(repoRoot, "data", "ops");
  const bundleDirs = list2026BundleDirectories(dataOpsPath);
  const out: NflPreseasonBundle[] = [];
  for (const bundleDirName of bundleDirs) {
    const bundle = loadBundleFromDir(dataOpsPath, bundleDirName);
    if (bundle) out.push(bundle);
    if (out.length >= limit) break;
  }
  return out;
}

/** Bundle directory names available for the week/history selector. */
export function listNflPreseasonBundleIds2026(): string[] {
  const repoRoot = findRepoRoot();
  if (!repoRoot) return [];
  const dataOpsPath = path.join(repoRoot, "data", "ops");
  return list2026BundleDirectories(dataOpsPath).filter((name) => {
    const teamPath = path.join(
      dataOpsPath,
      name,
      "team_regular_season_outcomes.csv",
    );
    return existsSync(teamPath);
  });
}

export function loadNflPreseasonBundleById2026(
  bundleId: string,
): NflPreseasonBundle | null {
  if (!bundleId.startsWith("nfl-preseason-sim-2026-")) return null;
  const repoRoot = findRepoRoot();
  if (!repoRoot) return null;
  return loadBundleFromDir(path.join(repoRoot, "data", "ops"), bundleId);
}
