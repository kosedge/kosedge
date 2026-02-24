// Sport config - single source of truth for shells and navigation

/** Generate 3-paragraph overview (intro, away pros/cons, home pros/cons) for edge board games */
export function generateGameOverview(awayTeam: string, homeTeam: string): string {
  const AWAY_PRO = [
    "Strong perimeter shooting and ball movement.",
    "Elite transition offense; capitalizes on turnovers.",
    "Experienced backcourt; handles pressure well.",
    "Solid defensive rebounding; limits second chances.",
  ];
  const AWAY_CON = [
    "Can struggle against length in the paint.",
    "Road performance has been inconsistent.",
    "Foul trouble has hurt in close games.",
    "Bench scoring has been thin lately.",
  ];
  const HOME_PRO = [
    "Home court advantage; crowd energy matters.",
    "Stout interior defense; protects the rim.",
    "Balanced scoring; multiple options.",
    "Physical in the paint; wins 50-50 balls.",
  ];
  const HOME_CON = [
    "Injuries have limited rotation options.",
    "Turnover rate has crept up recently.",
    "Three-point defense can be exploited.",
    "Slow starts have been an issue.",
  ];
  const hash = (s: string) => {
    let h = 0;
    for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) >>> 0;
    return h;
  };
  const pick = <T,>(arr: T[], seed: number, count: number): T[] => {
    const out: T[] = [];
    const n = arr.length;
    for (let i = 0; i < count; i++) out.push(arr[((seed + i * 17) % n + n) % n]!);
    return out;
  };
  const seed = hash(`${awayTeam}|${homeTeam}`);
  const p1 = `${awayTeam} travels to face ${homeTeam} in a matchup that could swing on a few key factors. Both teams bring distinct strengths and vulnerabilities to the floor.`;
  const p2 = `${awayTeam} — Pros: ${pick(AWAY_PRO, seed, 2).join(" ")} Cons: ${pick(AWAY_CON, seed + 1, 2).join(" ")}`;
  const p3 = `${homeTeam} — Pros: ${pick(HOME_PRO, seed + 2, 2).join(" ")} Cons: ${pick(HOME_CON, seed + 3, 2).join(" ")}`;
  return [p1, p2, p3].join("\n\n");
}

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

export function getSport(key: string) {
  return SPORTS.find((s) => s.key === key) ?? null;
}
