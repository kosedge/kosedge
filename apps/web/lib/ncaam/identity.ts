/**
 * NCAAM team identity — fail-closed alias resolution.
 *
 * Canonical sport key: `ncaam` only (`cbb` is retired as API/DB sport key).
 * Canonical team_id: clean KenPom-style team_norm (e.g. `miami fl`, `miami oh`).
 *
 * P0: Miami FL ≠ Miami OH — bare "miami" is omitted (ambiguous).
 * No fuzzy auto-publish joins; unknown / ambiguous alias → null.
 */

import aliasesDoc from "./aliases.json";

export type NcaamAliasSource =
  | "odds"
  | "kenpom"
  | "directory"
  | "manual"
  | "unknown";

export type NcaamResolveResult =
  | { ok: true; teamId: string; alias: string; source: NcaamAliasSource }
  | {
      ok: false;
      teamId: null;
      alias: string;
      reason: "empty" | "omit" | "unknown";
    };

const ALIASES: Record<string, string> = {
  ...(aliasesDoc.aliases as Record<string, string>),
};

const OMIT = new Set(
  (aliasesDoc.omit_aliases as string[]).map((a) => foldNcaamAlias(a)),
);

/** Inherited KenPom `normalize_team` bugs (st→state mangling) for ratings joins without remat. */
const RATINGS_NORM_BRIDGE: Record<string, string> = {
  ...(aliasesDoc.ratings_norm_bridge as Record<string, string>),
};

export function foldNcaamAlias(raw: string): string {
  return String(raw || "")
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[''`ʻ]/g, "")
    .replace(/[^a-z0-9\s-]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

/**
 * Resolve an odds / KenPom / directory alias to a canonical NCAAM team_id.
 * Fail-closed: ambiguous or unknown → null (omit from publish join).
 */
export function resolveTeamId(
  alias: string,
  source: NcaamAliasSource = "unknown",
): NcaamResolveResult {
  const folded = foldNcaamAlias(alias);
  if (!folded) {
    return { ok: false, teamId: null, alias: folded, reason: "empty" };
  }
  if (OMIT.has(folded)) {
    return { ok: false, teamId: null, alias: folded, reason: "omit" };
  }
  const teamId = ALIASES[folded];
  if (!teamId) {
    return { ok: false, teamId: null, alias: folded, reason: "unknown" };
  }
  return { ok: true, teamId, alias: folded, source };
}

/** Map clean team_id → ratings parquet team_norm when inherited grain differs. */
export function toRatingsNorm(teamId: string): string {
  return RATINGS_NORM_BRIDGE[teamId] ?? teamId;
}

export function resolveRatingsNorm(
  alias: string,
  source: NcaamAliasSource = "unknown",
): string | null {
  const r = resolveTeamId(alias, source);
  return r.ok ? toRatingsNorm(r.teamId) : null;
}

/** Retired API/DB sport key — product SoT is `ncaam` only. */
export const RETIRED_NCAAM_SPORT_KEYS = ["cbb", "ncaab"] as const;

export function isRetiredNcaamSportKey(
  key: string | null | undefined,
): boolean {
  const k = String(key || "")
    .trim()
    .toLowerCase();
  return (RETIRED_NCAAM_SPORT_KEYS as readonly string[]).includes(k);
}

export function isCanonicalNcaamSportKey(
  key: string | null | undefined,
): boolean {
  return (
    String(key || "")
      .trim()
      .toLowerCase() === "ncaam"
  );
}
