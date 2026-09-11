/**
 * Integer football score → margin PMF.
 *
 * Key numbers (3, 7, 10, 14, …) must emerge from TD/FG/PAT/safety scoring,
 * not from a hardcoded teaser table or a linear point-value assumption.
 *
 * Model mean margin and margin_sd are matched by shifting / adding smooth
 * integer noise — never by injecting extra mass onto 3 and 7.
 */

import type { ModelMarginInput, OutcomeMass } from "@/lib/line-curve/types";

export const MAX_TEAM_SCORE = 80;
export const MAX_ABS_MARGIN = 70;

/** Historical scoring composition (how teams score), not teaser geometry. */
const TD_POINT_SHARE = 0.72;
const SAFETY_POINT_SHARE = 0.008;
const PAT_RATE = 0.94;
const TWO_PT_RATE = 0.04;
const NO_EXTRA_RATE = 1 - PAT_RATE - TWO_PT_RATE;

export type MarginPmf = {
  /** P(home_score − away_score = k) for integer k. */
  mass: Map<number, number>;
  mean: number;
  sd: number;
  winHome: number;
  pushStraightUp: number;
  winAway: number;
};

function poissonPmf(lambda: number, k: number): number {
  if (k < 0) return 0;
  if (lambda <= 0) return k === 0 ? 1 : 0;
  let p = Math.exp(-lambda);
  for (let i = 1; i <= k; i += 1) p *= lambda / i;
  return p;
}

function convolve(a: number[], b: number[], max: number): number[] {
  const out = new Array(max + 1).fill(0);
  for (let i = 0; i < a.length; i += 1) {
    const ai = a[i];
    if (!ai) continue;
    const jMax = Math.min(b.length - 1, max - i);
    for (let j = 0; j <= jMax; j += 1) {
      const bj = b[j];
      if (bj) out[i + j] += ai * bj;
    }
  }
  return out;
}

function compoundPoisson(
  lambda: number,
  play: number[],
  max: number,
): number[] {
  const maxN = Math.min(14, Math.max(3, Math.ceil(lambda + 8)));
  const out = new Array(max + 1).fill(0);
  let nFold = new Array(max + 1).fill(0);
  nFold[0] = 1;
  for (let n = 0; n <= maxN; n += 1) {
    const pN = poissonPmf(lambda, n);
    if (pN > 0) {
      for (let s = 0; s <= max; s += 1) out[s] += pN * nFold[s];
    }
    if (n < maxN) nFold = convolve(nFold, play, max);
  }
  return out;
}

function normalize(arr: number[]): number[] {
  const sum = arr.reduce((a, b) => a + b, 0);
  if (sum <= 0) {
    const z = new Array(arr.length).fill(0);
    z[0] = 1;
    return z;
  }
  return arr.map((v) => v / sum);
}

/**
 * Discrete team-score PMF from expected points via TD / FG / safety lattice.
 */
export function teamScorePmf(expectedPoints: number): number[] {
  const mu = Math.max(0, Number(expectedPoints) || 0);
  const tdPlay = new Array(MAX_TEAM_SCORE + 1).fill(0);
  tdPlay[6] = NO_EXTRA_RATE;
  tdPlay[7] = PAT_RATE;
  tdPlay[8] = TWO_PT_RATE;
  const fgPlay = new Array(MAX_TEAM_SCORE + 1).fill(0);
  fgPlay[3] = 1;
  const safetyPlay = new Array(MAX_TEAM_SCORE + 1).fill(0);
  safetyPlay[2] = 1;

  const lambdaTd = (mu * TD_POINT_SHARE) / 6.95;
  const lambdaFg = (mu * (1 - TD_POINT_SHARE - SAFETY_POINT_SHARE)) / 3;
  const lambdaSafety = (mu * SAFETY_POINT_SHARE) / 2;

  const td = compoundPoisson(lambdaTd, tdPlay, MAX_TEAM_SCORE);
  const fg = compoundPoisson(lambdaFg, fgPlay, MAX_TEAM_SCORE);
  const saf = compoundPoisson(lambdaSafety, safetyPlay, MAX_TEAM_SCORE);
  return normalize(
    convolve(convolve(td, fg, MAX_TEAM_SCORE), saf, MAX_TEAM_SCORE),
  );
}

function moments(mass: Map<number, number>): { mean: number; sd: number } {
  let mean = 0;
  for (const [k, p] of mass) mean += k * p;
  let varSum = 0;
  for (const [k, p] of mass) varSum += (k - mean) ** 2 * p;
  return { mean, sd: Math.sqrt(Math.max(varSum, 0)) };
}

function shiftMass(
  mass: Map<number, number>,
  shift: number,
): Map<number, number> {
  const out = new Map<number, number>();
  for (const [k, p] of mass) {
    const nk = k + shift;
    if (Math.abs(nk) > MAX_ABS_MARGIN) continue;
    out.set(nk, (out.get(nk) ?? 0) + p);
  }
  return renormalizeMap(out);
}

function discreteGaussianKernel(sd: number): Map<number, number> {
  const width = Math.min(MAX_ABS_MARGIN, Math.max(1, Math.ceil(sd * 4)));
  const out = new Map<number, number>();
  const denom = 2 * sd * sd;
  for (let k = -width; k <= width; k += 1) {
    const w = Math.exp(-(k * k) / denom);
    out.set(k, w);
  }
  return renormalizeMap(out);
}

function convolveMaps(
  a: Map<number, number>,
  b: Map<number, number>,
): Map<number, number> {
  const out = new Map<number, number>();
  for (const [i, pa] of a) {
    for (const [j, pb] of b) {
      const k = i + j;
      if (Math.abs(k) > MAX_ABS_MARGIN) continue;
      out.set(k, (out.get(k) ?? 0) + pa * pb);
    }
  }
  return renormalizeMap(out);
}

function renormalizeMap(mass: Map<number, number>): Map<number, number> {
  let sum = 0;
  for (const p of mass.values()) sum += p;
  if (sum <= 0) return new Map([[0, 1]]);
  const out = new Map<number, number>();
  for (const [k, p] of mass) out.set(k, p / sum);
  return out;
}

function rawMarginFromScores(
  home: number[],
  away: number[],
): Map<number, number> {
  const mass = new Map<number, number>();
  for (let h = 0; h < home.length; h += 1) {
    const ph = home[h];
    if (!ph) continue;
    for (let a = 0; a < away.length; a += 1) {
      const pa = away[a];
      if (!pa) continue;
      const m = h - a;
      if (Math.abs(m) > MAX_ABS_MARGIN) continue;
      mass.set(m, (mass.get(m) ?? 0) + ph * pa);
    }
  }
  return renormalizeMap(mass);
}

/**
 * Build a home-margin PMF whose mean ≈ −modelSpreadHome and sd ≈ marginSd.
 */
export function buildMarginPmf(model: ModelMarginInput): MarginPmf {
  const home = teamScorePmf(model.expectedHomeScore);
  const away = teamScorePmf(model.expectedAwayScore);
  let mass = rawMarginFromScores(home, away);

  const targetMean = -model.modelSpreadHome;
  const targetSd = Math.max(6, Number(model.marginSd) || 15);

  const current = moments(mass);
  const shift = Math.round(targetMean - current.mean);
  if (shift !== 0) mass = shiftMass(mass, shift);

  const afterShift = moments(mass);
  if (afterShift.sd + 0.25 < targetSd) {
    const extra = Math.sqrt(Math.max(targetSd ** 2 - afterShift.sd ** 2, 0.25));
    mass = convolveMaps(mass, discreteGaussianKernel(extra));
  }

  const stats = moments(mass);
  let winHome = 0;
  let pushStraightUp = 0;
  let winAway = 0;
  for (const [k, p] of mass) {
    if (k > 0) winHome += p;
    else if (k === 0) pushStraightUp += p;
    else winAway += p;
  }

  return {
    mass,
    mean: stats.mean,
    sd: stats.sd,
    winHome,
    pushStraightUp,
    winAway,
  };
}

/**
 * ATS outcome for a side at a posted line (Odds API point for that team).
 * Home +3.5 covers when home_margin + 3.5 > 0.
 * Away +3.5 covers when −home_margin + 3.5 > 0.
 */
export function atsOutcomeMass(
  pmf: MarginPmf,
  side: "home" | "away",
  line: number,
): OutcomeMass {
  let cover = 0;
  let push = 0;
  let loss = 0;
  for (const [margin, p] of pmf.mass) {
    const adj = side === "home" ? margin + line : -margin + line;
    if (adj > 1e-9) cover += p;
    else if (Math.abs(adj) <= 1e-9) push += p;
    else loss += p;
  }
  const sum = cover + push + loss;
  if (sum <= 0) return { cover: 0, push: 0, loss: 1 };
  return { cover: cover / sum, push: push / sum, loss: loss / sum };
}

export function resolveSide(
  snapshotHome: string,
  snapshotAway: string,
  side: string,
): "home" | "away" | null {
  const s = normalizeName(side);
  if (!s) return null;
  if (s === "home" || normalizeName(snapshotHome) === s) return "home";
  if (s === "away" || normalizeName(snapshotAway) === s) return "away";
  return null;
}

export function normalizeName(value: string): string {
  return String(value || "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

/** Integer-margin mass near a key number — for tests, not pricing. */
export function massNear(pmf: MarginPmf, center: number, radius = 0): number {
  let p = 0;
  for (let k = center - radius; k <= center + radius; k += 1) {
    p += pmf.mass.get(k) ?? 0;
  }
  return p;
}
