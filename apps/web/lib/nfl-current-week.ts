/**
 * In-season NFL product week (chrome / slate / fantasy / Club Desk).
 *
 * Transition rule (Ryan / CoS 2026-09-15):
 *   currentWeek = the REG week whose first kickoff has occurred,
 *   OR the upcoming week after the previous week's last game is FINAL.
 *
 *   After the last game of week W is FINAL → default becomes W+1.
 *   Monday package = recap of W (Sunday clubs) + preview of W+1.
 *   MNF clubs drop Tuesday.
 *
 * SoT: canonical 2026 REG schedule kickoffs (`nfl-canonical-schedule`).
 * Live box FINAL is not joined here — a game is treated FINAL once
 * `kickoff + NFL_GAME_FINAL_BUFFER_MS` has passed. Fail closed when the
 * week cannot be proven. Never silently return Week 1.
 *
 * Out of scope: Edge Board assemble math, KEI, PLAY stamps, CFB.
 */

import {
  NFL_CANONICAL_SCHEDULE_SEASON,
  listCanonicalNflGames,
} from "@/lib/nfl-canonical-schedule";

/** Typical NFL game length used when box FINAL is not on the pack. */
export const NFL_GAME_FINAL_BUFFER_MS = 4 * 60 * 60 * 1000;

export type NflCurrentWeekReason =
  | "in_progress"
  | "prior_week_final"
  | "upcoming"
  | "unproven";

export type NflCurrentWeekResolution = {
  week: number | null;
  proven: boolean;
  reason: NflCurrentWeekReason;
  asOfMs: number;
};

type WeekSpan = {
  week: number;
  firstKickoffMs: number;
  lastKickoffMs: number;
};

function listRegWeekSpans(season: number): WeekSpan[] {
  const byWeek = new Map<number, { min: number; max: number }>();
  for (const game of listCanonicalNflGames()) {
    if (game.season !== season || game.game_type !== "REG") continue;
    if (!game.kickoff_utc) continue;
    const t = Date.parse(game.kickoff_utc);
    if (!Number.isFinite(t)) continue;
    const cur = byWeek.get(game.week);
    if (!cur) byWeek.set(game.week, { min: t, max: t });
    else {
      cur.min = Math.min(cur.min, t);
      cur.max = Math.max(cur.max, t);
    }
  }
  return [...byWeek.entries()]
    .sort((a, b) => a[0] - b[0])
    .map(([week, span]) => ({
      week,
      firstKickoffMs: span.min,
      lastKickoffMs: span.max,
    }));
}

function weekIsFinal(span: WeekSpan, nowMs: number): boolean {
  return nowMs >= span.lastKickoffMs + NFL_GAME_FINAL_BUFFER_MS;
}

/**
 * Proven current REG week, or null when the schedule cannot prove one.
 */
export function resolveCurrentNflRegWeek(
  nowMs: number = Date.now(),
  season: number = NFL_CANONICAL_SCHEDULE_SEASON,
): NflCurrentWeekResolution {
  const spans = listRegWeekSpans(season);
  if (!spans.length) {
    return { week: null, proven: false, reason: "unproven", asOfMs: nowMs };
  }

  let lastFinal: WeekSpan | null = null;
  for (const span of spans) {
    if (weekIsFinal(span, nowMs)) lastFinal = span;
  }

  if (lastFinal) {
    const next = spans.find((span) => span.week === lastFinal.week + 1);
    if (next) {
      return {
        week: next.week,
        proven: true,
        reason: "prior_week_final",
        asOfMs: nowMs,
      };
    }
    return {
      week: lastFinal.week,
      proven: true,
      reason: "prior_week_final",
      asOfMs: nowMs,
    };
  }

  const inProgress = [...spans]
    .reverse()
    .find(
      (span) =>
        nowMs >= span.firstKickoffMs &&
        nowMs < span.lastKickoffMs + NFL_GAME_FINAL_BUFFER_MS,
    );
  if (inProgress) {
    return {
      week: inProgress.week,
      proven: true,
      reason: "in_progress",
      asOfMs: nowMs,
    };
  }

  const upcoming = spans.find((span) => nowMs < span.firstKickoffMs);
  if (upcoming) {
    return {
      week: upcoming.week,
      proven: true,
      reason: "upcoming",
      asOfMs: nowMs,
    };
  }

  return { week: null, proven: false, reason: "unproven", asOfMs: nowMs };
}

/** Proven week number, or null. Never a silent Week 1 pin. */
export function currentNflRegWeekFromSchedule(
  nowMs: number = Date.now(),
  season: number = NFL_CANONICAL_SCHEDULE_SEASON,
): number | null {
  return resolveCurrentNflRegWeek(nowMs, season).week;
}

export function nflRegWeekPostureLine(
  nowMs: number = Date.now(),
  season: number = NFL_CANONICAL_SCHEDULE_SEASON,
): string {
  const resolved = resolveCurrentNflRegWeek(nowMs, season);
  if (!resolved.proven || resolved.week == null) {
    return "Regular-season week not proven — fail closed.";
  }
  return `Week ${resolved.week} REG live · PRE off board`;
}

export function nflRegWeekChromeLabel(
  nowMs: number = Date.now(),
  season: number = NFL_CANONICAL_SCHEDULE_SEASON,
): string | null {
  const week = currentNflRegWeekFromSchedule(nowMs, season);
  return week == null ? null : `Week ${week}`;
}
