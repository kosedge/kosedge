/**
 * ADP helpers shared by the desk.
 *
 * Historical note: `adpFromModelRank` was the Phase 1 consensus-style proxy.
 * The desk now prefers FantasyPros market ADP (`adp-fantasypros.ts`).
 * The proxy remains only for tests / emergency offline demos — never as a
 * silent stand-in on the live value board.
 */

export const ADP_PROXY_LABEL =
  "KosEdge ADP proxy v1 (legacy — not used on the live value board)";

function stableJitter(seed: string, amplitude: number): number {
  let hash = 0;
  for (let i = 0; i < seed.length; i += 1) {
    hash = (hash * 31 + seed.charCodeAt(i)) >>> 0;
  }
  const unit = (hash % 1000) / 1000; // [0, 1)
  return (unit - 0.5) * 2 * amplitude;
}

/**
 * Legacy model→ADP proxy. Prefer FantasyPros feed for production desks.
 */
export function adpFromModelRank(input: {
  modelRank: number;
  position: string;
  tier: string;
  playerId: string;
}): number {
  const pos = input.position.toUpperCase();
  let adp = input.modelRank;

  if (pos === "QB") {
    if (input.modelRank <= 12) adp += 8;
    else if (input.modelRank <= 40) adp += 22;
    else adp += 35;
  } else if (pos === "RB") {
    if (input.tier === "elite") adp -= 2;
    else if (input.tier === "RB1") adp -= 1;
    else if (input.modelRank > 60) adp += 4;
  } else if (pos === "WR") {
    if (input.tier === "elite") adp -= 1;
    else if (input.modelRank > 80) adp += 3;
  } else if (pos === "TE") {
    if (input.tier === "elite" || input.tier === "TE1") adp -= 4;
    else adp += 12;
  } else if (pos === "K" || pos === "DST") {
    adp = Math.max(adp, 140 + (input.modelRank % 40));
  }

  adp += stableJitter(input.playerId, 2.4);
  return Math.max(1, Math.round(adp * 10) / 10);
}

/** Positive = undervalued vs ADP (model rank earlier than ADP). */
export function valueDelta(modelRank: number, adp: number): number {
  return Math.round((adp - modelRank) * 10) / 10;
}

export function valueLabel(delta: number | null | undefined): {
  kind: "value" | "fair" | "reach" | "na";
  text: string;
} {
  if (delta == null || !Number.isFinite(delta)) {
    return { kind: "na", text: "—" };
  }
  if (delta >= 8) return { kind: "value", text: `+${delta.toFixed(0)} value` };
  if (delta <= -8) return { kind: "reach", text: `${delta.toFixed(0)} reach` };
  return { kind: "fair", text: "fair" };
}

export function formatAdp(adp: number | null | undefined, digits = 1): string {
  if (adp == null || !Number.isFinite(adp)) return "—";
  return adp.toFixed(digits);
}
