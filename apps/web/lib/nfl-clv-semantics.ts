/**
 * NFL CLV copy — must match services/model-service/src/services/nfl_clv_semantics.py.
 * Subscribers read “positive CLV” as beating the close. Label the math, or hide it.
 */

export const NFL_CLV_DEFINITION =
  "CLV is the movement of our recommended side's market from the first captured price (open) to the last captured price (called close) on the same market. Positive means the market moved toward our side after the play was implied — we got a better number than the later line (beat the close).";

export const NFL_CLV_POPULATION =
  "Population is +EV vs the open snapshot (moneyline: model win probability exceeds open implied probability on that side; total: |model − open| ≥ 1.0; spread: |model − open| ≥ 1.0). Not PLAY-only. Not graded-only.";

export const NFL_CLV_TIMESTAMPS =
  "Open = first legal snapshot and close = last snapshot strictly before kickoff (prefer labeled close) — post-kickoff rows are not the close.";

export const NFL_CLV_LIVE_INCOMPLETE_NOTE =
  "Live 2026 Tracking is incomplete until regular-season closes exist. Identical first/last scrapes are pushes, not losses — they are not “how often we beat the close.”";

export const NFL_CLV_BEAT_CLOSE_LABEL = "Beat later snapshot";
export const NFL_CLV_BEAT_CLOSE_HINT =
  "Share of rows where the line moved and moved toward our side. Pushes (open = close) are excluded from this rate and listed separately.";

export type LiveClvTrust = {
  trustworthy: boolean;
  reasons?: string[];
  decided_n?: number;
};

export function liveClvHeroAllowed(trust: LiveClvTrust | null | undefined): boolean {
  return Boolean(trust?.trustworthy) && (trust?.decided_n ?? 0) > 0;
}

export function formatClvRate(
  rate: number | null | undefined,
  decidedN: number | null | undefined,
): string {
  if (
    rate == null ||
    !Number.isFinite(rate) ||
    decidedN == null ||
    !Number.isFinite(decidedN) ||
    decidedN <= 0
  ) {
    return "—";
  }
  return `${(rate * 100).toFixed(1)}%`;
}
