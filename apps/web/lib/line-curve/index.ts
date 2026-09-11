export {
  americanImpliedProb,
  americanToDecimal,
  bookmakerHold,
  evPerDollarRisked,
  fairAmericanFromProb,
  isValidAmericanOdds,
  multiplicativeParlayAmerican,
} from "@/lib/line-curve/american";
export {
  evaluatePostedAlt,
  priceAlternateSurface,
} from "@/lib/line-curve/alternate-pricing";
export {
  getLineCurve,
  evaluateAltLine,
  optimizeTwoLegLineCurve,
} from "@/lib/line-curve/service";
export {
  independentJointModel,
  optimizeTwoLegAlternateSurface,
} from "@/lib/line-curve/joint-optimizer";
export {
  INDEPENDENT_JOINT_CAPTION,
  INDEPENDENT_JOINT_HEADING,
  impliesCorrelationAdjusted,
  jointCoverColumnLabel,
  jointProbabilityCaption,
} from "@/lib/line-curve/joint-presentation";
export {
  buildMarginPmf,
  atsOutcomeMass,
  teamScorePmf,
} from "@/lib/line-curve/margin-pmf";
export { missouriOklahomaFixture } from "@/lib/line-curve/fixtures/missouri-oklahoma";
export {
  LINE_CURVE_MAX_AGE_MS,
  LINE_CURVE_MAX_ALTS_PER_SIDE,
  LINE_CURVE_MAX_QUOTED_PARLAYS,
} from "@/lib/line-curve/types";
export type {
  LineCurvePoint,
  LineCurveResult,
  TwoLegCombo,
  TwoLegOptimizeResult,
  ResearchLabel,
} from "@/lib/line-curve/types";
