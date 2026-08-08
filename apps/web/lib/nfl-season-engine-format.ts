/**
 * Pure helpers for NFL season-engine UI request shaping + display.
 * Kept free of server-only imports for unit tests.
 */

export const NFL_SEASON_ENGINE_TEAMS = [
  "ARI",
  "ATL",
  "BAL",
  "BUF",
  "CAR",
  "CHI",
  "CIN",
  "CLE",
  "DAL",
  "DEN",
  "DET",
  "GB",
  "HOU",
  "IND",
  "JAX",
  "KC",
  "LA",
  "LAC",
  "LV",
  "MIA",
  "MIN",
  "NE",
  "NO",
  "NYG",
  "NYJ",
  "PHI",
  "PIT",
  "SEA",
  "SF",
  "TB",
  "TEN",
  "WAS",
] as const;

export type NflSeasonEngineTeam =
  (typeof NFL_SEASON_ENGINE_TEAMS)[number];

/** Named skill stars useful for injury scenario toggles (real 2026 depth). */
export const NFL_SEASON_ENGINE_STAR_OUTS: ReadonlyArray<{
  team: NflSeasonEngineTeam;
  playerName: string;
  label: string;
}> = [
  { team: "KC", playerName: "Patrick Mahomes", label: "P. Mahomes out" },
  { team: "BUF", playerName: "Josh Allen", label: "J. Allen out" },
  { team: "PHI", playerName: "Saquon Barkley", label: "S. Barkley out" },
  { team: "SF", playerName: "Christian McCaffrey", label: "C. McCaffrey out" },
  { team: "DET", playerName: "Amon-Ra St. Brown", label: "A. St. Brown out" },
];

export type StatDist = {
  mean: number;
  std: number;
  p10: number;
  p50: number;
  p90: number;
};

export type InjuryPathInput = {
  team: string;
  status: "out" | "limited" | "returning";
  week_start: number;
  week_end: number;
  player_name?: string;
  player_key?: string;
  availability?: number;
  severity?: number;
};

const TEAM_SET = new Set<string>(NFL_SEASON_ENGINE_TEAMS);

/** Normalize common aliases (LAR → LA) and uppercase. */
export function normalizeNflTeamCode(raw: string): string | null {
  const token = raw.trim().toUpperCase();
  if (!token) return null;
  const mapped = token === "LAR" ? "LA" : token === "WSH" ? "WAS" : token;
  return TEAM_SET.has(mapped) ? mapped : null;
}

export function parseAlreadyUsedTeams(raw: string | string[]): string[] {
  const tokens = Array.isArray(raw)
    ? raw
    : raw
        .split(/[\s,;]+/)
        .map((t) => t.trim())
        .filter(Boolean);
  const out: string[] = [];
  const seen = new Set<string>();
  for (const token of tokens) {
    const code = normalizeNflTeamCode(token);
    if (!code || seen.has(code)) continue;
    seen.add(code);
    out.push(code);
  }
  return out;
}

export function clampInt(
  value: unknown,
  fallback: number,
  min: number,
  max: number,
): number {
  const n =
    typeof value === "number"
      ? value
      : typeof value === "string"
        ? Number(value)
        : NaN;
  if (!Number.isFinite(n)) return fallback;
  return Math.min(max, Math.max(min, Math.round(n)));
}

export function buildGameBoxesQuery(input: {
  homeTeam: string;
  awayTeam: string;
  week?: number;
  season?: number;
  nReplicates?: number;
  seed?: number;
  demo?: boolean;
  includeDiagnostics?: boolean;
}): {
  home_team: string;
  away_team: string;
  week: number;
  season: number;
  n_replicates: number;
  seed?: number;
  demo?: boolean;
  include_diagnostics?: boolean;
} {
  const home = normalizeNflTeamCode(input.homeTeam);
  const away = normalizeNflTeamCode(input.awayTeam);
  if (!home || !away) {
    throw new Error("home_team and away_team must be valid NFL abbreviations");
  }
  if (home === away) {
    throw new Error("home_team and away_team must differ");
  }
  return {
    home_team: home,
    away_team: away,
    week: clampInt(input.week, 1, 1, 22),
    season: clampInt(input.season, 2026, 2020, 2030),
    n_replicates: clampInt(input.nReplicates, 50, 50, 500),
    ...(input.seed !== undefined
      ? { seed: clampInt(input.seed, 42, 0, 2_147_483_647) }
      : {}),
    ...(input.demo !== undefined ? { demo: Boolean(input.demo) } : {}),
    ...(input.includeDiagnostics
      ? { include_diagnostics: true }
      : {}),
  };
}

export function buildSurvivorBody(input: {
  week: number;
  alreadyUsed?: string | string[];
  nSims?: number;
  season?: number;
  seed?: number;
  demo?: boolean;
  topN?: number;
  injuryPaths?: InjuryPathInput[];
  includeDiagnostics?: boolean;
}): {
  season: number;
  week: number;
  n_sims: number;
  already_used: string[];
  top_n: number;
  seed?: number;
  demo?: boolean;
  injury_paths?: InjuryPathInput[];
  include_diagnostics?: boolean;
} {
  return {
    season: clampInt(input.season, 2026, 2020, 2030),
    week: clampInt(input.week, 1, 1, 22),
    n_sims: clampInt(input.nSims, 200, 50, 500),
    already_used: parseAlreadyUsedTeams(input.alreadyUsed ?? []),
    top_n: clampInt(input.topN, 16, 1, 32),
    ...(input.seed !== undefined
      ? { seed: clampInt(input.seed, 42, 0, 2_147_483_647) }
      : {}),
    ...(input.demo !== undefined ? { demo: Boolean(input.demo) } : {}),
    ...(input.injuryPaths?.length
      ? { injury_paths: input.injuryPaths }
      : {}),
    ...(input.includeDiagnostics === false
      ? { include_diagnostics: false }
      : { include_diagnostics: true }),
  };
}

/** Normalize planner picks ``{ week: team }``; drops invalid / duplicate teams. */
export function normalizeSurvivorPlanPicks(
  picks: Record<string, string> | Record<number, string> | null | undefined,
): Record<string, string> {
  if (!picks || typeof picks !== "object") return {};
  const out: Record<string, string> = {};
  const seen = new Set<string>();
  const weeks = Object.keys(picks)
    .map((k) => Number(k))
    .filter((w) => Number.isFinite(w) && w >= 1 && w <= 22)
    .sort((a, b) => a - b);
  for (const week of weeks) {
    const raw = (picks as Record<string | number, string>)[week] ??
      (picks as Record<string, string>)[String(week)];
    const team = normalizeNflTeamCode(String(raw ?? ""));
    if (!team || seen.has(team)) continue;
    seen.add(team);
    out[String(week)] = team;
  }
  return out;
}

export function buildSurvivorPlanBody(input: {
  picks?: Record<string, string> | Record<number, string>;
  nSims?: number;
  season?: number;
  seed?: number;
  demo?: boolean;
  topN?: number;
  injuryPaths?: InjuryPathInput[];
  includeDiagnostics?: boolean;
}): {
  season: number;
  n_sims: number;
  picks: Record<string, string>;
  top_n: number;
  seed?: number;
  demo?: boolean;
  injury_paths?: InjuryPathInput[];
  include_diagnostics?: boolean;
} {
  return {
    season: clampInt(input.season, 2026, 2020, 2030),
    n_sims: clampInt(input.nSims, 250, 50, 500),
    picks: normalizeSurvivorPlanPicks(input.picks),
    top_n: clampInt(input.topN, 6, 1, 32),
    ...(input.seed !== undefined
      ? { seed: clampInt(input.seed, 42, 0, 2_147_483_647) }
      : {}),
    ...(input.demo !== undefined ? { demo: Boolean(input.demo) } : {}),
    ...(input.injuryPaths?.length
      ? { injury_paths: input.injuryPaths }
      : {}),
    ...(input.includeDiagnostics === false
      ? { include_diagnostics: false }
      : { include_diagnostics: true }),
  };
}

export function buildStarOutInjuryPath(input: {
  team: string;
  playerName: string;
  week: number;
}): InjuryPathInput | null {
  const team = normalizeNflTeamCode(input.team);
  if (!team || !input.playerName.trim()) return null;
  const week = clampInt(input.week, 1, 1, 22);
  return {
    team,
    status: "out",
    week_start: week,
    week_end: week,
    player_name: input.playerName.trim(),
  };
}

export function starOutOptionsForMatchup(
  homeTeam: string,
  awayTeam: string,
): typeof NFL_SEASON_ENGINE_STAR_OUTS[number][] {
  const home = normalizeNflTeamCode(homeTeam);
  const away = normalizeNflTeamCode(awayTeam);
  return NFL_SEASON_ENGINE_STAR_OUTS.filter(
    (s) => s.team === home || s.team === away,
  );
}

/** Position-primary columns for box score tables. */
export function primaryStatsForPosition(position: string): string[] {
  const pos = position.toUpperCase();
  if (pos === "QB") return ["pass_yards", "pass_tds", "ints", "rush_yards"];
  if (pos === "RB") return ["rush_yards", "rush_tds", "rec_yards", "receptions"];
  if (pos === "WR" || pos === "TE")
    return ["rec_yards", "receptions", "rec_tds"];
  return ["rush_yards", "rec_yards", "receptions"];
}

export function formatStatLabel(stat: string): string {
  const map: Record<string, string> = {
    pass_yards: "Pass Yds",
    pass_tds: "Pass TD",
    ints: "INT",
    rush_yards: "Rush Yds",
    rush_tds: "Rush TD",
    rec_yards: "Rec Yds",
    receptions: "Rec",
    rec_tds: "Rec TD",
    pass_attempts: "Att",
    carries: "Car",
    targets: "Tgt",
  };
  return map[stat] ?? stat.replace(/_/g, " ");
}

export function formatStatNumber(value: number, digits = 1): string {
  if (!Number.isFinite(value)) return "—";
  if (Math.abs(value) >= 100) return value.toFixed(0);
  if (Number.isInteger(value)) return String(value);
  return value.toFixed(digits);
}

export function formatPct(value: number, digits = 1): string {
  if (!Number.isFinite(value)) return "—";
  return `${(value * 100).toFixed(digits)}%`;
}

/** Outlook-only slate band — harder schedule ≠ weaker team. */
export function formatScheduleDifficulty(
  band: string | null | undefined,
): string {
  switch (String(band || "").toLowerCase()) {
    case "easy":
      return "Easy slate";
    case "hard":
      return "Hard slate";
    case "average":
      return "Avg slate";
    default:
      return "—";
  }
}

/** Survivor path difficulty letter from projected SOS (not a PR dial). */
export function formatPathDifficultyGrade(
  grade: string | null | undefined,
): string {
  const g = String(grade || "").trim().toUpperCase();
  if (!g || g === "—" || g === "NULL") return "—";
  return g;
}

export function formatRange(dist: StatDist | undefined, digits = 1): string {
  if (!dist) return "";
  return `${formatStatNumber(dist.p10, digits)}–${formatStatNumber(dist.p90, digits)}`;
}

export function rankSurvivorPicks<T extends { pick_now_score?: number }>(
  picks: T[],
): Array<T & { rank: number }> {
  const sorted = [...picks].sort(
    (a, b) => (b.pick_now_score ?? 0) - (a.pick_now_score ?? 0),
  );
  return sorted.map((pick, i) => ({ ...pick, rank: i + 1 }));
}

export function positionSortKey(position: string): number {
  const order: Record<string, number> = {
    QB: 0,
    RB: 1,
    WR: 2,
    TE: 3,
  };
  return order[position.toUpperCase()] ?? 9;
}

export type SeasonEngineMatchupOption = {
  id: string;
  label: string;
  homeTeam: string;
  awayTeam: string;
  week: number | null;
  startTime: string | null;
  source: "fair-lines" | "wall-chart" | "manual";
};

/** Expand wall-chart week map (`@ LAC` / `vs SEA`) into unique matchups. */
export function matchupsFromWallChart(
  chart: Record<string, Record<string, string>>,
  opts?: { season?: number; maxWeek?: number },
): SeasonEngineMatchupOption[] {
  const season = opts?.season ?? 2026;
  const maxWeek = opts?.maxWeek ?? 18;
  const seen = new Set<string>();
  const out: SeasonEngineMatchupOption[] = [];
  for (const [teamRaw, weeks] of Object.entries(chart)) {
    const team = normalizeNflTeamCode(teamRaw);
    if (!team || !weeks) continue;
    for (const [weekRaw, matchupRaw] of Object.entries(weeks)) {
      const week = Number(weekRaw);
      if (!Number.isFinite(week) || week < 1 || week > maxWeek) continue;
      const m = String(matchupRaw || "").trim();
      let home: string | null = null;
      let away: string | null = null;
      if (m.startsWith("@ ")) {
        away = team;
        home = normalizeNflTeamCode(m.slice(2));
      } else if (m.startsWith("vs ")) {
        home = team;
        away = normalizeNflTeamCode(m.slice(3));
      }
      if (!home || !away) continue;
      const key = `${week}|${away}@${home}`;
      if (seen.has(key)) continue;
      seen.add(key);
      out.push({
        id: `${season}-W${String(week).padStart(2, "0")}-${away}@${home}`,
        label: `${away} @ ${home} · W${week}`,
        homeTeam: home,
        awayTeam: away,
        week,
        startTime: null,
        source: "wall-chart",
      });
    }
  }
  return out.sort(
    (a, b) =>
      (a.week ?? 99) - (b.week ?? 99) ||
      a.awayTeam.localeCompare(b.awayTeam) ||
      a.homeTeam.localeCompare(b.homeTeam),
  );
}
