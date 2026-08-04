/**
 * Pure helpers for CFB season-engine UI request shaping + display.
 */

export type CfbTeamOption = {
  code: string;
  label: string;
};

export type CfbPowerLadderRow = {
  rank: number;
  team: string;
  power_index: number;
  offense_index?: number;
  defense_index?: number;
  roster_strength?: number;
  early_season_uncertainty?: number;
  conference?: string;
};

export function normalizeTeamCode(raw: string): string {
  return String(raw || "")
    .trim()
    .toUpperCase()
    .replace(/\s+/g, "");
}

export function buildProjectGameBody(input: {
  homeTeam: string;
  awayTeam: string;
  week?: number;
  season?: number;
  neutralSite?: boolean;
  nightGame?: boolean;
  demo?: boolean;
}): {
  home_team: string;
  away_team: string;
  week: number;
  season: number;
  neutral_site: boolean;
  night_game: boolean;
  demo: boolean;
} {
  const home = normalizeTeamCode(input.homeTeam);
  const away = normalizeTeamCode(input.awayTeam);
  if (!home || home.length < 2) {
    throw new Error("homeTeam must be a valid FBS code");
  }
  if (!away || away.length < 2) {
    throw new Error("awayTeam must be a valid FBS code");
  }
  if (home === away) {
    throw new Error("homeTeam and awayTeam must differ");
  }
  const week = Number(input.week ?? 1);
  if (!Number.isFinite(week) || week < 1 || week > 20) {
    throw new Error("week must be between 1 and 20");
  }
  const season = Number(input.season ?? 2026);
  return {
    home_team: home,
    away_team: away,
    week: Math.round(week),
    season: Math.round(season),
    neutral_site: Boolean(input.neutralSite),
    night_game: Boolean(input.nightGame),
    demo: input.demo !== false,
  };
}

export function buildSimulateBody(input: {
  season?: number;
  nSims?: number;
  seed?: number;
  demo?: boolean;
  asOfWeek?: number;
}): {
  season: number;
  n_sims: number;
  seed: number;
  demo: boolean;
  as_of_week: number;
} {
  const nSims = Number(input.nSims ?? 10);
  if (!Number.isFinite(nSims) || nSims < 1 || nSims > 50) {
    throw new Error("nSims must be between 1 and 50 for the web proxy");
  }
  return {
    season: Math.round(Number(input.season ?? 2026)),
    n_sims: Math.round(nSims),
    seed: Math.round(Number(input.seed ?? 2026)),
    demo: input.demo !== false,
    as_of_week: Math.round(Number(input.asOfWeek ?? 1)),
  };
}

export function formatSpread(spreadHome: number | null | undefined): string {
  if (spreadHome == null || !Number.isFinite(spreadHome)) return "—";
  const v = Number(spreadHome);
  if (Math.abs(v) < 0.05) return "PK";
  return v > 0 ? `+${v.toFixed(1)}` : v.toFixed(1);
}

export function formatWinProb(p: number | null | undefined): string {
  if (p == null || !Number.isFinite(p)) return "—";
  return `${(Number(p) * 100).toFixed(1)}%`;
}

export function formatScore(n: number | null | undefined): string {
  if (n == null || !Number.isFinite(n)) return "—";
  return Number(n).toFixed(1);
}

export function formatIndex(n: number | null | undefined, digits = 2): string {
  if (n == null || !Number.isFinite(n)) return "—";
  return Number(n).toFixed(digits);
}

export function teamOptionsFromCodes(
  codes: string[] | undefined,
  fallback: string[] = ["UGA", "ALA", "OSU", "TEX", "MICH", "LSU", "CLEM", "PSU"],
): CfbTeamOption[] {
  const list = (codes && codes.length > 0 ? codes : fallback)
    .map(normalizeTeamCode)
    .filter(Boolean);
  const uniq = Array.from(new Set(list)).sort();
  return uniq.map((code) => ({ code, label: code }));
}

export function parsePowerLadder(raw: unknown): CfbPowerLadderRow[] {
  if (!raw || typeof raw !== "object") return [];
  const block = raw as { top?: unknown };
  const top = Array.isArray(block.top) ? block.top : Array.isArray(raw) ? raw : [];
  const rows: CfbPowerLadderRow[] = [];
  for (const item of top) {
    if (!item || typeof item !== "object") continue;
    const row = item as Record<string, unknown>;
    const team = typeof row.team === "string" ? row.team : "";
    const power =
      typeof row.power_index === "number"
        ? row.power_index
        : typeof row.roster_strength === "number"
          ? row.roster_strength
          : null;
    if (!team || power == null) continue;
    rows.push({
      rank: typeof row.rank === "number" ? row.rank : rows.length + 1,
      team,
      power_index: power,
      offense_index:
        typeof row.offense_index === "number" ? row.offense_index : undefined,
      defense_index:
        typeof row.defense_index === "number" ? row.defense_index : undefined,
      roster_strength:
        typeof row.roster_strength === "number" ? row.roster_strength : undefined,
      early_season_uncertainty:
        typeof row.early_season_uncertainty === "number"
          ? row.early_season_uncertainty
          : undefined,
      conference:
        typeof row.conference === "string" ? row.conference : undefined,
    });
  }
  return rows;
}
