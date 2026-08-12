import { valueLabel } from "@/lib/fantasy/adp-proxy";
import { MAX_RECOMMEND_RANK_DELTA } from "@/lib/fantasy/value-aware-recs";
import type { FantasyDeskRow, RiskFlag, ScheduleWindowNote } from "@/lib/fantasy/types";

/**
 * KosEdge Fantasy Expert — sharp, specific, non-generic rationales.
 * Template-driven voice (no LLM call); same desk contract if a model
 * voice is swapped in later.
 *
 * Honesty rules (display only — does not retrain the model):
 * - TE rec TDs in expert copy sit in a realistic band; TE2/TE3 never
 *   headline ~7 TDs.
 * - Huge ADP gaps on fringe TE / QB2 use soft "likes more than market"
 *   framing — not lottery +200 smash copy.
 * - Never tell users to take a player a full round early when
 *   |model − ADP| > MAX_RECOMMEND_RANK_DELTA (12).
 * - Prefer yards / role / schedule; TDs only when not absurd.
 */

/** Soft-cap band for elite TE1 TD headlines in expert copy. */
export const TE_REC_TD_HEADLINE_MIN = 6;
export const TE_REC_TD_SOFT_CAP = 8;
/** Positional rank ceiling for "true elite TE1 volume" TD headlines. */
export const TE_ELITE_POS_RANK_MAX = 5;

/**
 * ADP gaps at/above this threshold get soft framing unless the model
 * rank is early-round credible.
 */
export const LOTTERY_ADP_GAP = 60;
/** 12-team rounds 1–3 — model ranks beyond this are not "smash" credible. */
export const EARLY_ROUND_RANK_MAX = 36;
/** QB13+ is QB2 territory for soft ADP framing. */
export const QB2_POS_RANK_MIN = 13;

/**
 * Whether expert copy should avoid lottery-style "+N picks of value"
 * framing for this player.
 */
export function shouldSoftFrameAdpGap(input: {
  position: string;
  rankOverall: number;
  rankPosition: number;
  valueDelta: number | null;
}): boolean {
  if (input.valueDelta == null || !Number.isFinite(input.valueDelta)) {
    return false;
  }
  const gap = Math.abs(input.valueDelta);
  // ±12 policy: never imply "take a round early" when the gap is a full round+.
  return gap > MAX_RECOMMEND_RANK_DELTA;
}

/**
 * Rec TD number suitable for expert headlines, or null to skip TDs.
 * Caps / suppresses absurd TE TD cliffs without changing underlying projections.
 */
export function displayRecTdsForExpert(input: {
  position: string;
  tier: string;
  rankPosition: number;
  recTdsTotal: number;
}): number | null {
  const pos = input.position.toUpperCase();
  const raw = input.recTdsTotal;
  if (!Number.isFinite(raw) || raw < 0) return null;

  if (pos === "TE") {
    const tier = (input.tier || "").toLowerCase();
    const isEliteVolume =
      (tier === "elite" || tier === "te1") &&
      input.rankPosition <= TE_ELITE_POS_RANK_MAX;
    if (!isEliteVolume) {
      // TE2/TE3: never headline ~6–7+ TDs — prefer yards/role instead.
      return null;
    }
    if (raw < TE_REC_TD_HEADLINE_MIN) return null;
    return Math.min(raw, TE_REC_TD_SOFT_CAP);
  }

  if (pos === "WR") {
    if (raw < 6) return null;
    // Soft-cap absurd WR TD cliffs in copy (display honesty).
    return Math.min(raw, 14);
  }

  return null;
}

export function buildDrivers(input: {
  position: string;
  team: string;
  passYardsTotal: number;
  rushYardsTotal: number;
  receivingYardsTotal: number;
  receptionsTotal: number;
  passTdsTotal: number;
  rushTdsTotal: number;
  recTdsTotal: number;
  valueOverReplacement: number;
  tier: string;
  gamesProjected: number;
  rankPosition?: number;
}): string[] {
  const pos = input.position.toUpperCase();
  const drivers: string[] = [];
  const g = Math.max(1, input.gamesProjected || 17);
  const rankPosition = input.rankPosition ?? 99;

  if (pos === "QB") {
    if (input.passYardsTotal >= 3800)
      drivers.push(
        `${input.passYardsTotal.toFixed(0)} pass yards on ${input.team} (~${(input.passYardsTotal / g).toFixed(0)}/g)`,
      );
    if (input.passTdsTotal >= 26)
      drivers.push(`${input.passTdsTotal.toFixed(1)} pass TDs`);
    if (input.rushYardsTotal >= 250)
      drivers.push(
        `${input.rushYardsTotal.toFixed(0)} rush yards keep the floor alive on down weeks`,
      );
  } else if (pos === "RB") {
    if (input.rushYardsTotal >= 900)
      drivers.push(
        `${input.rushYardsTotal.toFixed(0)} rush yards — feature-back volume on ${input.team}`,
      );
    if (input.receptionsTotal >= 40)
      drivers.push(
        `${input.receptionsTotal.toFixed(0)} receptions (~${(input.receptionsTotal / g).toFixed(1)}/g) in the pass game`,
      );
    const tds = input.rushTdsTotal + input.recTdsTotal;
    if (tds >= 8) drivers.push(`${tds.toFixed(1)} total TDs projected`);
  } else if (pos === "WR" || pos === "TE") {
    // TE: lower yard/catch floors so role/yards fill the slot when TDs are suppressed.
    const yardFloor = pos === "TE" ? 450 : 900;
    const catchFloor = pos === "TE" ? 40 : 70;
    if (input.receivingYardsTotal >= yardFloor)
      drivers.push(
        `${input.receivingYardsTotal.toFixed(0)} receiving yards (~${(input.receivingYardsTotal / g).toFixed(0)}/g)`,
      );
    if (input.receptionsTotal >= catchFloor)
      drivers.push(
        `${input.receptionsTotal.toFixed(0)} catches — target security, not just splash plays`,
      );
    const displayTds = displayRecTdsForExpert({
      position: pos,
      tier: input.tier,
      rankPosition,
      recTdsTotal: input.recTdsTotal,
    });
    if (displayTds != null) {
      drivers.push(`${displayTds.toFixed(1)} receiving TDs`);
    }
    if (pos === "TE" && input.tier === "elite")
      drivers.push(`Scarce ${input.tier} TE tier — positional leverage in single-QB`);
  } else {
    drivers.push(`${input.tier} at ${pos} — late-round positional queue`);
  }

  if (input.valueOverReplacement >= 40) {
    drivers.push(`+${input.valueOverReplacement.toFixed(0)} VOR vs ${pos} replacement`);
  }

  if (drivers.length === 0) {
    drivers.push(
      `${input.team} ${pos}: near-replacement projection — streamer / bench depth, not a locked starter`,
    );
  }
  return drivers.slice(0, 3);
}

export function buildExpertBlurb(input: {
  playerName: string;
  team: string;
  position: string;
  rankOverall: number;
  rankPosition: number;
  adp: number | null;
  valueDelta: number | null;
  tier: string;
  floorPoints: number;
  ceilingPoints: number;
  medianPoints: number;
  schedule: ScheduleWindowNote;
  riskFlags: RiskFlag[];
  drivers: string[];
  /** When preseason-fallback, keep copy aligned with honesty banners. */
  source?: "model-service" | "preseason-fallback";
}): string {
  const value = valueLabel(input.valueDelta);
  const posRank = `${input.position}${input.rankPosition}`;
  const pickGap =
    input.valueDelta == null ? 0 : Math.abs(Math.round(input.valueDelta));
  const softGap = shouldSoftFrameAdpGap({
    position: input.position,
    rankOverall: input.rankOverall,
    rankPosition: input.rankPosition,
    valueDelta: input.valueDelta,
  });
  const isPreseason = input.source === "preseason-fallback";
  const modelNoun = isPreseason ? "preseason sim" : "model";

  let lead: string;
  if (input.adp == null) {
    lead = `${input.playerName} (${input.team}): ${modelNoun} ${posRank} / overall #${input.rankOverall} — no clean market ADP match yet, so value vs ADP stays blank.`;
  } else if (input.valueDelta == null) {
    lead = `${input.playerName} (${input.team}): ${modelNoun} ${posRank} / overall #${input.rankOverall} with market ADP ~${input.adp.toFixed(0)} from a sibling scoring panel — shown for coverage, Value Δ left blank until same-format confidence is high.`;
  } else if (value.kind === "value" && softGap) {
    lead = `${input.playerName} (${input.team}): ${modelNoun} ${posRank} / overall #${input.rankOverall} likes him more than market ADP ~${input.adp.toFixed(0)} — treat the gap as a signal, not a lottery smash.`;
  } else if (value.kind === "value") {
    lead = `${input.playerName} (${input.team}): ${modelNoun} ${posRank} / overall #${input.rankOverall} while market ADP sits ~${input.adp.toFixed(0)} — about ${pickGap} picks of value if the board stalls.`;
  } else if (value.kind === "reach") {
    lead = `${input.playerName} (${input.team}): market ADP ~${input.adp.toFixed(0)} is ahead of ${modelNoun} #${input.rankOverall} (${posRank}). Only jump if you need the ${input.tier} shape now — otherwise let someone else pay the premium.`;
  } else {
    lead = `${input.playerName} (${input.team}): market and ${modelNoun} agree near #${input.rankOverall} / ADP ~${input.adp.toFixed(0)} (${posRank}, ${input.tier}).`;
  }

  const range = `Season band ${input.floorPoints.toFixed(0)}–${input.ceilingPoints.toFixed(0)} (med ${input.medianPoints.toFixed(0)}).`;
  const why = input.drivers[0]
    ? `Edge: ${input.drivers.slice(0, 2).join("; ")}.`
    : "";

  let sched = "";
  if (input.schedule.early === "soft" && input.schedule.playoff === "hard") {
    sched =
      "Stack early weeks — soft open, then a tough fantasy-playoff stretch.";
  } else if (input.schedule.early === "hard" && input.schedule.playoff === "soft") {
    sched =
      "Survive a hard open; playoff weeks look softer than the start.";
  } else if (input.schedule.early !== "neutral" || input.schedule.playoff !== "neutral") {
    sched = `${input.schedule.label}.`;
  }

  const risk = input.riskFlags[0]
    ? `Flag: ${input.riskFlags[0].detail}`
    : "";

  const preseasonNote = isPreseason
    ? "Camp-season sim — not a locked regular-season board."
    : "";

  return [lead, range, why, sched, risk, preseasonNote].filter(Boolean).join(" ");
}

export function tierCliffNote(rows: FantasyDeskRow[], position: string): string | null {
  const posRows = rows
    .filter((r) => r.position.toUpperCase() === position.toUpperCase())
    .sort((a, b) => a.rankPosition - b.rankPosition);
  if (posRows.length < 6) return null;

  let bestGap = 0;
  let cliffAt = 0;
  for (let i = 0; i < Math.min(posRows.length - 1, 24); i += 1) {
    const gap =
      posRows[i]!.valueOverReplacement - posRows[i + 1]!.valueOverReplacement;
    if (gap > bestGap) {
      bestGap = gap;
      cliffAt = i + 1;
    }
  }
  if (bestGap < 12) return null;
  const before = posRows[cliffAt - 1]!;
  const after = posRows[cliffAt]!;
  const adpDelta =
    before.adp != null ? Math.abs(before.rankOverall - before.adp) : 0;
  if (adpDelta > MAX_RECOMMEND_RANK_DELTA) {
    return `${position} cliff: VOR drops after ${before.playerName} (${position}${before.rankPosition}, overall #${before.rankOverall}) — next is ${after.playerName} at −${bestGap.toFixed(0)} VOR. Not a take-early vs ADP.`;
  }
  return `${position} cliff: take ${before.playerName} (${position}${before.rankPosition}, overall #${before.rankOverall}) before the drop — next is ${after.playerName} at −${bestGap.toFixed(0)} VOR.`;
}

export function notableValueNotes(rows: FantasyDeskRow[], limit = 3): string[] {
  return [...rows]
    .filter(
      (r) =>
        !["K", "DST"].includes(r.position.toUpperCase()) &&
        r.adp != null &&
        r.valueDelta != null,
    )
    .sort((a, b) => (b.valueDelta ?? 0) - (a.valueDelta ?? 0))
    .slice(0, limit)
    .filter((r) => (r.valueDelta ?? 0) >= 8)
    .map((r) => {
      const driver = r.drivers[0] ?? `${r.tier} profile`;
      const soft = shouldSoftFrameAdpGap({
        position: r.position,
        rankOverall: r.rankOverall,
        rankPosition: r.rankPosition,
        valueDelta: r.valueDelta,
      });
      const isPreseason = r.source === "preseason-fallback";
      const modelNoun = isPreseason ? "preseason sim" : "model";
      if (soft) {
        return `${r.playerName} (${r.team} ${r.position}${r.rankPosition}): ${modelNoun} #${r.rankOverall} likes him more than ADP ~${r.adp!.toFixed(0)}. ${driver}.`;
      }
      return `${r.playerName} (${r.team} ${r.position}${r.rankPosition}): ${modelNoun} #${r.rankOverall} vs market ADP ~${r.adp!.toFixed(0)} (+${r.valueDelta!.toFixed(0)}). ${driver}.`;
    });
}
