import { formatAdp, valueLabel } from "@/lib/fantasy/adp-proxy";
import { shouldSoftFrameAdpGap } from "@/lib/fantasy/expert";
import type { FantasyDeskRow } from "@/lib/fantasy/types";

/** Late-round ADP floor for sleeper board (≈ round 8 in 12-team). */
export const SLEEPER_ADP_MIN = 84;
/** Model overall rank still "late board" when ADP unmatched. */
export const SLEEPER_MODEL_RANK_MIN = 72;
/** Minimum Value Δ (ADP − model rank) to count as market value. */
export const SLEEPER_MIN_VALUE_DELTA = 8;

/**
 * Late-round / ADP-value sleepers from an existing fantasy desk board.
 * Prefer matched ADP with positive Value Δ; unmatched ADP stays off the
 * value sort (shown separately only when model rank is late).
 */
export function selectSleeperRows(
  rows: FantasyDeskRow[],
  limit = 36,
): FantasyDeskRow[] {
  const skill = rows.filter(
    (r) => !["K", "DST"].includes(r.position.toUpperCase()),
  );

  const withMarketValue = skill.filter((r) => {
    if (r.adp == null || r.valueDelta == null) return false;
    if (r.valueDelta < SLEEPER_MIN_VALUE_DELTA) return false;
    return r.adp >= SLEEPER_ADP_MIN || r.rankOverall >= SLEEPER_MODEL_RANK_MIN;
  });

  const lateUnmatched = skill.filter((r) => {
    if (r.adp != null && r.valueDelta != null) return false;
    return r.rankOverall >= SLEEPER_MODEL_RANK_MIN;
  });

  const ranked = [
    ...withMarketValue.sort(
      (a, b) => (b.valueDelta ?? 0) - (a.valueDelta ?? 0),
    ),
    ...lateUnmatched.sort((a, b) => a.rankOverall - b.rankOverall),
  ];

  const seen = new Set<string>();
  const out: FantasyDeskRow[] = [];
  for (const row of ranked) {
    if (seen.has(row.playerId)) continue;
    seen.add(row.playerId);
    out.push(row);
    if (out.length >= limit) break;
  }
  return out;
}

/** One-line why — role / schedule / soft ADP framing; no absurd TE TD cliffs. */
export function sleeperWhyLine(row: FantasyDeskRow): string {
  const soft = shouldSoftFrameAdpGap({
    position: row.position,
    rankOverall: row.rankOverall,
    rankPosition: row.rankPosition,
    valueDelta: row.valueDelta,
  });
  const driver =
    row.drivers[0] ??
    `${row.team} ${row.position}${row.rankPosition} — late-board depth`;
  const sched =
    row.schedule.early === "soft"
      ? " Soft early schedule."
      : row.schedule.playoff === "soft"
        ? " Softer fantasy-playoff stretch."
        : "";

  if (row.adp == null || row.valueDelta == null) {
    return `${driver}.${sched}`.trim();
  }

  if (soft) {
    return `Model likes more than ADP ~${formatAdp(row.adp, 0)} — signal, not lottery. ${driver}.${sched}`.trim();
  }

  const gap = valueLabel(row.valueDelta);
  if (gap.kind === "value") {
    return `${gap.text} vs ADP ~${formatAdp(row.adp, 0)}. ${driver}.${sched}`.trim();
  }
  return `${driver}.${sched}`.trim();
}

export function formatSleeperGap(valueDelta: number | null): string {
  if (valueDelta == null || !Number.isFinite(valueDelta)) return "—";
  const rounded = Math.round(valueDelta);
  return rounded > 0 ? `+${rounded}` : String(rounded);
}
