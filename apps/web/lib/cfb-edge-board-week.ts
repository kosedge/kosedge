/**
 * CFB Edge Board week query — customer honesty.
 * Missing/invalid → Week 1 (W1 launch default).
 * A present finite integer ≥ 0 is kept as-is. Never coerce week=2 to week=1.
 */

export function parseCfbAssembleWeek(raw: string | null | undefined): number {
  if (raw == null || String(raw).trim() === "") return 1;
  const n = Number(raw);
  if (!Number.isFinite(n) || !Number.isInteger(n) || n < 0) return 1;
  return n;
}

/** Rows stamped for this week only. Empty is honest — never fall through to week 1. */
export function filterCfbEdgeBoardRowsByWeek<T>(
  rows: readonly T[],
  week: number,
): T[] {
  return rows.filter((r) => (r as { week?: unknown }).week === week);
}
