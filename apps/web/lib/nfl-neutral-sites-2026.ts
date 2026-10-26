/**
 * 2026 NFL international / neutral-site slate (league release).
 * Keyed by season + exact week + away-then-home order.
 * teams[0] is the away team and teams[1] is the home team.
 * A game that cannot be identified fails closed as UNKNOWN.
 */

export type NflNeutralSite = {
  week: number;
  teams: readonly [string, string];
  city: string;
  venue: string;
  /** HFA points the model should use on this site (0 = full neutral). */
  hfaPoints: number;
};

const SITES: readonly NflNeutralSite[] = [
  {
    week: 1,
    teams: ["SF", "LAR"],
    city: "Melbourne",
    venue: "Melbourne Cricket Ground",
    hfaPoints: 0,
  },
  {
    week: 3,
    teams: ["BAL", "DAL"],
    city: "Rio de Janeiro",
    venue: "Maracanã Stadium",
    hfaPoints: 0,
  },
  {
    week: 4,
    teams: ["IND", "WAS"],
    city: "London",
    venue: "Tottenham Hotspur Stadium",
    hfaPoints: 0,
  },
  {
    week: 5,
    teams: ["PHI", "JAX"],
    city: "London",
    venue: "Tottenham Hotspur Stadium",
    hfaPoints: 0,
  },
  {
    week: 6,
    teams: ["HOU", "JAX"],
    city: "London",
    venue: "Wembley Stadium",
    hfaPoints: 0,
  },
  {
    week: 7,
    teams: ["PIT", "NO"],
    city: "Paris",
    venue: "Stade de France",
    hfaPoints: 0,
  },
  {
    week: 9,
    teams: ["CIN", "ATL"],
    city: "Madrid",
    venue: "Bernabéu Stadium",
    hfaPoints: 0,
  },
  {
    week: 10,
    teams: ["NE", "DET"],
    city: "Munich",
    venue: "FC Bayern Munich Arena",
    hfaPoints: 0,
  },
  {
    week: 11,
    teams: ["MIN", "SF"],
    city: "Mexico City",
    venue: "Estadio Banorte",
    hfaPoints: 0,
  },
];

function canon(abbr: string): string {
  const a = String(abbr || "")
    .trim()
    .toUpperCase();
  if (a === "LA" || a === "LAR") return "LAR";
  if (a === "WSH") return "WAS";
  return a;
}

/** This slate is the 2026 regular season only. */
const NEUTRAL_SITE_SEASON = 2026;

type NeutralIdentity = {
  season: number;
  week: number;
  away: string;
  home: string;
};

function neutralIdentity(args: {
  season?: number | null;
  week: number | null | undefined;
  homeAbbr: string;
  awayAbbr: string;
}): NeutralIdentity | null {
  const season =
    args.season == null || args.season === ("" as unknown)
      ? NaN
      : Number(args.season);
  const weekNum =
    args.week == null || args.week === ("" as unknown)
      ? NaN
      : Number(args.week);
  const away = canon(args.awayAbbr);
  const home = canon(args.homeAbbr);
  if (
    season !== NEUTRAL_SITE_SEASON ||
    !Number.isInteger(weekNum) ||
    !away ||
    !home
  ) {
    return null;
  }
  return { season, week: weekNum, away, home };
}

function identityKey(identity: NeutralIdentity): string {
  return `${identity.season}|${identity.week}|${identity.away}|${identity.home}`;
}

const BY_IDENTITY = new Map<string, NflNeutralSite>();
for (const site of SITES) {
  const away = canon(site.teams[0]);
  const home = canon(site.teams[1]);
  BY_IDENTITY.set(`${NEUTRAL_SITE_SEASON}|${site.week}|${away}|${home}`, site);
}

/** Standard home HFA when the game is not neutral (framework prior). */
export const NFL_STANDARD_HFA_POINTS = 1.05;

export function lookupNflNeutralSite(args: {
  season?: number | null;
  week: number | null | undefined;
  homeAbbr: string;
  awayAbbr: string;
}): NflNeutralSite | null {
  const identity = neutralIdentity(args);
  if (!identity) return null;
  return BY_IDENTITY.get(identityKey(identity)) ?? null;
}

export function resolveNflSiteContext(args: {
  season?: number | null;
  week: number | null | undefined;
  homeAbbr: string;
  awayAbbr: string;
  /** Override when upstream already stamped the game. */
  neutralSite?: boolean | null;
  neutralCity?: string | null;
  neutralVenue?: string | null;
  hfaPoints?: number | null;
}): {
  isNeutral: boolean;
  city: string | null;
  venue: string | null;
  hfaPoints: number | null;
  siteLabel: "Home" | "Road" | "Neutral" | "UNKNOWN";
} {
  const looked = lookupNflNeutralSite(args);
  // A stamp counts only on an exact table identity. Otherwise ignore it.
  if (looked != null) {
    const hfa =
      args.hfaPoints != null && Number.isFinite(args.hfaPoints)
        ? Number(args.hfaPoints)
        : (looked?.hfaPoints ?? 0);
    return {
      isNeutral: true,
      city: (args.neutralCity || looked?.city || null)?.trim() || null,
      venue: (args.neutralVenue || looked?.venue || null)?.trim() || null,
      hfaPoints: hfa,
      siteLabel: "Neutral",
    };
  }
  const identity = neutralIdentity(args);
  if (identity == null) {
    return {
      isNeutral: false,
      city: null,
      venue: null,
      hfaPoints:
        args.hfaPoints != null && Number.isFinite(args.hfaPoints)
          ? Number(args.hfaPoints)
          : null,
      siteLabel: "UNKNOWN",
    };
  }
  return {
    isNeutral: false,
    city: null,
    venue: null,
    hfaPoints:
      args.hfaPoints != null && Number.isFinite(args.hfaPoints)
        ? Number(args.hfaPoints)
        : NFL_STANDARD_HFA_POINTS,
    siteLabel: "Home",
  };
}
