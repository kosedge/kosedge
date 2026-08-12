/**
 * Investable NFL props universe — skill positions + involvement floors.
 * Prefer missing rows over OL/DL/K anytime-TD junk. Tune floors here.
 */

export const POSITION_ALIASES: Record<string, string> = {
  HB: "RB",
  FB: "RB",
  OT: "OL",
  OG: "OL",
  C: "OL",
  T: "OL",
  G: "OL",
  LT: "OL",
  LG: "OL",
  RG: "OL",
  RT: "OL",
  DE: "DL",
  DT: "DL",
  NT: "DL",
  ILB: "LB",
  OLB: "LB",
  MLB: "LB",
  CB: "DB",
  S: "DB",
  FS: "DB",
  SS: "DB",
  SAF: "DB",
  P: "ST",
  LS: "ST",
  DEF: "DST",
};

export const SKILL_GROUPS = new Set(["QB", "RB", "WR", "TE"]);
export const EXCLUDED_GROUPS = new Set(["OL", "DL", "LB", "DB", "ST", "DST"]);

export const MARKETS_BY_GROUP: Record<string, readonly string[]> = {
  QB: ["pass_yds", "pass_tds", "completions", "attempts", "rush_yds", "anytime_td"],
  RB: ["rush_yds", "rush_att", "rec_yds", "receptions", "anytime_td"],
  WR: ["rec_yds", "receptions", "anytime_td", "longest_reception"],
  TE: ["rec_yds", "receptions", "anytime_td", "longest_reception"],
  K: ["fg_made", "fg_att"],
};

/** Tabs on the primary Props board (v1). */
export const PRIMARY_BOARD_MARKETS = [
  "pass_yds",
  "rush_yds",
  "rec_yds",
  "receptions",
  "anytime_td",
] as const;

const MEAN_FLOORS: Record<string, Record<string, number>> = {
  pass_yds: { QB: 150, "*": 150 },
  pass_tds: { QB: 0.8, "*": 0.8 },
  completions: { QB: 15, "*": 15 },
  attempts: { QB: 22, "*": 22 },
  rush_yds: { QB: 18, RB: 25, WR: 8, "*": 20 },
  rush_att: { RB: 6, "*": 6 },
  rec_yds: { RB: 8, WR: 20, TE: 18, "*": 15 },
  receptions: { RB: 1.2, WR: 2.5, TE: 2, "*": 1.5 },
  anytime_td: { QB: 0.12, RB: 0.1, WR: 0.08, TE: 0.08, "*": 0.1 },
  longest_reception: { WR: 12, TE: 12, "*": 12 },
  fg_made: { K: 1.2, "*": 1.2 },
  fg_att: { K: 1.5, "*": 1.5 },
};

export const STARTER_ROLE_CONFIDENCE = 0.55;
const ZERO_MEAN_EPS = 1e-6;
const PLACEHOLDER_CONFIDENCE_MAX = 0.12;

const UNKNOWN_POSITION_MARKETS = new Set([
  "pass_yds",
  "pass_tds",
  "completions",
  "attempts",
  "rush_yds",
  "rush_att",
  "rec_yds",
  "receptions",
  "anytime_td",
  "longest_reception",
]);

export const PROPS_ELIGIBILITY_NOTE =
  "Eligibility = skill positions (QB/RB/WR/TE) + involvement floors. OL/DL/ST and 0.0 model rows are omitted.";

export function canonicalizePosition(position: string | null | undefined): string {
  const pos = String(position || "").trim().toUpperCase();
  if (!pos) return "";
  return POSITION_ALIASES[pos] ?? pos;
}

export function meanFloor(marketKey: string, position?: string | null): number {
  const byPos = MEAN_FLOORS[marketKey] ?? {};
  const group = canonicalizePosition(position);
  if (group && byPos[group] != null) return byPos[group];
  return byPos["*"] ?? 0;
}

function volume(opts: {
  marketKey: string;
  modelMean: number | null | undefined;
  line: number | null | undefined;
}): number {
  const mean =
    opts.modelMean != null && Number.isFinite(opts.modelMean)
      ? opts.modelMean
      : null;
  if (mean != null && mean > ZERO_MEAN_EPS) return mean;
  if (opts.marketKey === "anytime_td") return 0;
  if (opts.line != null && Number.isFinite(opts.line) && opts.line > ZERO_MEAN_EPS) {
    return opts.line;
  }
  return 0;
}

export type PropEligibilityInput = {
  marketKey: string;
  position?: string | null;
  modelMean?: number | null;
  line?: number | null;
  confidence?: number | null;
  roleConfidence?: number | null;
  marketJoined?: boolean | null;
};

export function isInvestableProp(row: PropEligibilityInput): boolean {
  const mk = String(row.marketKey || "").trim();
  if (!mk) return false;
  const group = canonicalizePosition(row.position);

  if (EXCLUDED_GROUPS.has(group)) return false;
  if (group === "K" && mk === "anytime_td") return false;

  const allowed = group
    ? new Set(MARKETS_BY_GROUP[group] ?? [])
    : UNKNOWN_POSITION_MARKETS;
  if (!allowed.has(mk)) return false;

  const vol = volume({
    marketKey: mk,
    modelMean: row.modelMean,
    line: row.line,
  });
  if (vol <= ZERO_MEAN_EPS) return false;

  const floor = meanFloor(mk, group || null);
  const starter =
    row.roleConfidence != null &&
    row.roleConfidence >= STARTER_ROLE_CONFIDENCE &&
    SKILL_GROUPS.has(group);
  const need = floor * (starter ? 0.5 : 1);
  if (vol + 1e-9 < need) return false;

  if (
    row.confidence != null &&
    row.confidence <= PLACEHOLDER_CONFIDENCE_MAX &&
    vol <= need &&
    row.marketJoined !== true
  ) {
    return false;
  }

  return true;
}
