export type NbaFairLineRow = {
  gameId: string;
  gameDate: string | null;
  startTime: string | null;
  homeTeam: string;
  awayTeam: string;
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

export function formatAmericanOdds(value: number | null): string {
  if (value === null || !Number.isFinite(value)) return "—";
  const rounded = Math.round(value);
  return rounded > 0 ? `+${rounded}` : String(rounded);
}

export function formatSpread(value: number | null): string {
  if (value === null || !Number.isFinite(value)) return "—";
  const rounded = Math.round(value * 100) / 100;
  return rounded > 0 ? `+${rounded.toFixed(1)}` : rounded.toFixed(1);
}

export function formatTotal(value: number | null): string {
  if (value === null || !Number.isFinite(value)) return "—";
  return value.toFixed(1);
}

export function formatWinProb(value: number | null): string {
  if (value === null || !Number.isFinite(value)) return "—";
  return `${(value * 100).toFixed(1)}%`;
}

export function formatKickoff(value: string | null): string {
  if (!value) return "TBD";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "TBD";
  return date.toLocaleString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    timeZoneName: "short",
  });
}
