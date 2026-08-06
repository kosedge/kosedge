import { valueLabel } from "@/lib/fantasy/adp-proxy";
import type { FantasyDeskRow, RiskFlag, ScheduleWindowNote } from "@/lib/fantasy/types";

/**
 * KosEdge Fantasy Expert — sharp, specific, non-generic rationales.
 * Template-driven voice (no LLM call); same desk contract if a model
 * voice is swapped in later.
 */

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
}): string[] {
  const pos = input.position.toUpperCase();
  const drivers: string[] = [];
  const g = Math.max(1, input.gamesProjected || 17);

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
    if (input.receivingYardsTotal >= 900)
      drivers.push(
        `${input.receivingYardsTotal.toFixed(0)} receiving yards (~${(input.receivingYardsTotal / g).toFixed(0)}/g)`,
      );
    if (input.receptionsTotal >= 70)
      drivers.push(
        `${input.receptionsTotal.toFixed(0)} catches — target security, not just splash plays`,
      );
    if (input.recTdsTotal >= 6)
      drivers.push(`${input.recTdsTotal.toFixed(1)} receiving TDs`);
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
}): string {
  const value = valueLabel(input.valueDelta);
  const posRank = `${input.position}${input.rankPosition}`;
  const pickGap =
    input.valueDelta == null ? 0 : Math.abs(Math.round(input.valueDelta));

  let lead: string;
  if (input.adp == null) {
    lead = `${input.playerName} (${input.team}): model ${posRank} / overall #${input.rankOverall} — no clean market ADP match yet, so value vs ADP stays blank.`;
  } else if (input.valueDelta == null) {
    lead = `${input.playerName} (${input.team}): model ${posRank} / overall #${input.rankOverall} with market ADP ~${input.adp.toFixed(0)} from a sibling scoring panel — shown for coverage, Value Δ left blank until same-format confidence is high.`;
  } else if (value.kind === "value") {
    lead = `${input.playerName} (${input.team}): model ${posRank} / overall #${input.rankOverall} while market ADP sits ~${input.adp.toFixed(0)} — about ${pickGap} picks of value if the board stalls.`;
  } else if (value.kind === "reach") {
    lead = `${input.playerName} (${input.team}): market ADP ~${input.adp.toFixed(0)} is ahead of model #${input.rankOverall} (${posRank}). Only jump if you need the ${input.tier} shape now — otherwise let someone else pay the premium.`;
  } else {
    lead = `${input.playerName} (${input.team}): market and model agree near #${input.rankOverall} / ADP ~${input.adp.toFixed(0)} (${posRank}, ${input.tier}).`;
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

  return [lead, range, why, sched, risk].filter(Boolean).join(" ");
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
      return `${r.playerName} (${r.team} ${r.position}${r.rankPosition}): model #${r.rankOverall} vs market ADP ~${r.adp!.toFixed(0)} (+${r.valueDelta!.toFixed(0)}). ${driver}.`;
    });
}
