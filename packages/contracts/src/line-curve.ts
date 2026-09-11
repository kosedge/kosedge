import { z } from "zod";

/** Research labels only. No PLAY / LEAN / stake chrome. */
export const LineCurveResearchLabelSchema = z.enum([
  "BEST VALUE",
  "FAIR",
  "OVERPRICED",
  "INSUFFICIENT",
]);

export type LineCurveResearchLabel = z.infer<
  typeof LineCurveResearchLabelSchema
>;

export const LineCurvePointSchema = z.object({
  eventId: z.string(),
  side: z.string(),
  book: z.string(),
  baseLine: z.number(),
  altLine: z.number(),
  americanOdds: z.number(),
  impliedProbability: z.number(),
  modelCoverProbability: z.number(),
  modelPushProbability: z.number(),
  modelLossProbability: z.number(),
  fairAmericanOdds: z.number(),
  edgePct: z.number(),
  evPerDollar: z.number(),
  incrementalProbabilityGain: z.number().nullable(),
  incrementalPriceCost: z.number().nullable(),
  marginalCostPerProbPoint: z.number().nullable(),
  oddsSnapshotId: z.string(),
  modelRunId: z.string(),
  timestamp: z.string(),
});

export type LineCurvePoint = z.infer<typeof LineCurvePointSchema>;
