/**
 * NFL Pro navigation — re-exports from shared sport-pro-nav for compatibility.
 */

import {
  SPORT_DESK_SUBTITLE,
  SPORT_TAGLINE,
  getSportPrimaryNav,
  getSportToolNav,
  isSportNavActive,
  type SportNavItem,
} from "@/lib/sport-pro-nav";

export type NflNavItem = SportNavItem;

export const NFL_PRIMARY_NAV = getSportPrimaryNav("nfl");
export const NFL_TOOL_NAV = getSportToolNav("nfl");
export const NFL_TAGLINE = SPORT_TAGLINE;
export const NFL_DESK_SUBTITLE = SPORT_DESK_SUBTITLE;

/** Week 1 REG product posture — use on Edge Board / Overview CTAs, not “soft launch”. */
export const NFL_WEEK1_POSTURE = "Week 1 REG live · PRE off board";

export const NFL_GUEST_PATH =
  "Edge Board → Survivor → Fantasy → Season Model";

export function isNflNavActive(
  pathname: string | null | undefined,
  href: string,
): boolean {
  return isSportNavActive(pathname, href, "nfl");
}
