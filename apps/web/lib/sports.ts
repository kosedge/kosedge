// Sport config - single source of truth for shells and navigation

export { generateGameOverview } from "@/lib/game-overview";

export type SportKey = "ncaam" | "nba" | "nfl" | "mlb" | "nhl" | "cfb" | "wnba";

export type SportTier = "pro" | "college";

export const SPORTS: {
  key: SportKey;
  label: string;
  fullName: string;
  desc: string;
  tier: SportTier;
  supportsPropsFantasy: boolean;
}[] = [
  {
    key: "ncaam",
    label: "CBB",
    fullName: "College Basketball",
    desc: "Daily slate, fair lines, matchup context, execution.",
    tier: "college",
    supportsPropsFantasy: false,
  },
  {
    key: "nba",
    label: "NBA",
    fullName: "NBA",
    desc: "Daily slate, fair lines, execution tooling.",
    tier: "pro",
    supportsPropsFantasy: true,
  },
  {
    key: "nfl",
    label: "NFL",
    fullName: "NFL",
    desc: "Weekly slate, matchup pages, execution.",
    tier: "pro",
    supportsPropsFantasy: true,
  },
  {
    key: "mlb",
    label: "MLB",
    fullName: "MLB",
    desc: "Daily slate, markets, tracking.",
    tier: "pro",
    supportsPropsFantasy: true,
  },
  {
    key: "nhl",
    label: "NHL",
    fullName: "NHL",
    desc: "Daily slate, moneyline and totals, tracking.",
    tier: "pro",
    supportsPropsFantasy: true,
  },
  {
    key: "cfb",
    label: "CFB",
    fullName: "College Football",
    desc: "Weekly slate, matchup context, execution.",
    tier: "college",
    supportsPropsFantasy: false,
  },
  {
    key: "wnba",
    label: "WNBA",
    fullName: "WNBA",
    desc: "Daily slate, fair lines, matchup context.",
    tier: "pro",
    supportsPropsFantasy: true,
  },
];

/** Null-safe uppercase for team/sport tokens from params or upstream payloads. */
export function safeUpperCase(value: unknown, fallback = ""): string {
  if (value == null) return fallback;
  const token = String(value).trim();
  if (!token) return fallback;
  return token.toUpperCase();
}

/** Normalize a sport route/param token; empty when missing. */
export function resolveSportKey(value: unknown, fallback = ""): string {
  if (value == null) return fallback;
  const token = String(value).trim().toLowerCase();
  return token || fallback;
}

export function getSport(key: string | null | undefined) {
  if (!key) return null;
  return SPORTS.find((s) => s.key === key) ?? null;
}

/** Display label that never throws on missing sport codes. */
export function sportDisplayLabel(
  key: string | null | undefined,
  fallback = "Sport",
): string {
  const sportKey = resolveSportKey(key);
  if (!sportKey) return fallback;
  return getSport(sportKey)?.fullName ?? safeUpperCase(sportKey, fallback);
}

export function isProSport(key: string): boolean {
  return getSport(key)?.tier === "pro";
}

export function supportsPropsFantasy(key: string): boolean {
  return getSport(key)?.supportsPropsFantasy ?? false;
}
