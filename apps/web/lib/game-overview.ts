/**
 * Generate small 3-paragraph overview articles for edge board games.
 * Each overview: intro, away team pros/cons, home team pros/cons.
 */

const AWAY_PRO = [
  "Strong recent efficiency trend in core game-script situations.",
  "Disciplined execution in high-leverage possessions and late phases.",
  "Reliable unit cohesion with clear role allocation.",
  "Consistent control of possession-quality and field-position swings.",
];

const AWAY_CON = [
  "Road profile has shown more volatility than home baseline.",
  "Depth stress can appear when primary contributors are limited.",
  "Recent turnover and penalty profile has spiked in pressure windows.",
  "Late-sequence execution has been uneven in one-score scenarios.",
];

const HOME_PRO = [
  "Home environment has produced stronger baseline execution.",
  "Balanced production profile across primary and secondary units.",
  "Effective control of tempo and opponent rhythm disruption.",
  "Strong conversion rate in high-leverage scoring windows.",
];

const HOME_CON = [
  "Availability uncertainty can tighten rotation flexibility.",
  "Possession-management consistency has dipped in recent samples.",
  "Coverage and matchup adaptation has shown occasional leakage.",
  "Early-phase starts can trail expected baseline output.",
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
  const p1 = `${awayTeam} travels to face ${homeTeam} in a matchup likely to turn on a few high-leverage variables. Both teams enter with clear strengths and controllable vulnerabilities.`;
  const p2 = `${awayTeam} — Pros: ${pick(AWAY_PRO, seed, 2).join(" ")} Cons: ${pick(AWAY_CON, seed + 1, 2).join(" ")}`;
  const p3 = `${homeTeam} — Pros: ${pick(HOME_PRO, seed + 2, 2).join(" ")} Cons: ${pick(HOME_CON, seed + 3, 2).join(" ")}`;
  return [p1, p2, p3].join("\n\n");
}
