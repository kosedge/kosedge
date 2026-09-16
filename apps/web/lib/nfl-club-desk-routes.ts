/** Customer-facing Club Desk (in-season name for the former Camp Desk). */

export const NFL_CLUB_DESK_HREF = "/pro/nfl/club";
export const NFL_CLUB_DESK_LEGACY_HREF = "/pro/nfl/camp";
export const NFL_CLUB_DESK_LABEL = "Club Desk";

export function displayClubDeskTitle(title: string): string {
  return title
    .replace(/Training Camp desk/gi, NFL_CLUB_DESK_LABEL)
    .replace(/Camp Desk/gi, NFL_CLUB_DESK_LABEL)
    .replace(/camp desk/gi, NFL_CLUB_DESK_LABEL);
}
