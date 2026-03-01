export type PriceSide = { label: string; juice: string };
export type PricePair = { top: PriceSide; bottom: PriceSide };

export type TeamBlock = {
  name: string;
  keiRank?: string;
  keiNumber?: string;
  site: "Away" | "Home";
  record?: string;
  confRecord?: string;
};

export type LegacyEdgeBoardRow = {
  id: string;
  time?: string;
  teamA: TeamBlock;
  teamB: TeamBlock;
  openOU: PricePair;
  openLine: PricePair;
  bestLine: PricePair;
  bestOU: PricePair;
  keiLine?: PricePair;
  keiOU?: PricePair;
  edgeLine?: PricePair;
  edgeOU?: PricePair;
  edgeLineNum?: number;
  edgeOUNum?: number;
  tagLine?: "PLAY" | "LEAN" | "PASS";
  tagOU?: "PLAY" | "LEAN" | "PASS";
  overview?: string;
};
