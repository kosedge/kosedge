// Sport config - single source of truth for shells and navigation

/** Generate 3-paragraph overview (intro, away pros/cons, home pros/cons) for edge board games */
export function generateGameOverview(
  awayTeam: string,
  homeTeam: string,
): string {
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
  const hash = (s: string) => {
    let h = 0;
    for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) >>> 0;
    return h;
  };
  const pick = <T>(arr: T[], seed: number, count: number): T[] => {
    const out: T[] = [];
    const n = arr.length;
    for (let i = 0; i < count; i++)
      out.push(arr[(((seed + i * 17) % n) + n) % n]!);
    return out;
  };
  const seed = hash(`${awayTeam}|${homeTeam}`);
  const p1 = `${awayTeam} travels to face ${homeTeam} in a matchup likely to turn on a few high-leverage variables. Both teams enter with clear strengths and controllable vulnerabilities.`;
  const p2 = `${awayTeam} — Pros: ${pick(AWAY_PRO, seed, 2).join(" ")} Cons: ${pick(AWAY_CON, seed + 1, 2).join(" ")}`;
  const p3 = `${homeTeam} — Pros: ${pick(HOME_PRO, seed + 2, 2).join(" ")} Cons: ${pick(HOME_CON, seed + 3, 2).join(" ")}`;
  return [p1, p2, p3].join("\n\n");
}

export type SportKey = "ncaam" | "nba" | "nfl" | "mlb" | "nhl" | "cfb" | "wnba";

export type SportTier = "pro" | "college";

export const SPORTS: {
  key: SportKey;
  label: string;
  fullName: string;
  desc: string;
  tier: SportTier;
  supportsPropsFantasy: boolean;
}[] = [
  {
    key: "ncaam",
    label: "CBB",
    fullName: "College Basketball",
    desc: "Daily slate, fair lines, matchup context, execution.",
    tier: "college",
    supportsPropsFantasy: false,
  },
  {
    key: "nba",
    label: "NBA",
    fullName: "NBA",
    desc: "Daily slate, fair lines, execution tooling.",
    tier: "pro",
    supportsPropsFantasy: true,
  },
  {
    key: "nfl",
    label: "NFL",
    fullName: "NFL",
    desc: "Weekly slate, matchup pages, execution.",
    tier: "pro",
    supportsPropsFantasy: true,
  },
  {
    key: "mlb",
    label: "MLB",
    fullName: "MLB",
    desc: "Daily slate, markets, tracking.",
    tier: "pro",
    supportsPropsFantasy: true,
  },
  {
    key: "nhl",
    label: "NHL",
    fullName: "NHL",
    desc: "Daily slate, moneyline and totals, tracking.",
    tier: "pro",
    supportsPropsFantasy: true,
  },
  {
    key: "cfb",
    label: "CFB",
    fullName: "College Football",
    desc: "Weekly slate, matchup context, execution.",
    tier: "college",
    supportsPropsFantasy: false,
  },
  {
    key: "wnba",
    label: "WNBA",
    fullName: "WNBA",
    desc: "Daily slate, fair lines, matchup context.",
    tier: "pro",
    supportsPropsFantasy: true,
  },
];

export function getSport(key: string) {
  return SPORTS.find((s) => s.key === key) ?? null;
}

export function isProSport(key: string): boolean {
  return getSport(key)?.tier === "pro";
}

export function supportsPropsFantasy(key: string): boolean {
  return getSport(key)?.supportsPropsFantasy ?? false;
}
