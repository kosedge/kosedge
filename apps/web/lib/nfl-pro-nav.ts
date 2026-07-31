/**
 * Shared NFL Pro navigation — research desk IA.
 * Positioning: "I give the info, you make the picks."
 */

export type NflNavItem = {
  href: string;
  label: string;
  /** Highlight in primary subnav */
  primary?: boolean;
};

/** Primary subnav shown on every NFL Pro / Edge Board / Odds NFL surface */
export const NFL_PRIMARY_NAV: NflNavItem[] = [
  { href: "/pro/nfl/overview", label: "Overview", primary: true },
  { href: "/edge-board/nfl", label: "Edge Board", primary: true },
  { href: "/pro/nfl/slate/today", label: "Weekly Slate", primary: true },
  { href: "/pro/nfl/fair-lines", label: "KEI Lines" },
  { href: "/pro/nfl/edges", label: "Edges" },
  { href: "/pro/nfl/props", label: "Props" },
  { href: "/pro/power-ratings/nfl", label: "Power Ratings" },
  { href: "/pro/nfl/teams", label: "Teams" },
];

/** Secondary tools — used in overview grids and overflow menus */
export const NFL_TOOL_NAV: NflNavItem[] = [
  { href: "/pro/nfl/previews", label: "Team Previews" },
  { href: "/odds/nfl", label: "Compare Odds" },
  { href: "/pro/prediction-market", label: "Prediction Markets" },
  { href: "/pro/nfl/execution", label: "Execution Monitor" },
  { href: "/pro/nfl/projections", label: "Futures" },
  { href: "/pro/nfl/standings", label: "Standings" },
  { href: "/pro/nfl/depth-charts", label: "Depth Charts" },
  { href: "/pro/nfl/injuries", label: "Injuries" },
  { href: "/pro/nfl/fantasy", label: "Fantasy Draft" },
  { href: "/pro/nfl/weekly-fantasy", label: "Weekly Fantasy" },
  { href: "/pro/nfl/dfs", label: "DFS" },
  { href: "/pro/nfl/player-previews", label: "Player Previews" },
  { href: "/pro/nfl/awards", label: "Awards" },
  { href: "/wall-chart/nfl-2026", label: "Wall Chart" },
  { href: "/pro/nfl/camp", label: "Camp Desk" },
  { href: "/pro/model-transparency", label: "Model Health" },
];

export const NFL_TAGLINE = "I give the info, you make the picks.";
export const NFL_DESK_SUBTITLE =
  "Research desk • Model lines, context & tools";

export function isNflNavActive(
  pathname: string | null | undefined,
  href: string,
): boolean {
  if (!pathname) return false;
  if (href === "/pro/nfl/overview") {
    return (
      pathname === "/pro/nfl" ||
      pathname === "/pro/nfl/overview" ||
      pathname === "/pro/nfl/hub"
    );
  }
  if (href === "/edge-board/nfl") {
    return pathname === "/edge-board/nfl" || pathname === "/edge-board";
  }
  if (href === "/pro/nfl/slate/today") {
    return pathname.startsWith("/pro/nfl/slate");
  }
  if (href === "/pro/nfl/props") {
    return (
      pathname.startsWith("/pro/nfl/props") ||
      pathname.startsWith("/pro/nfl/weekly-fantasy")
    );
  }
  return pathname === href || pathname.startsWith(`${href}/`);
}
