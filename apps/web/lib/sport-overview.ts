/**
 * Shared At-a-Glance + Research Workflow copy for sport Overview pages.
 */

import { getSportDeskConfig } from "@/lib/pro-sport-desk";

export type GlanceItem = {
  href: string;
  title: string;
  body: string;
};

export type WorkflowStep = {
  step: string;
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
      href: "/pro/cfb/model",
      title: "Season Model",
      body: "Hierarchical engine hub — power-style ranks and fidelity honesty.",
    },
    {
      href: "/pro/cfb/project-game",
      title: "Project Game",
      body: "Matchup projections with roster, QB, unit, HFA, and coaching drivers.",
    },
    {
      href: "/pro/cfb/tempo",
      title: "Tempo & Havoc",
      body: "Pace and disruption signals that move totals and spreads.",
    },
    {
      href: "/pro/cfb/teams",
      title: "Conference Lens",
      body: "Team research with conference and scheme context.",
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

export function getSportWorkflow(sportKey: string): {
  label: string;
  steps: WorkflowStep[];
} {
  const desk = getSportDeskConfig(sportKey);
  const cards = desk.cards;
  const steps: WorkflowStep[] = cards.slice(0, 3).map((card, i) => ({
    step: String(i + 1).padStart(2, "0"),
    href: card.href,
    title: card.title,
    body: card.description,
  }));

  // Insert market view as step 2 when we have room / for props sports
  if (sportKey === "nba" || sportKey === "wnba" || sportKey === "nfl") {
    return {
      label: desk.pathLabel,
      steps: [
        {
          step: "01",
          href: `/pro/${sportKey}/fair-lines`,
          title: "KEI Lines",
          body: "Start with model spreads, totals, and fair moneylines.",
        },
        {
          step: "02",
          href: `/odds/${sportKey}`,
          title: "Market View",
          body: "Compare books and locate the best available number.",
        },
        {
          step: "03",
          href: `/pro/${sportKey}/props`,
          title: "Props Research",
          body: "Drill into player markets after the game frame is set.",
        },
      ],
    };
  }

  if (sportKey === "mlb") {
    return {
      label: desk.pathLabel,
      steps: [
        {
          step: "01",
          href: "/pro/mlb/fair-lines",
          title: "Fair Lines",
          body: "ML, totals, and run-line fair values for the slate.",
        },
        {
          step: "02",
          href: "/pro/mlb/edges",
          title: "Edges",
          body: "Thresholded separations with quality scoring.",
        },
        {
          step: "03",
          href: "/pro/mlb/fair-lines?focus=run-line",
          title: "Run Line",
          body: "Cover probabilities from the same projection set.",
        },
      ],
    };
  }

  if (sportKey === "nhl") {
    return {
      label: desk.pathLabel,
      steps: [
        {
          step: "01",
          href: "/pro/nhl/fair-lines",
          title: "Fair Lines",
          body: "Moneylines, totals, and puck-line framing.",
        },
        {
          step: "02",
          href: "/pro/nhl/edges",
          title: "Edges",
          body: "Thresholded ML and total separations.",
        },
        {
          step: "03",
          href: "/pro/nhl/goalies",
          title: "Goalie Desk",
          body: "Confirm starters before locking totals research.",
        },
      ],
    };
  }

  if (sportKey === "ncaam" || sportKey === "cfb") {
    const tempoHref = `/pro/${sportKey}/tempo`;
    return {
      label: desk.pathLabel,
      steps: [
        {
          step: "01",
          href: `/pro/${sportKey}/fair-lines`,
          title: "Fair Lines",
          body: "Model spreads and totals without pick language.",
        },
        {
          step: "02",
          href: `/pro/${sportKey}/edges`,
          title: "Edges",
          body: "Where the model separates from the market.",
        },
        {
          step: "03",
          href: tempoHref,
          title: sportKey === "cfb" ? "Tempo / Havoc" : "Tempo Signals",
          body:
            sportKey === "cfb"
              ? "Pace and havoc context for key-number translation."
              : "Tempo and variance context for totals research.",
        },
      ],
    };
  }

  return { label: desk.pathLabel, steps };
}
