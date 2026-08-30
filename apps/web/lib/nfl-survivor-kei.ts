/**
 * Survivor customer-facing win% — KEI SU probs (same fields as Pick’em),
 * joined on canonical team + REG week. Season-engine path math stays separate.
 */

import type { NflFairLineRow } from "@/lib/nfl-fair-lines";
import { normalizeNflTeamCode } from "@/lib/nfl-season-engine-format";

export type SurvivorWpSource = "kei" | "engine";

export type KeiWinProbHit = {
  wp: number;
  opponent: string;
  homeAway: "home" | "away";
  source: "kei";
};

export type SurvivorPickWpFields = {
  team: string;
  opponent?: string | null;
  home_away?: string | null;
  matchup_label?: string | null;
  win_rate: number;
  this_week_wp?: number;
  favorite_wp?: number;
  is_favorite?: boolean;
  favorite_team?: string | null;
  /** Preserved season-engine weekly wp for save / pick-now / path math. */
  engine_wp?: number;
  wp_source?: SurvivorWpSource;
  [key: string]: unknown;
};

export type SurvivorPlanWeekLike = {
  week: number;
  locked_team?: string | null;
  locked_pick?: SurvivorPickWpFields | null;
  ranked_picks?: SurvivorPickWpFields[];
  [key: string]: unknown;
};

export type SurvivorPlanLike = {
  weeks?: SurvivorPlanWeekLike[];
  locked_picks?: Record<string, string>;
  locked_pick_count?: number;
  avg_locked_wp?: number | null;
  [key: string]: unknown;
};

function resolveWinProbs(row: NflFairLineRow): {
  home: number | null;
  away: number | null;
} {
  const home = row.handicapHomeWinProb ?? row.homeWinProb;
  const away = row.handicapAwayWinProb ?? row.awayWinProb;
  return {
    home: home != null && Number.isFinite(home) ? home : null,
    away: away != null && Number.isFinite(away) ? away : null,
  };
}

function isRegLine(row: NflFairLineRow): boolean {
  const st = (row.seasonType ?? "").trim().toUpperCase();
  return st === "" || st === "REG";
}

function teamCode(raw: string | null | undefined): string | null {
  if (raw == null) return null;
  const mapped = normalizeNflTeamCode(String(raw));
  if (mapped) return mapped;
  const fallback = String(raw).trim().toUpperCase();
  return fallback || null;
}

/**
 * KEI SU win probability for a team in a REG week.
 * Join: canonicalize home/away abbrs; never invent a number.
 */
export function keiWinProbForTeam(
  lines: NflFairLineRow[],
  team: string,
  week: number,
): KeiWinProbHit | null {
  const want = teamCode(team);
  if (!want || !Number.isFinite(week)) return null;

  for (const row of lines) {
    if (row.week !== week) continue;
    if (!isRegLine(row)) continue;

    const home = teamCode(row.homeAbbr);
    const away = teamCode(row.awayAbbr);
    if (!home || !away) continue;

    const { home: homeWp, away: awayWp } = resolveWinProbs(row);

    if (want === home) {
      if (homeWp == null) return null;
      return {
        wp: homeWp,
        opponent: away,
        homeAway: "home",
        source: "kei",
      };
    }
    if (want === away) {
      if (awayWp == null) return null;
      return {
        wp: awayWp,
        opponent: home,
        homeAway: "away",
        source: "kei",
      };
    }
  }
  return null;
}

function engineWeeklyWp(pick: SurvivorPickWpFields): number {
  if (typeof pick.engine_wp === "number" && Number.isFinite(pick.engine_wp)) {
    return pick.engine_wp;
  }
  if (
    typeof pick.this_week_wp === "number" &&
    Number.isFinite(pick.this_week_wp)
  ) {
    return pick.this_week_wp;
  }
  return pick.win_rate;
}

/**
 * Overlay one pick: display wp fields become KEI when join hits;
 * engine_wp preserves season-engine weekly rate for path math.
 */
export function overlaySurvivorPickWithKei<T extends SurvivorPickWpFields>(
  pick: T,
  week: number,
  lines: NflFairLineRow[],
): T {
  const engine = engineWeeklyWp(pick);
  const hit = keiWinProbForTeam(lines, pick.team, week);
  if (!hit) {
    return {
      ...pick,
      engine_wp: engine,
      this_week_wp: pick.this_week_wp ?? engine,
      wp_source: "engine" as const,
    };
  }

  const homeAway = hit.homeAway;
  const isFavorite = hit.wp >= 0.5;
  return {
    ...pick,
    engine_wp: engine,
    this_week_wp: hit.wp,
    // Display win_rate = KEI; save/pick_now scores stay on the row as-is.
    win_rate: hit.wp,
    favorite_wp: hit.wp,
    favorite_team: pick.team,
    is_favorite: isFavorite,
    opponent: hit.opponent,
    home_away: homeAway,
    matchup_label:
      homeAway === "away"
        ? `${pick.team} @ ${hit.opponent}`
        : `${pick.team} vs ${hit.opponent}`,
    wp_source: "kei" as const,
  };
}

/** Mean KEI this_week_wp for locked weeks that joined; null if none. */
export function avgLockedKeiWp(
  weeks: SurvivorPlanWeekLike[] | undefined,
  lockedPicks: Record<string, string> | undefined,
): number | null {
  if (!weeks?.length) return null;
  const locks = lockedPicks ?? {};
  const values: number[] = [];

  for (const weekRow of weeks) {
    const week = weekRow.week;
    const lockedTeam =
      locks[String(week)] ||
      weekRow.locked_team ||
      weekRow.locked_pick?.team ||
      "";
    if (!lockedTeam) continue;

    const pick =
      weekRow.locked_pick?.team === lockedTeam
        ? weekRow.locked_pick
        : weekRow.ranked_picks?.find((p) => p.team === lockedTeam) ||
          weekRow.locked_pick;

    if (!pick || pick.wp_source !== "kei") continue;
    const wp = pick.this_week_wp;
    if (typeof wp === "number" && Number.isFinite(wp)) values.push(wp);
  }

  if (!values.length) return null;
  return values.reduce((a, b) => a + b, 0) / values.length;
}

export function overlaySurvivorPlanWithKei<T extends SurvivorPlanLike>(
  plan: T,
  lines: NflFairLineRow[],
): T {
  if (!Array.isArray(plan.weeks)) return plan;

  const weeks = plan.weeks.map((weekRow) => {
    const week = weekRow.week;
    const ranked = Array.isArray(weekRow.ranked_picks)
      ? weekRow.ranked_picks.map((p) =>
          overlaySurvivorPickWithKei(p, week, lines),
        )
      : weekRow.ranked_picks;
    const locked =
      weekRow.locked_pick && typeof weekRow.locked_pick === "object"
        ? overlaySurvivorPickWithKei(weekRow.locked_pick, week, lines)
        : weekRow.locked_pick;
    return { ...weekRow, ranked_picks: ranked, locked_pick: locked };
  });

  const next: SurvivorPlanLike = { ...plan, weeks };
  next.avg_locked_wp = avgLockedKeiWp(weeks, plan.locked_picks);
  return next as T;
}

export function overlaySurvivorHelperPicksWithKei<
  T extends SurvivorPickWpFields,
>(picks: T[], week: number, lines: NflFairLineRow[]): T[] {
  return picks.map((p) => overlaySurvivorPickWithKei(p, week, lines));
}

/** Display weekly wp for lean chips (KEI overlay when present). */
export function survivorDisplayWp(pick: {
  this_week_wp?: number;
  win_rate: number;
}): number {
  if (
    typeof pick.this_week_wp === "number" &&
    Number.isFinite(pick.this_week_wp)
  ) {
    return pick.this_week_wp;
  }
  return pick.win_rate;
}

/**
 * Top lean boxes for an open week: remaining (not burned) picks sorted by
 * display wp descending. Highest % first.
 */
export function sortSurvivorLeansByDisplayWp<
  T extends { team: string; this_week_wp?: number; win_rate: number },
>(
  picks: T[],
  opts?: { burned?: ReadonlySet<string> | Iterable<string>; limit?: number },
): T[] {
  const burned = new Set(
    opts?.burned
      ? [...opts.burned].map((t) => String(t).trim().toUpperCase())
      : [],
  );
  const limit = opts?.limit ?? 6;
  return [...picks]
    .filter((p) => !burned.has(String(p.team).trim().toUpperCase()))
    .sort((a, b) => {
      const d = survivorDisplayWp(b) - survivorDisplayWp(a);
      if (d !== 0) return d;
      return a.team.localeCompare(b.team);
    })
    .slice(0, limit);
}
