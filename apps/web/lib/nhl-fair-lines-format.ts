/**
 * NHL fair-lines format helpers (Chapter 4 team KEI).
 */

export type NhlFairLineRow = {
  gameId: string;
  gameDate: string | null;
  startTime: string | null;
  homeTeam: string;
  awayTeam: string;
  homeAbbr?: string | null;
  awayAbbr?: string | null;
  homeWinProb: number | null;
  fairHomeMl: number | null;
  fairAwayMl: number | null;
  totalMean: number | null;
  fairTotal: number | null;
  fairSpreadHome: number | null;
  homeCoverProb: number | null;
  marginMean: number | null;
  projectedAt: string | null;
  modelVersion: string;
  workerBuildId: string | null;
};

export function formatSpread(n: number | null | undefined): string {
  if (n == null || !Number.isFinite(n)) return "—";
  const v = Number(n);
  if (v > 0) return `+${v.toFixed(1)}`;
  return v.toFixed(1);
}

export function formatTotal(n: number | null | undefined): string {
  if (n == null || !Number.isFinite(n)) return "—";
  return Number(n).toFixed(1);
}

export function formatWinProb(n: number | null | undefined): string {
  if (n == null || !Number.isFinite(n)) return "—";
  return `${(Number(n) * 100).toFixed(1)}%`;
}

export function formatKickoff(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString("en-US", {
      timeZone: "America/New_York",
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  } catch {
    return String(iso);
  }
}

export function formatAmericanOdds(n: number | null | undefined): string {
  if (n == null || !Number.isFinite(n) || n === 0) return "—";
  const v = Math.round(Number(n));
  return v > 0 ? `+${v}` : String(v);
}
