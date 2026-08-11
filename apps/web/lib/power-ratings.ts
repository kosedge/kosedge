/**
 * Power ratings: team strength / rankings per sport.
 *
 * NFL Power Ratings desk (2026-08-11):
 *   Model PR = Method B compressed neutral-field strength (points vs avg)
 *   Ryan PR  = Model PR + Ryan Adj (default 0; never overwrites Model)
 * Snapshot: data/ops/nfl-power-ratings-desk/latest.json (Tuesday publish)
 * Fallback: preseason expected-wins board (outlook only) when desk missing.
 */

import { readFileSync, existsSync } from "node:fs";
import path from "node:path";
import { getSport } from "@/lib/sports";
import { getPowerRatingsPath } from "@/lib/data-paths";
import { canonicalizeNflTeam } from "@/lib/nfl-canonical-teams";
import {
  loadLatestNflPreseasonBundle2026,
  loadNflPreseasonBundleById2026,
  loadNflPreseasonBundles2026,
  listNflPreseasonBundleIds2026,
  loadNflWebLaunchPointer,
  type NflPreseasonBundle,
} from "@/lib/nfl-preseason-artifacts";
import { teamDisplayName } from "@/lib/nfl-team-intel";

export type PowerRatingRow = {
  rank: number;
  team: string;
  teamNorm?: string;
  /** @deprecated Prefer modelPr — kept for non-NFL / wins outlook fallback */
  rating: number;
  adjem?: number;
  torvik?: number;
  barthag?: number;
  year?: number;
  /** Offense EPA/play (intel) when desk Off PR unavailable */
  offense?: number | null;
  /** Defense EPA allowed/play (intel) when desk Def PR unavailable */
  defense?: number | null;
  weeklyDelta?: number | null;
  rankDelta?: number | null;
  record?: string | null;
  playoffProb?: number | null;
  /** Desk fields (points vs league average, neutral field) */
  modelPr?: number | null;
  ryanAdj?: number | null;
  ryanPr?: number | null;
  marketPr?: number | null;
  deltaMarket?: number | null;
  offPr?: number | null;
  defPr?: number | null;
  stPr?: number | null;
  stApproximate?: boolean;
  activePr?: number | null;
  uncertainty?: number | null;
  prevWeekModelPr?: number | null;
};

export type NflPowerIntelRow = {
  team?: unknown;
  wins?: unknown;
  losses?: unknown;
  ties?: unknown;
  epa_per_play_offense?: unknown;
  epa_per_play_defense_allowed?: unknown;
};

export type NflPowerDeskMeta = {
  method: string | null;
  methodLabel: string | null;
  phase: string | null;
  asOfWeek: number | null;
  deskVersion: string | null;
  meanModelPr: number | null;
  stNote: string | null;
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
  desk?: NflPowerDeskMeta | null;
  source: "power_desk" | "expected_wins_fallback";
};

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

function loadPowerDeskSnapshot(): {
  rows: PowerRatingRow[];
  meta: NflPowerDeskMeta;
  generatedAtUtc: string | null;
  engineVersion: string | null;
  activeRunId: string | null;
} | null {
  const root = findRepoRoot();
  if (!root) return null;
  const latest = path.join(
    root,
    "data",
    "ops",
    "nfl-power-ratings-desk",
    "latest.json",
  );
  if (!existsSync(latest)) return null;
  try {
    const raw = JSON.parse(readFileSync(latest, "utf8")) as {
      teams?: Array<Record<string, unknown>>;
      method?: string;
      method_label?: string;
      phase?: string;
      as_of_week?: number;
      desk_version?: string;
      mean_model_pr?: number;
      generated_at_utc?: string;
      engine_version?: string;
      active_run_id?: string;
    };
    if (!Array.isArray(raw.teams) || raw.teams.length === 0) return null;
    const rows: PowerRatingRow[] = raw.teams.map((t, idx) => {
      const teamNorm =
        canonicalizeNflTeam(String(t.team ?? "")) ?? String(t.team ?? "");
      const modelPr =
        typeof t.model_pr === "number" ? Number(t.model_pr) : null;
      const ryanAdj =
        typeof t.ryan_adj === "number" ? Number(t.ryan_adj) : 0;
      const ryanPr =
        typeof t.ryan_pr === "number" ? Number(t.ryan_pr) : modelPr;
      return {
        rank: typeof t.rank === "number" ? t.rank : idx + 1,
        team: teamDisplayName(teamNorm),
        teamNorm,
        rating: modelPr ?? 0,
        modelPr,
        ryanAdj,
        ryanPr,
        marketPr:
          typeof t.market_pr === "number" ? Number(t.market_pr) : null,
        deltaMarket:
          typeof t.delta_market === "number" ? Number(t.delta_market) : null,
        offPr: typeof t.off_pr === "number" ? Number(t.off_pr) : null,
        defPr: typeof t.def_pr === "number" ? Number(t.def_pr) : null,
        stPr: typeof t.st_pr === "number" ? Number(t.st_pr) : null,
        stApproximate: Boolean(t.st_approximate ?? true),
        activePr:
          typeof t.active_pr === "number" ? Number(t.active_pr) : null,
        uncertainty:
          typeof t.uncertainty === "number" ? Number(t.uncertainty) : null,
        prevWeekModelPr:
          typeof t.prev_week_model_pr === "number"
            ? Number(t.prev_week_model_pr)
            : null,
        weeklyDelta:
          typeof t.weekly_delta === "number" ? Number(t.weekly_delta) : null,
        offense: null,
        defense: null,
        record: null,
        playoffProb: null,
      };
    });
    rows.sort(
      (a, b) =>
        (b.modelPr ?? b.rating) - (a.modelPr ?? a.rating) ||
        String(a.teamNorm).localeCompare(String(b.teamNorm)),
    );
    rows.forEach((r, i) => {
      r.rank = i + 1;
    });
    return {
      rows,
      meta: {
        method: raw.method ?? "B",
        methodLabel: raw.method_label ?? null,
        phase: raw.phase ?? null,
        asOfWeek: typeof raw.as_of_week === "number" ? raw.as_of_week : null,
        deskVersion: raw.desk_version ?? null,
        meanModelPr:
          typeof raw.mean_model_pr === "number" ? raw.mean_model_pr : null,
        stNote: "ST approximate (st_index / post-kicker)",
      },
      generatedAtUtc: raw.generated_at_utc ?? null,
      engineVersion: raw.engine_version ?? null,
      activeRunId: raw.active_run_id ?? null,
    };
  } catch {
    return null;
  }
}

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
        // Outlook fallback only — not Model PR points.
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
    desk: null,
    source: "expected_wins_fallback",
  };
}

function nflRatingsFromPreseasonBundle(): PowerRatingRow[] {
  return getNflPowerRatingsBoard().rows;
}

export function getNflPowerRatingsBoard(options?: {
  bundleId?: string | null;
}): NflPowerRatingsBoard {
  const available = listNflPreseasonBundleIds2026();
  const pointer = loadNflWebLaunchPointer();
  const desk = loadPowerDeskSnapshot();

  // Prefer Power Ratings desk snapshot (Model PR points) when present.
  if (desk && !options?.bundleId) {
    return {
      rows: desk.rows,
      bundleId: pointer?.bundle_id ?? desk.activeRunId,
      previousBundleId: null,
      availableBundles: available,
      generatedAtUtc: desk.generatedAtUtc,
      engineVersion: desk.engineVersion ?? pointer?.engine_version ?? null,
      nTeamSims: pointer?.n_team_sims ?? null,
      launchIdentity: pointer?.identity ?? null,
      activeRunId:
        desk.activeRunId ??
        pointer?.active_run_id ??
        pointer?.bundle_id ??
        null,
      lineage: pointer?.lineage ?? null,
      desk: desk.meta,
      source: "power_desk",
    };
  }

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
      desk: null,
      source: "expected_wins_fallback",
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
