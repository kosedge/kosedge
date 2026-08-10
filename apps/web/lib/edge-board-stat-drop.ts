/**
 * Uniform Stat Drop schema for Edge Board cards.
 * Same 8 slots every game; missing → em dash. Always render.
 */

import type { EdgeBoardMatchupContext } from "@/lib/edge-board-matchup-context";
import { shortTeam } from "@/lib/edge-board-matchup-context";

export const STAT_DROP_SLOT_IDS = [
  "power",
  "spread",
  "total",
  "impliedWp",
  "site",
  "rest",
  "pace",
  "structural",
] as const;

export type StatDropSlotId = (typeof STAT_DROP_SLOT_IDS)[number];

export type StatDropSlot = {
  id: StatDropSlotId;
  label: string;
  value: string;
  /** True when power slot has a real number (required for success). */
  requiredOk?: boolean;
};

export type StatDrop = {
  slots: StatDropSlot[];
  /** Convenience: power value present. */
  hasPower: boolean;
};

const EM = "—";

function fmtSigned(n: number, digits = 1): string {
  const r = Number(n.toFixed(digits));
  if (Object.is(r, -0) || r === 0) return digits === 0 ? "0" : "0.0";
  return r > 0 ? `+${r.toFixed(digits)}` : r.toFixed(digits);
}

function fmtNum(n: number | null | undefined, digits = 1): string {
  if (n == null || !Number.isFinite(n)) return EM;
  return Number(n).toFixed(digits);
}

function fmtPct(p: number | null | undefined): string {
  if (p == null || !Number.isFinite(p)) return EM;
  return `${Math.round(p * 100)}%`;
}

function powerSlot(ctx: EdgeBoardMatchupContext): StatDropSlot {
  const away = shortTeam(ctx, "away");
  const home = shortTeam(ctx, "home");

  if (
    ctx.modelPowerAway != null &&
    ctx.modelPowerHome != null &&
    Number.isFinite(ctx.modelPowerAway) &&
    Number.isFinite(ctx.modelPowerHome)
  ) {
    const delta = ctx.modelPowerHome - ctx.modelPowerAway;
    const keiBit =
      ctx.keiPowerAway != null && ctx.keiPowerHome != null
        ? ` · KEI ${fmtSigned(ctx.keiPowerAway)}/${fmtSigned(ctx.keiPowerHome)}`
        : "";
    return {
      id: "power",
      label: "Power",
      value: `${away} ${fmtNum(ctx.modelPowerAway, 1)} / ${home} ${fmtNum(ctx.modelPowerHome, 1)} (Δ ${fmtSigned(delta)})${keiBit}`,
      requiredOk: true,
    };
  }

  if (ctx.keiPowerAway != null && ctx.keiPowerHome != null) {
    const delta = ctx.keiPowerHome - ctx.keiPowerAway;
    return {
      id: "power",
      label: "Power",
      value: `KEI ${away} ${fmtSigned(ctx.keiPowerAway)} / ${home} ${fmtSigned(ctx.keiPowerHome)} (Δ ${fmtSigned(delta)})`,
      requiredOk: true,
    };
  }

  return {
    id: "power",
    label: "Power",
    value: EM,
    requiredOk: false,
  };
}

function spreadSlot(ctx: EdgeBoardMatchupContext): StatDropSlot {
  const mkt =
    ctx.marketSpreadHome != null ? fmtSigned(ctx.marketSpreadHome) : EM;
  const kei = ctx.keiSpreadHome != null ? fmtSigned(ctx.keiSpreadHome) : EM;
  return {
    id: "spread",
    label: "Spread",
    value: mkt === EM && kei === EM ? EM : `Mkt ${mkt} · KEI ${kei}`,
  };
}

function totalSlot(ctx: EdgeBoardMatchupContext): StatDropSlot {
  const mkt = fmtNum(ctx.marketTotal, 1);
  const kei = fmtNum(ctx.keiTotal, 1);
  return {
    id: "total",
    label: "Total",
    value: mkt === EM && kei === EM ? EM : `Mkt ${mkt} · KEI ${kei}`,
  };
}

function impliedWpSlot(ctx: EdgeBoardMatchupContext): StatDropSlot {
  const away = shortTeam(ctx, "away");
  const home = shortTeam(ctx, "home");
  let awayWp = ctx.awayWinProb;
  let homeWp = ctx.homeWinProb;
  if (awayWp == null && homeWp != null) awayWp = 1 - homeWp;
  if (homeWp == null && awayWp != null) homeWp = 1 - awayWp;
  if (awayWp == null && homeWp == null) {
    return { id: "impliedWp", label: "Implied WP", value: EM };
  }
  return {
    id: "impliedWp",
    label: "Implied WP",
    value: `${away} ${fmtPct(awayWp)} / ${home} ${fmtPct(homeWp)}`,
  };
}

function siteSlot(ctx: EdgeBoardMatchupContext): StatDropSlot {
  if (ctx.isNeutral) {
    const city = ctx.siteCity || "Neutral";
    const venue = ctx.siteVenue ? ` · ${ctx.siteVenue}` : "";
    const hfa =
      ctx.hfaPoints === 0
        ? "HFA 0"
        : `partial HFA ${fmtNum(ctx.hfaPoints, 2)} pts`;
    return {
      id: "site",
      label: "Site",
      value: `Neutral · ${city}${venue} · ${hfa}`,
    };
  }
  return {
    id: "site",
    label: "Site",
    value: `Home / Road · HFA ${fmtNum(ctx.hfaPoints, 2)} pts`,
  };
}

function restLabel(
  days: number | null,
  bye: boolean,
  seasonOpen: boolean,
): string {
  if (bye) return "Bye";
  if (seasonOpen) return "Season open";
  if (days == null || !Number.isFinite(days)) return EM;
  return `${Math.round(days)}d`;
}

function restSlot(ctx: EdgeBoardMatchupContext): StatDropSlot {
  const seasonOpen = ctx.seasonGate === "week1";
  const away = shortTeam(ctx, "away");
  const home = shortTeam(ctx, "home");
  const a = restLabel(ctx.restDaysAway, ctx.byeAway, seasonOpen);
  const h = restLabel(ctx.restDaysHome, ctx.byeHome, seasonOpen);
  if (a === EM && h === EM) {
    return { id: "rest", label: "Rest", value: EM };
  }
  return {
    id: "rest",
    label: "Rest",
    value: `${away} ${a} / ${home} ${h}`,
  };
}

function paceSlot(ctx: EdgeBoardMatchupContext): StatDropSlot {
  const away = shortTeam(ctx, "away");
  const home = shortTeam(ctx, "home");
  const a = fmtNum(ctx.paceAway, 2);
  const h = fmtNum(ctx.paceHome, 2);
  if (a === EM && h === EM) {
    return { id: "pace", label: "Pace", value: EM };
  }
  return {
    id: "pace",
    label: "Pace",
    value: `${away} ${a} / ${home} ${h}`,
  };
}

function structuralSlot(ctx: EdgeBoardMatchupContext): StatDropSlot {
  const away = shortTeam(ctx, "away");
  const home = shortTeam(ctx, "home");
  const a = ctx.structuralTagAway || EM;
  const h = ctx.structuralTagHome || EM;
  if (a === EM && h === EM) {
    return { id: "structural", label: "Tags", value: EM };
  }
  return {
    id: "structural",
    label: "Tags",
    value: `${away} ${a} · ${home} ${h}`,
  };
}

export function buildStatDrop(ctx: EdgeBoardMatchupContext): StatDrop {
  const slots: StatDropSlot[] = [
    powerSlot(ctx),
    spreadSlot(ctx),
    totalSlot(ctx),
    impliedWpSlot(ctx),
    siteSlot(ctx),
    restSlot(ctx),
    paceSlot(ctx),
    structuralSlot(ctx),
  ];
  const power = slots.find((s) => s.id === "power");
  return {
    slots,
    hasPower: Boolean(power?.requiredOk),
  };
}

/** Assert schema completeness for tests. */
export function assertStatDropSchema(drop: StatDrop): boolean {
  if (drop.slots.length !== STAT_DROP_SLOT_IDS.length) return false;
  return STAT_DROP_SLOT_IDS.every((id, i) => drop.slots[i]?.id === id);
}
