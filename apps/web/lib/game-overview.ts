/**
 * Generate small 3-paragraph overview articles for edge board games.
 * Each overview: intro, away team pros/cons, home team pros/cons.
 */

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

function hash(str: string): number {
  let h = 0;
  for (let i = 0; i < str.length; i++) {
    h = (h * 31 + str.charCodeAt(i)) >>> 0;
  }
  return h;
}

function pick<T>(arr: T[], seed: number, count: number): T[] {
  const out: T[] = [];
  const n = arr.length;
  for (let i = 0; i < count; i++) {
    const idx = (((seed + i * 17) % n) + n) % n;
    out.push(arr[idx]!);
  }
  return out;
}

export function generateGameOverview(
  awayTeam: string,
  homeTeam: string,
): string {
  const seed = hash(`${awayTeam}|${homeTeam}`);
  const p1 = `${awayTeam} travels to face ${homeTeam} in a matchup that could swing on a few key factors. Both teams bring distinct strengths and vulnerabilities to the floor.`;
  const p2 = `${awayTeam} — Pros: ${pick(AWAY_PRO, seed, 2).join(" ")} Cons: ${pick(AWAY_CON, seed + 1, 2).join(" ")}`;
  const p3 = `${homeTeam} — Pros: ${pick(HOME_PRO, seed + 2, 2).join(" ")} Cons: ${pick(HOME_CON, seed + 3, 2).join(" ")}`;
  return [p1, p2, p3].join("\n\n");
}
