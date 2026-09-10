/**
 * Fixture rows for mobile-hierarchy QA / screenshots.
 * Presentation-only — no live Odds pull.
 */

import type { LegacyEdgeBoardRow } from "@/lib/flat-rows-to-legacy";
import type { FlatEdgeBoardRow } from "@/lib/flat-rows-to-legacy";

const EMPTY_PAIR = {
  top: { label: "—", juice: "—" },
  bottom: { label: "—", juice: "—" },
};

export function qaNflLeanCard(): LegacyEdgeBoardRow {
  return {
    id: "qa-ne-sea-lean",
    teamA: { name: "New England Patriots", site: "Away" },
    teamB: { name: "Seattle Seahawks", site: "Home" },
    awayAbbr: "NE",
    homeAbbr: "SEA",
    kickoffDate: "09/13",
    kickoffTime: "8:20 PM",
    linesAsOf: "2026-09-10T16:41:00Z",
    openLine: {
      top: { label: "+3.0", juice: "-110" },
      bottom: { label: "-3.0", juice: "-110" },
    },
    openOU: {
      top: { label: "o45.5", juice: "-110" },
      bottom: { label: "u45.5", juice: "-110" },
    },
    bestLine: {
      top: { label: "+2.5", juice: "-108" },
      bottom: { label: "-2.5", juice: "-108" },
    },
    bestOU: {
      top: { label: "o44.5", juice: "-105" },
      bottom: { label: "u44.5", juice: "-115" },
    },
    bestLineBook: "draftkings",
    bestOUBook: "fanduel",
    keiLine: {
      top: { label: "+3.9", juice: "—" },
      bottom: { label: "-3.9", juice: "—" },
    },
    keiOU: {
      top: { label: "o45.1", juice: "—" },
      bottom: { label: "u45.1", juice: "—" },
    },
    marketLineCurrent: -2.5,
    marketOUCurrent: 44.5,
    fairLineKei: -3.9,
    fairOUKei: 45.1,
    tagLine: "LEAN",
    tagOU: "PASS",
    actionLabelLine: "LEAN",
    actionLabelOU: "PASS",
    edgeMagnitudeLine: 1.4,
    edgeMagnitudeOU: 0.6,
    edgeLineNum: 1.4,
    edgeOUNum: 0.6,
    edgeLineFavor: "Seahawks",
    edgeOUFavor: "Over",
    modelConfidenceBand: "MEDIUM",
    modelConfidenceTierConstant: true,
    overview: "SEA is the house number. Market is the DK −2.5.",
  };
}

export function qaNflPlayCard(): LegacyEdgeBoardRow {
  return {
    ...qaNflLeanCard(),
    id: "qa-play",
    tagLine: "PLAY",
    actionLabelLine: "PLAY",
    marketLineCurrent: -6,
    fairLineKei: -3,
    edgeMagnitudeLine: 3,
    edgeLineNum: 3,
    edgeLineFavor: "49ers",
    bestLine: {
      top: { label: "+6.0", juice: "-110" },
      bottom: { label: "-6.0", juice: "-110" },
    },
    keiLine: {
      top: { label: "+3.0", juice: "—" },
      bottom: { label: "-3.0", juice: "—" },
    },
    awayAbbr: "SF",
    homeAbbr: "LAR",
    teamA: { name: "San Francisco 49ers", site: "Away" },
    teamB: { name: "Los Angeles Rams", site: "Home" },
  };
}

export function qaNflPassPickemCard(): LegacyEdgeBoardRow {
  return {
    ...qaNflLeanCard(),
    id: "qa-pickem-pass",
    tagLine: "PASS",
    actionLabelLine: "PASS",
    tagOU: "PASS",
    marketLineCurrent: 0,
    fairLineKei: 0,
    edgeMagnitudeLine: 0,
    edgeLineNum: 0,
    edgeLineFavor: undefined,
    bestLine: {
      top: { label: "+0", juice: "-110" },
      bottom: { label: "+0", juice: "-110" },
    },
    keiLine: {
      top: { label: "+0", juice: "—" },
      bottom: { label: "+0", juice: "—" },
    },
  };
}

export function qaNflNeutralCard(): LegacyEdgeBoardRow {
  return {
    ...qaNflLeanCard(),
    id: "qa-neutral",
    isNeutral: true,
    siteLabel: "Neutral · São Paulo",
    teamA: { name: "Green Bay Packers", site: "Away" },
    teamB: { name: "Minnesota Vikings", site: "Home" },
    awayAbbr: "GB",
    homeAbbr: "MIN",
  };
}

export function qaMissingJuiceOpenFair(): LegacyEdgeBoardRow {
  return {
    id: "qa-missing",
    teamA: { name: "Arizona Cardinals", site: "Away" },
    teamB: { name: "Los Angeles Chargers", site: "Home" },
    awayAbbr: "ARI",
    homeAbbr: "LAC",
    kickoffDate: "09/13",
    kickoffTime: "4:05 PM",
    openOU: EMPTY_PAIR,
    openLine: EMPTY_PAIR,
    bestLine: {
      top: { label: "+9.5", juice: "—" },
      bottom: { label: "-9.5", juice: "—" },
    },
    bestOU: EMPTY_PAIR,
    bestLineBook: "hardrockbet",
    marketLineCurrent: -9.5,
    tagLine: "PASS",
    actionLabelLine: "PASS",
  };
}

export function qaCfbEmptyCard(): LegacyEdgeBoardRow {
  return {
    id: "qa-cfb-empty",
    teamA: { name: "North Carolina Tar Heels", site: "Away" },
    teamB: { name: "TCU Horned Frogs", site: "Home" },
    awayAbbr: "UNC",
    homeAbbr: "TCU",
    kickoffDate: "08/29",
    kickoffTime: "12:00 PM",
    openOU: EMPTY_PAIR,
    openLine: EMPTY_PAIR,
    bestLine: EMPTY_PAIR,
    bestOU: EMPTY_PAIR,
  };
}

export function qaLongNameCard(): LegacyEdgeBoardRow {
  return {
    ...qaCfbEmptyCard(),
    id: "qa-long",
    teamA: {
      name: "San Jose State Spartans",
      site: "Away",
    },
    teamB: {
      name: "University of Southern California Trojans",
      site: "Home",
    },
    awayAbbr: "SJSU",
    homeAbbr: "USC",
    bestLine: {
      top: { label: "+21.5", juice: "-110" },
      bottom: { label: "-21.5", juice: "-110" },
    },
    bestLineBook: "betrivers",
    marketLineCurrent: -21.5,
  };
}

/** Flat rows so full EdgeBoard (mobile + desktop table) can render without Odds. */
export function qaNflFlatRows(): FlatEdgeBoardRow[] {
  return [
    {
      id: "qa-ne-sea-spread",
      game: "New England Patriots @ Seattle Seahawks",
      market: "Spread",
      best: "+2.5",
      bookKey: "draftkings",
      book: "DraftKings",
      bestJuice: "-108",
      bestJuiceHome: "-108",
      open: "+3.0",
      openJuice: "-110",
      openJuiceHome: "-110",
      kei: "-3.9",
      awayAbbr: "NE",
      homeAbbr: "SEA",
      publishTag: "LEAN",
      actionLabel: "LEAN",
      fairLine: -3.9,
      decisionMarketLine: -2.5,
      edgeMagnitude: 1.4,
      kickoffDate: "09/13",
      kickoffTime: "8:20 PM",
      linesAsOf: "2026-09-10T16:41:00Z",
      modelConfidenceBand: "MEDIUM",
      modelConfidenceTierConstant: true,
    },
    {
      id: "qa-ne-sea-total",
      game: "New England Patriots @ Seattle Seahawks",
      market: "Total",
      best: "44.5",
      bookKey: "fanduel",
      book: "FanDuel",
      bestJuice: "-105",
      bestJuiceHome: "-115",
      open: "45.5",
      kei: "45.1",
      awayAbbr: "NE",
      homeAbbr: "SEA",
      publishTag: "PASS",
      actionLabel: "PASS",
      fairLine: 45.1,
      decisionMarketLine: 44.5,
      edgeMagnitude: 0.6,
      kickoffDate: "09/13",
      kickoffTime: "8:20 PM",
      linesAsOf: "2026-09-10T16:41:00Z",
    },
  ];
}
