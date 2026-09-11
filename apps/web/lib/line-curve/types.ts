/**
 * Line Curve research types.
 * Alternate-spread pricing surface — not a teaser calculator.
 */

export type LineCurveSport = "cfb" | "nfl";

export type ResearchLabel =
  | "BEST VALUE"
  | "FAIR"
  | "OVERPRICED"
  | "INSUFFICIENT";

export type LineCurvePoint = {
  eventId: string;
  side: string;
  book: string;
  baseLine: number;
  altLine: number;
  americanOdds: number;
  impliedProbability: number;
  modelCoverProbability: number;
  modelPushProbability: number;
  modelLossProbability: number;
  fairAmericanOdds: number;
  edgePct: number;
  evPerDollar: number;
  incrementalProbabilityGain: number | null;
  incrementalPriceCost: number | null;
  marginalCostPerProbPoint: number | null;
  oddsSnapshotId: string;
  modelRunId: string;
  timestamp: string;
  label: ResearchLabel;
  bookmakerHold: number | null;
};

/** Cover / push / loss masses. Must sum to 1 within tolerance. */
export type OutcomeMass = {
  cover: number;
  push: number;
  loss: number;
};

/**
 * Phase 1 default is independence — but it is never silent.
 * Correlation adjustment is a reserved interface for later same-game / slate work.
 */
export type JointCorrelationAssumption = "independent" | "adjusted";

export type JointCorrelationAdjustment = {
  rho?: number;
  source?: string;
};

export type JointCorrelationMeta = {
  assumption: JointCorrelationAssumption;
  documented: true;
  adjustment: JointCorrelationAdjustment | null;
  note: string;
};

export type JointMass = {
  bothCover: number;
  aCoverBPush: number;
  aPushBCover: number;
  bothPush: number;
  anyLoss: number;
};

export type JointCorrelationModel = {
  assumption: JointCorrelationAssumption;
  adjustment: JointCorrelationAdjustment | null;
  note: string;
  joint: (legA: OutcomeMass, legB: OutcomeMass) => JointMass;
};

export type PostedAlt = {
  line: number;
  americanOdds: number;
  opposingAmericanOdds?: number | null;
};

export type OddsAltSnapshotSource =
  | "odds_api"
  | "research_fixture"
  | "injected";

export type OddsAltSnapshot = {
  eventId: string;
  sport: LineCurveSport;
  book: string;
  homeTeam: string;
  awayTeam: string;
  capturedAt: string;
  oddsSnapshotId: string;
  source: OddsAltSnapshotSource;
  /** Mainline spread for each side name (Odds API team name). */
  baseLineBySide: Record<string, number>;
  altsBySide: Record<string, PostedAlt[]>;
};

export type ModelMarginInput = {
  eventId: string;
  modelRunId: string;
  sport: LineCurveSport;
  homeTeam: string;
  awayTeam: string;
  /** Odds API / KEI sign: negative = home favored. */
  modelSpreadHome: number;
  expectedHomeScore: number;
  expectedAwayScore: number;
  marginSd: number;
};

export type LineCurveFailureCode =
  | "stale_odds"
  | "missing_odds"
  | "duplicate_odds"
  | "inconsistent_odds"
  | "missing_model_run"
  | "unbound_model_event"
  | "missing_alt_price"
  | "invalid_american"
  | "missing_snapshot";

export type LineCurveClosed = {
  ok: false;
  code: LineCurveFailureCode;
  message: string;
  label: "INSUFFICIENT";
};

export type LineCurveOk = {
  ok: true;
  sport: LineCurveSport;
  eventId: string;
  side: string;
  book: string;
  baseLine: number;
  modelFairLine: number;
  modelRunId: string;
  oddsSnapshotId: string;
  timestamp: string;
  points: LineCurvePoint[];
  winProbability: number;
  pushStraightUp: number;
};

export type LineCurveResult = LineCurveOk | LineCurveClosed;

export type TwoLegInput = {
  eventId: string;
  side: string;
  snapshot: OddsAltSnapshot;
  model: ModelMarginInput;
};

export type QuotedParlayPrice = {
  lineA: number;
  lineB: number;
  americanOdds: number;
};

export type TwoLegCombo = {
  rank: number;
  lineA: number;
  lineB: number;
  bookParlayAmerican: number;
  parlayPriceSource: "book_quoted" | "multiplicative_from_posted_legs";
  modelJointCoverProbability: number;
  modelJointPushReduceProbability: number;
  modelAnyLossProbability: number;
  fairAmericanOdds: number;
  evPerDollar: number;
  edgePct: number;
  label: ResearchLabel;
  correlation: JointCorrelationMeta;
  oddsSnapshotIdA: string;
  oddsSnapshotIdB: string;
  modelRunIdA: string;
  modelRunIdB: string;
  timestamp: string;
};

export type TwoLegOptimizeOk = {
  ok: true;
  book: string;
  sideA: string;
  sideB: string;
  eventIdA: string;
  eventIdB: string;
  correlation: JointCorrelationMeta;
  combos: TwoLegCombo[];
};

export type TwoLegOptimizeResult = TwoLegOptimizeOk | LineCurveClosed;

export const LINE_CURVE_MAX_AGE_MS = 2 * 60 * 60 * 1000;

export const INDEPENDENT_JOINT_NOTE =
  "Phase 1 joint probability uses an explicit independence assumption: the product of each leg's cover/push/loss masses. This is not a silent multiply of two cover percentages. Correlation adjustment is reserved on JointCorrelationModel and will be filled in later.";
