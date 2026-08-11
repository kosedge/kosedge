/**
 * Shared multi-sport Pro navigation — research desk IA.
 * Tagline: Built on Data, Driven by Edge.
 *
 * NFL keeps its expanded tool set (Wall Chart, Fantasy, DFS, Awards, etc.).
 * Other sports get the shared foundation plus sport-specific desks only.
 */

import type { SportKey } from "@/lib/sports";
import { getSport, supportsPropsFantasy } from "@/lib/sports";

export type SportNavItem = {
  href: string;
  label: string;
  primary?: boolean;
  /** Green glow emphasis — Edge Board primary CTA in subnav. */
  emphasis?: "green";
};

export const SPORT_TAGLINE = "Built on Data, Driven by Edge";
export const SPORT_DESK_SUBTITLE = "Pro research desk";

type SportNavConfig = {
  primary: SportNavItem[];
  tools: SportNavItem[];
  slateLabel: string;
};

function sharedTools(sport: SportKey): SportNavItem[] {
  return [
    { href: `/odds/${sport}`, label: "Compare Odds" },
    { href: `/pro/${sport}/execution`, label: "Execution Monitor" },
    { href: `/pro/kei-lines/${sport}`, label: "KEI Projections" },
    { href: `/pro/${sport}/tracking`, label: "Sport Tracking" },
    { href: "/pro/model-transparency", label: "Model Health" },
    { href: "/pro/clv-tracker", label: "CLV Tracker" },
  ];
}

function corePrimary(
  sport: SportKey,
  opts: {
    slateLabel: string;
    /** Extra desk item after Edges (Tempo, Run Line, Goalie, Props, etc.) */
    deskExtras?: SportNavItem[];
  },
): SportNavItem[] {
  return [
    { href: `/pro/${sport}/overview`, label: "Overview", primary: true },
    {
      href: `/edge-board/${sport}`,
      label: "Edge Board",
      primary: true,
      emphasis: "green",
    },
    {
      href: `/pro/${sport}/slate/today`,
      label: opts.slateLabel,
      primary: true,
    },
    { href: `/pro/${sport}/fair-lines`, label: "KEI Lines" },
    {
      href: sport === "mlb" ? "/pro/mlb/edges" : `/pro/${sport}/edges`,
      label: "Edges",
    },
    ...(opts.deskExtras ?? []),
    { href: `/pro/power-ratings/${sport}`, label: "Power Ratings" },
    { href: `/pro/${sport}/teams`, label: "Teams" },
  ];
}

const SPORT_NAV: Record<SportKey, SportNavConfig> = {
  nfl: {
    slateLabel: "Weekly Slate",
    primary: [
      { href: "/pro/nfl/overview", label: "Overview", primary: true },
      {
        href: "/edge-board/nfl",
        label: "Edge Board",
        primary: true,
        emphasis: "green",
      },
      { href: "/pro/nfl/slate/today", label: "Weekly Slate", primary: true },
      { href: "/pro/nfl/edges", label: "Edges" },
      { href: "/pro/nfl/survivor", label: "Survivor", primary: true },
      // Draft Desk for now; post-kickoff can retarget to Weekly Fantasy Projections.
      { href: "/pro/nfl/fantasy", label: "Fantasy", primary: true },
      { href: "/pro/power-ratings/nfl", label: "Power Ratings" },
      { href: "/pro/nfl/camp", label: "Camp Desk", primary: true },
      { href: "/pro/nfl/teams", label: "Teams" },
    ],
    tools: [
      // Demoted from primary — live in Overview body / More tools.
      { href: "/pro/nfl/fair-lines", label: "KEI Lines" },
      { href: "/pro/nfl/model", label: "Season Model" },
      { href: "/pro/nfl/game-boxes", label: "Game Boxes" },
      { href: "/pro/nfl/previews", label: "Team Previews" },
      { href: "/odds/nfl", label: "Compare Odds" },
      { href: "/pro/prediction-market", label: "Prediction Markets" },
      { href: "/pro/nfl/execution", label: "Execution Monitor" },
      { href: "/pro/nfl/projections", label: "Futures" },
      { href: "/pro/nfl/standings", label: "Standings" },
      { href: "/pro/nfl/depth-charts", label: "Depth Charts" },
      { href: "/pro/nfl/injuries", label: "Injuries & News" },
      // Fantasy primary nav covers Draft Desk; weekly stays in tools.
      { href: "/pro/nfl/weekly-fantasy", label: "Weekly Fantasy" },
      { href: "/wall-chart/nfl-2026", label: "Wall Chart" },
      { href: "/pro/model-transparency", label: "Model Health" },
    ],
  },
  ncaam: {
    slateLabel: "Daily Slate",
    primary: corePrimary("ncaam", {
      slateLabel: "Daily Slate",
      deskExtras: [{ href: "/pro/ncaam/tempo", label: "Tempo" }],
    }),
    tools: [
      ...sharedTools("ncaam"),
      { href: "/pro/ncaam/standings", label: "Standings" },
      { href: "/pro/ncaam/stats", label: "Efficiency" },
    ],
  },
  cfb: {
    slateLabel: "Weekly Slate",
    primary: corePrimary("cfb", {
      slateLabel: "Weekly Slate",
      deskExtras: [
        { href: "/pro/cfb/tempo", label: "Tempo" },
        { href: "/pro/cfb/model", label: "Season Model" },
        { href: "/pro/cfb/project-game", label: "Project Game" },
      ],
    }),
    tools: [
      ...sharedTools("cfb"),
      { href: "/pro/cfb/standings", label: "Standings" },
      { href: "/pro/cfb/stats", label: "Havoc / Efficiency" },
    ],
  },
  nba: {
    slateLabel: "Daily Slate",
    primary: corePrimary("nba", {
      slateLabel: "Daily Slate",
      deskExtras: [{ href: "/pro/nba/props", label: "Props" }],
    }),
    tools: [
      ...sharedTools("nba"),
      { href: "/pro/nba/injuries", label: "Injuries & News" },
      { href: "/pro/nba/standings", label: "Standings" },
      { href: "/pro/nba/stats", label: "Pace / Efficiency" },
    ],
  },
  mlb: {
    slateLabel: "Daily Slate",
    primary: corePrimary("mlb", {
      slateLabel: "Daily Slate",
      deskExtras: [
        { href: "/pro/mlb/fair-lines?focus=run-line", label: "Run Line" },
        { href: "/pro/mlb/props", label: "Props" },
      ],
    }),
    tools: [
      ...sharedTools("mlb"),
      { href: "/pro/mlb/injuries", label: "Injuries & News" },
      { href: "/pro/mlb/standings", label: "Standings" },
    ],
  },
  nhl: {
    slateLabel: "Daily Slate",
    primary: corePrimary("nhl", {
      slateLabel: "Daily Slate",
      deskExtras: [{ href: "/pro/nhl/goalies", label: "Goalie Desk" }],
    }),
    tools: [
      ...sharedTools("nhl"),
      { href: "/pro/nhl/injuries", label: "Injuries & News" },
      { href: "/pro/nhl/standings", label: "Standings" },
      { href: "/pro/nhl/props", label: "Limited Props" },
    ],
  },
  wnba: {
    slateLabel: "Daily Slate",
    primary: corePrimary("wnba", {
      slateLabel: "Daily Slate",
      deskExtras: [{ href: "/pro/wnba/props", label: "Props" }],
    }),
    tools: [
      ...sharedTools("wnba"),
      { href: "/pro/wnba/injuries", label: "Injuries & News" },
      { href: "/pro/wnba/standings", label: "Standings" },
      { href: "/pro/wnba/stats", label: "Pace / Usage" },
    ],
  },
};

export function getSportNavConfig(sportKey: string): SportNavConfig {
  const key = (sportKey || "nfl") as SportKey;
  return SPORT_NAV[key] ?? SPORT_NAV.nfl;
}

export function getSportPrimaryNav(sportKey: string): SportNavItem[] {
  return getSportNavConfig(sportKey).primary;
}

export function getSportToolNav(sportKey: string): SportNavItem[] {
  return getSportNavConfig(sportKey).tools;
}

export function getSportOverviewHref(sportKey: string): string {
  return `/pro/${sportKey || "nfl"}/overview`;
}

export function getSportEdgeBoardHref(sportKey: string): string {
  return `/edge-board/${sportKey || "nfl"}`;
}

export function sportHubHref(sportKey: string): string {
  return getSportOverviewHref(sportKey);
}

export function isSportNavActive(
  pathname: string | null | undefined,
  href: string,
  sportKey: string,
): boolean {
  if (!pathname) return false;

  const overview = `/pro/${sportKey}/overview`;
  if (href === overview) {
    return (
      pathname === `/pro/${sportKey}` ||
      pathname === overview ||
      pathname === `/pro/${sportKey}/hub`
    );
  }

  if (href === `/edge-board/${sportKey}`) {
    return (
      pathname === `/edge-board/${sportKey}` ||
      (sportKey === "nfl" && pathname === "/edge-board")
    );
  }

  if (href.startsWith(`/pro/${sportKey}/slate`)) {
    return pathname.startsWith(`/pro/${sportKey}/slate`);
  }

  if (href.includes("?")) {
    const base = href.split("?")[0]!;
    return pathname === base || pathname.startsWith(`${base}/`);
  }

  if (href === `/pro/${sportKey}/props`) {
    return (
      pathname.startsWith(`/pro/${sportKey}/props`) ||
      pathname.startsWith(`/pro/${sportKey}/weekly-fantasy`)
    );
  }

  return pathname === href || pathname.startsWith(`${href}/`);
}

export function sportDisplayShort(sportKey: string): string {
  return getSport(sportKey)?.label ?? sportKey.toUpperCase();
}

export function sportSupportsPropsNav(sportKey: string): boolean {
  return supportsPropsFantasy(sportKey);
}
