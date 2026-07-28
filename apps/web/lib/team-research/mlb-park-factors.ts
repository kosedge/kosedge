/**
 * Run-environment park factors mirrored from model-service mlb_data.py.
 * Shown only as static reference context — not invented game-day numbers.
 */
export const MLB_PARK_FACTOR_RUNS: Record<string, number> = {
  ARI: 1.02,
  ATL: 1.01,
  BAL: 1.0,
  BOS: 1.01,
  CHC: 1.01,
  CIN: 1.05,
  CLE: 0.97,
  COL: 1.12,
  CWS: 0.99,
  DET: 0.96,
  HOU: 0.98,
  KC: 0.97,
  LAA: 1.0,
  LAD: 0.99,
  MIA: 0.95,
  MIL: 1.0,
  MIN: 1.0,
  NYM: 0.98,
  NYY: 1.03,
  OAK: 0.94,
  PHI: 1.03,
  PIT: 0.96,
  SD: 0.95,
  SEA: 0.96,
  SF: 0.93,
  STL: 0.99,
  TB: 0.97,
  TEX: 1.04,
  TOR: 1.01,
  WSH: 1.0,
};

export function mlbParkFactorLabel(code: string): string | null {
  const factor = MLB_PARK_FACTOR_RUNS[code.toUpperCase()];
  if (typeof factor !== "number") return null;
  const pct = Math.round((factor - 1) * 100);
  if (pct === 0) return `${factor.toFixed(2)} · league-neutral run environment`;
  if (pct > 0) return `${factor.toFixed(2)} · +${pct}% runs vs average`;
  return `${factor.toFixed(2)} · ${pct}% runs vs average`;
}
