/**
 * Shared At-a-Glance copy for sport Overview pages.
 */

import { getSportDeskConfig } from "@/lib/pro-sport-desk";

export type GlanceItem = {
  href: string;
  title: string;
  body: string;
};


const GLANCE: Record<string, GlanceItem[]> = {
  ncaam: [
    {
      href: "/pro/ncaam/fair-lines",
      title: "Model vs Market",
      body: "Fair lines beside open books — where tempo-aware models separate.",
    },
    {
      href: "/pro/ncaam/tempo",
      title: "Tempo & Variance",
      body: "Pace environments and possession volatility that reshape totals.",
    },
    {
      href: "/pro/ncaam/teams",
      title: "Conference Lens",
      body: "Team research with conference context and efficiency baselines.",
    },
    {
      href: "/pro/power-ratings/ncaam",
      title: "Power Ratings",
      body: "Strength tiers for slate scanning and matchup framing.",
    },
  ],
  cfb: [
    {
      href: "/pro/cfb/slate",
      title: "1. Official slate",
      body: "Week 0 / Week 1 ESPN board — open any FBS row in Project Game.",
    },
    {
      href: "/pro/cfb/project-game",
      title: "2. Project Game",
      body: "Research-fair spread, total, WP, and drivers. No KEI.",
    },
    {
      href: "/pro/cfb/projections",
      title: "3. Projections",
      body: "Frozen N=10,000 win totals. CFP omitted. used_in_spread=false.",
    },
    {
      href: "/pro/cfb/teams",
      title: "4. Teams / Power",
      body: "136 FBS rows, conference filter, then Edge Board (markets only).",
    },
  ],
  nba: [
    {
      href: "/pro/nba/fair-lines",
      title: "Model vs Market",
      body: "Spreads, totals, and MLs with pace-aware baselines.",
    },
    {
      href: "/pro/nba/injuries",
      title: "Availability",
      body: "Injury and rest context that reshapes usage and pricing.",
    },
    {
      href: "/pro/nba/props",
      title: "Props Research",
      body: "Player markets after the game frame is set.",
    },
    {
      href: "/pro/nba/teams",
      title: "Team Research",
      body: "Club hubs with pace, rest, and matchup angles.",
    },
  ],
  mlb: [
    {
      href: "/pro/mlb/fair-lines",
      title: "Model vs Market",
      body: "ML, totals, and run-line fair values for today’s slate.",
    },
    {
      href: "/pro/mlb/fair-lines?focus=run-line",
      title: "Run Line",
      body: "Cover probabilities from the same projection set.",
    },
    {
      href: "/pro/mlb/edges",
      title: "SP & Bullpen",
      body: "Edges framed by starter quality and relief leverage.",
    },
    {
      href: "/pro/mlb/teams",
      title: "Park Factors",
      body: "Team hubs with park and pitcher context.",
    },
  ],
  nhl: [
    {
      href: "/pro/nhl/fair-lines",
      title: "Model vs Market",
      body: "Moneylines, totals, and puck-line framing.",
    },
    {
      href: "/pro/nhl/goalies",
      title: "Goalie Desk",
      body: "Starter confirmation sensitivity for totals and ML.",
    },
    {
      href: "/pro/nhl/edges",
      title: "Key Edges",
      body: "Thresholded ML and total separations.",
    },
    {
      href: "/pro/nhl/teams",
      title: "Team Research",
      body: "Club hubs with goalie and five-on-five context.",
    },
  ],
  wnba: [
    {
      href: "/pro/wnba/fair-lines",
      title: "Model vs Market",
      body: "Spreads, totals, and MLs with usage-aware baselines.",
    },
    {
      href: "/pro/wnba/props",
      title: "Props Research",
      body: "Player markets after travel and rest frames are set.",
    },
    {
      href: "/pro/wnba/injuries",
      title: "Availability",
      body: "Injury, rest, and travel context for pricing.",
    },
    {
      href: "/pro/wnba/teams",
      title: "Team Research",
      body: "Club hubs with pace and usage angles.",
    },
  ],
};

export function getSportGlance(sportKey: string): GlanceItem[] {
  if (GLANCE[sportKey]) return GLANCE[sportKey]!;
  const desk = getSportDeskConfig(sportKey);
  return desk.cards.map((c) => ({
    href: c.href,
    title: c.title,
    body: c.description,
  }));
}
