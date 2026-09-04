/**
 * Homepage Edge Board eye-catcher rows.
 *
 * Stamped matchup chrome (teams / best line / edge magnitude) is fixed for
 * the hero card — but Tag MUST go through `cfbEdgeTag` so sit flags
 * (`CFB_*_PLAY_ELIGIBLE`) cannot be bypassed by hardcoded "PLAY".
 *
 * Do not invent KEI or flip PLAY eligibility here.
 */

import { cfbEdgeTag, type CfbEdgeTag } from "@/lib/cfb-trusted-market";

export type HomePreviewPricePair = {
  top: { label: string; juice: string };
  bottom: { label: string; juice: string };
};

export type HomePreviewRow = {
  id: string;
  teamA: { name: string; site: string };
  teamB: { name: string; site: string };
  openOU: HomePreviewPricePair;
  openLine: HomePreviewPricePair;
  bestLine: HomePreviewPricePair;
  bestOU: HomePreviewPricePair;
  /** Absolute spread edge (pts). Tag is derived — never hardcode PLAY. */
  edgeLineNum: number;
  tagLine: CfbEdgeTag;
};

const EMPTY_PAIR: HomePreviewPricePair = {
  top: { label: "—", juice: "—" },
  bottom: { label: "—", juice: "—" },
};

/** Raw stamped fixtures (edges only — tags applied by `buildHomePreviewRows`). */
export const HOME_PREVIEW_FIXTURES: ReadonlyArray<{
  id: string;
  away: string;
  home: string;
  bestLineTop: string;
  bestOuTop: string;
  edgeLineNum: number;
}> = [
  {
    id: "home-smu-fsu",
    away: "SMU",
    home: "FSU",
    bestLineTop: "SMU -3",
    bestOuTop: "o53.5",
    edgeLineNum: 5.4,
  },
  {
    id: "home-unlv-hawaii",
    away: "UNLV",
    home: "Hawaii",
    bestLineTop: "HAW +2.5",
    bestOuTop: "o58.5",
    edgeLineNum: 5.5,
  },
  {
    id: "home-sjsu-emu",
    away: "SJSU",
    home: "E. Michigan",
    bestLineTop: "SJSU +3.5",
    bestOuTop: "o56.5",
    edgeLineNum: 1.4,
  },
];

/**
 * Build homepage preview rows with sit-aware tags.
 * PLAY-band trusted edges (≥4.0) → PASS while CFB_SPREAD_PLAY_ELIGIBLE=false.
 */
export function buildHomePreviewRows(): HomePreviewRow[] {
  return HOME_PREVIEW_FIXTURES.map((f) => ({
    id: f.id,
    teamA: { name: f.away, site: "Away" },
    teamB: { name: f.home, site: "Home" },
    openOU: EMPTY_PAIR,
    openLine: EMPTY_PAIR,
    bestLine: {
      top: { label: f.bestLineTop, juice: "—" },
      bottom: { label: "—", juice: "—" },
    },
    bestOU: {
      top: { label: f.bestOuTop, juice: "—" },
      bottom: { label: "—", juice: "—" },
    },
    edgeLineNum: f.edgeLineNum,
    tagLine: cfbEdgeTag(f.edgeLineNum, "spread"),
  }));
}
