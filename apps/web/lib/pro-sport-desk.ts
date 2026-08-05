import { supportsPropsFantasy, type SportKey } from "@/lib/sports";

export type DeskAccent = "gold" | "green" | "neutral";

export type BettingDeskCard = {
  href: string;
  title: string;
  description: string;
  cta: string;
  accent: DeskAccent;
  status: "active" | "placeholder";
};

export type HubFooterCard = {
  href: string;
  title: string;
  description: string;
  cta: string;
  accent: DeskAccent;
};

export type SportDeskConfig = {
  /** Short path label shown under Betting Desk, e.g. "KEI Lines → Edges → Props" */
  pathLabel: string;
  /** Hero / market-section subtitle describing the desk workflow */
  pathSubtitle: string;
  cards: BettingDeskCard[];
  footerCards: HubFooterCard[];
};

const SHARED_FOOTER = (sportKey: string): HubFooterCard[] => [
  {
    href: `/pro/power-ratings/${sportKey}`,
    title: "Power Ratings",
    description:
      "Team strength, tiering, and historical movement with slate context.",
    cta: "View ratings →",
    accent: "gold",
  },
  {
    href: `/pro/kei-lines/${sportKey}`,
    title: "KEI Lines",
    description:
      "Projected spread/total baselines to benchmark current market prices.",
    cta: "View KEI lines →",
    accent: "neutral",
  },
];

function stubFairLines(sportKey: string, marketNoun: string): BettingDeskCard {
  return {
    href: `/pro/${sportKey}/fair-lines`,
    title: "Fair Lines",
    description: `Model ${marketNoun} reference board — fair prices without pick language. Board shell is live; model join pending.`,
    cta: "Open fair lines →",
    accent: "gold",
    // Navigable sport-specific shell (not a dead Pending tile).
    status: "active",
  };
}

function stubEdges(sportKey: string, edgeHint: string): BettingDeskCard {
  return {
    href: `/pro/${sportKey}/edges`,
    title: "Edges",
    description: edgeHint,
    cta: "Open edges desk →",
    accent: "green",
    status: "active",
  };
}

function stubThirdCard(
  sportKey: string,
  title: string,
  description: string,
  href?: string,
): BettingDeskCard {
  const propsHref = href ?? `/pro/${sportKey}/props`;
  return {
    href: propsHref,
    title,
    description,
    cta: `Open ${title.toLowerCase()} →`,
    accent: "neutral",
    status: "active",
  };
}

const DESK_BY_SPORT: Record<SportKey, SportDeskConfig> = {
  nfl: {
    pathLabel: "KEI Lines → Edges → Props",
    pathSubtitle:
      "Betting desk path: KEI Lines → Edges → Props, then execution quality.",
    cards: [
      {
        href: "/pro/nfl/fair-lines",
        title: "KEI Lines",
        description:
          "Kosedge spreads, totals, and fair moneylines for the slate.",
        cta: "Open KEI Lines →",
        accent: "gold",
        status: "active",
      },
      {
        href: "/pro/nfl/edges",
        title: "Edges",
        description: "Thresholded game + prop edges with side and confidence.",
        cta: "Open edges desk →",
        accent: "green",
        status: "active",
      },
      {
        href: "/pro/nfl/props",
        title: "Props",
        description:
          "Full player prop board — model means, fair prices, market joins.",
        cta: "Open props board →",
        accent: "neutral",
        status: "active",
      },
    ],
    footerCards: [
      // Bottom resource grid: no KEI Lines duplicate (lives in Betting Desk).
      {
        href: "/pro/power-ratings/nfl",
        title: "Power Ratings",
        description:
          "Team strength, offense/defense splits, and weekly movement from the model engine.",
        cta: "View ratings →",
        accent: "gold",
      },
      {
        href: "/pro/nfl/previews",
        title: "Team Previews",
        description:
          "All 32 KosEdge 2026 season previews with angles and win-total guides.",
        cta: "Read previews →",
        accent: "gold",
      },
      {
        href: "/pro/nfl/teams",
        title: "Team Research Hub",
        description:
          "32-team directory with depth, injuries, tendencies, and preview slots.",
        cta: "Open team hub →",
        accent: "neutral",
      },
      {
        href: "/pro/nfl/camp",
        title: "Training Camp Desk",
        description:
          "Beat map, public camp headlines, and KosEdge coverage into kickoff.",
        cta: "Open camp desk →",
        accent: "green",
      },
      {
        href: "/pro/nfl/projections",
        title: "Futures",
        description:
          "Wins, division, conference, and Super Bowl projections from the sim bundle.",
        cta: "Open futures →",
        accent: "gold",
      },
      {
        href: "/wall-chart/nfl-2026",
        title: "2026 Wall Chart",
        description:
          "Interactive + print-friendly 24×18 schedule tracker for the full season.",
        cta: "Open wall chart →",
        accent: "green",
      },
      {
        href: "/pro/nfl/fantasy",
        title: "Fantasy Draft Board",
        description:
          "VOR-ranked draft board across QB/RB/WR/TE/K/DST with scoring toggles.",
        cta: "Open draft board →",
        accent: "gold",
      },
      {
        href: "/pro/nfl/dfs",
        title: "DFS Board",
        description:
          "DraftKings and FanDuel salary, projection, value, and ownership research.",
        cta: "Open DFS →",
        accent: "neutral",
      },
      {
        href: "/pro/nfl/player-previews",
        title: "Player Previews",
        description:
          "Selective star and role-change outlooks with position filters.",
        cta: "Open player previews →",
        accent: "neutral",
      },
      {
        href: "/pro/nfl/awards",
        title: "Awards",
        description:
          "MVP, OPOY, DPOY, Rookie, and Coach races with ranked evidence tables.",
        cta: "View awards →",
        accent: "neutral",
      },
      {
        href: "/pro/model-transparency",
        title: "Model Health",
        description:
          "Transparency, CLV tracking, and performance accountability.",
        cta: "Open model health →",
        accent: "green",
      },
    ],
  },
  mlb: {
    pathLabel: "Fair Lines → Edges → Run Line",
    pathSubtitle:
      "MLB desk path: Fair Lines → Edges → Run Line, with starter/bullpen context into execution.",
    cards: [
      {
        href: "/pro/mlb/fair-lines",
        title: "Fair Lines",
        description:
          "Kosedge moneylines, totals, and run-line cover probs for today’s slate.",
        cta: "Open fair lines →",
        accent: "gold",
        status: "active",
      },
      {
        href: "/pro/mlb/edges",
        title: "Edges",
        description:
          "Today’s ML and total edges with quality score and stake fraction.",
        cta: "Open edges desk →",
        accent: "green",
        status: "active",
      },
      {
        href: "/pro/mlb/fair-lines?focus=run-line",
        title: "Run Line",
        description:
          "Home run-line fair spread and cover probability from the same projection set.",
        cta: "Open run line →",
        accent: "neutral",
        status: "active",
      },
    ],
    footerCards: [
      ...SHARED_FOOTER("mlb"),
      {
        href: "/odds/mlb",
        title: "Compare Odds",
        description:
          "Side-by-side moneylines and totals across books for the MLB slate.",
        cta: "Open odds compare →",
        accent: "gold",
      },
      {
        href: "/edge-board/mlb",
        title: "Public Edge Board",
        description:
          "Best Moneyline + Best O/U vs Our Moneyline / Our O/U; ML edge in prob points (LEAN ≥1.5pp / PLAY ≥3.0pp).",
        cta: "Open edge board →",
        accent: "green",
      },
    ],
  },
  nba: {
    pathLabel: "Fair Lines → Edges → Props",
    pathSubtitle:
      "NBA desk path: Fair Lines → Edges → Props, with availability and pace into execution.",
    cards: [
      stubFairLines("nba", "spread / total / ML"),
      stubEdges(
        "nba",
        "Thresholded game edges once the NBA model board is connected.",
      ),
      stubThirdCard(
        "nba",
        "Props",
        "Player props and alternates staged for launch once feeds clear validation.",
      ),
    ],
    footerCards: [
      ...SHARED_FOOTER("nba"),
      {
        href: "/odds/nba",
        title: "Compare Odds",
        description:
          "Side-by-side spreads and totals across books for the NBA slate.",
        cta: "Open odds compare →",
        accent: "gold",
      },
      {
        href: "/edge-board/nba",
        title: "Public Edge Board",
        description: "Open vs best prices with KEI and directional edge tags.",
        cta: "Open edge board →",
        accent: "green",
      },
    ],
  },
  nhl: {
    pathLabel: "Fair Lines → Edges → Goalie Desk",
    pathSubtitle:
      "NHL desk path: Fair Lines → Edges → Goalie confirmation, then totals execution.",
    cards: [
      stubFairLines("nhl", "moneyline / total"),
      stubEdges(
        "nhl",
        "ML and total edges once the NHL model board is connected.",
      ),
      stubThirdCard(
        "nhl",
        "Goalie Desk",
        "Starter confirmation and total sensitivity for ML and totals research.",
        "/pro/nhl/goalies",
      ),
    ],
    footerCards: [
      ...SHARED_FOOTER("nhl"),
      {
        href: "/odds/nhl",
        title: "Compare Odds",
        description:
          "Side-by-side moneylines and totals across books for the NHL slate.",
        cta: "Open odds compare →",
        accent: "gold",
      },
      {
        href: "/edge-board/nhl",
        title: "Public Edge Board",
        description: "Open vs best prices with KEI and directional edge tags.",
        cta: "Open edge board →",
        accent: "green",
      },
    ],
  },
  wnba: {
    pathLabel: "Fair Lines → Edges → Props",
    pathSubtitle:
      "WNBA desk path: Fair Lines → Edges → Props, with usage and travel into execution.",
    cards: [
      {
        href: "/pro/wnba/fair-lines",
        title: "Fair Lines",
        description:
          "Possession-sim ML / spread / total reference board — research only. Harmonic-mean pace, 40-min scaling.",
        cta: "Open fair lines →",
        accent: "gold",
        status: "active",
      },
      stubEdges(
        "wnba",
        "Thresholded game edges from WNBA fair lines vs live books.",
      ),
      stubThirdCard(
        "wnba",
        "Props",
        "Player props (pts/reb/ast/threes) research board — role-collapse Under refusal; never stake-eligible.",
      ),
    ],
    footerCards: [
      ...SHARED_FOOTER("wnba"),
      {
        href: "/odds/wnba",
        title: "Compare Odds",
        description:
          "Side-by-side spreads and totals across books for the WNBA slate.",
        cta: "Open odds compare →",
        accent: "gold",
      },
      {
        href: "/edge-board/wnba",
        title: "Public Edge Board",
        description: "Open vs best prices with KEI and directional edge tags.",
        cta: "Open edge board →",
        accent: "green",
      },
    ],
  },
  cfb: {
    pathLabel: "Fair Lines → Edges → Tempo",
    pathSubtitle:
      "CFB desk path: Fair Lines → Edges → Tempo signals, then key-number execution.",
    cards: [
      stubFairLines("cfb", "spread / total"),
      stubEdges(
        "cfb",
        "Weekly game edges once the CFB model board is connected.",
      ),
      stubThirdCard(
        "cfb",
        "Tempo Signals",
        "Pace and havoc context for key-number market translation.",
        "/pro/cfb/tempo",
      ),
    ],
    footerCards: [
      ...SHARED_FOOTER("cfb"),
      {
        href: "/odds/cfb",
        title: "Compare Odds",
        description:
          "Side-by-side spreads and totals across books for the CFB slate.",
        cta: "Open odds compare →",
        accent: "gold",
      },
      {
        href: "/edge-board/cfb",
        title: "Public Edge Board",
        description: "Open vs best prices with KEI and directional edge tags.",
        cta: "Open edge board →",
        accent: "green",
      },
    ],
  },
  ncaam: {
    pathLabel: "Fair Lines → Edges → Tempo",
    pathSubtitle:
      "CBB desk path: Fair Lines → Edges → Tempo signals, then variance-aware execution.",
    cards: [
      stubFairLines("ncaam", "spread / total"),
      stubEdges(
        "ncaam",
        "Daily game edges once the CBB model board is connected.",
      ),
      stubThirdCard(
        "ncaam",
        "Tempo Signals",
        "Tempo and variance context for market translation.",
        "/pro/ncaam/tempo",
      ),
    ],
    footerCards: [
      ...SHARED_FOOTER("ncaam"),
      {
        href: "/odds/ncaam",
        title: "Compare Odds",
        description:
          "Side-by-side spreads and totals across books for the CBB slate.",
        cta: "Open odds compare →",
        accent: "gold",
      },
      {
        href: "/edge-board/ncaam",
        title: "Public Edge Board",
        description: "Open vs best prices with KEI and directional edge tags.",
        cta: "Open edge board →",
        accent: "green",
      },
    ],
  },
};

export function getSportDeskConfig(sportKey: string): SportDeskConfig {
  const key = sportKey as SportKey;
  if (key in DESK_BY_SPORT) return DESK_BY_SPORT[key];
  return {
    pathLabel: "Fair Lines → Edges → Markets",
    pathSubtitle:
      "Translate market movement into clear model-versus-price decision support.",
    cards: [
      stubFairLines(sportKey, "spread / total / ML"),
      stubEdges(sportKey, "Game edges pending model board connection."),
      supportsPropsFantasy(sportKey)
        ? stubThirdCard(
            sportKey,
            "Props",
            "Player props pending feed validation.",
          )
        : stubThirdCard(
            sportKey,
            "Markets",
            "Additional market views staged for this league.",
            `/pro/${sportKey}/execution`,
          ),
    ],
    footerCards: SHARED_FOOTER(sportKey),
  };
}

export function deskCardClassName(
  accent: DeskAccent,
  status: "active" | "placeholder",
): string {
  const pending = status === "placeholder" ? " opacity-90" : "";
  if (accent === "gold") {
    return `rounded-2xl border border-kos-gold/25 bg-kos-gold/5 p-5 transition hover:border-kos-gold/45 hover:bg-kos-gold/10${pending}`;
  }
  if (accent === "green") {
    return `rounded-2xl border border-edge-green/30 bg-edge-green/5 p-5 transition hover:border-edge-green/50 hover:bg-edge-green/10${pending}`;
  }
  return `rounded-2xl border border-white/12 bg-black/30 p-5 transition hover:border-kos-gold/40${pending}`;
}

export function footerCardClassName(accent: DeskAccent): string {
  if (accent === "gold") {
    return "rounded-2xl border border-kos-gold/25 bg-kos-gold/5 p-6 transition hover:border-kos-gold/45 hover:bg-kos-gold/10";
  }
  if (accent === "green") {
    return "rounded-2xl border border-edge-green/30 bg-linear-to-br from-edge-green/10 via-black/30 to-black/55 p-6 transition hover:border-edge-green/50 hover:bg-edge-green/10";
  }
  return "rounded-2xl border border-white/12 bg-black/30 p-6 transition hover:border-kos-gold/40";
}

export function footerTitleClassName(accent: DeskAccent): string {
  if (accent === "gold") return "text-xl font-semibold text-kos-gold";
  if (accent === "green") return "text-xl font-semibold text-edge-green";
  return "text-xl font-semibold text-kos-text";
}

export function footerCtaClassName(accent: DeskAccent): string {
  if (accent === "green")
    return "mt-4 inline-block text-sm font-semibold text-edge-green";
  return "mt-4 inline-block text-sm font-semibold text-kos-gold";
}
