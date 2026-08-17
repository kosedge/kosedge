/**
 * Frozen CFB research artifacts — power SoT + season win totals.
 * Bundled into the web app so Teams / Projections render without Railway.
 * used_in_spread stays false. No KEI. CFP / natty omitted.
 */

import powerPack from "@/lib/data/cfb-power-sot-2026.json";
import projPack from "@/lib/data/cfb-season-projections-2026.json";

export type CfbPowerSotTeam = {
  team: string;
  conference?: string;
  rank?: number;
  offense_index?: number | null;
  defense_index?: number | null;
  power_index?: number | null;
  early_season_uncertainty?: number | null;
  qb_class?: string | null;
  qb_name?: string | null;
  open_qb?: boolean;
  efficiency_source?: string | null;
  efficiency_fill?: string | null;
  off_eff?: number | null;
  def_eff?: number | null;
  next?: {
    week?: number;
    opponent?: string;
    home?: boolean;
    neutral_site?: boolean;
  } | null;
};

export type CfbPowerSotPack = {
  power_version?: string;
  power_as_of?: string;
  engine_version?: string;
  n_teams?: number;
  used_in_spread?: boolean;
  kei?: boolean;
  research_only?: boolean;
  method?: string;
  teams?: CfbPowerSotTeam[];
};

export type CfbProjectionTeam = {
  team: string;
  conference?: string;
  rank?: number;
  mean?: number;
  std?: number;
  p10?: number;
  p50?: number;
  p90?: number;
  p_bowl?: number;
  power_index?: number | null;
  power_rank?: number | null;
};

export type CfbProjectionPack = {
  artifact_id?: string;
  engine_version?: string;
  power_version?: string;
  power_as_of?: string;
  as_of?: string;
  n_sims?: number;
  n_teams?: number;
  n_games_scored?: number;
  sum_expected_wins?: number;
  method?: string;
  used_in_spread?: boolean;
  kei?: boolean;
  research_only?: boolean;
  win_tables_final?: boolean;
  cfp_make?: unknown;
  natty?: unknown;
  teams?: CfbProjectionTeam[];
};

const POWER = powerPack as CfbPowerSotPack;
const PROJ = projPack as CfbProjectionPack;

export function loadCfbPowerSot(): CfbPowerSotPack {
  return POWER;
}

export function loadCfbSeasonProjections(): CfbProjectionPack {
  return PROJ;
}

export function cfbPowerTeams(): CfbPowerSotTeam[] {
  return POWER.teams ?? [];
}

export function cfbProjectionTeams(): CfbProjectionTeam[] {
  return PROJ.teams ?? [];
}

export function cfbPowerByCode(): Map<string, CfbPowerSotTeam> {
  return new Map(
    cfbPowerTeams().map((row) => [String(row.team || "").toUpperCase(), row]),
  );
}

export function cfbProjectionByCode(): Map<string, CfbProjectionTeam> {
  return new Map(
    cfbProjectionTeams().map((row) => [
      String(row.team || "").toUpperCase(),
      row,
    ]),
  );
}

export function findCfbPowerTeam(code: string): CfbPowerSotTeam | undefined {
  return cfbPowerByCode().get(String(code || "").trim().toUpperCase());
}

export function findCfbProjectionTeam(
  code: string,
): CfbProjectionTeam | undefined {
  return cfbProjectionByCode().get(String(code || "").trim().toUpperCase());
}

export function cfbResearchVersionStrip(): {
  engine_version: string;
  power_version: string;
  n_sims: number;
  as_of: string;
  used_in_spread: false;
  kei: false;
} {
  return {
    engine_version: String(PROJ.engine_version || POWER.engine_version || "—"),
    power_version: String(PROJ.power_version || POWER.power_version || "—"),
    n_sims: Number(PROJ.n_sims ?? 0),
    as_of: String(PROJ.as_of || POWER.power_as_of || "—"),
    used_in_spread: false,
    kei: false,
  };
}

export function projectGameHref(input: {
  team: string;
  next?: CfbPowerSotTeam["next"];
}): string | null {
  const next = input.next;
  if (!next?.opponent) return null;
  if (/^FCS:/i.test(next.opponent) || /^FCS:/i.test(input.team)) return null;
  const home = next.home ? input.team : next.opponent;
  const away = next.home ? next.opponent : input.team;
  const q = new URLSearchParams({
    home,
    away,
    week: String(next.week ?? 0),
  });
  if (next.neutral_site) q.set("neutral", "1");
  return `/pro/cfb/project-game?${q.toString()}`;
}
