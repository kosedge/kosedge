/**
 * UI-only week labeling for NFL Pro boards.
 * Avoids presenting a completed-season MAX(week) fallback (often 18) as the
 * active board week before that REG week exists.
 */

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
  },
): string {
  const week =
    typeof currentWeek === "number" && Number.isFinite(currentWeek)
      ? Math.trunc(currentWeek)
      : null;
  if (week == null || week < 1) return "Preseason / camp";

  const emptySlate =
    opts?.lineCount === 0 ||
    (opts?.slateStatus != null &&
      EMPTY_SLATE_STATUSES.has(opts.slateStatus.trim()));
  const noRowsForWeek = opts?.hasRowsForCurrentWeek === false;

  // Backend MAX(week) often returns 18 when no upcoming games remain.
  if (week >= 18 && (emptySlate || noRowsForWeek)) {
    return "Preseason / camp";
  }

  return `Week ${week}`;
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
