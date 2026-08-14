import "server-only";
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";

const POWER_REL =
  "services/model-service/src/services/cfb_season_engine/data/cfb_power_sot_2026.json";
const PROJ_REL =
  "services/model-service/src/services/cfb_season_engine/data/cfb_season_projections_2026.json";

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
  win_tables_final?: boolean;
  cfp_make?: unknown;
  natty?: unknown;
  teams?: CfbProjectionTeam[];
};

function findRepoRoot(): string | null {
  let current = process.cwd();
  for (let depth = 0; depth < 8; depth += 1) {
    if (existsSync(path.join(current, POWER_REL))) return current;
    if (existsSync(path.join(current, "data", "ops"))) {
      if (existsSync(path.join(current, POWER_REL))) return current;
    }
    const parent = path.dirname(current);
    if (parent === current) break;
    current = parent;
  }
  return null;
}

function readJson(rel: string): Record<string, unknown> | null {
  const root = findRepoRoot();
  const candidates = [
    root ? path.join(root, rel) : "",
    path.join(process.cwd(), rel),
    path.join(process.cwd(), "..", "..", rel),
  ].filter(Boolean);
  for (const file of candidates) {
    if (!existsSync(file)) continue;
    try {
      return JSON.parse(readFileSync(file, "utf8")) as Record<string, unknown>;
    } catch {
      return null;
    }
  }
  return null;
}

export function loadCfbPowerSot(): CfbPowerSotPack | null {
  const raw = readJson(POWER_REL);
  return raw ? (raw as CfbPowerSotPack) : null;
}

export function loadCfbSeasonProjections(): CfbProjectionPack | null {
  const raw = readJson(PROJ_REL);
  return raw ? (raw as CfbProjectionPack) : null;
}
