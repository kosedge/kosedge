import { valueLabel } from "@/lib/fantasy/adp-proxy";
import type { FantasyDeskRow, RiskFlag, ScheduleWindowNote } from "@/lib/fantasy/types";

/**
 * KosEdge Fantasy Expert — sharp, specific, non-generic rationales.
 * Template-driven Phase 1 foundation (no LLM call); ready to swap to
 * a model-backed voice later without changing the desk contract.
 */

export function buildDrivers(input: {
  position: string;
  passYardsTotal: number;
  rushYardsTotal: number;
  receivingYardsTotal: number;
  receptionsTotal: number;
  passTdsTotal: number;
  rushTdsTotal: number;
  recTdsTotal: number;
  valueOverReplacement: number;
  tier: string;
}): string[] {
  const pos = input.position.toUpperCase();
  const drivers: string[] = [];

  if (pos === "QB") {
    if (input.passYardsTotal >= 3800)
      drivers.push(`${input.passYardsTotal.toFixed(0)} pass-yard volume`);
    if (input.passTdsTotal >= 26)
      drivers.push(`${input.passTdsTotal.toFixed(1)} pass TD projection`);
    if (input.rushYardsTotal >= 250)
      drivers.push(`${input.rushYardsTotal.toFixed(0)} rush yards — dual-threat floor`);
  } else if (pos === "RB") {
    if (input.rushYardsTotal >= 900)
      drivers.push(`${input.rushYardsTotal.toFixed(0)} rush-yard workload`);
    if (input.receptionsTotal >= 40)
      drivers.push(`${input.receptionsTotal.toFixed(0)} receptions — pass-game juice`);
    if (input.rushTdsTotal + input.recTdsTotal >= 8)
      drivers.push(
        `${(input.rushTdsTotal + input.recTdsTotal).toFixed(1)} total TDs`,
      );
  } else if (pos === "WR" || pos === "TE") {
    if (input.receivingYardsTotal >= 900)
      drivers.push(`${input.receivingYardsTotal.toFixed(0)} receiving yards`);
    if (input.receptionsTotal >= 70)
      drivers.push(`${input.receptionsTotal.toFixed(0)} catches — volume security`);
    if (input.recTdsTotal >= 6)
      drivers.push(`${input.recTdsTotal.toFixed(1)} receiving TDs`);
  } else {
    drivers.push(`${input.tier} tier on the season board`);
  }

  if (input.valueOverReplacement >= 40) {
    drivers.push(`+${input.valueOverReplacement.toFixed(0)} VOR vs replacement`);
  }

  if (drivers.length === 0) {
    drivers.push("Projection sits near replacement — streamer / depth profile");
  }
  return drivers.slice(0, 3);
}

export function buildExpertBlurb(input: {
  playerName: string;
  team: string;
  position: string;
  rankOverall: number;
  rankPosition: number;
  adp: number;
  valueDelta: number;
  tier: string;
  floorPoints: number;
  ceilingPoints: number;
  schedule: ScheduleWindowNote;
  riskFlags: RiskFlag[];
  drivers: string[];
}): string {
  const value = valueLabel(input.valueDelta);
  const posRank = `${input.position}${input.rankPosition}`;
  const lead =
    value.kind === "value"
      ? `${input.playerName} is a board value at ~ADP ${input.adp.toFixed(0)} while the model has him at overall #${input.rankOverall} (${posRank}).`
      : value.kind === "reach"
        ? `${input.playerName} is being drafted ahead of the model (#${input.rankOverall} / ADP ~${input.adp.toFixed(0)}) — pay up only if you need the ${input.tier} profile.`
        : `${input.playerName} is priced about where the model sits (#${input.rankOverall}, ADP ~${input.adp.toFixed(0)}).`;

  const range = `Season band ${input.floorPoints.toFixed(0)}–${input.ceilingPoints.toFixed(0)} fantasy points.`;
  const why = input.drivers[0]
    ? `Driven by ${input.drivers.slice(0, 2).join(" and ")}.`
    : "";
  const sched =
    input.schedule.early !== "neutral" || input.schedule.playoff !== "neutral"
      ? `Schedule: ${input.schedule.label}.`
      : "";
  const risk = input.riskFlags[0]
    ? `Watch: ${input.riskFlags[0].label.toLowerCase()} — ${input.riskFlags[0].detail}`
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
  return `${position} cliff after ${before.playerName} (${position}${before.rankPosition}): VOR drops ${bestGap.toFixed(0)} into ${after.playerName}.`;
}

export function notableValueNotes(rows: FantasyDeskRow[], limit = 3): string[] {
  return [...rows]
    .filter((r) => !["K", "DST"].includes(r.position.toUpperCase()))
    .sort((a, b) => b.valueDelta - a.valueDelta)
    .slice(0, limit)
    .filter((r) => r.valueDelta >= 8)
    .map(
      (r) =>
        `${r.playerName} (${r.team} ${r.position}): model #${r.rankOverall} vs ADP ~${r.adp.toFixed(0)} (+${r.valueDelta.toFixed(0)} value).`,
    );
}
