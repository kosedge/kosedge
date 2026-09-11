/**
 * Weekly Slate SSR fair-lines horizon.
 *
 * The displayed board is current REG week + next week (or a single week / ISO
 * day). A 120-day live pull returns the rest of the season (~256 rows / ~1.3MB)
 * and routinely exceeds the 12s SSR board budget. Edge Board already uses a
 * 10-day live window; this helper sizes the slate request from canonical
 * kickoffs so we only ask for games the page will paint.
 */

import {
  currentNflRegWeekFromSchedule,
  listCanonicalNflGames,
} from "@/lib/nfl-canonical-schedule";

/** Never request more than two NFL weeks plus a one-day kickoff buffer. */
export const NFL_WEEKLY_SLATE_MAX_DAYS_AHEAD = 16;
export const NFL_WEEKLY_SLATE_MAX_PAST_DAYS = 7;

export type NflSlateDateMode = "today" | "week" | "iso";

export type NflSlateDateToken = {
  mode: NflSlateDateMode;
  week?: number;
  iso?: string;
};

export type NflWeeklySlateFairLinesWindow = {
  weeks: number[];
  daysAhead: number;
  includePastDays: number;
};

const DAY_MS = 86_400_000;

export function resolveNflSlateDateToken(
  date: string | null | undefined,
): NflSlateDateToken {
  const token = String(date ?? "")
    .trim()
    .toLowerCase();
  if (!token || token === "today" || token === "latest") {
    return { mode: "today" };
  }
  const weekMatch = token.match(/^w(?:eek)?-?(\d+)$/);
  if (weekMatch) return { mode: "week", week: Number(weekMatch[1]) };
  if (/^\d{4}-\d{2}-\d{2}$/.test(token)) return { mode: "iso", iso: token };
  return { mode: "today" };
}

export function resolveNflWeeklySlateWeeks(
  dateToken: string | null | undefined,
  nowMs: number = Date.now(),
): number[] {
  const resolved = resolveNflSlateDateToken(dateToken);
  if (resolved.mode === "week" && resolved.week) {
    return Number.isFinite(resolved.week) && resolved.week >= 1
      ? [resolved.week]
      : [];
  }
  if (resolved.mode === "iso" && resolved.iso) {
    const week =
      weekForIsoKickoff(resolved.iso) ?? currentNflRegWeekFromSchedule(nowMs);
    return [week];
  }
  const current = currentNflRegWeekFromSchedule(nowMs);
  return [current, current + 1].filter((week) => week >= 1 && week <= 18);
}

function weekForIsoKickoff(iso: string): number | null {
  for (const game of listCanonicalNflGames()) {
    if (game.game_type !== "REG" || !game.kickoff_utc) continue;
    if (game.kickoff_utc.slice(0, 10) === iso) return game.week;
  }
  return null;
}

function kickoffMsForWeeks(weeks: number[]): number[] {
  const want = new Set(weeks);
  const times: number[] = [];
  for (const game of listCanonicalNflGames()) {
    if (game.game_type !== "REG" || !want.has(game.week) || !game.kickoff_utc) {
      continue;
    }
    const t = Date.parse(game.kickoff_utc);
    if (Number.isFinite(t)) times.push(t);
  }
  return times;
}

/**
 * Date window that covers the displayed weeks' kickoffs, clamped so SSR
 * cannot reintroduce the 120-day season pull.
 */
export function nflWeeklySlateFairLinesWindow(
  dateToken: string | null | undefined = "today",
  nowMs: number = Date.now(),
): NflWeeklySlateFairLinesWindow {
  const weeks = resolveNflWeeklySlateWeeks(dateToken, nowMs);
  const kickoffs = kickoffMsForWeeks(weeks);
  if (kickoffs.length === 0) {
    return {
      weeks,
      daysAhead: NFL_WEEKLY_SLATE_MAX_DAYS_AHEAD,
      includePastDays: 2,
    };
  }
  const minT = Math.min(...kickoffs);
  const maxT = Math.max(...kickoffs);
  const daysAhead = Math.min(
    NFL_WEEKLY_SLATE_MAX_DAYS_AHEAD,
    Math.max(1, Math.ceil((maxT - nowMs) / DAY_MS) + 1),
  );
  const includePastDays = Math.min(
    NFL_WEEKLY_SLATE_MAX_PAST_DAYS,
    Math.max(0, Math.ceil((nowMs - minT) / DAY_MS) + 1),
  );
  return { weeks, daysAhead, includePastDays };
}
