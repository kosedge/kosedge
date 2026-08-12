/**
 * Pure helpers for NFL season-engine UI request shaping + display.
 * Kept free of server-only imports for unit tests.
 */

import { canonicalizeNflTeam } from "@/lib/nfl-canonical-teams";

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
  "LAC",
  "LAR",
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
  /** TD honesty fields (engine ≥ research-depth runs). */
  p_td?: number;
  expected_rate?: number;
  fair_american?: number | null;
  display?: string;
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

/** Whole-token Rams code `LA` (never LAC). */
const RAW_LA_RAMS = /(^|[^A-Z])LA(?![A-Z])/;

/** Product canonical: LA/STL → LAR. LAC unchanged. Unknown codes stay null. */
export function normalizeNflTeamCode(raw: string): string | null {
  const mapped = canonicalizeNflTeam(raw);
  if (!mapped) return null;
  return TEAM_SET.has(mapped) ? mapped : null;
}

/** Canonicalize any NFL code for API ingest (unknown tokens pass through uppercased). */
export function canonicalizeSurvivorTeamCode(raw: unknown): string {
  if (raw == null) return "";
  const mapped = canonicalizeNflTeam(String(raw));
  return mapped ?? "";
}

export type SurvivorPickTeamFields = {
  team?: string;
  opponent?: string | null;
  matchup_label?: string | null;
  favorite_team?: string | null;
  home_away?: string | null;
};

export function canonicalizeSurvivorPickRow<T extends SurvivorPickTeamFields>(
  row: T,
): T {
  const team = row.team ? canonicalizeSurvivorTeamCode(row.team) : row.team;
  const opponent =
    row.opponent != null && row.opponent !== ""
      ? canonicalizeSurvivorTeamCode(row.opponent)
      : row.opponent;
  const favorite_team =
    row.favorite_team != null && row.favorite_team !== ""
      ? canonicalizeSurvivorTeamCode(row.favorite_team)
      : row.favorite_team;
  let matchup_label = row.matchup_label;
  if (team && opponent) {
    matchup_label =
      row.home_away === "away" ? `${team} @ ${opponent}` : `${team} vs ${opponent}`;
  } else if (typeof matchup_label === "string" && matchup_label) {
    matchup_label = matchup_label.replace(/(^|[^A-Z])LA(?![A-Z])/g, "$1LAR");
  }
  return { ...row, team, opponent, favorite_team, matchup_label };
}

export function canonicalizeTeamCodeMap(
  raw: Record<string, string> | null | undefined,
): Record<string, string> {
  if (!raw || typeof raw !== "object") return {};
  const out: Record<string, string> = {};
  for (const [week, team] of Object.entries(raw)) {
    const code = canonicalizeSurvivorTeamCode(team);
    if (code) out[week] = code;
  }
  return out;
}

const SURVIVOR_TEAM_KEYS = new Set([
  "team",
  "opponent",
  "locked_team",
  "favorite_team",
]);
const SURVIVOR_TEAM_LIST_KEYS = new Set([
  "already_used",
  "used_teams",
  "available_teams",
]);

/** Paths where raw Rams code `LA` appears in survivor JSON (empty = clean). */
export function rawLaRamsHits(payload: unknown, path = "$"): string[] {
  const hits: string[] = [];
  if (payload == null) return hits;
  if (Array.isArray(payload)) {
    payload.forEach((item, i) => {
      hits.push(...rawLaRamsHits(item, `${path}[${i}]`));
    });
    return hits;
  }
  if (typeof payload !== "object") return hits;
  const rec = payload as Record<string, unknown>;
  for (const [key, value] of Object.entries(rec)) {
    const next = `${path}.${key}`;
    if (SURVIVOR_TEAM_KEYS.has(key) && value === "LA") {
      hits.push(next);
    } else if (
      SURVIVOR_TEAM_LIST_KEYS.has(key) &&
      Array.isArray(value) &&
      value.includes("LA")
    ) {
      hits.push(next);
    } else if (
      key === "matchup_label" &&
      typeof value === "string" &&
      RAW_LA_RAMS.test(value)
    ) {
      hits.push(next);
    } else if (
      (key === "locked_picks" || key === "picks") &&
      value &&
      typeof value === "object" &&
      !Array.isArray(value)
    ) {
      for (const [week, team] of Object.entries(
        value as Record<string, unknown>,
      )) {
        if (team === "LA") hits.push(`${next}.${week}`);
      }
    } else {
      hits.push(...rawLaRamsHits(value, next));
    }
  }
  return hits;
}

export function canonicalizeSurvivorPlanWeek<
  T extends {
    locked_team?: string | null;
    locked_pick?: SurvivorPickTeamFields | null;
    ranked_picks?: SurvivorPickTeamFields[];
    available_teams?: string[];
  },
>(week: T): T {
  return {
    ...week,
    locked_team: week.locked_team
      ? canonicalizeSurvivorTeamCode(week.locked_team)
      : week.locked_team,
    locked_pick: week.locked_pick
      ? canonicalizeSurvivorPickRow(week.locked_pick)
      : week.locked_pick,
    ranked_picks: Array.isArray(week.ranked_picks)
      ? week.ranked_picks.map((row) => canonicalizeSurvivorPickRow(row))
      : week.ranked_picks,
    available_teams: Array.isArray(week.available_teams)
      ? parseAlreadyUsedTeams(week.available_teams)
      : week.available_teams,
  };
}

export function canonicalizeSuggestedPath<
  T extends {
    picks?: Record<string, string>;
    weeks?: SurvivorPickTeamFields[];
  },
>(path: T): T {
  return {
    ...path,
    picks: path.picks ? canonicalizeTeamCodeMap(path.picks) : path.picks,
    weeks: Array.isArray(path.weeks)
      ? path.weeks.map((row) => canonicalizeSurvivorPickRow(row))
      : path.weeks,
  };
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

/** Research-depth floor for honest 1-decimal WP / stable tails. */
export const NFL_HONEST_PRECISION_MIN_N = 2000;

/** Interactive desk defaults (match model-service sim_depth knobs). */
export const NFL_DEFAULT_N_GAME_BOX = 2000;
export const NFL_DEFAULT_N_SURVIVOR_PATHS = 2000;

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

export function isHonestPrecision(n: number | null | undefined): boolean {
  return typeof n === "number" && Number.isFinite(n) && n >= NFL_HONEST_PRECISION_MIN_N;
}

export function depthLabel(n: number | null | undefined): string {
  return isHonestPrecision(n) ? "research depth" : "low-depth estimate";
}

export function formatDepthBadge(
  n: number | null | undefined,
  opts?: { surface?: string },
): string {
  const count = typeof n === "number" && Number.isFinite(n) ? Math.round(n) : null;
  const label = depthLabel(count);
  const surface = opts?.surface ? `${opts.surface} · ` : "";
  if (count == null) return `${surface}${label}`;
  return `${surface}${count.toLocaleString()} · ${label}`;
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
    n_replicates: clampInt(
      input.nReplicates,
      NFL_DEFAULT_N_GAME_BOX,
      1,
      10_000,
    ),
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
    n_sims: clampInt(
      input.nSims,
      NFL_DEFAULT_N_SURVIVOR_PATHS,
      1,
      20_000,
    ),
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
    n_sims: clampInt(
      input.nSims,
      NFL_DEFAULT_N_SURVIVOR_PATHS,
      1,
      20_000,
    ),
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

/**
 * Win% honesty: when ``n`` is provided, 1-decimal only if n ≥ research depth;
 * otherwise whole %. Without ``n``, keep the requested digit count (legacy).
 */
export function formatPct(
  value: number,
  digitsOrOpts: number | { n?: number | null; digits?: number } = 1,
): string {
  if (!Number.isFinite(value)) return "—";
  const opts =
    typeof digitsOrOpts === "number"
      ? { digits: digitsOrOpts }
      : digitsOrOpts ?? {};
  const requested =
    typeof opts.digits === "number" && Number.isFinite(opts.digits)
      ? opts.digits
      : 1;
  const digits =
    opts.n == null
      ? requested
      : isHonestPrecision(opts.n)
        ? Math.min(requested, 1)
        : 0;
  return `${(value * 100).toFixed(digits)}%`;
}

export function formatAmericanOdds(odds: number | null | undefined): string {
  if (odds == null || !Number.isFinite(odds)) return "";
  const n = Math.round(odds);
  return n > 0 ? `+${n}` : String(n);
}

/** TD cell: prefer P(TD) + expected rate; avoid headline median/p90 tails. */
export function formatTdStat(
  dist: StatDist | undefined,
  opts?: { n?: number | null },
): { primary: string; secondary: string } {
  if (!dist) return { primary: "—", secondary: "" };
  const pTd =
    typeof dist.p_td === "number" && Number.isFinite(dist.p_td)
      ? dist.p_td
      : typeof dist.mean === "number"
        ? Math.min(1, Math.max(0, dist.mean))
        : null;
  const rate =
    typeof dist.expected_rate === "number" && Number.isFinite(dist.expected_rate)
      ? dist.expected_rate
      : dist.mean;
  const primary =
    pTd == null ? "—" : `P(TD) ${formatPct(pTd, { n: opts?.n, digits: 1 })}`;
  const fair = formatAmericanOdds(dist.fair_american ?? null);
  const secondary = [
    `exp ${formatStatNumber(rate ?? 0, 2)}`,
    fair ? `fair ${fair}` : null,
  ]
    .filter(Boolean)
    .join(" · ");
  return { primary, secondary };
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

/**
 * Yard / volume bands: show typical range (p10–p90 values) at research depth;
 * thin n (when provided) uses a wider mean± band so we don't overclaim precision.
 */
export function formatRange(
  dist: StatDist | undefined,
  digitsOrOpts: number | { n?: number | null; digits?: number } = 1,
): string {
  if (!dist) return "";
  const opts =
    typeof digitsOrOpts === "number"
      ? { digits: digitsOrOpts }
      : digitsOrOpts ?? {};
  const digits =
    typeof opts.digits === "number" && Number.isFinite(opts.digits)
      ? opts.digits
      : 1;
  if (opts.n != null && !isHonestPrecision(opts.n)) {
    const mean = dist.mean;
    const std = dist.std;
    if (!Number.isFinite(mean)) return "";
    const half = Number.isFinite(std)
      ? Math.max(std * 1.65, Math.abs(mean) * 0.25)
      : Math.abs(mean) * 0.35;
    return `~${formatStatNumber(mean - half, digits)}–${formatStatNumber(mean + half, digits)}`;
  }
  return `${formatStatNumber(dist.p10, digits)}–${formatStatNumber(dist.p90, digits)}`;
}

export function isTdStat(stat: string): boolean {
  return /_tds?$/.test(stat) || stat === "pass_tds" || stat === "rush_tds" || stat === "rec_tds";
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
