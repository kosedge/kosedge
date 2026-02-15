// Sport config - single source of truth for shells and navigation

export type SportKey = "ncaam" | "nba" | "nfl" | "mlb" | "cfb" | "wnba";

export const SPORTS: { key: SportKey; label: string; fullName: string; desc: string }[] = [
  { key: "ncaam", label: "CBB", fullName: "College Basketball", desc: "Daily slate, fair lines, matchup context, execution." },
  { key: "nba", label: "NBA", fullName: "NBA", desc: "Daily slate, fair lines, execution tooling." },
  { key: "nfl", label: "NFL", fullName: "NFL", desc: "Weekly slate, matchup pages, execution." },
  { key: "mlb", label: "MLB", fullName: "MLB", desc: "Daily slate, markets, tracking." },
  { key: "cfb", label: "CFB", fullName: "College Football", desc: "Weekly slate, matchup context, execution." },
  { key: "wnba", label: "WNBA", fullName: "WNBA", desc: "Daily slate, fair lines, matchup context." },
];

export function getSport(key: string) {
  return SPORTS.find((s) => s.key === key) ?? null;
}
