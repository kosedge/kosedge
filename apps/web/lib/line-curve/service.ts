/**
 * Line Curve service layer. Keep calculation out of UI components.
 *
 *   getLineCurve(eventId, side, book)
 *   evaluateAltLine(eventId, side, altLine, book)
 *   optimizeTwoLegLineCurve(legA, legB, book)
 */

import {
  evaluatePostedAlt,
  priceAlternateSurface,
} from "@/lib/line-curve/alternate-pricing";
import { optimizeTwoLegAlternateSurface } from "@/lib/line-curve/joint-optimizer";
import { fetchAlternateSpreadSnapshot } from "@/lib/line-curve/odds-adapter";
import { closed } from "@/lib/line-curve/guardrails";
import type {
  LineCurveResult,
  LineCurveSport,
  ModelMarginInput,
  OddsAltSnapshot,
  QuotedParlayPrice,
  TwoLegInput,
  TwoLegOptimizeResult,
} from "@/lib/line-curve/types";

export type LineCurveRequest = {
  eventId: string;
  side: string;
  book: string;
  snapshot?: OddsAltSnapshot;
  model?: ModelMarginInput;
  sport?: LineCurveSport;
  nowMs?: number;
};

export type EvaluateAltRequest = LineCurveRequest & { altLine: number };

export type TwoLegServiceRequest = {
  book: string;
  legA: TwoLegInput;
  legB: TwoLegInput;
  quotedParlays?: QuotedParlayPrice[];
  nowMs?: number;
};

async function resolveSnapshot(
  req: LineCurveRequest,
): Promise<OddsAltSnapshot | ReturnType<typeof closed>> {
  if (req.snapshot) return req.snapshot;
  if (!req.sport) {
    return closed(
      "missing_odds",
      "Sport is required when no snapshot is injected.",
    );
  }
  return fetchAlternateSpreadSnapshot({
    sport: req.sport,
    eventId: req.eventId,
    book: req.book,
  });
}

export async function getLineCurve(
  eventId: string,
  side: string,
  book: string,
  extras: Omit<LineCurveRequest, "eventId" | "side" | "book"> = {},
): Promise<LineCurveResult> {
  if (!extras.model) {
    return closed(
      "missing_model_run",
      "Model run must be bound to this event before pricing. Live odds are not fetched until the model is bound.",
    );
  }
  const snapshot = await resolveSnapshot({ eventId, side, book, ...extras });
  if ("ok" in snapshot && snapshot.ok === false) return snapshot;
  return priceAlternateSurface({
    snapshot: snapshot as OddsAltSnapshot,
    model: extras.model,
    side,
    nowMs: extras.nowMs,
  });
}

export async function evaluateAltLine(
  eventId: string,
  side: string,
  altLine: number,
  book: string,
  extras: Omit<
    EvaluateAltRequest,
    "eventId" | "side" | "altLine" | "book"
  > = {},
): Promise<LineCurveResult> {
  if (!extras.model) {
    return closed(
      "missing_model_run",
      "Model run must be bound to this event before pricing. Live odds are not fetched until the model is bound.",
    );
  }
  const snapshot = await resolveSnapshot({
    eventId,
    side,
    book,
    ...extras,
  });
  if ("ok" in snapshot && snapshot.ok === false) return snapshot;
  return evaluatePostedAlt({
    snapshot: snapshot as OddsAltSnapshot,
    model: extras.model,
    side,
    altLine,
    nowMs: extras.nowMs,
  });
}

export function optimizeTwoLegLineCurve(
  legA: TwoLegInput,
  legB: TwoLegInput,
  book: string,
  extras: {
    quotedParlays?: QuotedParlayPrice[];
    nowMs?: number;
  } = {},
): TwoLegOptimizeResult {
  return optimizeTwoLegAlternateSurface({
    legA,
    legB,
    book,
    quotedParlays: extras.quotedParlays,
    nowMs: extras.nowMs,
  });
}
