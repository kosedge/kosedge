/**
 * Uniform Edge Board Stat Drop — always 8 slots, always rendered.
 * Missing values → em dash. Never collapse the section. Never fake zeros.
 */

import {
  isNeutralSite,
  siteLabel,
  type MatchupOverviewContext,
} from "@/lib/edge-board-matchup-overview";

export type StatDropSlot = {
  key: string;
  label: string;
  /** Primary scannable value (numbers first). */
  value: string;
  /** Optional secondary line (away · home). */
  detail?: string;
  /** Highlight meaningful gaps only. */
  highlight?: boolean;
};

export type StatDrop = {
  slots: StatDropSlot[];
  siteLabel: string;
  sportKey: string;
};

const EM = "—";

function fmtSigned(n: number | null | undefined, digits = 1): string {
  if (n == null || !Number.isFinite(n)) return EM;
  const r = Number(n.toFixed(digits));
  if (Object.is(r, -0) || r === 0) return "0";
  return r > 0 ? `+${r}` : String(r);
}

function fmtNum(n: number | null | undefined, digits = 1): string {
  if (n == null || !Number.isFinite(n)) return EM;
  return n.toFixed(digits);
}

function fmtPct(p: number | null | undefined): string {
  if (p == null || !Number.isFinite(p)) return EM;
  return `${(p * 100).toFixed(0)}%`;
}

function shortName(name: string): string {
  const parts = String(name || "")
    .trim()
    .split(/\s+/)
    .filter(Boolean);
  if (parts.length === 0) return EM;
  return parts[parts.length - 1]!;
}

/** NFL (and football-like) slot labels. */
const NFL_LABELS = [
  "Power (KEI)",
  "Spread / KEI",
  "Total / KEI",
  "Implied WP",
  "HFA / site",
  "Rest",
  "Pace / plays",
  "Units to watch",
] as const;

/** MLB analogs. */
const MLB_LABELS = [
  "Power (KEI)",
  "Run line / KEI",
  "Total / KEI",
  "Implied WP",
  "Park / site",
  "Rest",
  "Starter",
  "Bullpen tag",
] as const;

function labelsForSport(sportKey: string): readonly string[] {
  const s = String(sportKey).toLowerCase();
  if (s === "mlb") return MLB_LABELS;
  return NFL_LABELS;
}

/**
 * Default NFL HFA when model does not supply a per-game figure.
 * Neutral → 0. Partial reduced HFA only when explicitly provided.
 */
export const NFL_DEFAULT_HFA_POINTS = 2.0;
export const POWER_DELTA_HIGHLIGHT = 3.0;

export type StatDropContext = MatchupOverviewContext & {
  /** Optional projected plays / pace proxy. */
  projectedPlays?: number | null;
  /** Optional park factor (MLB). */
  parkFactor?: number | null;
  /** Optional starter / bullpen tags (MLB). */
  awayStarterTag?: string | null;
  homeStarterTag?: string | null;
  awayBullpenTag?: string | null;
  homeBullpenTag?: string | null;
};

export function resolveHfaPoints(ctx: StatDropContext): number | null {
  if (isNeutralSite(ctx)) {
    if (ctx.hfaPoints != null && Number.isFinite(ctx.hfaPoints)) {
      return ctx.hfaPoints;
    }
    return 0;
  }
  if (ctx.hfaPoints != null && Number.isFinite(ctx.hfaPoints)) {
    return ctx.hfaPoints;
  }
  const sport = String(ctx.sportKey).toLowerCase();
  if (sport === "nfl" || sport === "cfb") return NFL_DEFAULT_HFA_POINTS;
  if (sport === "nba" || sport === "ncaam" || sport === "wnba") return 3.0;
  if (sport === "mlb") return null; // park factor slot instead
  return null;
}

export function buildStatDrop(ctx: StatDropContext): StatDrop {
  const sport = String(ctx.sportKey).toLowerCase();
  const labels = labelsForSport(sport);
  const neutral = isNeutralSite(ctx);
  const site = siteLabel(ctx);
  const hfa = resolveHfaPoints(ctx);

  const keiHome = ctx.keiSpreadHome ?? null;
  const mktAway = ctx.marketSpreadAway ?? null;
  const marketHome =
    mktAway != null && Number.isFinite(mktAway) ? -mktAway : null;

  // Power: KEI home-relative rating gap (negative KEI = home stronger).
  const powerDelta =
    keiHome != null && Number.isFinite(keiHome) ? Math.abs(keiHome) : null;
  const powerValue =
    keiHome == null
      ? EM
      : keiHome === 0
        ? "Even"
        : keiHome < 0
          ? `${shortName(ctx.homeTeam)} −${powerDelta!.toFixed(1)}`
          : `${shortName(ctx.awayTeam)} −${powerDelta!.toFixed(1)}`;
  const powerHighlight =
    powerDelta != null && powerDelta >= POWER_DELTA_HIGHLIGHT;

  const spreadGap =
    keiHome != null && marketHome != null
      ? Math.abs(keiHome - marketHome)
      : (ctx.edgeLineNum ?? null);
  const totalGap =
    ctx.keiTotal != null && ctx.marketTotal != null
      ? Math.abs(ctx.keiTotal - ctx.marketTotal)
      : (ctx.edgeOUNum ?? null);

  const restH = ctx.restDaysHome;
  const restA = ctx.restDaysAway;
  const restHighlight =
    restH != null && restA != null && Math.abs(restH - restA) >= 2;

  const slots: StatDropSlot[] = [
    {
      key: "power",
      label: labels[0]!,
      value: powerValue,
      detail:
        keiHome != null
          ? `${shortName(ctx.awayTeam)} ${fmtSigned(-keiHome)} · ${shortName(ctx.homeTeam)} ${fmtSigned(keiHome)}`
          : undefined,
      highlight: powerHighlight,
    },
    {
      key: "spread",
      label: labels[1]!,
      value:
        marketHome != null || keiHome != null
          ? `${fmtSigned(marketHome)} / ${fmtSigned(keiHome)}`
          : EM,
      detail: spreadGap != null ? `gap ${spreadGap.toFixed(1)}` : undefined,
      highlight: spreadGap != null && spreadGap >= 2.0,
    },
    {
      key: "total",
      label: labels[2]!,
      value:
        ctx.marketTotal != null || ctx.keiTotal != null
          ? `${fmtNum(ctx.marketTotal)} / ${fmtNum(ctx.keiTotal)}`
          : EM,
      detail: totalGap != null ? `gap ${totalGap.toFixed(1)}` : undefined,
      highlight: totalGap != null && totalGap >= 2.0,
    },
    {
      key: "wp",
      label: labels[3]!,
      value:
        ctx.awayWinProb != null || ctx.homeWinProb != null
          ? `${fmtPct(ctx.awayWinProb)} · ${fmtPct(ctx.homeWinProb)}`
          : EM,
      detail: `${shortName(ctx.awayTeam)} · ${shortName(ctx.homeTeam)}`,
      highlight:
        ctx.homeWinProb != null &&
        ctx.awayWinProb != null &&
        Math.abs(ctx.homeWinProb - ctx.awayWinProb) >= 0.12,
    },
    {
      key: "site",
      label: labels[4]!,
      value:
        sport === "mlb"
          ? ctx.parkFactor != null
            ? `PF ${ctx.parkFactor.toFixed(2)}`
            : site
          : neutral
            ? `${site}${hfa != null ? ` · HFA ${fmtNum(hfa, 1)}` : ""}`
            : `Home · HFA ${hfa != null ? fmtNum(hfa, 1) : EM}`,
      detail: neutral ? "reduced / zero HFA" : undefined,
      highlight: neutral,
    },
    {
      key: "rest",
      label: labels[5]!,
      value:
        restA != null || restH != null
          ? `${restA != null ? `${restA}d` : EM} · ${restH != null ? `${restH}d` : EM}`
          : EM,
      detail: `${shortName(ctx.awayTeam)} · ${shortName(ctx.homeTeam)}`,
      highlight: restHighlight,
    },
    {
      key: "pace",
      label: labels[6]!,
      value:
        sport === "mlb"
          ? ctx.awayStarterTag || ctx.homeStarterTag
            ? `${ctx.awayStarterTag ?? EM} · ${ctx.homeStarterTag ?? EM}`
            : EM
          : ctx.projectedPlays != null
            ? `${Math.round(ctx.projectedPlays)} plays`
            : EM,
      detail: sport === "mlb" ? "starter quality" : undefined,
    },
    {
      key: "units",
      label: labels[7]!,
      value:
        sport === "mlb"
          ? ctx.awayBullpenTag || ctx.homeBullpenTag
            ? `${ctx.awayBullpenTag ?? EM} · ${ctx.homeBullpenTag ?? EM}`
            : EM
          : ctx.awayUnitTag || ctx.homeUnitTag
            ? `${ctx.awayUnitTag ?? EM} · ${ctx.homeUnitTag ?? EM}`
            : EM,
      detail: `${shortName(ctx.awayTeam)} · ${shortName(ctx.homeTeam)}`,
    },
  ];

  // Guarantee exactly 8 slots with labels even if somehow short.
  while (slots.length < 8) {
    slots.push({
      key: `pad-${slots.length}`,
      label: labels[slots.length] ?? "—",
      value: EM,
    });
  }

  return {
    slots: slots.slice(0, 8),
    siteLabel: site,
    sportKey: sport,
  };
}
