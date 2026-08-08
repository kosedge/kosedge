/** Format ISO date YYYY-MM-DD for display. */
export function formatInsightDate(iso: string): string {
  const d = new Date(`${iso}T12:00:00Z`);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    timeZone: "UTC",
  });
}

export function sportLabel(key: string): string {
  const map: Record<string, string> = {
    ncaam: "CBB",
    nba: "NBA",
    nfl: "NFL",
    mlb: "MLB",
    nhl: "NHL",
    cfb: "CFB",
    wnba: "WNBA",
  };
  return map[key] ?? key.toUpperCase();
}
