// Sport config - single source of truth for shells and navigation
export { generateGameOverview } from "@/lib/game-overview";

export type SportKey = "ncaam" | "nba" | "nfl" | "mlb" | "nhl" | "cfb" | "wnba";

export const SPORTS: { key: SportKey; label: string; fullName: string; desc: string }[] = [
  { key: "ncaam", label: "CBB", fullName: "College Basketball", desc: "Daily slate, fair lines, matchup context, execution." },
  { key: "nba", label: "NBA", fullName: "NBA", desc: "Daily slate, fair lines, execution tooling." },
  { key: "nfl", label: "NFL", fullName: "NFL", desc: "Weekly slate, matchup pages, execution." },
  { key: "mlb", label: "MLB", fullName: "MLB", desc: "Daily slate, markets, tracking." },
  { key: "nhl", label: "NHL", fullName: "NHL", desc: "Daily slate, moneyline and totals, tracking." },
  { key: "cfb", label: "CFB", fullName: "College Football", desc: "Weekly slate, matchup context, execution." },
  { key: "wnba", label: "WNBA", fullName: "WNBA", desc: "Daily slate, fair lines, matchup context." },
];

const KEY_ALIASES: Record<string, SportKey> = {
  cbb: "ncaam",
  ncaam: "ncaam",
  nba: "nba",
  nfl: "nfl",
  mlb: "mlb",
  nhl: "nhl",
  cfb: "cfb",
  wnba: "wnba",
};

export function getSport(key: string) {
  const normalized = KEY_ALIASES[key.toLowerCase()] ?? key;
  return SPORTS.find((s) => s.key === normalized) ?? null;
}
