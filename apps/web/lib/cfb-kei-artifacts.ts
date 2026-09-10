/**
 * Frozen CFB KEI (W0–W2) + futures artifacts.
 * Model packs stay research-fair. This file is the published KEI / futures SoT.
 * Filename stays cfb-kei-w0-w1-2026.json (product import); pack.weeks includes 2.
 */

import keiPack from "@/lib/data/cfb-kei-w0-w1-2026.json";
import futuresPack from "@/lib/data/cfb-futures-2026.json";
import { cfbGameMatchKeys } from "@/lib/cfb-match-keys";

export type CfbKeiGame = {
  game_id?: string;
  week?: number;
  home?: string;
  away?: string;
  home_name?: string;
  away_name?: string;
  kickoff?: string;
  neutral_site?: boolean;
  fbs_vs_fbs?: boolean;
  fcs_home?: boolean;
  fcs_away?: boolean;
  model_spread_home?: number | null;
  model_total?: number | null;
  model_home_win_prob?: number | null;
  kei?: {
    kei_version?: string;
    used_in_spread?: boolean;
    model_spread_home?: number | null;
    kei_spread_home?: number | null;
    kei_total?: number | null;
    kei_home_win_prob?: number | null;
    tag?: string;
    fcs_opener?: boolean;
    reason?: string;
    drivers?: Array<{ factor?: string; reason?: string; applied?: boolean }>;
  };
};

export type CfbKeiPack = {
  kei_version?: string;
  engine_version?: string;
  as_of?: string;
  weeks?: number[];
  n_fbs_with_kei?: number;
  n_w0_fbs_with_kei?: number;
  n_w2_fbs_with_kei?: number;
  used_in_spread?: boolean;
  model_used_in_spread?: boolean;
  games?: CfbKeiGame[];
};

export type CfbFuturesTeam = {
  team: string;
  conference?: string;
  rank?: number;
  power_index?: number;
  cfp_make_pct?: number;
  natty_pct?: number;
  conf_title_pct?: number | null;
  g5?: boolean;
  power4?: boolean;
};

export type CfbFuturesPack = {
  futures_version?: string;
  engine_version?: string;
  as_of?: string;
  n_sims?: number;
  cfp_field?: number;
  method?: string;
  assumptions?: Record<string, unknown>;
  used_in_spread?: boolean;
  kei?: boolean;
  teams?: CfbFuturesTeam[];
  conference_titles?: Record<
    string,
    Array<{ team: string; conf_title_pct: number; cfp_make_pct: number }>
  >;
  top_natty?: CfbFuturesTeam[];
  top_cfp?: CfbFuturesTeam[];
};

const KEI = keiPack as CfbKeiPack;
const FUTURES = futuresPack as CfbFuturesPack;

export function loadCfbKeiPack(): CfbKeiPack {
  return KEI;
}

export function loadCfbFuturesPack(): CfbFuturesPack {
  return FUTURES;
}

export function cfbKeiGames(week?: number): CfbKeiGame[] {
  const rows = KEI.games ?? [];
  if (week == null) return rows;
  return rows.filter((g) => g.week === week);
}

export function findCfbKeiGame(
  home: string,
  away: string,
  week?: number,
): CfbKeiGame | undefined {
  const h = String(home || "").toUpperCase();
  const a = String(away || "").toUpperCase();
  return (KEI.games ?? []).find((g) => {
    if (String(g.home || "").toUpperCase() !== h) return false;
    if (String(g.away || "").toUpperCase() !== a) return false;
    // Fail closed: requested week must match. Missing W2 ≠ recycle W1.
    if (week != null && g.week !== week) return false;
    return true;
  });
}

export function cfbFuturesByCode(): Map<string, CfbFuturesTeam> {
  return new Map(
    (FUTURES.teams ?? []).map((row) => [
      String(row.team || "").toUpperCase(),
      row,
    ]),
  );
}

export function findCfbFutures(team: string): CfbFuturesTeam | undefined {
  return cfbFuturesByCode().get(String(team || "").trim().toUpperCase());
}

export function stampCfbEdgeBoardWeek<T extends { game?: string; week?: number }>(
  rows: T[],
): T[] {
  const byKey = new Map<string, number>();
  for (const g of KEI.games ?? []) {
    if (g.week == null) continue;
    const label = `${g.away_name || g.away || ""} @ ${g.home_name || g.home || ""}`;
    const abbr = `${g.away || ""} @ ${g.home || ""}`;
    for (const key of [...cfbGameMatchKeys(label), ...cfbGameMatchKeys(abbr)]) {
      byKey.set(key, g.week);
    }
  }
  return rows.map((row) => {
    if (typeof row.week === "number") return row;
    const week = cfbGameMatchKeys(String(row.game || "")).reduce<
      number | undefined
    >((found, key) => found ?? byKey.get(key), undefined);
    return week == null ? row : { ...row, week };
  });
}

export function cfbKeiVersionStrip(): {
  kei_version: string;
  futures_version: string;
  engine_version: string;
  n_sims: number;
  as_of: string;
} {
  return {
    kei_version: String(KEI.kei_version || "cfb-kei-v1.0-2026w0"),
    futures_version: String(FUTURES.futures_version || "cfb-futures-v1-cfp12-2026"),
    engine_version: String(KEI.engine_version || FUTURES.engine_version || "—"),
    n_sims: Number(FUTURES.n_sims ?? 0),
    as_of: String(KEI.as_of || FUTURES.as_of || "—"),
  };
}
