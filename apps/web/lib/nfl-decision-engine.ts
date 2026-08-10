/**
 * KosEdge NFL Decision Engine (Edge Board Action Layer).
 *
 * Doctrine
 * --------
 * We bet prices, not teams.
 * The same game can be a PLAY, LEAN, or PASS depending only on the current market number.
 *
 * This layer sits on top of locked model fair lines. It does not change true PR /
 * season-engine math, and it does not unlock or alter the locked preseason baseline.
 *
 * Contract coexistence (Model vs KEI vs Edge)
 * ------------------------------------------
 * - Model research fair → decision-engine fair vs market (this module).
 * - KEI reprice → published product handicap on Edge Board columns.
 * - Edge / publish tags (publishTag*) → KEI vs market only (existing PLAY desk tags).
 * - Action layer (this module) → Model fair vs market for Action Labels + Play-To.
 *
 * Mirrors services/model-service/src/services/nfl_decision_engine.py
 */

export const BREAKEVEN_ATS_MINUS_110 = 0.5238;

export const SPREAD_KEY_NUMBERS = [3, 7, 10, 14] as const;
export const TOTAL_KEY_NUMBERS = [37, 41, 44, 47, 51] as const;

export const COVER_PASS_MAX = 0.53;
export const COVER_LEAN_MAX = 0.54;
export const COVER_PLAY_MAX = 0.56;
export const COVER_STRONG_MAX = 0.58;
export const COVER_MODEL_WARNING = 0.6;

export const TOTAL_PASS_MAX = 1.5;
export const TOTAL_STRONG_MIN = 3.5;

export const CONFIDENCE_PLAY_MIN = 0.55;
export const CONFIDENCE_BEST_BET_MIN = 0.75;

export type ActionLabel =
  | "PASS"
  | "LEAN"
  | "PLAY"
  | "BEST VALUE"
  | "ALERT"
  | "STAY AWAY";

export type PointGrade =
  | "PASS"
  | "LEAN"
  | "PLAY"
  | "STRONG PLAY"
  | "EXCEPTIONAL";

export type WeekRegime = "early" | "standard" | "inseason" | "late";
export type DecisionMarket = "spread" | "total";
export type ConfidenceBand = "LOW" | "MEDIUM" | "HIGH";

export type SidePointThresholds = {
  passMax: number;
  leanMax: number;
  playMin: number;
  strongMin: number;
};

export const EARLY_SIDE: SidePointThresholds = {
  passMax: 1.5,
  leanMax: 2.0,
  playMin: 2.5,
  strongMin: 3.5,
};

export const STANDARD_SIDE: SidePointThresholds = {
  passMax: 1.0,
  leanMax: 1.5,
  playMin: 2.0,
  strongMin: 3.0,
};

export const INSEASON_SIDE: SidePointThresholds = {
  passMax: 1.0,
  leanMax: 1.5,
  playMin: 2.0,
  strongMin: 3.0,
};

export type PlayToLadder = {
  sideOrTotal: string;
  playTo: number;
  leanTo: number;
  passFrom: number;
  fairLine: number;
  marketLine: number;
  edgePoints: number;
  notes: string;
};

export type MarketConfirmation = {
  modelFair: number | null;
  opening: number | null;
  current: number | null;
  closing: number | null;
  confirmsThesis: boolean | null;
  weakensThesis: boolean | null;
  note: string;
};

export type ConfidenceAssessment = {
  score: number;
  band: ConfidenceBand;
  factors: Record<string, unknown>;
  unresolvedFlags: string[];
};

export type DecisionResult = {
  market: DecisionMarket;
  actionLabel: ActionLabel;
  pointGrade: PointGrade;
  edgeMagnitude: number;
  modelConfidence: ConfidenceAssessment;
  coverProb: number | null;
  coverGrade: PointGrade | null;
  playTo: PlayToLadder | null;
  marketConfirmation: MarketConfirmation;
  isBestBet: boolean;
  modelWarning: boolean;
  keyNumberCross: boolean;
  priceStillAvailable: boolean;
  numericalEdge: boolean;
  confidenceOk: boolean;
  reason: string;
  week: number | null;
  weekRegime: WeekRegime;
  fairLine: number | null;
  marketLine: number | null;
};

export function weekRegime(week: number | null | undefined): WeekRegime {
  if (week == null || !Number.isFinite(week)) return "early";
  const w = Math.trunc(week);
  if (w <= 2) return "early";
  if (w >= 6 && w <= 12) return "inseason";
  if (w >= 13) return "late";
  return "standard";
}

export function sideThresholdsForWeek(
  week: number | null | undefined,
): SidePointThresholds {
  const regime = weekRegime(week);
  if (regime === "early") return EARLY_SIDE;
  if (regime === "inseason" || regime === "late") return INSEASON_SIDE;
  return STANDARD_SIDE;
}

export function confidenceBand(score: number): ConfidenceBand {
  const s = Math.max(0, Math.min(1, score));
  if (s >= 0.75) return "HIGH";
  if (s >= 0.55) return "MEDIUM";
  return "LOW";
}

/** Default clear-board base (0.72 → MEDIUM). Not a calibrated cover probability. */
export const CONFIDENCE_TIER_BASE = 0.72;

/**
 * True when confidence is the untuned tier constant (no flags / no historical fit).
 * UI should label as a band, not invent false precision like "72%".
 */
export function isTierConstantConfidence(
  assessment: Pick<ConfidenceAssessment, "score" | "unresolvedFlags"> & {
    factors?: ConfidenceAssessment["factors"];
  },
): boolean {
  if (assessment.unresolvedFlags.length > 0) return false;
  const hf = assessment.factors?.historicalFit;
  if (typeof hf === "number" && Number.isFinite(hf)) {
    return false;
  }
  return Math.abs(assessment.score - CONFIDENCE_TIER_BASE) < 1e-9;
}

export function assessConfidence(args: {
  baseScore?: number | null;
  schemeStable?: boolean;
  injuryClear?: boolean;
  weatherClear?: boolean;
  qbClear?: boolean;
  historicalFit?: number | null;
  conflictingInputs?: boolean;
  liquidityOk?: boolean;
  extraFlags?: string[];
} = {}): ConfidenceAssessment {
  let score = args.baseScore == null ? 0.72 : Number(args.baseScore);
  const flags: string[] = [];
  if (args.schemeStable === false) {
    score -= 0.12;
    flags.push("scheme_unstable");
  }
  if (args.injuryClear === false) {
    score -= 0.18;
    flags.push("injury_unresolved");
  }
  if (args.weatherClear === false) {
    score -= 0.1;
    flags.push("weather_unresolved");
  }
  if (args.qbClear === false) {
    score -= 0.22;
    flags.push("qb_unresolved");
  }
  if (args.conflictingInputs) {
    score -= 0.25;
    flags.push("conflicting_inputs");
  }
  if (args.liquidityOk === false) {
    score -= 0.08;
    flags.push("liquidity_thin");
  }
  if (args.historicalFit != null && Number.isFinite(args.historicalFit)) {
    const hf = Math.max(0, Math.min(1, Number(args.historicalFit)));
    score = 0.7 * score + 0.3 * hf;
  }
  if (args.extraFlags?.length) flags.push(...args.extraFlags.filter(Boolean));
  score = Math.max(0, Math.min(1, Math.round(score * 10000) / 10000));
  return {
    score,
    band: confidenceBand(score),
    factors: {
      schemeStable: args.schemeStable !== false,
      injuryClear: args.injuryClear !== false,
      weatherClear: args.weatherClear !== false,
      qbClear: args.qbClear !== false,
      conflictingInputs: Boolean(args.conflictingInputs),
      liquidityOk: args.liquidityOk !== false,
      historicalFit: args.historicalFit ?? null,
    },
    unresolvedFlags: flags,
  };
}

export function gradeSidePoints(
  absEdge: number,
  week?: number | null,
): PointGrade {
  const e = Math.abs(Number(absEdge));
  const t = sideThresholdsForWeek(week);
  if (e < t.passMax) return "PASS";
  if (e < t.playMin) return "LEAN";
  if (e < t.strongMin) return "PLAY";
  return "STRONG PLAY";
}

export function gradeTotalPoints(absEdge: number): PointGrade {
  const e = Math.abs(Number(absEdge));
  if (e < TOTAL_PASS_MAX) return "PASS";
  if (e < 2.5) return "LEAN";
  if (e < TOTAL_STRONG_MIN) return "PLAY";
  return "STRONG PLAY";
}

export function gradeCoverProb(
  coverProb: number | null | undefined,
): PointGrade | null {
  if (coverProb == null || !Number.isFinite(coverProb)) return null;
  const p = Number(coverProb);
  if (p < COVER_PASS_MAX) return "PASS";
  if (p < COVER_LEAN_MAX) return "LEAN";
  if (p < COVER_PLAY_MAX) return "PLAY";
  if (p < COVER_STRONG_MAX) return "STRONG PLAY";
  return "EXCEPTIONAL";
}

export function crossesKeyNumber(
  fair: number,
  market: number,
  marketKind: DecisionMarket = "spread",
): boolean {
  const keys = marketKind === "spread" ? SPREAD_KEY_NUMBERS : TOTAL_KEY_NUMBERS;
  const lo = Math.min(fair, market);
  const hi = Math.max(fair, market);
  if (hi <= lo) return false;
  for (const k of keys) {
    if ((lo < k && k < hi) || (lo < -k && -k < hi)) return true;
  }
  return false;
}

export function preferKeyNumberEdge(
  absEdgeA: number,
  crossesA: boolean,
  absEdgeB: number,
  crossesB: boolean,
): "a" | "b" | "tie" {
  if (Math.abs(absEdgeA - absEdgeB) < 1e-9) {
    if (crossesA && !crossesB) return "a";
    if (crossesB && !crossesA) return "b";
    return "tie";
  }
  if (crossesA && !crossesB && absEdgeA + 0.5 >= absEdgeB) return "a";
  if (crossesB && !crossesA && absEdgeB + 0.5 >= absEdgeA) return "b";
  return absEdgeA > absEdgeB ? "a" : "b";
}

function roundHalf(x: number): number {
  return Math.round(x * 2) / 2;
}

export function buildSidePlayToLadder(args: {
  fairSpreadHome: number;
  marketSpreadHome: number;
  homeAbbr?: string;
  awayAbbr?: string;
}): PlayToLadder {
  const edge = args.fairSpreadHome - args.marketSpreadHome;
  const likesHome = edge < 0;
  const absEdge = Math.abs(edge);
  if (likesHome) {
    const team = args.homeAbbr ?? "HOME";
    const marketNum = args.marketSpreadHome;
    let playTo = roundHalf(marketNum + absEdge / 3);
    let leanTo = roundHalf(marketNum + absEdge / 2);
    const passFrom = roundHalf(marketNum + (absEdge * 2) / 3);
    if (playTo < leanTo) [playTo, leanTo] = [leanTo, playTo];
    return {
      sideOrTotal: `${team} ${marketNum >= 0 ? "+" : ""}${marketNum}`,
      playTo,
      leanTo,
      passFrom,
      fairLine: args.fairSpreadHome,
      marketLine: args.marketSpreadHome,
      edgePoints: Math.round(absEdge * 1000) / 1000,
      notes: `Play ${team} to ${fmtSigned(playTo)}; lean ${fmtSigned(leanTo)}; pass ${fmtSigned(passFrom)} or worse`,
    };
  }
  const team = args.awayAbbr ?? "AWAY";
  const marketNum = -args.marketSpreadHome;
  const playTo = roundHalf(marketNum - absEdge / 3);
  const leanTo = roundHalf(marketNum - absEdge / 2);
  const passFrom = roundHalf(marketNum - (absEdge * 2) / 3);
  return {
    sideOrTotal: `${team} ${fmtSigned(marketNum)}`,
    playTo,
    leanTo,
    passFrom,
    fairLine: args.fairSpreadHome,
    marketLine: args.marketSpreadHome,
    edgePoints: Math.round(absEdge * 1000) / 1000,
    notes: `Play ${team} to ${fmtSigned(playTo)}; lean ${fmtSigned(leanTo)}; pass ${fmtSigned(passFrom)} or worse`,
  };
}

export function buildTotalPlayToLadder(args: {
  fairTotal: number;
  marketTotal: number;
}): PlayToLadder {
  const edge = args.fairTotal - args.marketTotal;
  const likesOver = edge > 0;
  const absEdge = Math.abs(edge);
  const m = args.marketTotal;
  if (likesOver) {
    const playTo = roundHalf(m + 0.5);
    const leanLo = roundHalf(m + 1.0);
    const leanHi = roundHalf(m + 1.5);
    const passFrom = roundHalf(m + 2.0);
    return {
      sideOrTotal: `Over ${m}`,
      playTo,
      leanTo: leanHi,
      passFrom,
      fairLine: args.fairTotal,
      marketLine: args.marketTotal,
      edgePoints: Math.round(absEdge * 1000) / 1000,
      notes: `Play Over ${playTo} or better; lean ${leanLo}–${leanHi}; pass ${passFrom}+`,
    };
  }
  const playTo = roundHalf(m - 0.5);
  const leanLo = roundHalf(m - 1.5);
  const leanHi = roundHalf(m - 1.0);
  const passFrom = roundHalf(m - 2.0);
  return {
    sideOrTotal: `Under ${m}`,
    playTo,
    leanTo: leanLo,
    passFrom,
    fairLine: args.fairTotal,
    marketLine: args.marketTotal,
    edgePoints: Math.round(absEdge * 1000) / 1000,
    notes: `Play Under ${playTo} or better; lean ${leanLo}–${leanHi}; pass ${passFrom} or lower`,
  };
}

function fmtSigned(n: number): string {
  if (Object.is(n, -0) || n === 0) return "+0";
  return n > 0 ? `+${n}` : String(n);
}

export function assessMarketConfirmation(args: {
  modelFair: number | null | undefined;
  opening: number | null | undefined;
  current: number | null | undefined;
  closing?: number | null;
  likesHomeOrOver?: boolean | null;
}): MarketConfirmation {
  let confirms: boolean | null = null;
  let weakens: boolean | null = null;
  let note = "Market movement is information only; fair line unchanged.";
  if (
    args.modelFair != null &&
    args.opening != null &&
    args.current != null &&
    args.likesHomeOrOver != null
  ) {
    const move = Number(args.current) - Number(args.opening);
    const towardModel =
      (Number(args.modelFair) - Number(args.opening)) * move > 0;
    confirms = towardModel;
    weakens = !towardModel && Math.abs(move) >= 0.5;
    note = confirms
      ? "Market moved toward model fair — confirms thesis; fair unchanged."
      : weakens
        ? "Market moved away from model fair — weakens thesis; fair unchanged."
        : note;
  }
  return {
    modelFair: args.modelFair ?? null,
    opening: args.opening ?? null,
    current: args.current ?? null,
    closing: args.closing ?? null,
    confirmsThesis: confirms,
    weakensThesis: weakens,
    note,
  };
}

function pointRank(grade: PointGrade): number {
  const order: Record<PointGrade, number> = {
    PASS: 0,
    LEAN: 1,
    PLAY: 2,
    "STRONG PLAY": 3,
    EXCEPTIONAL: 4,
  };
  return order[grade];
}

function mergeGrades(
  pointGrade: PointGrade,
  coverGrade: PointGrade | null,
): PointGrade {
  if (!coverGrade) return pointGrade;
  return pointRank(pointGrade) <= pointRank(coverGrade)
    ? pointGrade
    : coverGrade;
}

export function evaluateBestBet(args: {
  pointGrade: PointGrade;
  confidence: ConfidenceAssessment;
  priceAvailable: boolean;
  keyNumberCross: boolean;
  marketConfirmation: MarketConfirmation;
  matchupSupport: boolean;
  liquidityOk: boolean;
}): boolean {
  const largeEdge =
    args.pointGrade === "STRONG PLAY" ||
    args.pointGrade === "EXCEPTIONAL" ||
    (args.pointGrade === "PLAY" && args.keyNumberCross);
  const highConf =
    args.confidence.score >= CONFIDENCE_BEST_BET_MIN &&
    args.confidence.band === "HIGH";
  const limitedUnresolved = args.confidence.unresolvedFlags.length === 0;
  const favorableNumber =
    args.priceAvailable && !args.marketConfirmation.weakensThesis;
  return Boolean(
    largeEdge &&
      highConf &&
      favorableNumber &&
      limitedUnresolved &&
      args.matchupSupport &&
      args.liquidityOk,
  );
}

export function decideSide(args: {
  fairSpreadHome: number | null | undefined;
  marketSpreadHome: number | null | undefined;
  week?: number | null;
  coverProb?: number | null;
  openingSpreadHome?: number | null;
  closingSpreadHome?: number | null;
  homeAbbr?: string;
  awayAbbr?: string;
  confidence?: ConfidenceAssessment;
  priceStillAvailable?: boolean;
  matchupSupport?: boolean;
  liquidityOk?: boolean;
  stayAway?: boolean;
}): DecisionResult {
  const conf = args.confidence ?? assessConfidence();
  const week = args.week ?? null;
  const regime = weekRegime(week);
  const priceStillAvailable = args.priceStillAvailable !== false;
  const matchupSupport = args.matchupSupport !== false;
  const liquidityOk = args.liquidityOk !== false;
  const mc = assessMarketConfirmation({
    modelFair: args.fairSpreadHome,
    opening: args.openingSpreadHome,
    current: args.marketSpreadHome,
    closing: args.closingSpreadHome,
    likesHomeOrOver:
      args.fairSpreadHome == null || args.marketSpreadHome == null
        ? null
        : args.fairSpreadHome - args.marketSpreadHome < 0,
  });

  if (args.fairSpreadHome == null || args.marketSpreadHome == null) {
    return {
      market: "spread",
      actionLabel: "PASS",
      pointGrade: "PASS",
      edgeMagnitude: 0,
      modelConfidence: conf,
      coverProb: args.coverProb ?? null,
      coverGrade: gradeCoverProb(args.coverProb),
      playTo: null,
      marketConfirmation: mc,
      isBestBet: false,
      modelWarning: false,
      keyNumberCross: false,
      priceStillAvailable,
      numericalEdge: false,
      confidenceOk: false,
      reason: "missing_fair_or_market",
      week,
      weekRegime: regime,
      fairLine: args.fairSpreadHome ?? null,
      marketLine: args.marketSpreadHome ?? null,
    };
  }

  const edge = args.fairSpreadHome - args.marketSpreadHome;
  const absEdge = Math.abs(edge);
  let pointGrade = gradeSidePoints(absEdge, week);
  const coverGrade = gradeCoverProb(args.coverProb);
  let effective = mergeGrades(pointGrade, coverGrade);
  const keyCross = crossesKeyNumber(
    args.fairSpreadHome,
    args.marketSpreadHome,
    "spread",
  );
  if (keyCross && pointGrade === "LEAN" && absEdge >= 2.0) {
    if (pointRank(effective) < pointRank("PLAY")) effective = "PLAY";
    pointGrade = "PLAY";
  }

  const modelWarning =
    args.coverProb != null && Number(args.coverProb) >= COVER_MODEL_WARNING;
  const numericalEdge = ["LEAN", "PLAY", "STRONG PLAY", "EXCEPTIONAL"].includes(
    effective,
  );
  const confidenceOk =
    conf.score >= CONFIDENCE_PLAY_MIN &&
    !conf.unresolvedFlags.includes("qb_unresolved");
  const majorUncertainty = conf.unresolvedFlags.some((f) =>
    [
      "qb_unresolved",
      "injury_unresolved",
      "weather_unresolved",
      "conflicting_inputs",
    ].includes(f),
  );

  const ladderArgs = {
    fairSpreadHome: args.fairSpreadHome,
    marketSpreadHome: args.marketSpreadHome,
    homeAbbr: args.homeAbbr,
    awayAbbr: args.awayAbbr,
  };

  let actionLabel: ActionLabel;
  let reason: string;
  let playTo: PlayToLadder | null = null;

  if (args.stayAway || conf.unresolvedFlags.includes("conflicting_inputs")) {
    actionLabel = "STAY AWAY";
    reason = "conflicting_inputs_or_bad_market";
  } else if (numericalEdge && majorUncertainty) {
    actionLabel = "ALERT";
    reason = "edge_with_material_uncertainty";
    playTo = buildSidePlayToLadder(ladderArgs);
  } else if (effective === "PASS") {
    actionLabel = "PASS";
    reason = "edge_below_week_threshold";
  } else if (effective === "LEAN") {
    actionLabel = "LEAN";
    reason = "mild_edge_watch_list";
    playTo = buildSidePlayToLadder(ladderArgs);
  } else if (numericalEdge && confidenceOk && priceStillAvailable) {
    const isBb = evaluateBestBet({
      pointGrade: effective === "EXCEPTIONAL" ? "STRONG PLAY" : effective,
      confidence: conf,
      priceAvailable: priceStillAvailable,
      keyNumberCross: keyCross,
      marketConfirmation: mc,
      matchupSupport,
      liquidityOk,
    });
    actionLabel = isBb ? "BEST VALUE" : "PLAY";
    reason = isBb ? "best_bet_strict_cleared" : "play_triple_cleared";
    playTo = buildSidePlayToLadder(ladderArgs);
  } else if (numericalEdge && !priceStillAvailable) {
    actionLabel = "ALERT";
    reason = "edge_but_price_gone";
    playTo = buildSidePlayToLadder(ladderArgs);
  } else if (numericalEdge && !confidenceOk) {
    actionLabel = "ALERT";
    reason = "edge_but_confidence_insufficient";
    playTo = buildSidePlayToLadder(ladderArgs);
  } else {
    actionLabel = "LEAN";
    reason = "partial_play_requirements";
    playTo = buildSidePlayToLadder(ladderArgs);
  }

  if (
    modelWarning &&
    (actionLabel === "PLAY" ||
      actionLabel === "BEST VALUE" ||
      actionLabel === "LEAN")
  ) {
    reason = `${reason}|model_warning_60pct_plus_ats`;
  }

  return {
    market: "spread",
    actionLabel,
    pointGrade,
    edgeMagnitude: Math.round(absEdge * 1000) / 1000,
    modelConfidence: conf,
    coverProb: args.coverProb ?? null,
    coverGrade,
    playTo,
    marketConfirmation: mc,
    isBestBet: actionLabel === "BEST VALUE",
    modelWarning,
    keyNumberCross: keyCross,
    priceStillAvailable,
    numericalEdge,
    confidenceOk,
    reason,
    week,
    weekRegime: regime,
    fairLine: args.fairSpreadHome,
    marketLine: args.marketSpreadHome,
  };
}

export function decideTotal(args: {
  fairTotal: number | null | undefined;
  marketTotal: number | null | undefined;
  week?: number | null;
  overProb?: number | null;
  openingTotal?: number | null;
  closingTotal?: number | null;
  confidence?: ConfidenceAssessment;
  priceStillAvailable?: boolean;
  matchupSupport?: boolean;
  liquidityOk?: boolean;
  stayAway?: boolean;
}): DecisionResult {
  const conf = args.confidence ?? assessConfidence();
  const week = args.week ?? null;
  const regime = weekRegime(week);
  const priceStillAvailable = args.priceStillAvailable !== false;
  const matchupSupport = args.matchupSupport !== false;
  const liquidityOk = args.liquidityOk !== false;
  const mc = assessMarketConfirmation({
    modelFair: args.fairTotal,
    opening: args.openingTotal,
    current: args.marketTotal,
    closing: args.closingTotal,
    likesHomeOrOver:
      args.fairTotal == null || args.marketTotal == null
        ? null
        : args.fairTotal - args.marketTotal > 0,
  });

  if (args.fairTotal == null || args.marketTotal == null) {
    return {
      market: "total",
      actionLabel: "PASS",
      pointGrade: "PASS",
      edgeMagnitude: 0,
      modelConfidence: conf,
      coverProb: args.overProb ?? null,
      coverGrade: gradeCoverProb(args.overProb),
      playTo: null,
      marketConfirmation: mc,
      isBestBet: false,
      modelWarning: false,
      keyNumberCross: false,
      priceStillAvailable,
      numericalEdge: false,
      confidenceOk: false,
      reason: "missing_fair_or_market",
      week,
      weekRegime: regime,
      fairLine: args.fairTotal ?? null,
      marketLine: args.marketTotal ?? null,
    };
  }

  const edge = args.fairTotal - args.marketTotal;
  const absEdge = Math.abs(edge);
  const pointGrade = gradeTotalPoints(absEdge);
  let coverSideProb = args.overProb ?? null;
  if (args.overProb != null && edge < 0) {
    coverSideProb = 1 - Number(args.overProb);
  }
  const coverGrade = gradeCoverProb(coverSideProb);
  const effective = mergeGrades(pointGrade, coverGrade);
  const keyCross = crossesKeyNumber(args.fairTotal, args.marketTotal, "total");
  const modelWarning =
    coverSideProb != null && Number(coverSideProb) >= COVER_MODEL_WARNING;
  const numericalEdge = ["LEAN", "PLAY", "STRONG PLAY", "EXCEPTIONAL"].includes(
    effective,
  );
  const confidenceOk = conf.score >= CONFIDENCE_PLAY_MIN;
  const majorUncertainty =
    conf.unresolvedFlags.length > 0 && conf.score < CONFIDENCE_PLAY_MIN;

  const ladderArgs = {
    fairTotal: args.fairTotal,
    marketTotal: args.marketTotal,
  };

  let actionLabel: ActionLabel;
  let reason: string;
  let playTo: PlayToLadder | null = null;

  if (args.stayAway || conf.unresolvedFlags.includes("conflicting_inputs")) {
    actionLabel = "STAY AWAY";
    reason = "conflicting_inputs_or_bad_market";
  } else if (numericalEdge && majorUncertainty) {
    actionLabel = "ALERT";
    reason = "edge_with_material_uncertainty";
    playTo = buildTotalPlayToLadder(ladderArgs);
  } else if (effective === "PASS") {
    actionLabel = "PASS";
    reason = "edge_below_total_threshold";
  } else if (effective === "LEAN") {
    actionLabel = "LEAN";
    reason = "mild_edge_watch_list";
    playTo = buildTotalPlayToLadder(ladderArgs);
  } else if (numericalEdge && confidenceOk && priceStillAvailable) {
    const isBb = evaluateBestBet({
      pointGrade: effective === "EXCEPTIONAL" ? "STRONG PLAY" : effective,
      confidence: conf,
      priceAvailable: priceStillAvailable,
      keyNumberCross: keyCross,
      marketConfirmation: mc,
      matchupSupport,
      liquidityOk,
    });
    actionLabel = isBb ? "BEST VALUE" : "PLAY";
    reason = isBb ? "best_bet_strict_cleared" : "play_triple_cleared";
    playTo = buildTotalPlayToLadder(ladderArgs);
  } else if (numericalEdge && !priceStillAvailable) {
    actionLabel = "ALERT";
    reason = "edge_but_price_gone";
    playTo = buildTotalPlayToLadder(ladderArgs);
  } else if (numericalEdge && !confidenceOk) {
    actionLabel = "ALERT";
    reason = "edge_but_confidence_insufficient";
    playTo = buildTotalPlayToLadder(ladderArgs);
  } else {
    actionLabel = "LEAN";
    reason = "partial_play_requirements";
    playTo = buildTotalPlayToLadder(ladderArgs);
  }

  return {
    market: "total",
    actionLabel,
    pointGrade,
    edgeMagnitude: Math.round(absEdge * 1000) / 1000,
    modelConfidence: conf,
    coverProb: coverSideProb,
    coverGrade,
    playTo,
    marketConfirmation: mc,
    isBestBet: actionLabel === "BEST VALUE",
    modelWarning,
    keyNumberCross: keyCross,
    priceStillAvailable,
    numericalEdge,
    confidenceOk,
    reason,
    week,
    weekRegime: regime,
    fairLine: args.fairTotal,
    marketLine: args.marketTotal,
  };
}

export function decideGame(args: {
  week: number | null | undefined;
  fairSpreadHome: number | null | undefined;
  marketSpreadHome: number | null | undefined;
  fairTotal: number | null | undefined;
  marketTotal: number | null | undefined;
  homeAbbr?: string;
  awayAbbr?: string;
  coverProb?: number | null;
  overProb?: number | null;
  openingSpreadHome?: number | null;
  openingTotal?: number | null;
  closingSpreadHome?: number | null;
  closingTotal?: number | null;
  confidence?: ConfidenceAssessment;
  priceStillAvailableSpread?: boolean;
  priceStillAvailableTotal?: boolean;
  matchupSupport?: boolean;
  liquidityOk?: boolean;
  stayAway?: boolean;
}): {
  doctrine: string;
  week: number | null;
  weekRegime: WeekRegime;
  spread: DecisionResult;
  total: DecisionResult;
  edgeMagnitudeSpread: number;
  edgeMagnitudeTotal: number;
  modelConfidence: ConfidenceAssessment;
  actionLabelSpread: ActionLabel;
  actionLabelTotal: ActionLabel;
} {
  const conf = args.confidence ?? assessConfidence();
  const week = args.week ?? null;
  const spread = decideSide({
    fairSpreadHome: args.fairSpreadHome,
    marketSpreadHome: args.marketSpreadHome,
    week,
    coverProb: args.coverProb,
    openingSpreadHome: args.openingSpreadHome,
    closingSpreadHome: args.closingSpreadHome,
    homeAbbr: args.homeAbbr,
    awayAbbr: args.awayAbbr,
    confidence: conf,
    priceStillAvailable: args.priceStillAvailableSpread,
    matchupSupport: args.matchupSupport,
    liquidityOk: args.liquidityOk,
    stayAway: args.stayAway,
  });
  const total = decideTotal({
    fairTotal: args.fairTotal,
    marketTotal: args.marketTotal,
    week,
    overProb: args.overProb,
    openingTotal: args.openingTotal,
    closingTotal: args.closingTotal,
    confidence: conf,
    priceStillAvailable: args.priceStillAvailableTotal,
    matchupSupport: args.matchupSupport,
    liquidityOk: args.liquidityOk,
    stayAway: args.stayAway,
  });
  return {
    doctrine: "We bet prices, not teams.",
    week,
    weekRegime: weekRegime(week),
    spread,
    total,
    edgeMagnitudeSpread: spread.edgeMagnitude,
    edgeMagnitudeTotal: total.edgeMagnitude,
    modelConfidence: conf,
    actionLabelSpread: spread.actionLabel,
    actionLabelTotal: total.actionLabel,
  };
}

/** Serialize DecisionResult for Edge Board / API passthrough (snake_case). */
export function decisionResultToApi(d: DecisionResult): Record<string, unknown> {
  return {
    market: d.market,
    action_label: d.actionLabel,
    point_grade: d.pointGrade,
    edge_magnitude: d.edgeMagnitude,
    model_confidence: {
      score: d.modelConfidence.score,
      band: d.modelConfidence.band,
      factors: d.modelConfidence.factors,
      unresolved_flags: d.modelConfidence.unresolvedFlags,
    },
    cover_prob: d.coverProb,
    cover_grade: d.coverGrade,
    play_to: d.playTo
      ? {
          side_or_total: d.playTo.sideOrTotal,
          play_to: d.playTo.playTo,
          lean_to: d.playTo.leanTo,
          pass_from: d.playTo.passFrom,
          fair_line: d.playTo.fairLine,
          market_line: d.playTo.marketLine,
          edge_points: d.playTo.edgePoints,
          notes: d.playTo.notes,
        }
      : null,
    market_confirmation: {
      model_fair: d.marketConfirmation.modelFair,
      opening: d.marketConfirmation.opening,
      current: d.marketConfirmation.current,
      closing: d.marketConfirmation.closing,
      confirms_thesis: d.marketConfirmation.confirmsThesis,
      weakens_thesis: d.marketConfirmation.weakensThesis,
      note: d.marketConfirmation.note,
    },
    is_best_bet: d.isBestBet,
    model_warning: d.modelWarning,
    key_number_cross: d.keyNumberCross,
    price_still_available: d.priceStillAvailable,
    numerical_edge: d.numericalEdge,
    confidence_ok: d.confidenceOk,
    reason: d.reason,
    week: d.week,
    week_regime: d.weekRegime,
    fair_line: d.fairLine,
    market_line: d.marketLine,
  };
}
