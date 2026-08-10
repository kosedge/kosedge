/**
 * Season form-language gates for Edge Board matchup copy.
 * Missing data → omit. Never invent recent form.
 */

export type SeasonFormGate = "week1" | "early" | "mid" | "unknown";

export type SeasonGateInput = {
  week?: number | null;
  /** Prior games this season for the team (0 = first game). */
  gamesPlayedAway?: number | null;
  gamesPlayedHome?: number | null;
  seasonType?: string | null;
};

/** Forbidden phrases when gate is week1 / first team game. */
export const FORBIDDEN_WEEK1_FORM_PATTERNS: readonly RegExp[] = [
  /\brecent turnovers?\b/i,
  /\blast[\s-]?3\b/i,
  /\blast[\s-]?four\b/i,
  /\blast[\s-]?4\b/i,
  /\bhot\b/i,
  /\bcold\b/i,
  /\brecent form\b/i,
  /\brecent samples?\b/i,
  /\brecent efficiency\b/i,
  /\bhot streak\b/i,
  /\bcold streak\b/i,
  /\bin recent\b/i,
  /\bover their last\b/i,
];

function asInt(value: unknown): number | null {
  if (value == null || value === "") return null;
  const n = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(n)) return null;
  return Math.trunc(n);
}

export function resolveSeasonFormGate(input: SeasonGateInput): SeasonFormGate {
  const week = asInt(input.week);
  const awayGpRaw = asInt(input.gamesPlayedAway);
  const homeGpRaw = asInt(input.gamesPlayedHome);
  const awayGp = awayGpRaw != null ? Math.max(0, awayGpRaw) : null;
  const homeGp = homeGpRaw != null ? Math.max(0, homeGpRaw) : null;

  // First team game this season, or Week 1 — no recent-form language.
  if (week === 1) return "week1";
  if (awayGp === 0 || homeGp === 0) return "week1";

  const minGp =
    awayGp != null && homeGp != null
      ? Math.min(awayGp, homeGp)
      : (awayGp ?? homeGp);

  if (minGp != null) {
    if (minGp <= 0) return "week1";
    if (minGp <= 3) return "early"; // games 2–4
    return "mid";
  }

  if (week != null) {
    if (week <= 4) return "early";
    return "mid";
  }
  return "unknown";
}

export function allowsRecentFormLanguage(gate: SeasonFormGate): boolean {
  return gate === "mid";
}

export function allowsLightFormLanguage(gate: SeasonFormGate): boolean {
  return gate === "early" || gate === "mid";
}

/** True when copy still needs an early-season uncertainty clause. */
export function needsEarlySeasonUncertainty(gate: SeasonFormGate): boolean {
  return gate === "week1" || gate === "early" || gate === "unknown";
}

export function copyContainsForbiddenWeek1Form(text: string): boolean {
  return FORBIDDEN_WEEK1_FORM_PATTERNS.some((re) => re.test(text));
}

/**
 * Strip / reject form language for week1. Returns cleaned text or null if empty.
 * Prefer generating without form language over stripping after the fact.
 */
export function scrubWeek1FormLanguage(text: string): string {
  let out = text;
  for (const re of FORBIDDEN_WEEK1_FORM_PATTERNS) {
    out = out.replace(re, "");
  }
  return out.replace(/\s{2,}/g, " ").replace(/\s+([.,;:])/g, "$1").trim();
}
