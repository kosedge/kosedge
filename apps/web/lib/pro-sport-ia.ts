import type { LegacyEdgeBoardRow } from "@/components/EdgeBoard";
import { getSportDeskConfig } from "@/lib/pro-sport-desk";
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
    market: "Betting Desk",
    props: "Props & Fantasy Snapshot",
    intel: "League Intel",
  },
};

type SportCopyOverride = Omit<Partial<OverviewContent>, "sectionTitles"> & {
  sectionTitles?: Partial<OverviewContent["sectionTitles"]>;
};

const SPORT_COPY: Record<string, SportCopyOverride> = {
  nfl: {
    heroBadge: "Pro NFL intelligence hub",
    heroSummary:
      "Weekly NFL workflow for the betting desk (KEI Lines → Edges → Props), key-number execution, matchup briefs, and governance checkpoints.",
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
      market: "Betting Desk",
      props: "Props & Fantasy (Data Pending)",
      intel: "League Intel",
    },
  },
  mlb: {
    heroBadge: "Pro MLB intelligence hub",
    heroSummary:
      "MLB premium workflow for the betting desk (Fair Lines → Edges → Run Line), starter and bullpen context, and run-environment-aware matchup briefs.",
    articleToneBadge: "MLB analyst desk",
    sectionTitles: {
      market: "Betting Desk",
      props: "Props Snapshot (Stake Gate Off)",
      intel: "League Intel",
    },
  },
  nhl: {
    heroBadge: "Pro NHL intelligence hub",
    heroSummary:
      "NHL premium workflow for the betting desk (Fair Lines → Edges → Goalie Desk), five-on-five context, and market-to-model execution clarity.",
    articleToneBadge: "NHL analyst desk",
    sectionTitles: {
      market: "Betting Desk",
      intel: "League Intel",
    },
  },
  nba: {
    heroBadge: "Pro NBA intelligence hub",
    heroSummary:
      "NBA premium workflow for the betting desk (Fair Lines → Edges → Props), availability-driven pricing, pace environments, and matchup-level article context.",
    articleToneBadge: "NBA analyst desk",
    sectionTitles: {
      market: "Betting Desk",
      intel: "League Intel",
    },
  },
  wnba: {
    heroBadge: "Pro WNBA intelligence hub",
    heroSummary:
      "WNBA premium workflow for the betting desk (Fair Lines → Edges → Props), usage concentration, travel context, and market-aware matchup briefs.",
    articleToneBadge: "WNBA analyst desk",
    sectionTitles: {
      market: "Betting Desk",
      intel: "League Intel",
    },
  },
  ncaam: {
    heroBadge: "Pro CBB intelligence hub",
    heroSummary:
      "College basketball workflow for the betting desk (Fair Lines → Edges → Tempo), variance context, model edge translation, and disciplined game-to-game execution.",
    articleToneBadge: "CBB analyst desk",
    sectionTitles: {
      market: "Betting Desk",
      props: "Props & Fantasy (Data Pending)",
      intel: "League Intel",
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

  if (sportKey === "nfl") {
    return [
      {
        href: "/pro/nfl/props",
        label: "Player props board",
        hint: "Model mean vs line, fair odds, and confidence — market edges when books join.",
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

  if (sportKey === "mlb") {
    return [
      {
        label: "Player props board",
        hint: "MLB props models exist server-side; play-stake eligibility is gated off until the soft-launch bar clears.",
        status: "placeholder",
        premium: true,
      },
      {
        href: "/pro/props-center",
        label: "Cross-sport props center",
        hint: "Portfolio-style scan across supported pro leagues.",
        status: "active",
      },
    ];
  }

  return [
    {
      href: `${base}/props`,
      label: "Sport props board",
      hint: "Player and team prop views scoped to this sport — board shell live; model feed pending.",
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
    label: "KEI Lines board",
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
    href: "/odds/nfl",
    label: "Compare odds",
    hint: "Side-by-side spreads and totals across all 9 books (best cells highlighted).",
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
    label: "Team research hub",
    hint: "Team cards with writer preview slots, depth/stats/injuries/tendencies intel.",
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

function mlbIntelLinks(base: string): OverviewSectionLink[] {
  return [
    {
      href: "/pro/mlb/fair-lines",
      label: "Fair lines board",
      hint: "ML, totals, and run-line fair values for today’s MLB slate.",
      premium: true,
      status: "active",
    },
    {
      href: "/pro/mlb/edges",
      label: "Edges desk",
      hint: "Today’s ML and total edges with quality score and recommended stake fraction.",
      premium: true,
      status: "active",
    },
    {
      href: "/pro/mlb/fair-lines?focus=run-line",
      label: "Run line board",
      hint: "Home run-line fair spread and cover probability from the active model.",
      premium: true,
      status: "active",
    },
    {
      href: "/odds/mlb",
      label: "Compare odds",
      hint: "Side-by-side moneylines and totals across books.",
      premium: true,
      status: "active",
    },
    {
      href: "/edge-board/mlb",
      label: "Public edge board",
      hint: "Open vs best prices, KEI, and directional edge tags.",
      premium: true,
      status: "active",
    },
    {
      href: `/pro/kei-lines/mlb`,
      label: "KEI projections",
      hint: "Projected baselines to benchmark current market prices.",
      premium: true,
      status: "active",
    },
    {
      href: `${base}/teams`,
      label: "Team research hub",
      hint: "Club directory with park factors, writer preview slots, and handicapping shells.",
      premium: true,
      status: "active",
    },
    {
      label: "Standings & form",
      hint: "Division race and recent form cards pending MLB intel tables.",
      premium: true,
      status: "placeholder",
    },
  ];
}

function genericIntelLinks(
  sportKey: string,
  base: string,
): OverviewSectionLink[] {
  const desk = getSportDeskConfig(sportKey);
  const primary = desk.cards[0];
  const edges = desk.cards[1];

  return [
    {
      href: primary?.href,
      label: primary?.title ?? "Fair lines",
      hint: primary?.description ?? "Model fair-value reference board.",
      premium: true,
      status: primary?.status ?? "placeholder",
    },
    {
      href: edges?.status === "active" ? edges.href : undefined,
      label: edges?.title ?? "Edges desk",
      hint: edges?.description ?? "Thresholded edges pending model board.",
      premium: true,
      status: edges?.status ?? "placeholder",
    },
    {
      href: `/odds/${sportKey}`,
      label: "Compare odds",
      hint: "Side-by-side prices across books for this sport’s slate.",
      premium: true,
      status: "active",
    },
    {
      href: `/edge-board/${sportKey}`,
      label: "Public edge board",
      hint: "Open vs best prices, KEI, and directional edge tags.",
      premium: true,
      status: "active",
    },
    {
      href: `/pro/kei-lines/${sportKey}`,
      label: "KEI projections",
      hint: "Projected spread and total table by matchup.",
      premium: true,
      status: "active",
    },
    {
      href: `${base}/teams`,
      label: "Team research hub",
      hint: "Per-team handicapping shells with writer preview ownership and sport-aware sections.",
      premium: true,
      status: "active",
    },
    {
      label: "League standings",
      hint: "Standings and race context unlock with sport intel tables.",
      premium: true,
      status: "placeholder",
    },
    {
      label: "Injuries / availability",
      hint: "Availability tracker pending sport-level health feed.",
      premium: true,
      status: "placeholder",
    },
  ];
}

function intelLinksForSport(
  sportKey: string,
  base: string,
): OverviewSectionLink[] {
  if (sportKey === "nfl") return NFL_INTEL_LINKS;
  if (sportKey === "mlb") return mlbIntelLinks(base);
  return genericIntelLinks(sportKey, base);
}

function marketLinksForSport({
  sportKey,
  base,
  edgeBoardHref,
}: {
  sportKey: string;
  base: string;
  edgeBoardHref: string;
}): OverviewSectionLink[] {
  const desk = getSportDeskConfig(sportKey);

  const deskLinks: OverviewSectionLink[] = desk.cards.map((card) => ({
    href: card.status === "active" ? card.href : card.href,
    label: card.title,
    hint: card.description,
    premium: true,
    status: card.status,
  }));

  return [
    ...deskLinks,
    {
      href: edgeBoardHref,
      label: "Public edge board",
      hint: "Open vs best prices, KEI, and directional edge tags.",
      premium: true,
      status: "active",
    },
    {
      href: `/pro/kei-lines/${sportKey}`,
      label: "KEI projections",
      hint: "Projected spread and total table by matchup.",
      premium: true,
      status: "active",
    },
    {
      href: `${base}/execution`,
      label: "Execution monitor",
      hint: "Book dispersion, timing windows, and price quality checks.",
      premium: true,
      status: "active",
    },
  ];
}

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
  const desk = getSportDeskConfig(sportKey);
  const slateLabel =
    sportKey === "nfl" || sportKey === "cfb"
      ? "Weekly slate board"
      : "Daily slate board";

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
          href: sportKey === "nfl" ? "/pro/nfl/teams" : `${base}/teams`,
          label: "Team research hub",
          hint: "Per-team handicapping research pages with writer preview ownership.",
          status: "active",
        },
      ],
    },
    {
      title: content.sectionTitles.market,
      subtitle: desk.pathSubtitle,
      links: marketLinksForSport({ sportKey, base, edgeBoardHref }),
    },
    {
      title: content.sectionTitles.props,
      subtitle:
        "Surface player-level opportunities where feeds are launch-ready while preserving risk discipline.",
      links: propsLinks(sportKey, base),
    },
    {
      title: content.sectionTitles.intel ?? "League Intel",
      subtitle:
        sportKey === "nfl"
          ? "Premium team and league context cards for roster quality, health, and competitive positioning."
          : "League context, odds compare, and sport-specific intel surfaces — live where feeds are ready.",
      links: intelLinksForSport(sportKey, base),
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
