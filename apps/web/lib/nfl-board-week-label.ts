/**
 * UI-only week labeling for NFL Pro boards.
 * Avoids presenting a completed-season MAX(week) fallback (often 18) as the
 * active board week before that REG week exists.
 */

import { formatNflWeekLabel } from "@/lib/nfl-truth-label";

const EMPTY_SLATE_STATUSES = new Set([
  "no_slate",
  "preseason_empty",
  "offseason_empty",
  "no_reg_week_games",
  "no_projections_yet",
  "empty",
]);

export function formatNflBoardWeekLabel(
  currentWeek: number | null | undefined,
  opts?: {
    hasRowsForCurrentWeek?: boolean;
    lineCount?: number;
    slateStatus?: string | null;
    season?: number | null;
    now?: Date;
  },
): string {
  const emptySlate =
    opts?.lineCount === 0 ||
    (opts?.slateStatus != null &&
      EMPTY_SLATE_STATUSES.has(opts.slateStatus.trim()));
  const noRowsForWeek = opts?.hasRowsForCurrentWeek === false;

  return formatNflWeekLabel(currentWeek, {
    season: opts?.season,
    now: opts?.now,
    emptySlate: emptySlate || noRowsForWeek,
  });
}

/** Default week for projection desks — never open on a stale Week 18 MAX fallback. */
export function resolveNflProjectionDefaultWeek(
  currentWeek: number | null | undefined,
): number {
  const week =
    typeof currentWeek === "number" && Number.isFinite(currentWeek)
      ? Math.trunc(currentWeek)
      : 1;
  if (week < 1) return 1;
  if (week >= 18) return 1;
  return week;
}
