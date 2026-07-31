import type { NflIntelResponseRow } from "@/lib/nfl-intel";
import { formatIntelNumber } from "@/lib/intel-numeric";

export type NflTeamIntelView =
  | "overview"
  | "stats"
  | "depth-chart"
  | "injuries"
  | "splits"
  | "tendencies";

export type NflTeamDirectoryEntry = {
  code: string;
  name: string;
  conference: "AFC" | "NFC";
  division: "East" | "North" | "South" | "West";
};

export type TeamIntelFilters = {
  season?: number;
  week?: number;
  conference?: "AFC" | "NFC";
  division?: "East" | "North" | "South" | "West";
  query?: string;
};

const VIEW_ORDER: NflTeamIntelView[] = [
  "overview",
  "stats",
  "depth-chart",
  "injuries",
  "splits",
  "tendencies",
];

export const NFL_TEAM_DIRECTORY: NflTeamDirectoryEntry[] = [
  {
    code: "ARI",
    name: "Arizona Cardinals",
    conference: "NFC",
    division: "West",
  },
  {
    code: "ATL",
    name: "Atlanta Falcons",
    conference: "NFC",
    division: "South",
  },
  {
    code: "BAL",
    name: "Baltimore Ravens",
    conference: "AFC",
    division: "North",
  },
  { code: "BUF", name: "Buffalo Bills", conference: "AFC", division: "East" },
  {
    code: "CAR",
    name: "Carolina Panthers",
    conference: "NFC",
    division: "South",
  },
  { code: "CHI", name: "Chicago Bears", conference: "NFC", division: "North" },
  {
    code: "CIN",
    name: "Cincinnati Bengals",
    conference: "AFC",
    division: "North",
  },
  {
    code: "CLE",
    name: "Cleveland Browns",
    conference: "AFC",
    division: "North",
  },
  { code: "DAL", name: "Dallas Cowboys", conference: "NFC", division: "East" },
  { code: "DEN", name: "Denver Broncos", conference: "AFC", division: "West" },
  { code: "DET", name: "Detroit Lions", conference: "NFC", division: "North" },
  {
    code: "GB",
    name: "Green Bay Packers",
    conference: "NFC",
    division: "North",
  },
  { code: "HOU", name: "Houston Texans", conference: "AFC", division: "South" },
  {
    code: "IND",
    name: "Indianapolis Colts",
    conference: "AFC",
    division: "South",
  },
  {
    code: "JAX",
    name: "Jacksonville Jaguars",
    conference: "AFC",
    division: "South",
  },
  {
    code: "KC",
    name: "Kansas City Chiefs",
    conference: "AFC",
    division: "West",
  },
  {
    code: "LV",
    name: "Las Vegas Raiders",
    conference: "AFC",
    division: "West",
  },
  {
    code: "LAC",
    name: "Los Angeles Chargers",
    conference: "AFC",
    division: "West",
  },
  {
    code: "LAR",
    name: "Los Angeles Rams",
    conference: "NFC",
    division: "West",
  },
  { code: "MIA", name: "Miami Dolphins", conference: "AFC", division: "East" },
  {
    code: "MIN",
    name: "Minnesota Vikings",
    conference: "NFC",
    division: "North",
  },
  {
    code: "NE",
    name: "New England Patriots",
    conference: "AFC",
    division: "East",
  },
  {
    code: "NO",
    name: "New Orleans Saints",
    conference: "NFC",
    division: "South",
  },
  { code: "NYG", name: "New York Giants", conference: "NFC", division: "East" },
  { code: "NYJ", name: "New York Jets", conference: "AFC", division: "East" },
  {
    code: "PHI",
    name: "Philadelphia Eagles",
    conference: "NFC",
    division: "East",
  },
  {
    code: "PIT",
    name: "Pittsburgh Steelers",
    conference: "AFC",
    division: "North",
  },
  {
    code: "SEA",
    name: "Seattle Seahawks",
    conference: "NFC",
    division: "West",
  },
  {
    code: "SF",
    name: "San Francisco 49ers",
    conference: "NFC",
    division: "West",
  },
  {
    code: "TB",
    name: "Tampa Bay Buccaneers",
    conference: "NFC",
    division: "South",
  },
  {
    code: "TEN",
    name: "Tennessee Titans",
    conference: "AFC",
    division: "South",
  },
  {
    code: "WAS",
    name: "Washington Commanders",
    conference: "NFC",
    division: "East",
  },
];

const NFL_TEAM_DIRECTORY_BY_CODE = new Map(
  NFL_TEAM_DIRECTORY.map((entry) => [entry.code, entry] as const),
);

export function isNflTeamIntelView(value: string): value is NflTeamIntelView {
  return VIEW_ORDER.includes(value as NflTeamIntelView);
}

export function normalizeTeamCode(
  value: string | undefined | null,
): string | null {
  if (!value) return null;
  const normalized = value.trim().toUpperCase();
  if (!normalized) return null;
  return normalized;
}

export function parseTeamIntelFilters(
  searchParams: Record<string, string | string[] | undefined>,
): TeamIntelFilters {
  const seasonRaw = firstQueryValue(searchParams.season);
  const weekRaw = firstQueryValue(searchParams.week);
  const conferenceRaw = firstQueryValue(searchParams.conference);
  const divisionRaw = firstQueryValue(searchParams.division);
  const queryRaw = firstQueryValue(searchParams.q);

  const parsedSeason = Number(seasonRaw);
  const season =
    Number.isFinite(parsedSeason) &&
    parsedSeason >= 2010 &&
    parsedSeason <= 2100
      ? parsedSeason
      : undefined;
  const parsedWeek = Number(weekRaw);
  const week =
    Number.isFinite(parsedWeek) && parsedWeek >= 1 && parsedWeek <= 25
      ? parsedWeek
      : undefined;
  const conference =
    conferenceRaw === "AFC" || conferenceRaw === "NFC"
      ? conferenceRaw
      : undefined;
  const division =
    divisionRaw === "East" ||
    divisionRaw === "North" ||
    divisionRaw === "South" ||
    divisionRaw === "West"
      ? divisionRaw
      : undefined;
  const query =
    queryRaw && queryRaw.trim().length > 0 ? queryRaw.trim() : undefined;

  return {
    season,
    week,
    conference,
    division,
    query,
  };
}

export function buildTeamIntelHref(
  team: string,
  view: NflTeamIntelView,
  filters?: Pick<TeamIntelFilters, "season" | "week">,
): string {
  const params = new URLSearchParams();
  if (typeof filters?.season === "number")
    params.set("season", String(filters.season));
  if (typeof filters?.week === "number")
    params.set("week", String(filters.week));
  const query = params.toString();
  const base = `/pro/nfl/teams/${team}/${view}`;
  return query ? `${base}?${query}` : base;
}

export function teamDisplayName(teamCode: string): string {
  const normalized = normalizeTeamCode(teamCode);
  if (!normalized) return "Unknown team";
  return NFL_TEAM_DIRECTORY_BY_CODE.get(normalized)?.name ?? normalized;
}

export function resolveConferenceDivision(
  teamCode: string | undefined | null,
): {
  conference: "AFC" | "NFC";
  division: "East" | "North" | "South" | "West";
} | null {
  const normalized = normalizeTeamCode(teamCode);
  if (!normalized) return null;
  const entry = NFL_TEAM_DIRECTORY_BY_CODE.get(normalized);
  if (!entry) return null;
  return {
    conference: entry.conference,
    division: entry.division,
  };
}

export function resolveTeamCode(
  candidate: string | undefined,
  availableTeams: string[],
): string {
  const normalizedCandidate = normalizeTeamCode(candidate);
  const normalizedAvailable = availableTeams
    .map((team) => normalizeTeamCode(team))
    .filter(Boolean) as string[];

  // Always honor a valid NFL directory code from the URL first.
  // Never remap KC/DAL/etc. onto BUF when intel rows are empty or lagged.
  if (
    normalizedCandidate &&
    NFL_TEAM_DIRECTORY_BY_CODE.has(normalizedCandidate)
  ) {
    return normalizedCandidate;
  }

  if (normalizedCandidate && normalizedAvailable.includes(normalizedCandidate))
    return normalizedCandidate;

  if (normalizedAvailable.length > 0) return normalizedAvailable[0];
  return "BUF";
}

export function extractTeamCodes(rows: NflIntelResponseRow[]): string[] {
  const set = new Set<string>();
  for (const row of rows) {
    const team = normalizeTeamCode(
      typeof row.team === "string" ? row.team : undefined,
    );
    if (team) set.add(team);
  }
  return Array.from(set).sort();
}

export function filterTeamDirectory(
  filters: TeamIntelFilters,
): NflTeamDirectoryEntry[] {
  return NFL_TEAM_DIRECTORY.filter((team) => {
    if (filters.conference && team.conference !== filters.conference)
      return false;
    if (filters.division && team.division !== filters.division) return false;
    if (!filters.query) return true;
    const q = filters.query.toLowerCase();
    return (
      team.name.toLowerCase().includes(q) || team.code.toLowerCase().includes(q)
    );
  });
}

type TrendRankContext = {
  pass_rate?: number;
  red_zone_td_rate?: number;
  epa_per_play_offense?: number;
  epa_per_play_defense_allowed?: number;
};

export function buildTrendSnippets(
  statsRow: NflIntelResponseRow | undefined,
  ranks?: TrendRankContext,
): string[] {
  if (!statsRow) {
    return [
      "No weekly stat profile available for the selected filter.",
      "Use latest week defaults or switch team to surface trends.",
    ];
  }
  const passRate = asNumber(statsRow.pass_rate);
  const rzRate = asNumber(statsRow.red_zone_td_rate);
  const offEpa = asNumber(statsRow.epa_per_play_offense);
  const defEpaAllowed = asNumber(statsRow.epa_per_play_defense_allowed);

  return [
    `Pass rate: ${formatPct(passRate, ranks?.pass_rate)} with red-zone TD rate ${formatPct(rzRate, ranks?.red_zone_td_rate)}.`,
    `Offense EPA/play ${formatSigned(offEpa, ranks?.epa_per_play_offense)}; defense EPA allowed ${formatSigned(
      defEpaAllowed,
      ranks?.epa_per_play_defense_allowed,
    )}.`,
    "Signal quality improves with full-week injury and depth updates.",
  ];
}

export function firstQueryValue(
  value: string | string[] | undefined,
): string | undefined {
  if (Array.isArray(value)) return value[0];
  return value;
}

function asNumber(value: unknown): number | null {
  if (typeof value !== "number" || !Number.isFinite(value)) return null;
  return value;
}

function formatPct(value: number | null, rank?: number): string {
  if (value === null) return "N/A";
  const base = formatIntelNumber(value * 100, false);
  const rankSuffix =
    typeof rank === "number" && Number.isFinite(rank)
      ? ` (${Math.trunc(rank)})`
      : "";
  return `${base}${rankSuffix}%`;
}

function formatSigned(value: number | null, rank?: number): string {
  if (value === null) return "N/A";
  const abs = formatIntelNumber(Math.abs(value), false);
  const base = value >= 0 ? `+${abs}` : `-${abs}`;
  const rankSuffix =
    typeof rank === "number" && Number.isFinite(rank)
      ? ` (${Math.trunc(rank)})`
      : "";
  return `${base}${rankSuffix}`;
}
