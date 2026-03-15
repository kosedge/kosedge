/**
 * Eastern Time (US) date/time helpers for game dates and date-key filtering.
 */

const ET = "America/New_York";

/** Format an ISO timestamp as YYYY-MM-DD in ET (for date-key grouping). */
export function getDateKeyET(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("en-CA", { timeZone: ET, year: "numeric", month: "2-digit", day: "2-digit" }).replace(/\//g, "-");
}

/** Today's date in ET as YYYY-MM-DD. */
export function todayET(): string {
  return new Date().toLocaleDateString("en-CA", { timeZone: ET, year: "numeric", month: "2-digit", day: "2-digit" }).replace(/\//g, "-");
}

/** Format a date key (YYYY-MM-DD) for display, e.g. "Wed, Feb 25". */
export function formatDateKeyET(dateKey: string): string {
  const [y, m, d] = dateKey.split("-").map(Number);
  const date = new Date(y, (m ?? 1) - 1, d ?? 1);
  return date.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" });
}

/** Format game date from ISO (ET), e.g. "2/25". */
export function formatGameDateET(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("en-US", { timeZone: ET, month: "numeric", day: "numeric" });
}

/** Format game time from ISO (ET), e.g. "7:30 PM". */
export function formatGameTimeET(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleTimeString("en-US", {
    timeZone: ET,
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  });
}
