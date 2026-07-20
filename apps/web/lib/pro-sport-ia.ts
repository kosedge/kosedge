import type { LegacyEdgeBoardRow } from "@/components/EdgeBoard";
import { supportsPropsFantasy } from "@/lib/sports";

export type OverviewContent = {
  heroBadge: string;
  heroSummary: string;
  boardCta: string;
  slateCta: string;
  articleToneBadge: string;
  articleSubtitle: string;
  articleEmpty: string;
  sectionTitles: {
    market: string;
    props: string;
    intel?: string;
  };
};

export type OverviewSectionLink = {
  href?: string;
  label: string;
  hint: string;
  premium?: boolean;
  status?: "active" | "placeholder";
};

export type OverviewSection = {
  title: string;
  subtitle: string;
  links: OverviewSectionLink[];
};

const DEFAULT_OVERVIEW_CONTENT: OverviewContent = {
  heroBadge: "Pro intelligence hub",
  heroSummary:
    "Premium workflow for slate review, model-vs-market edges, matchup article briefs, and governance health checks.",
  boardCta: "Open live edge board",
  slateCta: "Open current slate",
  articleToneBadge: "Analyst desk",
  articleSubtitle:
    "Matchup briefs grounded in market context, model edge, and execution risk framing.",
  articleEmpty:
    "Article highlights populate as games ingest into the board pipeline. Premium placeholders are shown until feed coverage is complete.",
  sectionTitles: {
    market: "Market Edges & Projections",
    props: "Props & Fantasy Snapshot",
  },
};

type SportCopyOverride = Omit<Partial<OverviewContent>, "sectionTitles"> & {
  sectionTitles?: Partial<OverviewContent["sectionTitles"]>;
};

const SPORT_COPY: Record<string, SportCopyOverride> = {
  nfl: {
    heroBadge: "Pro NFL intelligence hub",
    heroSummary:
      "Weekly NFL workflow for the betting desk (Fair Lines → Edges → Props), key-number execution, matchup briefs, and governance checkpoints.",
    slateCta: "Open weekly slate",
    articleToneBadge: "NFL analyst desk",
    sectionTitles: {
      market: "Betting Desk",
      intel: "Team Intel",
    },
  },
  cfb: {
    heroBadge: "Pro CFB intelligence hub",
    heroSummary:
      "College football workflow for tempo and havoc context, market edge translation, and disciplined execution windows.",
    slateCta: "Open weekly slate",
    articleToneBadge: "CFB analyst desk",
    sectionTitles: {
      market: "Market Edges & Tempo Signals",
      props: "Props & Fantasy (Data Pending)",
    },
  },
  mlb: {
    heroBadge: "Pro MLB intelligence hub",
    heroSummary:
      "MLB premium workflow for starter and bullpen context, market edges, and run-environment-aware matchup briefs.",
    articleToneBadge: "MLB analyst desk",
    sectionTitles: {
      market: "Market Edges & Run Environment",
      props: "Props & Fantasy Snapshot",
    },
  },
  nhl: {
    heroBadge: "Pro NHL intelligence hub",
    heroSummary:
      "NHL premium workflow for goalie confirmation, five-on-five context, and market-to-model execution clarity.",
    articleToneBadge: "NHL analyst desk",
    sectionTitles: {
      market: "Market Edges & Goalie Context",
      props: "Props & Fantasy Snapshot",
    },
  },
  nba: {
    heroBadge: "Pro NBA intelligence hub",
    heroSummary:
      "NBA premium workflow for availability-driven pricing, pace environments, and matchup-level article context.",
    articleToneBadge: "NBA analyst desk",
    sectionTitles: {
      market: "Market Edges & Rotation Signals",
      props: "Props & Fantasy Snapshot",
    },
  },
  wnba: {
    heroBadge: "Pro WNBA intelligence hub",
    heroSummary:
      "WNBA premium workflow for usage concentration, travel context, and market-aware matchup briefs.",
    articleToneBadge: "WNBA analyst desk",
    sectionTitles: {
      market: "Market Edges & Rotation Signals",
      props: "Props & Fantasy Snapshot",
    },
  },
  ncaam: {
    heroBadge: "Pro CBB intelligence hub",
    heroSummary:
      "College basketball workflow for tempo and variance context, model edge translation, and disciplined game-to-game execution.",
    articleToneBadge: "CBB analyst desk",
    sectionTitles: {
      market: "Market Edges & Tempo Signals",
      props: "Props & Fantasy (Data Pending)",
    },
  },
};

function sportCopy(sportKey: string, sportName: string): OverviewContent {
  const copy = SPORT_COPY[sportKey] ?? {};
  return {
    ...DEFAULT_OVERVIEW_CONTENT,
    heroBadge: copy.heroBadge ?? `Pro ${sportName} intelligence hub`,
    articleToneBadge: copy.articleToneBadge ?? `${sportName} analyst tone`,
    ...copy,
    sectionTitles: {
      ...DEFAULT_OVERVIEW_CONTENT.sectionTitles,
      ...(copy.sectionTitles ?? {}),
    },
  };
}

function propsLinks(sportKey: string, base: string): OverviewSectionLink[] {
  if (!supportsPropsFantasy(sportKey)) {
    return [
      {
        label: "Player props board",
        hint: "Data pending for this league in soft launch. Sport-level props unlock after feed validation.",
        status: "placeholder",
        premium: true,
      },
      {
        label: "Fantasy projections",
        hint: "Projection cards are staged for future rollout once player data reaches launch quality.",
        status: "placeholder",
      },
    ];
  }

  return [
    {
      href: sportKey === "nfl" ? "/pro/nfl/props" : `${base}/props`,
      label: sportKey === "nfl" ? "Player props board" : "Sport props board",
      hint:
        sportKey === "nfl"
          ? "Model mean vs line, fair odds, and confidence — market edges when books join."
          : "Player and team prop views scoped to this sport.",
      premium: true,
      status: "active",
    },
    {
      href: "/pro/props-center",
      label: "Cross-sport props center",
      hint: "Portfolio-style scan across supported pro leagues.",
      status: "active",
    },
  ];
}

const NFL_INTEL_LINKS: OverviewSectionLink[] = [
  {
    href: "/pro/nfl/projections",
    label: "Projections hub",
    hint: "Team wins/futures plus player fantasy totals in one betting view.",
    premium: true,
    status: "active",
  },
  {
    href: "/pro/nfl/fair-lines",
    label: "Fair lines board",
    hint: "Kosedge spreads, totals, and fair moneylines for the upcoming slate.",
    premium: true,
    status: "active",
  },
  {
    href: "/pro/nfl/edges",
    label: "Edges desk",
    hint: "Actionable game + prop edges that clear Kosedge vs Vegas thresholds.",
    premium: true,
    status: "active",
  },
  {
    href: "/pro/nfl/props",
    label: "Props board",
    hint: "Player prop model means, fair prices, and confidence by market.",
    premium: true,
    status: "active",
  },
  {
    href: "/pro/nfl/fantasy",
    label: "Fantasy draft board",
    hint: "Full VOR-ranked draft board across QB/RB/WR/TE/K/DST with tiers and scoring toggles.",
    premium: true,
    status: "active",
  },
  {
    href: "/pro/nfl/awards",
    label: "MVP & OPOY race",
    hint: "Real projected award contenders with the supporting team + stat evidence behind each rank.",
    premium: true,
    status: "active",
  },
  {
    href: "/wall-chart/nfl-2026",
    label: "2026 NFL wall chart",
    hint: "Printable 24×18 schedule tracker for laminated wet-erase use.",
    premium: true,
    status: "active",
  },
  {
    href: "/pro/nfl/teams",
    label: "Team intel hub",
    hint: "Team cards, filters, and direct jump to depth/stats/injuries/tendencies.",
    premium: true,
    status: "active",
  },
  {
    href: "/pro/nfl/stats",
    label: "League stats",
    hint: "Weekly league-level production and situational context.",
    premium: true,
    status: "active",
  },
  {
    href: "/pro/nfl/standings",
    label: "League standings",
    hint: "Division and conference race context with tiebreak outlook.",
    premium: true,
    status: "active",
  },
  {
    href: "/pro/nfl/depth-charts",
    label: "Depth charts",
    hint: "Role hierarchy and rotational snapshots by position group.",
    premium: true,
    status: "active",
  },
  {
    href: "/pro/nfl/injuries",
    label: "Injuries",
    hint: "Availability, return windows, and practice progression tracker.",
    premium: true,
    status: "active",
  },
];

export function buildSportOverviewContent(
  sportKey: string,
  sportName: string,
): OverviewContent {
  return sportCopy(sportKey, sportName);
}

export function buildSportOverviewSections({
  sportKey,
  base,
  edgeBoardHref,
  content,
}: {
  sportKey: string;
  base: string;
  edgeBoardHref: string;
  content: OverviewContent;
}): OverviewSection[] {
  const slateLabel =
    sportKey === "nfl" || sportKey === "cfb" ? "Weekly slate board" : "Daily slate board";

  const sections: OverviewSection[] = [
    {
      title: "Weekly Slate",
      subtitle:
        "Move from macro board context into matchup-level detail and team baselines.",
      links: [
        {
          href: `${base}/slate/today`,
          label: slateLabel,
          hint: "Collapsed matchup cards with model reference context.",
          premium: true,
          status: "active",
        },
        {
          href: `${base}/teams`,
          label: "Team baseline hub",
          hint: "Current form, ratings, and opponent context by team.",
          status: "active",
        },
      ],
    },
    {
      title: content.sectionTitles.market,
      subtitle:
        sportKey === "nfl"
          ? "Betting desk path: Fair Lines → Edges → Props, then execution quality."
          : "Translate market movement into clear model-versus-price decision support.",
      links:
        sportKey === "nfl"
          ? [
              {
                href: "/pro/nfl/fair-lines",
                label: "Fair lines",
                hint: "Kosedge-made spreads, totals, and fair moneylines for the upcoming slate.",
                premium: true,
                status: "active" as const,
              },
              {
                href: "/pro/nfl/edges",
                label: "Edges",
                hint: "Thresholded game + prop edges ready for the desk.",
                premium: true,
                status: "active" as const,
              },
              {
                href: "/pro/nfl/props",
                label: "Props",
                hint: "Full prop board with model means, fair prices, and market joins.",
                premium: true,
                status: "active" as const,
              },
              {
                href: edgeBoardHref,
                label: "Public edge board",
                hint: "Open vs best prices, KEI, and directional edge tags.",
                premium: true,
                status: "active" as const,
              },
              {
                href: `/pro/kei-lines/${sportKey}`,
                label: "KEI projections",
                hint: "Projected spread and total table by matchup.",
                premium: true,
                status: "active" as const,
              },
              {
                href: `${base}/execution`,
                label: "Execution monitor",
                hint: "Book dispersion, timing windows, and price quality checks.",
                premium: true,
                status: "active" as const,
              },
            ]
          : [
              {
                href: edgeBoardHref,
                label: "Edge board",
                hint: "Open vs best prices, KEI, and directional edge tags.",
                premium: true,
                status: "active" as const,
              },
              {
                href: `${base}/fair-lines`,
                label: "Fair lines",
                hint: "Neutral model fair-value reference without pick language.",
                premium: true,
                status: "placeholder" as const,
              },
              {
                href: `/pro/kei-lines/${sportKey}`,
                label: "KEI projections",
                hint: "Projected spread and total table by matchup.",
                premium: true,
                status: "active" as const,
              },
              {
                href: `${base}/execution`,
                label: "Execution monitor",
                hint: "Book dispersion, timing windows, and price quality checks.",
                premium: true,
                status: "active" as const,
              },
            ],
    },
    {
      title: content.sectionTitles.props,
      subtitle:
        "Surface player-level opportunities where feeds are launch-ready while preserving risk discipline.",
      links: propsLinks(sportKey, base),
    },
    {
      title: "Model & Governance Health",
      subtitle:
        "Stay outcome-neutral with process quality, CLV, and calibration visibility.",
      links: [
        {
          href: "/pro/model-transparency",
          label: "Model transparency",
          hint: "Model vs open/close and edge capture accountability.",
          premium: true,
          status: "active",
        },
        {
          href: `${base}/tracking`,
          label: "Sport tracking",
          hint: "CLV and post-close quality review pipeline.",
          premium: true,
          status: "active",
        },
        {
          href: "/pro/clv-tracker",
          label: "Global CLV tracker",
          hint: "Cross-market close-line value distribution monitor.",
          status: "active",
        },
      ],
    },
  ];

  if (sportKey === "nfl") {
    sections.splice(3, 0, {
      title: content.sectionTitles.intel ?? "Team Intel",
      subtitle:
        "Premium team and league context cards for roster quality, health, and competitive positioning.",
      links: NFL_INTEL_LINKS,
    });
  }

  return sections;
}

function normalizedLabel(value: string | undefined): string {
  return (value ?? "").trim().toLowerCase();
}

export function hasArticleData(row: LegacyEdgeBoardRow): boolean {
  const bestLine = normalizedLabel(row.bestLine?.top?.label);
  const bestOu = normalizedLabel(row.bestOU?.top?.label);
  const away = normalizedLabel(row.teamA?.name);
  const home = normalizedLabel(row.teamB?.name);

  if (!away || !home) return false;
  if (!bestLine || bestLine === "—" || bestLine === "coming soon") return false;
  if (!bestOu || bestOu === "—" || bestOu === "coming soon") return false;
  return true;
}
