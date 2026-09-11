/**
 * Research fixture modeled after Missouri +1.5 / Oklahoma +1.5 @ −103.
 *
 * Prices and model inputs are explicit. The optimizer answer is NOT hardcoded —
 * tests must let the joint optimizer rank this combo against every other
 * posted alternate pair.
 */

import type {
  ModelMarginInput,
  OddsAltSnapshot,
  PostedAlt,
  QuotedParlayPrice,
} from "@/lib/line-curve/types";

export const MIZZOU_OKLAHOMA_FIXTURE_AS_OF = "2026-09-11T01:00:00.000Z";
export const MIZZOU_OKLAHOMA_BOOK = "draftkings";

const MIZZOU_EVENT = "fixture-cfb-missouri-2026w2";
const OU_EVENT = "fixture-cfb-oklahoma-2026w2";

function alts(rows: Array<[number, number, number | null]>): PostedAlt[] {
  return rows.map(([line, americanOdds, opposingAmericanOdds]) => ({
    line,
    americanOdds,
    opposingAmericanOdds,
  }));
}

/** Missouri getting points as a small dog. Model is slightly more bullish. */
export const missouriSnapshot: OddsAltSnapshot = {
  eventId: MIZZOU_EVENT,
  sport: "cfb",
  book: MIZZOU_OKLAHOMA_BOOK,
  homeTeam: "Kansas",
  awayTeam: "Missouri",
  capturedAt: MIZZOU_OKLAHOMA_FIXTURE_AS_OF,
  oddsSnapshotId: `${MIZZOU_EVENT}:${MIZZOU_OKLAHOMA_BOOK}:${MIZZOU_OKLAHOMA_FIXTURE_AS_OF}`,
  source: "research_fixture",
  baseLineBySide: {
    Missouri: 1.5,
    Kansas: -1.5,
  },
  altsBySide: {
    Missouri: alts([
      [-2.5, 165, -195],
      [-1.5, 140, -165],
      [1.5, -110, -110],
      [2.5, -125, 105],
      [3.5, -145, 125],
      [4.5, -165, 140],
      [6.5, -210, 175],
      [7.5, -240, 195],
    ]),
    Kansas: alts([
      [2.5, -195, 165],
      [1.5, -165, 140],
      [-1.5, -110, -110],
      [-2.5, 105, -125],
      [-3.5, 125, -145],
      [-4.5, 140, -165],
      [-6.5, 175, -210],
      [-7.5, 195, -240],
    ]),
  },
};

export const oklahomaSnapshot: OddsAltSnapshot = {
  eventId: OU_EVENT,
  sport: "cfb",
  book: MIZZOU_OKLAHOMA_BOOK,
  homeTeam: "Tennessee",
  awayTeam: "Oklahoma",
  capturedAt: MIZZOU_OKLAHOMA_FIXTURE_AS_OF,
  oddsSnapshotId: `${OU_EVENT}:${MIZZOU_OKLAHOMA_BOOK}:${MIZZOU_OKLAHOMA_FIXTURE_AS_OF}`,
  source: "research_fixture",
  baseLineBySide: {
    Oklahoma: 1.5,
    Tennessee: -1.5,
  },
  altsBySide: {
    Oklahoma: alts([
      [-2.5, 160, -190],
      [-1.5, 135, -160],
      [1.5, -110, -110],
      [2.5, -128, 108],
      [3.5, -150, 128],
      [4.5, -172, 145],
      [6.5, -215, 180],
      [7.5, -250, 200],
    ]),
    Tennessee: alts([
      [2.5, -190, 160],
      [1.5, -160, 135],
      [-1.5, -110, -110],
      [-2.5, 108, -128],
      [-3.5, 128, -150],
      [-4.5, 145, -172],
      [-6.5, 180, -215],
      [-7.5, 200, -250],
    ]),
  },
};

export const missouriModel: ModelMarginInput = {
  eventId: MIZZOU_EVENT,
  modelRunId:
    "cfb-season-engine-v0.15-power-sot:cfb-kei-v1.0-2026w0:fixture-mizzou",
  sport: "cfb",
  homeTeam: "Kansas",
  awayTeam: "Missouri",
  modelSpreadHome: 0.4,
  expectedHomeScore: 24.8,
  expectedAwayScore: 25.2,
  marginSd: 16.4,
};

export const oklahomaModel: ModelMarginInput = {
  eventId: OU_EVENT,
  modelRunId:
    "cfb-season-engine-v0.15-power-sot:cfb-kei-v1.0-2026w0:fixture-ou",
  sport: "cfb",
  homeTeam: "Tennessee",
  awayTeam: "Oklahoma",
  modelSpreadHome: -0.8,
  expectedHomeScore: 27.1,
  expectedAwayScore: 26.3,
  marginSd: 16.2,
};

/** The ticket under study — not declared optimal. */
export const quotedPlus15Parlay: QuotedParlayPrice = {
  lineA: 1.5,
  lineB: 1.5,
  americanOdds: -103,
};

import { priceAlternateSurface } from "@/lib/line-curve/alternate-pricing";
import { optimizeTwoLegLineCurve } from "@/lib/line-curve/service";
import type {
  LineCurveResult,
  TwoLegOptimizeResult,
} from "@/lib/line-curve/types";

export function getMissouriOklahomaLineCurve(
  side: "Missouri" | "Oklahoma",
): LineCurveResult {
  const leg =
    side === "Missouri"
      ? missouriOklahomaFixture.missouri
      : missouriOklahomaFixture.oklahoma;
  return priceAlternateSurface({
    snapshot: leg.snapshot,
    model: leg.model,
    side: leg.side,
  });
}

export function optimizeMissouriOklahomaLineCurve(): TwoLegOptimizeResult {
  const fx = missouriOklahomaFixture;
  return optimizeTwoLegLineCurve(
    {
      eventId: fx.missouri.snapshot.eventId,
      side: fx.missouri.side,
      snapshot: fx.missouri.snapshot,
      model: fx.missouri.model,
    },
    {
      eventId: fx.oklahoma.snapshot.eventId,
      side: fx.oklahoma.side,
      snapshot: fx.oklahoma.snapshot,
      model: fx.oklahoma.model,
    },
    fx.book,
    { quotedParlays: fx.quotedParlays },
  );
}

export const missouriOklahomaFixture = {
  book: MIZZOU_OKLAHOMA_BOOK,
  capturedAt: MIZZOU_OKLAHOMA_FIXTURE_AS_OF,
  missouri: {
    snapshot: missouriSnapshot,
    model: missouriModel,
    side: "Missouri",
  },
  oklahoma: {
    snapshot: oklahomaSnapshot,
    model: oklahomaModel,
    side: "Oklahoma",
  },
  quotedParlays: [quotedPlus15Parlay] as QuotedParlayPrice[],
};
