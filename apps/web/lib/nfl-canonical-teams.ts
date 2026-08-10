/**
 * Canonical NFL team IDs for Truth Layer joins.
 * Product / web Rams code is LAR; engine / nflverse often emit LA.
 */

export const NFL_CANONICAL_TEAMS = [
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

export type NflCanonicalTeam = (typeof NFL_CANONICAL_TEAMS)[number];

const TEAM_ALIASES: Record<string, NflCanonicalTeam> = {
  LA: "LAR",
  LAR: "LAR",
  WSH: "WAS",
  WAS: "WAS",
  JAC: "JAX",
  JAX: "JAX",
  STL: "LAR",
  SD: "LAC",
  OAK: "LV",
};

export function canonicalizeNflTeam(
  code: string | null | undefined,
): string | null {
  if (code == null) return null;
  const raw = String(code).trim().toUpperCase();
  if (!raw) return null;
  if (raw in TEAM_ALIASES) return TEAM_ALIASES[raw];
  if ((NFL_CANONICAL_TEAMS as readonly string[]).includes(raw)) return raw;
  return raw;
}

export function missingCanonicalNflTeams(present: Iterable<string>): string[] {
  const have = new Set<string>();
  for (const t of present) {
    const c = canonicalizeNflTeam(t);
    if (c) have.add(c);
  }
  return NFL_CANONICAL_TEAMS.filter((t) => !have.has(t));
}
