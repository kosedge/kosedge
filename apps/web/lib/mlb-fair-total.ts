/**
 * Certified MLB fair-total / KEI-total quantization.
 *
 * Locked product policy (do not invent a different board grain):
 *
 *   fair_*_total = nearest half-run of the matching *_total_mean
 *
 * Matches model-service `quantize_mlb_fair_total`: Python 3 `round(mean * 2) / 2`
 * (half-even at exact .25 / .75). FG and F5 means are quantized independently.
 *
 * This is not a stub constant. Means clustered at 9.09–9.11 honestly share
 * KEI 9.0; means that cross a half-run boundary must not collapse.
 *
 * Provenance token: `nearest_half_run`.
 */

export const MLB_FAIR_TOTAL_QUANTIZATION = "nearest_half_run" as const;
export const MLB_FAIR_TOTAL_TICK = 0.5;

export type MlbFairTotalQuantization = typeof MLB_FAIR_TOTAL_QUANTIZATION;

function firstFinite(
  ...candidates: Array<number | null | undefined>
): number | null {
  for (const c of candidates) {
    if (typeof c === "number" && Number.isFinite(c)) return c;
  }
  return null;
}

/** Python 3 `round()` — ties (.5) go to the nearest even integer. */
export function roundHalfEven(n: number): number {
  if (!Number.isFinite(n)) return n;
  const sign = n < 0 ? -1 : 1;
  const abs = Math.abs(n);
  const floor = Math.floor(abs);
  const frac = abs - floor;
  let rounded: number;
  if (frac < 0.5) rounded = floor;
  else if (frac > 0.5) rounded = floor + 1;
  else rounded = floor % 2 === 0 ? floor : floor + 1;
  return sign * rounded;
}

/** Nearest half-run (0.5) of a continuous run total mean. */
export function quantizeMlbFairTotal(mean: number): number {
  return roundHalfEven(mean * 2) / 2;
}

export type MlbResolvedFairTotal = {
  /** Board / KEI total (published fair, else quantized mean). */
  kei: number | null;
  /** Continuous sim mean when present. */
  mean: number | null;
  quantization: MlbFairTotalQuantization;
  /** True when KEI was derived here because published fair was missing. */
  quantizedFromMean: boolean;
};

/**
 * Customer KEI total = published `fair_*_total` when present; otherwise the
 * certified half-run of the mean. Never treat the raw mean as the board line.
 */
export function resolveMlbKeiTotal(args: {
  handicapTotal?: number | null;
  fairTotal?: number | null;
  handicapTotalMean?: number | null;
  totalMean?: number | null;
}): MlbResolvedFairTotal {
  const mean = firstFinite(args.handicapTotalMean, args.totalMean);
  const published = firstFinite(args.handicapTotal, args.fairTotal);
  if (published != null) {
    return {
      kei: published,
      mean,
      quantization: MLB_FAIR_TOTAL_QUANTIZATION,
      quantizedFromMean: false,
    };
  }
  if (mean != null) {
    return {
      kei: quantizeMlbFairTotal(mean),
      mean,
      quantization: MLB_FAIR_TOTAL_QUANTIZATION,
      quantizedFromMean: true,
    };
  }
  return {
    kei: null,
    mean: null,
    quantization: MLB_FAIR_TOTAL_QUANTIZATION,
    quantizedFromMean: false,
  };
}

/** Continuous mean for provenance (two decimals) — not the board KEI. */
export function formatMlbTotalMean(value: number | null | undefined): string {
  if (value == null || !Number.isFinite(value)) return "—";
  return value.toFixed(2);
}

export function mlbKeiDiffersFromMean(
  kei: number | null,
  mean: number | null,
): boolean {
  if (kei == null || mean == null) return false;
  return Math.abs(kei - mean) > 1e-9;
}
