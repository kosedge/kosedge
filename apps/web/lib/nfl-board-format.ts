/** Client-safe NFL board formatters (no server-only). */

export function formatAmericanOdds(value: number | null): string {
  if (value === null || !Number.isFinite(value)) return "—";
  const rounded = Math.round(value);
  return rounded > 0 ? `+${rounded}` : String(rounded);
}

export function formatSpread(value: number | null): string {
  if (value === null || !Number.isFinite(value)) return "—";
  const rounded = Math.round(value * 100) / 100;
  return rounded > 0 ? `+${rounded.toFixed(2)}` : rounded.toFixed(2);
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
    timeZone: "America/New_York",
    timeZoneName: "short",
  });
}

export function edgeToneClass(value: number | null): string {
  if (value === null || !Number.isFinite(value)) return "text-kos-text/55";
  if (value >= 0.02) return "text-edge-green";
  if (value <= -0.02) return "text-rose-300";
  return "text-kos-text/70";
}
