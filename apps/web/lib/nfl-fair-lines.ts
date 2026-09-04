import "server-only";
import { env } from "@/lib/config/env";
import { inferHonestEmptySlateStatus } from "@/lib/model-service-status";
import { UPSTREAM_TIMEOUT_MS, upstreamFetch } from "@/lib/upstream-fetch";
import { keiRepriceDriverLine } from "@/lib/nfl-kei-driver-line";
import { canonicalKickoffForMatchup } from "@/lib/nfl-canonical-schedule";
import { humanizeCompetitionTokensInText } from "@/lib/nfl-depth-pack-freshness";
import type {
  ActionLabel,
  ConfidenceAssessment,
  DecisionResult,
  WeekRegime,
} from "@/lib/nfl-decision-engine";

export { keiRepriceDriverLine };

export type NflDecisionConfidence = ConfidenceAssessment;

export type NflFairLineDecision = {
  doctrine?: string;
  week: number | null;
  weekRegime: WeekRegime;
  spread: DecisionResult | null;
  total: DecisionResult | null;
  edgeMagnitudeSpread: number | null;
  edgeMagnitudeTotal: number | null;
  modelConfidence: NflDecisionConfidence | null;
  actionLabelSpread: ActionLabel | null;
  actionLabelTotal: ActionLabel | null;
};

export type NflKeiRepriceFactor = {
  factor: string;
  applied: boolean;
  team: string | null;
  direction: string;
  spreadPts: number;
  totalPts: number;
  confidenceDelta: number;
  reason: string;
};

export type NflKeiRepriceLog = {
  applied: boolean;
  skipped: boolean;
  reason: string;
  spreadDelta: number;
  totalDelta: number;
  qbClear: boolean | null;
  injuryClear: boolean | null;
  capped: boolean;
  appliedFactors: NflKeiRepriceFactor[];
  consideredNotApplied: NflKeiRepriceFactor[];
};

export type NflFairLineRow = {
  gameId: string;
  season: number;
  week: number | null;
  /** REG / PRE / POST — PRE never gets season PLAY tags under info desk. */
  seasonType: string | null;
  startTime: string | null;
  gameDate: string | null;
  homeTeam: string;
  awayTeam: string;
  homeAbbr: string;
  awayAbbr: string;
  homeWinProb: number | null;
  awayWinProb: number | null;
  /** KEI handicap (published product line). Alias of spreadHome. */
  spreadHome: number | null;
  /** KEI handicap total. Alias of totalMean. */
  totalMean: number | null;
  fairHomeMl: number | null;
  fairAwayMl: number | null;
  /** Explicit handicap namespace (same as published when API is current). */
  handicapSpreadHome: number | null;
  handicapTotal: number | null;
  handicapHomeWinProb: number | null;
  handicapAwayWinProb: number | null;
  handicapHomeMl: number | null;
  handicapAwayMl: number | null;
  /**
   * Research Model = pre-market-blend Monte Carlo fair when blend applied;
   * otherwise identity with handicap. ML/win probs are identity today.
   */
  modelSpreadHome: number | null;
  modelTotal: number | null;
  modelHomeWinProb: number | null;
  modelAwayWinProb: number | null;
  modelHomeMl: number | null;
  modelAwayMl: number | null;
  /** True when Model spread/total match KEI (no blend or Week 1 desk-factor divergence). */
  modelEqualsKei: boolean | null;
  /** Gate B adjustment log (Week 1 REG). Null/absent when reprice skipped. */
  keiReprice: NflKeiRepriceLog | null;
  modelVersion: string;
  simulationCount: number | null;
  projectionCreatedAt: string | null;
  marketHomeMl: number | null;
  marketAwayMl: number | null;
  marketTotal: number | null;
  marketSpreadHome: number | null;
  /**
   * First-captured / official open (home spread). Immutable once set upstream.
   * Null when history has no open yet — UI must show — (not invent open=current).
   */
  openSpreadHome: number | null;
  /** First-captured open total. */
  openTotal: number | null;
  /** Latest odds snapshot timestamp (ISO) for as-of / stale hints. */
  oddsCapturedAt: string | null;
  /** Best home spread number across books (pairs with best away). Shop column only. */
  bestSpreadHome: number | null;
  /** Best total number across books (Over-favorable). Shop column only. */
  bestTotal: number | null;
  bestSpreadBook: string | null;
  bestTotalBook: string | null;
  bestSpreadAwayJuice: number | null;
  bestSpreadHomeJuice: number | null;
  bestTotalOverJuice: number | null;
  bestTotalUnderJuice: number | null;
  /** DraftKings home spread (Odds API sign). PLAY grades this before FanDuel. */
  dkSpreadHome: number | null;
  fdSpreadHome: number | null;
  /** DK → FD → consensus. Never best-of-books. */
  stakeSpreadHome: number | null;
  stakeSpreadBook: string | null;
  dkTotal: number | null;
  fdTotal: number | null;
  stakeTotal: number | null;
  stakeTotalBook: string | null;
  marketHomeProbNoVig: number | null;
  mlEdgeProb: number | null;
  totalEdge: number | null;
  spreadEdge: number | null;
  marketJoined: boolean;
  /** Server publish policy (mirrors Edge Board; authoritative for PRE block). */
  publishTagSpread: "PLAY" | "LEAN" | "PASS" | null;
  publishTagTotal: "PLAY" | "LEAN" | "PASS" | null;
  publishTagMl: "PLAY" | "LEAN" | "PASS" | null;
  /**
   * Decision Engine action layer (Model fair vs market).
   * Coexists with publishTag* (KEI vs market). Does not replace KEI tags.
   */
  decision: NflFairLineDecision | null;
  actionLabelSpread: ActionLabel | null;
  actionLabelTotal: ActionLabel | null;
};

export type NflFairLinesResponse = {
  season: number;
  modelVersion: string;
  /**
   * Market capture stamp (Odds API last_update / stored odds_captured_at).
   * Null when unknown — never request/fetch time. Same honesty as oddsAsOf.
   */
  asOf: string | null;
  /** Latest market snapshot capture when books joined. */
  oddsAsOf: string | null;
  currentWeek: number;
  count: number;
  lines: NflFairLineRow[];
  window: { daysAhead: number; includePastDays: number };
  diagnostics: {
    oddsFeedStatus: string;
    oddsFeedError: string | null;
    oddsEventsSeen: number;
    marketJoinedCount: number;
    bookmakers: string[];
    kosedgeOnly: boolean;
    oddsPersisted?: {
      eventsPersisted: number;
      snapshotsInserted: number;
      historyUpserted: number;
    };
  };
  error?: string;
  slateStatus?: string;
};

function toNumberOrNull(value: unknown): number | null {
  if (value === null || value === undefined) return null;
  if (typeof value === "number") return Number.isFinite(value) ? value : null;
  if (typeof value === "string") {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function toNumber(value: unknown, fallback = 0): number {
  return toNumberOrNull(value) ?? fallback;
}

function toIsoOrNull(value: unknown): string | null {
  if (typeof value === "string") return value;
  if (value instanceof Date) return value.toISOString();
  return null;
}

function normalizePublishTag(value: unknown): "PLAY" | "LEAN" | "PASS" | null {
  if (value == null) return null;
  const token = String(value).trim().toUpperCase();
  if (!token) return null;
  if (token === "PLAY" || token === "LEAN" || token === "PASS") return token;
  return null;
}

const ACTION_LABELS = new Set<ActionLabel>([
  "PASS",
  "LEAN",
  "PLAY",
  "BEST VALUE",
  "ALERT",
  "STAY AWAY",
]);

function normalizeActionLabel(value: unknown): ActionLabel | null {
  if (value == null) return null;
  const token = String(value).trim().toUpperCase();
  if (ACTION_LABELS.has(token as ActionLabel)) return token as ActionLabel;
  return null;
}

function normalizeConfidence(raw: unknown): NflDecisionConfidence | null {
  if (!raw || typeof raw !== "object") return null;
  const o = raw as Record<string, unknown>;
  const score = toNumberOrNull(o.score);
  if (score == null) return null;
  const bandRaw = String(o.band ?? "").toUpperCase();
  const band =
    bandRaw === "HIGH" || bandRaw === "MEDIUM" || bandRaw === "LOW"
      ? bandRaw
      : score >= 0.75
        ? "HIGH"
        : score >= 0.55
          ? "MEDIUM"
          : "LOW";
  const flags = o.unresolved_flags ?? o.unresolvedFlags;
  return {
    score,
    band,
    factors:
      o.factors && typeof o.factors === "object"
        ? (o.factors as Record<string, unknown>)
        : {},
    unresolvedFlags: Array.isArray(flags) ? flags.map((f) => String(f)) : [],
  };
}

function normalizeKeiRepriceFactor(raw: unknown): NflKeiRepriceFactor | null {
  if (!raw || typeof raw !== "object") return null;
  const o = raw as Record<string, unknown>;
  const factor = typeof o.factor === "string" ? o.factor : "";
  if (!factor) return null;
  return {
    factor,
    applied: Boolean(o.applied),
    team: typeof o.team === "string" ? o.team : null,
    direction: typeof o.direction === "string" ? o.direction : "none",
    spreadPts: toNumber(o.spread_pts ?? o.spreadPts, 0),
    totalPts: toNumber(o.total_pts ?? o.totalPts, 0),
    confidenceDelta: toNumber(o.confidence_delta ?? o.confidenceDelta, 0),
    // Customer serialize: never leak pack snake_case (open_competition → Open competition).
    reason:
      typeof o.reason === "string"
        ? humanizeCompetitionTokensInText(o.reason)
        : "",
  };
}

function normalizeKeiReprice(raw: unknown): NflKeiRepriceLog | null {
  if (!raw || typeof raw !== "object") return null;
  const o = raw as Record<string, unknown>;
  const appliedFactors = Array.isArray(o.applied_factors ?? o.appliedFactors)
    ? ((o.applied_factors ?? o.appliedFactors) as unknown[])
        .map(normalizeKeiRepriceFactor)
        .filter((x): x is NflKeiRepriceFactor => x != null)
    : [];
  const considered = Array.isArray(
    o.considered_not_applied ?? o.consideredNotApplied,
  )
    ? ((o.considered_not_applied ?? o.consideredNotApplied) as unknown[])
        .map(normalizeKeiRepriceFactor)
        .filter((x): x is NflKeiRepriceFactor => x != null)
    : [];
  return {
    applied: Boolean(o.applied),
    skipped: Boolean(o.skipped),
    reason:
      typeof o.reason === "string"
        ? humanizeCompetitionTokensInText(o.reason)
        : "",
    spreadDelta: toNumber(o.spread_delta ?? o.spreadDelta, 0),
    totalDelta: toNumber(o.total_delta ?? o.totalDelta, 0),
    qbClear: typeof o.qb_clear === "boolean" ? o.qb_clear : null,
    injuryClear: typeof o.injury_clear === "boolean" ? o.injury_clear : null,
    capped: Boolean(o.capped),
    appliedFactors,
    consideredNotApplied: considered,
  };
}

function normalizeDecisionResult(
  raw: unknown,
  market: "spread" | "total",
): DecisionResult | null {
  if (!raw || typeof raw !== "object") return null;
  const o = raw as Record<string, unknown>;
  const actionLabel = normalizeActionLabel(o.action_label ?? o.actionLabel);
  if (!actionLabel) return null;
  const playToRaw = (o.play_to ?? o.playTo) as Record<string, unknown> | null;
  const mcRaw = (o.market_confirmation ?? o.marketConfirmation) as
    | Record<string, unknown>
    | null
    | undefined;
  const conf =
    normalizeConfidence(o.model_confidence ?? o.modelConfidence) ??
    ({
      score: 0,
      band: "LOW" as const,
      factors: {},
      unresolvedFlags: [],
    } satisfies NflDecisionConfidence);
  return {
    market,
    actionLabel,
    pointGrade: String(
      o.point_grade ?? o.pointGrade ?? "PASS",
    ) as DecisionResult["pointGrade"],
    edgeMagnitude: toNumber(o.edge_magnitude ?? o.edgeMagnitude, 0),
    modelConfidence: conf,
    coverProb: toNumberOrNull(o.cover_prob ?? o.coverProb),
    coverGrade: (o.cover_grade ??
      o.coverGrade ??
      null) as DecisionResult["coverGrade"],
    playTo: playToRaw
      ? {
          sideOrTotal: String(
            playToRaw.side_or_total ?? playToRaw.sideOrTotal ?? "",
          ),
          playTo: toNumber(playToRaw.play_to ?? playToRaw.playTo, 0),
          leanTo: toNumber(playToRaw.lean_to ?? playToRaw.leanTo, 0),
          passFrom: toNumber(playToRaw.pass_from ?? playToRaw.passFrom, 0),
          fairLine: toNumber(playToRaw.fair_line ?? playToRaw.fairLine, 0),
          marketLine: toNumber(
            playToRaw.market_line ?? playToRaw.marketLine,
            0,
          ),
          edgePoints: toNumber(
            playToRaw.edge_points ?? playToRaw.edgePoints,
            0,
          ),
          notes: String(playToRaw.notes ?? ""),
        }
      : null,
    marketConfirmation: {
      modelFair: toNumberOrNull(mcRaw?.model_fair ?? mcRaw?.modelFair),
      opening: toNumberOrNull(mcRaw?.opening),
      current: toNumberOrNull(mcRaw?.current),
      closing: toNumberOrNull(mcRaw?.closing),
      confirmsThesis:
        typeof (mcRaw?.confirms_thesis ?? mcRaw?.confirmsThesis) === "boolean"
          ? Boolean(mcRaw?.confirms_thesis ?? mcRaw?.confirmsThesis)
          : null,
      weakensThesis:
        typeof (mcRaw?.weakens_thesis ?? mcRaw?.weakensThesis) === "boolean"
          ? Boolean(mcRaw?.weakens_thesis ?? mcRaw?.weakensThesis)
          : null,
      note: String(mcRaw?.note ?? ""),
    },
    isBestBet: Boolean(o.is_best_bet ?? o.isBestBet),
    modelWarning: Boolean(o.model_warning ?? o.modelWarning),
    keyNumberCross: Boolean(o.key_number_cross ?? o.keyNumberCross),
    priceStillAvailable: Boolean(
      o.price_still_available ?? o.priceStillAvailable ?? true,
    ),
    numericalEdge: Boolean(o.numerical_edge ?? o.numericalEdge),
    confidenceOk: Boolean(o.confidence_ok ?? o.confidenceOk),
    reason: String(o.reason ?? ""),
    week: toNumberOrNull(o.week),
    weekRegime: String(o.week_regime ?? o.weekRegime ?? "early") as WeekRegime,
    fairLine: toNumberOrNull(o.fair_line ?? o.fairLine),
    marketLine: toNumberOrNull(o.market_line ?? o.marketLine),
  };
}

function normalizeDecision(raw: unknown): NflFairLineDecision | null {
  if (!raw || typeof raw !== "object") return null;
  const o = raw as Record<string, unknown>;
  const conf = normalizeConfidence(o.model_confidence ?? o.modelConfidence);
  return {
    doctrine:
      typeof o.doctrine === "string" ? o.doctrine : "We bet prices, not teams.",
    week: toNumberOrNull(o.week),
    weekRegime: String(o.week_regime ?? o.weekRegime ?? "early") as WeekRegime,
    spread: normalizeDecisionResult(o.spread, "spread"),
    total: normalizeDecisionResult(o.total, "total"),
    edgeMagnitudeSpread: toNumberOrNull(
      o.edge_magnitude_spread ?? o.edgeMagnitudeSpread,
    ),
    edgeMagnitudeTotal: toNumberOrNull(
      o.edge_magnitude_total ?? o.edgeMagnitudeTotal,
    ),
    modelConfidence: conf,
    actionLabelSpread: normalizeActionLabel(
      o.action_label_spread ?? o.actionLabelSpread,
    ),
    actionLabelTotal: normalizeActionLabel(
      o.action_label_total ?? o.actionLabelTotal,
    ),
  };
}

function normalizeFairLine(raw: Record<string, unknown>): NflFairLineRow {
  const week = toNumberOrNull(raw.week);
  const homeAbbr = String(raw.home_abbr ?? "—");
  const awayAbbr = String(raw.away_abbr ?? "—");
  const packed = canonicalKickoffForMatchup({
    gameId: typeof raw.game_id === "string" ? raw.game_id : null,
    season: toNumberOrNull(raw.season),
    week,
    awayAbbr,
    homeAbbr,
  });
  const oddsKickoff = toIsoOrNull(raw.start_time);
  return {
    gameId: String(raw.game_id ?? ""),
    season: toNumber(raw.season),
    week,
    seasonType:
      typeof raw.season_type === "string" && raw.season_type.trim()
        ? raw.season_type.trim().toUpperCase()
        : null,
    startTime: packed.found ? packed.kickoffUtc : oddsKickoff,
    gameDate: toIsoOrNull(raw.game_date),
    homeTeam: String(raw.home_team ?? "Home"),
    awayTeam: String(raw.away_team ?? "Away"),
    homeAbbr: String(raw.home_abbr ?? "—"),
    awayAbbr: String(raw.away_abbr ?? "—"),
    homeWinProb: toNumberOrNull(raw.home_win_prob),
    awayWinProb: toNumberOrNull(raw.away_win_prob),
    spreadHome: toNumberOrNull(raw.spread_home),
    totalMean: toNumberOrNull(raw.total_mean),
    fairHomeMl: toNumberOrNull(raw.fair_home_ml),
    fairAwayMl: toNumberOrNull(raw.fair_away_ml),
    handicapSpreadHome: toNumberOrNull(
      raw.handicap_spread_home ?? raw.spread_home,
    ),
    handicapTotal: toNumberOrNull(raw.handicap_total_mean ?? raw.total_mean),
    handicapHomeWinProb: toNumberOrNull(
      raw.handicap_home_win_prob ?? raw.home_win_prob,
    ),
    handicapAwayWinProb: toNumberOrNull(
      raw.handicap_away_win_prob ?? raw.away_win_prob,
    ),
    handicapHomeMl: toNumberOrNull(
      raw.handicap_fair_home_ml ?? raw.fair_home_ml,
    ),
    handicapAwayMl: toNumberOrNull(
      raw.handicap_fair_away_ml ?? raw.fair_away_ml,
    ),
    modelSpreadHome: toNumberOrNull(
      raw.model_spread_home ?? raw.handicap_spread_home ?? raw.spread_home,
    ),
    modelTotal: toNumberOrNull(
      raw.model_total_mean ?? raw.handicap_total_mean ?? raw.total_mean,
    ),
    modelHomeWinProb: toNumberOrNull(
      raw.model_home_win_prob ??
        raw.handicap_home_win_prob ??
        raw.home_win_prob,
    ),
    modelAwayWinProb: toNumberOrNull(
      raw.model_away_win_prob ??
        raw.handicap_away_win_prob ??
        raw.away_win_prob,
    ),
    modelHomeMl: toNumberOrNull(
      raw.model_fair_home_ml ?? raw.handicap_fair_home_ml ?? raw.fair_home_ml,
    ),
    modelAwayMl: toNumberOrNull(
      raw.model_fair_away_ml ?? raw.handicap_fair_away_ml ?? raw.fair_away_ml,
    ),
    modelEqualsKei:
      typeof raw.model_equals_kei === "boolean" ? raw.model_equals_kei : null,
    keiReprice: normalizeKeiReprice(raw.kei_reprice),
    modelVersion: String(raw.model_version ?? ""),
    simulationCount: toNumberOrNull(raw.simulation_count),
    projectionCreatedAt: toIsoOrNull(raw.projection_created_at),
    marketHomeMl: toNumberOrNull(raw.market_home_ml),
    marketAwayMl: toNumberOrNull(raw.market_away_ml),
    marketTotal: toNumberOrNull(raw.market_total),
    marketSpreadHome: toNumberOrNull(raw.market_spread_home),
    openSpreadHome: toNumberOrNull(
      raw.open_spread_home ?? raw.opening_spread_home,
    ),
    openTotal: toNumberOrNull(raw.open_total ?? raw.opening_total),
    oddsCapturedAt: toIsoOrNull(raw.odds_captured_at ?? raw.market_captured_at),
    bestSpreadHome: toNumberOrNull(raw.best_spread_home),
    bestTotal: toNumberOrNull(raw.best_total),
    bestSpreadBook:
      typeof raw.best_spread_book === "string" && raw.best_spread_book.trim()
        ? raw.best_spread_book.trim().toLowerCase()
        : null,
    bestTotalBook:
      typeof raw.best_total_book === "string" && raw.best_total_book.trim()
        ? raw.best_total_book.trim().toLowerCase()
        : null,
    bestSpreadAwayJuice: toNumberOrNull(raw.best_spread_away_juice),
    bestSpreadHomeJuice: toNumberOrNull(raw.best_spread_home_juice),
    bestTotalOverJuice: toNumberOrNull(raw.best_total_over_juice),
    bestTotalUnderJuice: toNumberOrNull(raw.best_total_under_juice),
    dkSpreadHome: toNumberOrNull(raw.dk_spread_home),
    fdSpreadHome: toNumberOrNull(raw.fd_spread_home),
    stakeSpreadHome: toNumberOrNull(raw.stake_spread_home),
    stakeSpreadBook:
      typeof raw.stake_spread_book === "string" && raw.stake_spread_book.trim()
        ? raw.stake_spread_book.trim().toLowerCase()
        : null,
    dkTotal: toNumberOrNull(raw.dk_total),
    fdTotal: toNumberOrNull(raw.fd_total),
    stakeTotal: toNumberOrNull(raw.stake_total),
    stakeTotalBook:
      typeof raw.stake_total_book === "string" && raw.stake_total_book.trim()
        ? raw.stake_total_book.trim().toLowerCase()
        : null,
    marketHomeProbNoVig: toNumberOrNull(raw.market_home_prob_no_vig),
    mlEdgeProb: toNumberOrNull(raw.ml_edge_prob),
    totalEdge: toNumberOrNull(raw.total_edge),
    spreadEdge: toNumberOrNull(raw.spread_edge),
    marketJoined: Boolean(raw.market_joined),
    publishTagSpread: normalizePublishTag(raw.publish_tag_spread),
    publishTagTotal: normalizePublishTag(raw.publish_tag_total),
    publishTagMl: normalizePublishTag(raw.publish_tag_ml),
    decision: normalizeDecision(raw.decision),
    actionLabelSpread: normalizeActionLabel(raw.action_label_spread),
    actionLabelTotal: normalizeActionLabel(raw.action_label_total),
  };
}

export async function fetchNflFairLines(params: {
  season: number;
  daysAhead?: number;
  includePastDays?: number;
  modelVersion?: string;
  /** Comma-separated Odds API bookmaker keys for market join. */
  bookmakers?: string;
  /**
   * Upstream abort budget. Default = board (12s) for Overview/SSR HTML paths.
   * Page-data APIs pass UPSTREAM_TIMEOUT_MS.pageData (25s).
   */
  timeoutMs?: number;
  /**
   * When true, timeout/transport/upstream failures throw instead of returning a
   * soft-empty board (count=0, oddsAsOf=null). Page-data routes use this so the
   * client gets 503/504 and retries — not a fake empty slate.
   */
  throwOnTransportError?: boolean;
  /**
   * When false (default), send persist=0 so model-service skips odds_snapshots
   * writes on this subscriber/page-data read. Beat/worker scheduled persist stays.
   * Pass true only for rare ops paths that intentionally land training snaps.
   */
  persistOdds?: boolean;
}): Promise<NflFairLinesResponse> {
  const base = env.MODEL_SERVICE_URL;
  const emptyDiagnostics = {
    oddsFeedStatus: "unknown",
    oddsFeedError: null as string | null,
    oddsEventsSeen: 0,
    marketJoinedCount: 0,
    bookmakers: [] as string[],
    kosedgeOnly: true,
  };
  const softEmpty = (error: string): NflFairLinesResponse => ({
    season: params.season,
    modelVersion: "",
    asOf: null,
    oddsAsOf: null,
    currentWeek: 1,
    count: 0,
    lines: [],
    window: {
      daysAhead: params.daysAhead ?? 14,
      includePastDays: params.includePastDays ?? 0,
    },
    diagnostics: emptyDiagnostics,
    error,
  });

  if (!base) {
    const error = "MODEL_SERVICE_URL is not configured.";
    if (params.throwOnTransportError) throw new Error(error);
    return softEmpty(error);
  }

  const url = new URL(`${base.replace(/\/+$/, "")}/nfl/fair-lines`);
  url.searchParams.set("season", String(params.season));
  url.searchParams.set("days_ahead", String(params.daysAhead ?? 14));
  url.searchParams.set(
    "include_past_days",
    String(params.includePastDays ?? 0),
  );
  if (params.modelVersion) {
    url.searchParams.set("model_version", params.modelVersion);
  }
  if (params.bookmakers) {
    url.searchParams.set("bookmakers", params.bookmakers);
  }
  // Default read-only: page-data / SSR must not write odds_snapshots on GET.
  const persistOdds = params.persistOdds === true;
  url.searchParams.set("persist", persistOdds ? "1" : "0");

  try {
    const response = await upstreamFetch(url.toString(), {
      cache: "no-store",
      // Default board cap keeps Overview / SSR from hanging on cold Railway.
      timeoutMs: params.timeoutMs ?? UPSTREAM_TIMEOUT_MS.board,
      headers: {
        accept: "application/json",
        ...(env.INTERNAL_API_SECRET
          ? { "x-kosedge-secret": env.INTERNAL_API_SECRET }
          : {}),
      },
    });
    if (!response.ok) {
      const statusError = `Model service returned ${response.status}.`;
      const honestStatus = inferHonestEmptySlateStatus({
        season: params.season,
        error: statusError,
      });
      if (params.throwOnTransportError && !honestStatus) {
        throw new Error(statusError);
      }
      return {
        season: params.season,
        modelVersion: "",
        asOf: null,
        oddsAsOf: null,
        currentWeek: 1,
        count: 0,
        lines: [],
        window: {
          daysAhead: params.daysAhead ?? 14,
          includePastDays: params.includePastDays ?? 0,
        },
        diagnostics: emptyDiagnostics,
        slateStatus: honestStatus ?? undefined,
        error: honestStatus ? undefined : statusError,
      };
    }
    const payload = (await response.json()) as {
      season?: number;
      model_version?: string;
      as_of?: string;
      odds_as_of?: string;
      current_week?: number;
      count?: number;
      slate_status?: string;
      lines?: Array<Record<string, unknown>>;
      window?: { days_ahead?: number; include_past_days?: number };
      diagnostics?: {
        odds_feed_status?: string;
        odds_feed_error?: string | null;
        odds_events_seen?: number;
        market_joined_count?: number;
        bookmakers?: string[];
        kosedge_only?: boolean;
        odds_persisted?: {
          events_persisted?: number;
          snapshots_inserted?: number;
          history_upserted?: number;
        };
        current_week?: number;
      };
    };
    const lines = Array.isArray(payload.lines)
      ? payload.lines.map(normalizeFairLine)
      : [];
    const persisted = payload.diagnostics?.odds_persisted;
    const apiSlateStatus =
      typeof payload.slate_status === "string" ? payload.slate_status : null;
    const slateStatus =
      apiSlateStatus ?? (lines.length === 0 ? "no_slate" : "ok");
    return {
      season:
        typeof payload.season === "number" ? payload.season : params.season,
      modelVersion: String(payload.model_version ?? ""),
      asOf: toIsoOrNull(payload.as_of),
      oddsAsOf: toIsoOrNull(payload.odds_as_of),
      currentWeek: toNumber(
        payload.current_week ?? payload.diagnostics?.current_week,
        1,
      ),
      count: typeof payload.count === "number" ? payload.count : lines.length,
      lines,
      slateStatus,
      window: {
        daysAhead: payload.window?.days_ahead ?? params.daysAhead ?? 14,
        includePastDays:
          payload.window?.include_past_days ?? params.includePastDays ?? 0,
      },
      diagnostics: {
        oddsFeedStatus: String(
          payload.diagnostics?.odds_feed_status ?? "unknown",
        ),
        oddsFeedError:
          typeof payload.diagnostics?.odds_feed_error === "string"
            ? payload.diagnostics.odds_feed_error
            : null,
        oddsEventsSeen: toNumber(payload.diagnostics?.odds_events_seen),
        marketJoinedCount: toNumber(payload.diagnostics?.market_joined_count),
        bookmakers: Array.isArray(payload.diagnostics?.bookmakers)
          ? payload.diagnostics.bookmakers.map(String)
          : [],
        kosedgeOnly: Boolean(
          payload.diagnostics?.kosedge_only ??
          lines.every((line) => !line.marketJoined),
        ),
        oddsPersisted: persisted
          ? {
              eventsPersisted: toNumber(persisted.events_persisted),
              snapshotsInserted: toNumber(persisted.snapshots_inserted),
              historyUpserted: toNumber(persisted.history_upserted),
            }
          : undefined,
      },
    };
  } catch (cause) {
    if (params.throwOnTransportError) {
      throw cause;
    }
    const transportError = "Unable to reach model service.";
    const honestStatus = inferHonestEmptySlateStatus({
      season: params.season,
      error: transportError,
      cause,
    });
    return {
      season: params.season,
      modelVersion: "",
      asOf: null,
      oddsAsOf: null,
      currentWeek: 1,
      count: 0,
      lines: [],
      window: {
        daysAhead: params.daysAhead ?? 14,
        includePastDays: params.includePastDays ?? 0,
      },
      diagnostics: emptyDiagnostics,
      slateStatus: honestStatus ?? undefined,
      error: honestStatus ? undefined : transportError,
    };
  }
}

export function formatAmericanOdds(value: number | null): string {
  if (value === null || !Number.isFinite(value)) return "—";
  const rounded = Math.round(value);
  return rounded > 0 ? `+${rounded}` : String(rounded);
}

export function formatSpread(value: number | null): string {
  if (value === null || !Number.isFinite(value)) return "—";
  const rounded = Math.round(value * 100) / 100;
  return rounded > 0 ? `+${rounded.toFixed(2)}` : rounded.toFixed(2);
}

export function formatTotal(value: number | null): string {
  if (value === null || !Number.isFinite(value)) return "—";
  return value.toFixed(1);
}

export function formatWinProb(value: number | null): string {
  if (value === null || !Number.isFinite(value)) return "—";
  return `${(value * 100).toFixed(1)}%`;
}

export function formatKickoff(value: string | null): string {
  if (!value) return "TBD";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "TBD";
  return date.toLocaleString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    timeZone: "America/New_York",
    timeZoneName: "short",
  });
}

export function edgeToneClass(value: number | null): string {
  if (value === null || !Number.isFinite(value)) return "text-kos-text/55";
  if (value >= 0.02) return "text-edge-green";
  if (value <= -0.02) return "text-rose-300";
  return "text-kos-text/70";
}
