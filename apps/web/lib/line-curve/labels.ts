/**
 * Research labels only. Never PLAY / LEAN / stake language.
 */

import type { LineCurvePoint, ResearchLabel } from "@/lib/line-curve/types";

const FAIR_EDGE_ABS = 0.015;

export function labelFromEdge(
  edgePct: number,
  evPerDollar: number,
): ResearchLabel {
  if (!Number.isFinite(edgePct) || !Number.isFinite(evPerDollar)) {
    return "INSUFFICIENT";
  }
  if (Math.abs(edgePct) <= FAIR_EDGE_ABS && evPerDollar >= -0.02) {
    return "FAIR";
  }
  if (edgePct < -FAIR_EDGE_ABS || evPerDollar < 0) return "OVERPRICED";
  return "FAIR";
}

/** Mark the single highest-EV sufficient row as BEST VALUE when EV > 0. */
export function applyBestValue<
  T extends { evPerDollar: number; label: ResearchLabel },
>(rows: T[]): T[] {
  const eligible = rows.filter(
    (r) => r.label !== "INSUFFICIENT" && Number.isFinite(r.evPerDollar),
  );
  if (!eligible.length) return rows;
  const best = eligible.reduce((a, b) =>
    b.evPerDollar > a.evPerDollar ? b : a,
  );
  if (best.evPerDollar <= 0) return rows;
  return rows.map((row) =>
    row === best ? { ...row, label: "BEST VALUE" as const } : row,
  );
}

export function assertNoPlayLanguage(value: string): boolean {
  return !/\b(play|lean|teaser)\b/i.test(value);
}

export function pointLabel(point: LineCurvePoint): ResearchLabel {
  return point.label;
}
