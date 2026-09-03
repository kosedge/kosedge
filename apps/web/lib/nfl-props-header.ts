/**
 * Props board header honesty — period label follows the spine week, not the
 * calendar preseason cutoff. Kickoff / game time is never line vintage.
 */

export type NflPropsSeasonType = "REG" | "PRE" | "POST";

/**
 * Subscriber period chrome for `/pro/nfl/props`.
 *
 * Weekly props share the REG player-production spine with Edge Board.
 * Do not call a Week 1 REG board "Preseason" just because Labor Day has not
 * passed — that disagrees with Edge Board ("Week 1 REG").
 *
 * Preseason label is reserved for an explicit PRE season type only.
 */
export function formatNflPropsBoardPeriod(
  season: number,
  week: number,
  opts?: { seasonType?: NflPropsSeasonType | string | null },
): string {
  const s =
    Number.isFinite(season) && season >= 2010 ? Math.trunc(season) : NaN;
  const w = Number.isFinite(week) && week >= 1 ? Math.trunc(week) : NaN;
  if (!Number.isFinite(s) || !Number.isFinite(w)) {
    return "Props board week unavailable";
  }

  const raw = String(opts?.seasonType ?? "REG")
    .trim()
    .toUpperCase();
  const seasonType: NflPropsSeasonType =
    raw === "PRE" || raw === "POST" ? raw : "REG";

  if (seasonType === "PRE") {
    return `${s} Preseason`;
  }
  if (seasonType === "POST") {
    return `${s} · Week ${w} POST`;
  }
  return `${s} · Week ${w} REG`;
}
