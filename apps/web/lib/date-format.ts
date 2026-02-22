/**
 * Eastern time date/time formatting for game slates.
 */

const ET = "America/New_York";

/** Format ISO commence time as date in ET (e.g. "Mon, Feb 24"). */
export function formatGameDateET(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("en-US", {
    timeZone: ET,
    weekday: "short",
    month: "short",
    day: "numeric",
  });
}

/** Format ISO commence time as time in ET (e.g. "7:00 PM"). */
export function formatGameTimeET(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleTimeString("en-US", {
    timeZone: ET,
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  });
}

/** Get YYYY-MM-DD in ET for an ISO timestamp (for filtering by date). */
export function getDateKeyET(iso: string): string {
  const d = new Date(iso);
  const parts = d.toLocaleDateString("en-CA", { timeZone: ET }).split("-");
  return parts.length === 3 ? parts.join("-") : "";
}

/** Today in ET as YYYY-MM-DD. */
export function todayET(): string {
  const d = new Date();
  return d.toLocaleDateString("en-CA", { timeZone: ET }).replace(/\//g, "-");
}

/** Format a YYYY-MM-DD date key as "Monday, Jan 29" in ET (for dropdown labels). */
export function formatDateKeyET(dateKey: string): string {
  const d = new Date(dateKey + "T12:00:00Z");
  return d.toLocaleDateString("en-US", {
    timeZone: ET,
    weekday: "long",
    month: "short",
    day: "numeric",
  });
}

/** Next N days in ET: { value: YYYY-MM-DD, label: "Monday, Feb 24" }. */
export function nextDaysET(count: number): { value: string; label: string }[] {
  const today = todayET();
  const [y, m, day] = today.split("-").map(Number);
  const options: { value: string; label: string }[] = [];
  for (let i = 0; i < count; i++) {
    const d = new Date(Date.UTC(y, m - 1, day + i, 12, 0, 0));
    const value = d
      .toLocaleDateString("en-CA", { timeZone: ET })
      .replace(/\//g, "-");
    const label = d.toLocaleDateString("en-US", {
      timeZone: ET,
      weekday: "long",
      month: "short",
      day: "numeric",
    });
    options.push({ value, label });
  }
  return options;
}
