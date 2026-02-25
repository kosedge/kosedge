/**
 * Insights rotate every Monday. Week index 0–3 repeats (week 0 = sections .1, week 1 = .2, etc.).
 * Epoch: first Monday used as reference (Jan 1, 2024 was a Monday).
 */
const EPOCH_MONDAY = new Date("2024-01-01T00:00:00Z");

function getMondayOfWeek(d: Date): Date {
  const day = d.getUTCDay();
  const diff = d.getUTCDate() - day + (day === 0 ? -6 : 1);
  return new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), diff));
}

export function getCurrentWeekIndex(): number {
  const now = new Date();
  const monday = getMondayOfWeek(now);
  const diffMs = monday.getTime() - EPOCH_MONDAY.getTime();
  const diffWeeks = Math.floor(diffMs / (7 * 24 * 60 * 60 * 1000));
  return diffWeeks % 4;
}

/** 1-based section number for this week (1, 2, 3, or 4). */
export function getCurrentSectionNumber(): number {
  return getCurrentWeekIndex() + 1;
}

/** 0–11 index for Pro insight of the week (cycles through pillars 5, 6, 7). */
export function getProInsightWeekIndex(): number {
  const now = new Date();
  const monday = getMondayOfWeek(now);
  const diffMs = monday.getTime() - EPOCH_MONDAY.getTime();
  const diffWeeks = Math.floor(diffMs / (7 * 24 * 60 * 60 * 1000));
  return diffWeeks % 12;
}
