/**
 * KosEdge ADP proxy v1.
 *
 * There is no live FantasyPros/Sleeper/Yahoo ADP ingest in-repo yet.
 * This maps model VOR rank → a consensus-style ADP that mirrors well-known
 * single-QB draft behavior (QBs fall, elite RBs rise, K/DST last).
 * Labeled honestly in the UI as a proxy until a real feed is wired.
 */

export const ADP_PROXY_LABEL =
  "KosEdge ADP proxy v1 (consensus-style — not a live marketplace ADP feed)";

function stableJitter(seed: string, amplitude: number): number {
  let hash = 0;
  for (let i = 0; i < seed.length; i += 1) {
    hash = (hash * 31 + seed.charCodeAt(i)) >>> 0;
  }
  const unit = (hash % 1000) / 1000; // [0, 1)
  return (unit - 0.5) * 2 * amplitude;
}

/**
 * Convert model overall rank into an ADP-like pick number for a 12-team,
 * ~15–16 round draft (~180–192 picks).
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
    // Mid/late QBs typically wait longer than pure VOR suggests.
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
    // Real ADP parks these near the end regardless of raw points.
    adp = Math.max(adp, 140 + (input.modelRank % 40));
  }

  adp += stableJitter(input.playerId, 2.4);
  return Math.max(1, Math.round(adp * 10) / 10);
}

/** Positive = undervalued vs ADP (model rank earlier than ADP). */
export function valueDelta(modelRank: number, adp: number): number {
  return Math.round((adp - modelRank) * 10) / 10;
}

export function valueLabel(delta: number): {
  kind: "value" | "fair" | "reach";
  text: string;
} {
  if (delta >= 8) return { kind: "value", text: `+${delta.toFixed(0)} value` };
  if (delta <= -8)
    return { kind: "reach", text: `${delta.toFixed(0)} reach` };
  return { kind: "fair", text: "fair" };
}
