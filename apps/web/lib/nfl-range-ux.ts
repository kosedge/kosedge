/**
 * Range copy doctrine (2026-08-12):
 * Uncertainty stays in the product. Casual paths don’t lead with p10–p90 jargon.
 * Research / detail surfaces show the sim band as Range (low–high).
 */

export const RANGE_LABEL = "Range";
export const TYPICAL_RANGE_LABEL = "Typical range";

export const RANGE_TOOLTIP =
  "Most simulated seasons fall in this band (10th–90th percentile). Not a guaranteed floor or ceiling.";

export const SHOW_PERCENTILES_LABEL = "Show percentiles";
export const HIDE_PERCENTILES_LABEL = "Hide percentiles";

function formatBandNumber(value: number, digits: number): string {
  if (!Number.isFinite(value)) return "—";
  if (digits <= 0) return String(Math.round(value));
  return value.toFixed(digits);
}

/** Plain low–high band from p10–p90 values. Never invents a tighter interval. */
export function formatRangeBand(
  low: number,
  high: number,
  digits = 0,
): string {
  return `${formatBandNumber(low, digits)}–${formatBandNumber(high, digits)}`;
}

/** Advanced reveal: p10 / p50 / p90 + optional replicate count. */
export function formatPercentileReveal(input: {
  p10: number;
  p50: number;
  p90: number;
  nSims?: number | null;
  digits?: number;
}): string {
  const digits = input.digits ?? 0;
  const parts = [
    `p10 ${formatBandNumber(input.p10, digits)}`,
    `p50 ${formatBandNumber(input.p50, digits)}`,
    `p90 ${formatBandNumber(input.p90, digits)}`,
  ];
  if (
    input.nSims != null &&
    Number.isFinite(input.nSims) &&
    input.nSims > 0
  ) {
    parts.push(`${Math.round(input.nSims).toLocaleString()} sims`);
  }
  return parts.join(" · ");
}
