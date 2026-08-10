/**
 * 2026 NFL international / neutral-site slate (league release).
 * Keyed by week + sorted team pair so home/away listing order does not matter.
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

function pairKey(a: string, b: string): string {
  return [canon(a), canon(b)].sort().join("|");
}

const BY_WEEK_PAIR = new Map<string, NflNeutralSite>();
const BY_PAIR = new Map<string, NflNeutralSite>();
for (const site of SITES) {
  const pk = pairKey(site.teams[0], site.teams[1]);
  BY_WEEK_PAIR.set(`${site.week}|${pk}`, site);
  // Pair-only fallback when week is missing on the row (still exact 2026 slate).
  BY_PAIR.set(pk, site);
}

/** Standard home HFA when the game is not neutral (framework prior). */
export const NFL_STANDARD_HFA_POINTS = 1.05;

export function lookupNflNeutralSite(args: {
  week: number | null | undefined;
  homeAbbr: string;
  awayAbbr: string;
}): NflNeutralSite | null {
  const pk = pairKey(args.homeAbbr, args.awayAbbr);
  const weekNum =
    args.week == null || args.week === ("" as unknown)
      ? NaN
      : Number(args.week);
  if (Number.isFinite(weekNum)) {
    const hit = BY_WEEK_PAIR.get(`${Math.trunc(weekNum)}|${pk}`);
    if (hit) return hit;
  }
  return BY_PAIR.get(pk) ?? null;
}

export function resolveNflSiteContext(args: {
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
  hfaPoints: number;
  siteLabel: "Home" | "Road" | "Neutral";
} {
  const looked = lookupNflNeutralSite(args);
  const isNeutral =
    args.neutralSite === true ||
    looked != null ||
    (typeof args.neutralCity === "string" && args.neutralCity.trim() !== "");
  if (isNeutral) {
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
