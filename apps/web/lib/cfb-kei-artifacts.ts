/**
 * Frozen CFB KEI (W0/W1) + futures artifacts.
 * Model packs stay research-fair. This file is the published KEI / futures SoT.
 */

import keiPack from "@/lib/data/cfb-kei-w0-w1-2026.json";
import futuresPack from "@/lib/data/cfb-futures-2026.json";

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
  n_fbs_with_kei?: number;
  n_w0_fbs_with_kei?: number;
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

export function findCfbKeiGame(home: string, away: string): CfbKeiGame | undefined {
  const h = String(home || "").toUpperCase();
  const a = String(away || "").toUpperCase();
  return (KEI.games ?? []).find(
    (g) =>
      String(g.home || "").toUpperCase() === h &&
      String(g.away || "").toUpperCase() === a,
  );
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
  const byName = new Map<string, number>();
  for (const g of KEI.games ?? []) {
    if (g.week == null) continue;
    const key = `${String(g.away_name || g.away || "").toLowerCase()} @ ${String(g.home_name || g.home || "").toLowerCase()}`;
    byName.set(key, g.week);
  }
  return rows.map((row) => {
    if (typeof row.week === "number") return row;
    const key = String(row.game || "")
      .toLowerCase()
      .replace(/\s+/g, " ")
      .trim();
    const week = byName.get(key);
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
