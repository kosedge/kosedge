/**
 * One-leg alternate-spread pricing surface.
 * Every row requires a posted sportsbook price — no interpolation.
 */

import {
  americanImpliedProb,
  bookmakerHold,
  evPerDollarRisked,
  fairAmericanFromProb,
} from "@/lib/line-curve/american";
import {
  assertAlternateMarketAvailable,
  assertBaseLine,
  assertModelBound,
  assertPostedAlts,
  assertSnapshotFresh,
  assertSnapshotIdentity,
  closed,
  uniqueAlts,
} from "@/lib/line-curve/guardrails";
import { applyBestValue, labelFromEdge } from "@/lib/line-curve/labels";
import {
  atsOutcomeMass,
  buildMarginPmf,
  resolveSide,
} from "@/lib/line-curve/margin-pmf";
import type {
  LineCurveOk,
  LineCurvePoint,
  LineCurveResult,
  ModelMarginInput,
  OddsAltSnapshot,
} from "@/lib/line-curve/types";

function fairNoPush(cover: number, push: number, loss: number): number {
  const denom = cover + loss;
  if (denom <= 0) return push > 0 ? 0.5 : 0;
  return cover / denom;
}

export function priceAlternateSurface(args: {
  snapshot: OddsAltSnapshot;
  model: ModelMarginInput;
  side: string;
  nowMs?: number;
}): LineCurveResult {
  const { snapshot, model, side } = args;
  const identity = assertSnapshotIdentity(snapshot);
  if (identity) return identity;
  const fresh = assertSnapshotFresh(snapshot, args.nowMs);
  if (fresh) return fresh;
  const bound = assertModelBound(model, snapshot);
  if (bound) return bound;

  const sided = resolveSide(snapshot.homeTeam, snapshot.awayTeam, side);
  if (!sided) {
    return closed("missing_odds", `Side ${side} is not on this event.`);
  }

  const sideKey = sided === "home" ? snapshot.homeTeam : snapshot.awayTeam;
  const rawAlts =
    snapshot.altsBySide[sideKey] ?? snapshot.altsBySide[side] ?? [];
  const postedCheck = assertPostedAlts(rawAlts);
  if (postedCheck) return postedCheck;

  let alts;
  try {
    alts = uniqueAlts(rawAlts);
  } catch {
    return closed("duplicate_odds", "Duplicate disagreeing alternate prices.");
  }

  const baseLine =
    snapshot.baseLineBySide[sideKey] ?? snapshot.baseLineBySide[side];
  const baseCheck = assertBaseLine(baseLine, alts);
  if (baseCheck) return baseCheck;
  const altMarket = assertAlternateMarketAvailable(alts, baseLine);
  if (altMarket) return altMarket;

  const pmf = buildMarginPmf(model);
  const modelFairLine =
    sided === "home" ? model.modelSpreadHome : -model.modelSpreadHome;

  const priced: LineCurvePoint[] = [];
  const byLine = new Map<number, LineCurvePoint>();

  for (const alt of alts) {
    const mass = atsOutcomeMass(pmf, sided, alt.line);
    const implied = americanImpliedProb(alt.americanOdds);
    if (implied == null) {
      return closed("invalid_american", `Invalid American at ${alt.line}.`);
    }
    const fairP = fairNoPush(mass.cover, mass.push, mass.loss);
    const ev = evPerDollarRisked({
      cover: mass.cover,
      push: mass.push,
      loss: mass.loss,
      americanOdds: alt.americanOdds,
    });
    if (ev == null) {
      return closed("invalid_american", `Cannot price EV at ${alt.line}.`);
    }
    const hold =
      alt.opposingAmericanOdds != null
        ? bookmakerHold(alt.americanOdds, alt.opposingAmericanOdds)
        : null;
    const point: LineCurvePoint = {
      eventId: snapshot.eventId,
      side: sideKey,
      book: snapshot.book,
      baseLine,
      altLine: alt.line,
      americanOdds: alt.americanOdds,
      impliedProbability: implied,
      modelCoverProbability: mass.cover,
      modelPushProbability: mass.push,
      modelLossProbability: mass.loss,
      fairAmericanOdds: fairAmericanFromProb(fairP),
      edgePct: fairP - implied,
      evPerDollar: ev,
      incrementalProbabilityGain: null,
      incrementalPriceCost: null,
      marginalCostPerProbPoint: null,
      oddsSnapshotId: snapshot.oddsSnapshotId,
      modelRunId: model.modelRunId,
      timestamp: snapshot.capturedAt,
      label: labelFromEdge(fairP - implied, ev),
      bookmakerHold: hold,
    };
    priced.push(point);
    byLine.set(alt.line, point);
  }

  const basePoint = byLine.get(baseLine);
  if (!basePoint) {
    return closed("missing_odds", "Base line vanished after pricing.");
  }

  const buyingOrder = [...priced].sort((a, b) => a.altLine - b.altLine);
  for (let i = 0; i < buyingOrder.length; i += 1) {
    const row = buyingOrder[i];
    row.incrementalProbabilityGain =
      row.altLine === baseLine
        ? 0
        : row.modelCoverProbability - basePoint.modelCoverProbability;
    row.incrementalPriceCost =
      row.altLine === baseLine
        ? 0
        : row.impliedProbability - basePoint.impliedProbability;
    if (i > 0) {
      const prev = buyingOrder[i - 1];
      const dProb = row.modelCoverProbability - prev.modelCoverProbability;
      const dPrice = row.impliedProbability - prev.impliedProbability;
      row.marginalCostPerProbPoint =
        Math.abs(dProb) < 1e-9 ? null : dPrice / dProb;
    }
  }

  const labeled = applyBestValue(priced).sort((a, b) => a.altLine - b.altLine);
  const result: LineCurveOk = {
    ok: true,
    sport: snapshot.sport,
    eventId: snapshot.eventId,
    side: sideKey,
    book: snapshot.book,
    baseLine,
    modelFairLine,
    modelRunId: model.modelRunId,
    oddsSnapshotId: snapshot.oddsSnapshotId,
    timestamp: snapshot.capturedAt,
    points: labeled,
    winProbability: sided === "home" ? pmf.winHome : pmf.winAway,
    pushStraightUp: pmf.pushStraightUp,
  };
  return result;
}

export function evaluatePostedAlt(args: {
  snapshot: OddsAltSnapshot;
  model: ModelMarginInput;
  side: string;
  altLine: number;
  nowMs?: number;
}): LineCurveResult {
  const curve = priceAlternateSurface(args);
  if (!curve.ok) return curve;
  const hit = curve.points.find((p) => p.altLine === args.altLine);
  if (!hit) {
    return closed(
      "missing_alt_price",
      `No posted sportsbook price at ${args.altLine} — no interpolation.`,
    );
  }
  return { ...curve, points: [hit] };
}
