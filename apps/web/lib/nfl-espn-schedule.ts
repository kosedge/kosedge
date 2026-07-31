import "server-only";

export type EspnNflGame = {
  id: string;
  seasonType: "PRE" | "REG" | "POST";
  week: number;
  startTime: string;
  awayAbbr: string;
  homeAbbr: string;
  awayTeam: string;
  homeTeam: string;
  marketSpreadHome: number | null;
  marketTotal: number | null;
  marketDetail: string | null;
  source: "espn";
};

type EspnCompetitor = {
  homeAway?: string;
  team?: {
    abbreviation?: string;
    displayName?: string;
    name?: string;
  };
};

type EspnOdds = {
  details?: string;
  overUnder?: number | string;
  spread?: number | string;
};

type EspnEvent = {
  id?: string;
  date?: string;
  name?: string;
  competitions?: Array<{
    competitors?: EspnCompetitor[];
    odds?: EspnOdds[];
  }>;
};

const ESPN_ABBR_MAP: Record<string, string> = {
  WSH: "WAS",
  WAS: "WAS",
  LAR: "LAR",
  LA: "LAR",
  STL: "LAR",
  SD: "LAC",
  OAK: "LV",
  JAC: "JAX",
};

function normalizeAbbr(value: string | undefined): string {
  const raw = (value ?? "").trim().toUpperCase();
  return ESPN_ABBR_MAP[raw] ?? raw;
}

function toNumberOrNull(value: unknown): number | null {
  if (value === null || value === undefined) return null;
  const n = typeof value === "number" ? value : Number(value);
  return Number.isFinite(n) ? n : null;
}

/** Parse ESPN odds details like "CAR -1.5" into home-relative spread. */
function parseSpreadHome(
  details: string | undefined,
  homeAbbr: string,
  awayAbbr: string,
): number | null {
  if (!details) return null;
  const match = details.trim().match(/^([A-Z]{2,3})\s*([+-]?\d+(?:\.\d+)?)$/i);
  if (!match) return null;
  const favored = normalizeAbbr(match[1]);
  const line = Number(match[2]);
  if (!Number.isFinite(line)) return null;
  if (favored === homeAbbr) return line; // home favored → negative if "-3.5"
  if (favored === awayAbbr) return -line; // away -3.5 → home +3.5
  return null;
}

function mapEvent(
  event: EspnEvent,
  seasonType: "PRE" | "REG" | "POST",
  week: number,
): EspnNflGame | null {
  const competition = event.competitions?.[0];
  const competitors = competition?.competitors ?? [];
  const home = competitors.find((c) => c.homeAway === "home");
  const away = competitors.find((c) => c.homeAway === "away");
  if (!home?.team?.abbreviation || !away?.team?.abbreviation) return null;

  const homeAbbr = normalizeAbbr(home.team.abbreviation);
  const awayAbbr = normalizeAbbr(away.team.abbreviation);
  const odds = competition?.odds?.[0];
  const marketTotal = toNumberOrNull(odds?.overUnder);
  const marketSpreadHome =
    parseSpreadHome(odds?.details, homeAbbr, awayAbbr) ??
    toNumberOrNull(odds?.spread);

  return {
    id: String(event.id ?? `${seasonType}-${week}-${awayAbbr}-${homeAbbr}`),
    seasonType,
    week,
    startTime: event.date ?? "",
    awayAbbr,
    homeAbbr,
    awayTeam: away.team.displayName ?? away.team.name ?? awayAbbr,
    homeTeam: home.team.displayName ?? home.team.name ?? homeAbbr,
    marketSpreadHome,
    marketTotal,
    marketDetail: odds?.details ?? null,
    source: "espn",
  };
}

async function fetchEspnScoreboard(params: {
  seasonType: 1 | 2 | 3;
  week: number;
  year?: number;
}): Promise<EspnNflGame[]> {
  const year = params.year ?? 2026;
  const seasonTypeLabel =
    params.seasonType === 1 ? "PRE" : params.seasonType === 3 ? "POST" : "REG";
  const url = new URL(
    "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard",
  );
  url.searchParams.set("seasontype", String(params.seasonType));
  url.searchParams.set("week", String(params.week));
  url.searchParams.set("dates", String(year));

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 12000);
  try {
    const response = await fetch(url.toString(), {
      next: { revalidate: 1800 },
      signal: controller.signal,
      headers: { accept: "application/json" },
    });
    if (!response.ok) return [];
    const payload = (await response.json()) as { events?: EspnEvent[] };
    const events = Array.isArray(payload.events) ? payload.events : [];
    return events
      .map((event) => mapEvent(event, seasonTypeLabel, params.week))
      .filter((game): game is EspnNflGame => Boolean(game));
  } catch {
    return [];
  } finally {
    clearTimeout(timeout);
  }
}

/** Preseason weeks currently published by ESPN for the target year. */
export async function fetchEspnPreseasonSlate(options?: {
  year?: number;
  weeks?: number[];
}): Promise<EspnNflGame[]> {
  const year = options?.year ?? 2026;
  const weeks = options?.weeks ?? [1, 2, 3];
  const batches = await Promise.all(
    weeks.map((week) =>
      fetchEspnScoreboard({ seasonType: 1, week, year }),
    ),
  );
  return batches
    .flat()
    .sort((a, b) => (a.startTime || "").localeCompare(b.startTime || ""));
}

export type EspnStandingRow = {
  team: string;
  wins: number;
  losses: number;
  ties: number;
  win_pct: number;
  points_for: number;
  points_against: number;
  point_diff: number;
  conference: string;
  division: string;
  record: string;
  source: string;
};

export async function fetchEspnNflStandings(
  season = 2025,
): Promise<EspnStandingRow[]> {
  const url = `https://site.api.espn.com/apis/v2/sports/football/nfl/standings?season=${season}`;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 12000);
  try {
    const response = await fetch(url, {
      next: { revalidate: 3600 },
      signal: controller.signal,
      headers: { accept: "application/json" },
    });
    if (!response.ok) return [];
    const payload = (await response.json()) as {
      children?: Array<{
        abbreviation?: string;
        name?: string;
        children?: Array<{
          abbreviation?: string;
          name?: string;
          standings?: {
            entries?: Array<{
              team?: { abbreviation?: string };
              stats?: Array<{ name?: string; value?: number; displayValue?: string }>;
            }>;
          };
        }>;
        standings?: {
          entries?: Array<{
            team?: { abbreviation?: string };
            stats?: Array<{ name?: string; value?: number; displayValue?: string }>;
          }>;
        };
      }>;
    };

    const rows: EspnStandingRow[] = [];
    for (const conference of payload.children ?? []) {
      const confName = conference.abbreviation ?? conference.name ?? "NFL";
      const divisions = conference.children?.length
        ? conference.children
        : [conference];
      for (const division of divisions) {
        const divName =
          division.abbreviation ??
          division.name?.replace(`${confName} `, "") ??
          "League";
        for (const entry of division.standings?.entries ?? []) {
          const team = normalizeAbbr(entry.team?.abbreviation);
          if (!team) continue;
          const stats = new Map(
            (entry.stats ?? []).map((stat) => [stat.name ?? "", stat] as const),
          );
          const wins = toNumberOrNull(stats.get("wins")?.value) ?? 0;
          const losses = toNumberOrNull(stats.get("losses")?.value) ?? 0;
          const ties = toNumberOrNull(stats.get("ties")?.value) ?? 0;
          const pointsFor =
            toNumberOrNull(stats.get("pointsFor")?.value) ?? 0;
          const pointsAgainst =
            toNumberOrNull(stats.get("pointsAgainst")?.value) ?? 0;
          const games = wins + losses + ties;
          const winPct =
            toNumberOrNull(stats.get("winPercent")?.value) ??
            (games > 0 ? (wins + ties * 0.5) / games : 0);
          const record =
            ties > 0 ? `${wins}-${losses}-${ties}` : `${wins}-${losses}`;
          rows.push({
            team,
            wins,
            losses,
            ties,
            win_pct: winPct,
            points_for: pointsFor,
            points_against: pointsAgainst,
            point_diff: pointsFor - pointsAgainst,
            conference: confName,
            division: divName,
            record,
            source: `espn-standings-${season}`,
          });
        }
      }
    }
    return rows;
  } catch {
    return [];
  } finally {
    clearTimeout(timeout);
  }
}
