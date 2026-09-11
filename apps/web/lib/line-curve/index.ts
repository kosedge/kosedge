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
  getMissouriOklahomaLineCurve,
  optimizeMissouriOklahomaLineCurve,
} from "@/lib/line-curve/service";
export {
  independentJointModel,
  optimizeTwoLegAlternateSurface,
} from "@/lib/line-curve/joint-optimizer";
export {
  buildMarginPmf,
  atsOutcomeMass,
  teamScorePmf,
} from "@/lib/line-curve/margin-pmf";
export { missouriOklahomaFixture } from "@/lib/line-curve/fixtures/missouri-oklahoma";
export type {
  LineCurvePoint,
  LineCurveResult,
  TwoLegCombo,
  TwoLegOptimizeResult,
  ResearchLabel,
} from "@/lib/line-curve/types";
