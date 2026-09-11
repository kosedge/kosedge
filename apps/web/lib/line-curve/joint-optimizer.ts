/**
 * Two-leg line-curve optimizer.
 * Asymmetric movement is allowed. Correlation is a reserved interface.
 *
 * Independence is the Phase 1 default and is written into every combo's
 * `correlation` metadata. Do not treat a bare product of two cover
 * percentages as a correlated joint.
 */

import {
  americanImpliedProb,
  evPerDollarRisked,
  fairAmericanFromProb,
  multiplicativeParlayAmerican,
} from "@/lib/line-curve/american";
import { priceAlternateSurface } from "@/lib/line-curve/alternate-pricing";
import {
  assertQuotedParlaySize,
  assertSurfaceSize,
  closed,
} from "@/lib/line-curve/guardrails";
import { applyBestValue, labelFromEdge } from "@/lib/line-curve/labels";
import {
  INDEPENDENT_JOINT_NOTE,
  type JointCorrelationMeta,
  type JointCorrelationModel,
  type JointMass,
  type OutcomeMass,
  type QuotedParlayPrice,
  type TwoLegCombo,
  type TwoLegInput,
  type TwoLegOptimizeResult,
} from "@/lib/line-curve/types";

export function independentJointModel(): JointCorrelationModel {
  return {
    assumption: "independent",
    adjustment: null,
    note: INDEPENDENT_JOINT_NOTE,
    joint(legA: OutcomeMass, legB: OutcomeMass): JointMass {
      const bothCover = legA.cover * legB.cover;
      const aCoverBPush = legA.cover * legB.push;
      const aPushBCover = legA.push * legB.cover;
      const bothPush = legA.push * legB.push;
      const anyLoss = 1 - (1 - legA.loss) * (1 - legB.loss);
      return { bothCover, aCoverBPush, aPushBCover, bothPush, anyLoss };
    },
  };
}

export function correlationMeta(
  model: JointCorrelationModel,
): JointCorrelationMeta {
  return {
    assumption: model.assumption,
    documented: true,
    adjustment: model.adjustment,
    note: model.note,
  };
}

function comboEv(args: {
  joint: JointMass;
  parlayAmerican: number;
  americanA: number;
  americanB: number;
}): number | null {
  const parlay = evPerDollarRisked({
    cover: args.joint.bothCover,
    push: 0,
    loss: 0,
    americanOdds: args.parlayAmerican,
  });
  const straightA = evPerDollarRisked({
    cover: args.joint.aCoverBPush,
    push: 0,
    loss: 0,
    americanOdds: args.americanA,
  });
  const straightB = evPerDollarRisked({
    cover: args.joint.aPushBCover,
    push: 0,
    loss: 0,
    americanOdds: args.americanB,
  });
  if (parlay == null || straightA == null || straightB == null) return null;
  // Push-reduce: cover+push pays the covering straight; double push = 0;
  // any loss = −1. The helpers above only applied the win legs; add loss.
  return (
    parlay +
    straightA +
    straightB +
    args.joint.bothPush * 0 +
    args.joint.anyLoss * -1
  );
}

export function optimizeTwoLegAlternateSurface(args: {
  legA: TwoLegInput;
  legB: TwoLegInput;
  book: string;
  quotedParlays?: QuotedParlayPrice[];
  correlation?: JointCorrelationModel;
  nowMs?: number;
}): TwoLegOptimizeResult {
  const correlation = args.correlation ?? independentJointModel();
  const meta = correlationMeta(correlation);

  if (
    args.legA.snapshot.book !== args.book ||
    args.legB.snapshot.book !== args.book
  ) {
    return closed(
      "inconsistent_odds",
      "Both legs must be priced at the requested book.",
    );
  }
  if (args.legA.eventId === args.legB.eventId) {
    return closed(
      "same_game",
      "Same-game combinations cannot be labeled under naive independence. Correlation is reserved — fail closed.",
    );
  }

  const quotedSize = assertQuotedParlaySize(args.quotedParlays);
  if (quotedSize) return quotedSize;

  for (const snapshot of [args.legA.snapshot, args.legB.snapshot]) {
    for (const alts of Object.values(snapshot.altsBySide)) {
      const size = assertSurfaceSize(alts);
      if (size) return size;
    }
  }

  const curveA = priceAlternateSurface({
    snapshot: args.legA.snapshot,
    model: args.legA.model,
    side: args.legA.side,
    nowMs: args.nowMs,
  });
  if (!curveA.ok) return curveA;
  const curveB = priceAlternateSurface({
    snapshot: args.legB.snapshot,
    model: args.legB.model,
    side: args.legB.side,
    nowMs: args.nowMs,
  });
  if (!curveB.ok) return curveB;

  const quoted = new Map<string, number>();
  for (const q of args.quotedParlays ?? []) {
    quoted.set(`${q.lineA}|${q.lineB}`, q.americanOdds);
  }

  const raw: TwoLegCombo[] = [];
  for (const a of curveA.points) {
    for (const b of curveB.points) {
      const quotedPrice = quoted.get(`${a.altLine}|${b.altLine}`);
      const derived = multiplicativeParlayAmerican(
        a.americanOdds,
        b.americanOdds,
      );
      const bookParlayAmerican = quotedPrice ?? derived;
      if (bookParlayAmerican == null) continue;

      const joint = correlation.joint(
        {
          cover: a.modelCoverProbability,
          push: a.modelPushProbability,
          loss: a.modelLossProbability,
        },
        {
          cover: b.modelCoverProbability,
          push: b.modelPushProbability,
          loss: b.modelLossProbability,
        },
      );
      const ev = comboEv({
        joint,
        parlayAmerican: bookParlayAmerican,
        americanA: a.americanOdds,
        americanB: b.americanOdds,
      });
      if (ev == null) continue;
      const implied = americanImpliedProb(bookParlayAmerican);
      if (implied == null) continue;
      const fairP = joint.bothCover;
      raw.push({
        rank: 0,
        lineA: a.altLine,
        lineB: b.altLine,
        bookParlayAmerican,
        parlayPriceSource:
          quotedPrice != null
            ? "book_quoted"
            : "multiplicative_from_posted_legs",
        modelJointCoverProbability: joint.bothCover,
        modelJointPushReduceProbability: joint.aCoverBPush + joint.aPushBCover,
        modelAnyLossProbability: joint.anyLoss,
        fairAmericanOdds: fairAmericanFromProb(fairP),
        evPerDollar: ev,
        edgePct: fairP - implied,
        label: labelFromEdge(fairP - implied, ev),
        correlation: meta,
        oddsSnapshotIdA: a.oddsSnapshotId,
        oddsSnapshotIdB: b.oddsSnapshotId,
        modelRunIdA: a.modelRunId,
        modelRunIdB: b.modelRunId,
        timestamp: a.timestamp <= b.timestamp ? a.timestamp : b.timestamp,
      });
    }
  }

  if (!raw.length) {
    return closed("missing_odds", "No valid posted two-leg combinations.");
  }

  const labeled = applyBestValue(raw).sort(
    (x, y) => y.evPerDollar - x.evPerDollar,
  );
  const combos = labeled.map((row, i) => ({ ...row, rank: i + 1 }));

  return {
    ok: true,
    book: args.book,
    sideA: curveA.side,
    sideB: curveB.side,
    eventIdA: curveA.eventId,
    eventIdB: curveB.eventId,
    correlation: meta,
    combos,
  };
}
