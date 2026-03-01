import type { LegacyEdgeBoardRow } from "@/lib/edge-board-types";

export type FeaturedGame = {
  slug: string;
  row: LegacyEdgeBoardRow;
  sport: string;
};

const SAMPLE_ROW = (away: string, home: string, time: string): LegacyEdgeBoardRow => ({
  id: `${away}-${home}`.toLowerCase().replace(/\s+/g, "-"),
  time,
  teamA: { name: away, site: "Away" },
  teamB: { name: home, site: "Home" },
  openOU: { top: { label: "o148.5", juice: "-110" }, bottom: { label: "u148.5", juice: "-110" } },
  openLine: { top: { label: "+4.5", juice: "-110" }, bottom: { label: "-4.5", juice: "-110" } },
  bestLine: { top: { label: "+5.5", juice: "-112" }, bottom: { label: "-5.0", juice: "-110" } },
  bestOU: { top: { label: "o147.5", juice: "-110" }, bottom: { label: "u149.5", juice: "-112" } },
});

/** Top edge = first featured game. */
export const TOP_EDGE: FeaturedGame = {
  slug: "duke-unc-feb-28",
  row: SAMPLE_ROW("Duke", "UNC", "8:30pm"),
  sport: "cbb",
};

/** 3–5 highlighted games for article cards. */
export const HIGHLIGHTED_GAMES: FeaturedGame[] = [
  {
    slug: "duke-unc-feb-28",
    row: SAMPLE_ROW("Duke", "UNC", "8:30pm"),
    sport: "cbb",
  },
  {
    slug: "lakers-celtics-feb-28",
    row: SAMPLE_ROW("Lakers", "Celtics", "7:00pm"),
    sport: "nba",
  },
  {
    slug: "chiefs-49ers-feb-28",
    row: SAMPLE_ROW("Chiefs", "49ers", "6:30pm"),
    sport: "nfl",
  },
  {
    slug: "dodgers-yankees-feb-28",
    row: SAMPLE_ROW("Dodgers", "Yankees", "4:00pm"),
    sport: "mlb",
  },
];
