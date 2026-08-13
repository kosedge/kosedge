/**
 * ADP-deviation QA flags for the fantasy desk.
 * Extreme |modelRank − ADP| is allowed — but must be flagged and explainable,
 * not silent “alpha.” Unmatched ADP (—) never gets a false flag.
 */

import { QB2_POS_RANK_MIN } from "@/lib/fantasy/expert";
import type { RiskFlag, ScheduleWindowNote } from "@/lib/fantasy/types";

/** Default |modelRank − ADP| to flag (RB/WR/QB1) as a role/data warning. */
export const ADP_QA_GAP_DEFAULT = 8;
/** TE and QB2 still flag at |Δ|≥8 — noisier ADP, same investigate-role rule. */
export const ADP_QA_GAP_TE_OR_QB2 = 8;

export type AdpQaFlagKind = "model_ahead" | "market_ahead";

export type AdpQaFlag = {
  kind: AdpQaFlagKind;
  /** Short chip: "Model ≫ market" / "Market ≫ model" */
  label: string;
  /** Umbrella copy for title/tooltip. */
  categoryLabel: "Check role";
  absGap: number;
  threshold: number;
  /** Required when flagged — role, volume, VOR/Δ, depth/availability, schedule. */
  drivers: string[];
  preseason: boolean;
};

export function adpQaGapThreshold(
  position: string,
  rankPosition: number,
): number {
  const pos = position.toUpperCase();
  if (pos === "TE") return ADP_QA_GAP_TE_OR_QB2;
  if (pos === "QB" && rankPosition >= QB2_POS_RANK_MIN) {
    return ADP_QA_GAP_TE_OR_QB2;
  }
  return ADP_QA_GAP_DEFAULT;
}

function volumeLines(input: {
  position: string;
  team: string;
  gamesProjected: number;
  passYardsTotal: number;
  rushYardsTotal: number;
  receivingYardsTotal: number;
  receptionsTotal: number;
}): string[] {
  const pos = input.position.toUpperCase();
  const g = Math.max(1, input.gamesProjected || 17);
  const lines: string[] = [];
  if (pos === "QB" && input.passYardsTotal > 0) {
    lines.push(
      `${input.passYardsTotal.toFixed(0)} pass yards on ${input.team} (~${(input.passYardsTotal / g).toFixed(0)}/g)`,
    );
  }
  if (pos === "RB") {
    if (input.rushYardsTotal > 0) {
      lines.push(
        `${input.rushYardsTotal.toFixed(0)} rush yards on ${input.team} (~${(input.rushYardsTotal / g).toFixed(0)}/g)`,
      );
    }
    if (input.receptionsTotal >= 20) {
      lines.push(
        `${input.receptionsTotal.toFixed(0)} receptions (~${(input.receptionsTotal / g).toFixed(1)}/g)`,
      );
    }
  }
  if (pos === "WR" || pos === "TE") {
    if (input.receivingYardsTotal > 0) {
      lines.push(
        `${input.receivingYardsTotal.toFixed(0)} receiving yards (~${(input.receivingYardsTotal / g).toFixed(0)}/g)`,
      );
    }
    if (input.receptionsTotal > 0) {
      lines.push(
        `${input.receptionsTotal.toFixed(0)} catches — projected volume, not ADP consensus`,
      );
    }
  }
  return lines;
}

export function buildAdpQaDrivers(input: {
  position: string;
  team: string;
  rankPosition: number;
  tier: string;
  gamesProjected: number;
  passYardsTotal: number;
  rushYardsTotal: number;
  receivingYardsTotal: number;
  receptionsTotal: number;
  valueOverReplacement: number;
  valueDelta: number;
  adp: number;
  rankOverall: number;
  existingDrivers: string[];
  riskFlags: RiskFlag[];
  schedule: ScheduleWindowNote;
  source?: "model-service" | "preseason-fallback";
}): string[] {
  const pos = input.position.toUpperCase();
  const out: string[] = [];

  out.push(
    `Role: ${input.team} ${pos}${input.rankPosition} (${input.tier}) · model #${input.rankOverall}`,
  );

  const volume = volumeLines(input);
  for (const line of volume.slice(0, 2)) out.push(line);
  for (const d of input.existingDrivers) {
    if (out.length >= 4) break;
    if (!out.includes(d)) out.push(d);
  }

  out.push(
    `Value Δ ${input.valueDelta >= 0 ? "+" : ""}${input.valueDelta.toFixed(0)} vs ADP ~${input.adp.toFixed(0)}`,
  );
  if (Number.isFinite(input.valueOverReplacement)) {
    out.push(
      `VOR ${input.valueOverReplacement >= 0 ? "+" : ""}${input.valueOverReplacement.toFixed(0)} vs ${pos} replacement`,
    );
  }

  const depth = input.riskFlags.find(
    (f) => f.kind === "depth_volatility" || f.kind === "committee",
  );
  if (depth) out.push(`${depth.label}: ${depth.detail}`);

  const avail = input.riskFlags.find((f) => f.kind === "availability");
  if (avail) out.push(`${avail.label}: ${avail.detail}`);

  if (
    input.schedule.early !== "neutral" ||
    input.schedule.playoff !== "neutral"
  ) {
    out.push(`Game script / SOS: ${input.schedule.label}`);
  }

  if (input.source === "preseason-fallback") {
    out.push("Preseason sim ranks — not a locked regular-season board.");
  }

  const seen = new Set<string>();
  const unique: string[] = [];
  for (const line of out) {
    const key = line.toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    unique.push(line);
  }
  return unique.slice(0, 8);
}

export function resolveAdpQaFlag(input: {
  position: string;
  rankPosition: number;
  rankOverall: number;
  tier: string;
  team: string;
  gamesProjected: number;
  passYardsTotal: number;
  rushYardsTotal: number;
  receivingYardsTotal: number;
  receptionsTotal: number;
  valueOverReplacement: number;
  adp: number | null;
  valueDelta: number | null;
  existingDrivers: string[];
  riskFlags: RiskFlag[];
  schedule: ScheduleWindowNote;
  source?: "model-service" | "preseason-fallback";
}): AdpQaFlag | null {
  if (input.adp == null || input.valueDelta == null) return null;
  if (!Number.isFinite(input.adp) || !Number.isFinite(input.valueDelta)) {
    return null;
  }

  const absGap = Math.abs(input.valueDelta);
  const threshold = adpQaGapThreshold(input.position, input.rankPosition);
  if (absGap < threshold) return null;

  const kind: AdpQaFlagKind =
    input.valueDelta > 0 ? "model_ahead" : "market_ahead";
  const label =
    kind === "model_ahead" ? "Role vs ADP" : "ADP vs role";

  return {
    kind,
    label,
    categoryLabel: "Check role",
    absGap,
    threshold,
    preseason: input.source === "preseason-fallback",
    drivers: buildAdpQaDrivers({
      ...input,
      adp: input.adp,
      valueDelta: input.valueDelta,
    }),
  };
}
