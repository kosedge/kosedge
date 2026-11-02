/** Client-safe KEI / fair-lines row shapes (no server-only). */

import {
  FixtureHardRefuse,
  consumeFixtureEligibility,
  type EligibilityDecision,
  type EligibilityDecisionInput,
} from "@/lib/nfl-fixture-assembly-contract";
import { assertFixtureChainRecord } from "@/lib/nfl-fixture-chain-consume";

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
  week: number | null;
  startTime: string | null;
  awayTeam: string;
  homeTeam: string;
  awayAbbr: string;
  homeAbbr: string;
  handicapSpreadHome: number | null;
  spreadHome: number | null;
  handicapTotal: number | null;
  totalMean: number | null;
  modelSpreadHome: number | null;
  modelTotal: number | null;
  fairHomeMl: number | null;
  fairAwayMl: number | null;
  homeWinProb: number | null;
  awayWinProb: number | null;
  marketHomeMl: number | null;
  marketAwayMl: number | null;
  marketTotal: number | null;
  marketJoined: boolean;
  mlEdgeProb: number | null;
  keiReprice: NflKeiRepriceLog | null;
};

export type NflFairLinesResponse = {
  season: number;
  modelVersion: string;
  asOf: string | null;
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
  };
  error?: string;
  slateStatus?: string;
  fixture?: boolean;
  persistOdds?: boolean;
  eligibility?: {
    result: string;
    reason?: string;
    fixture?: boolean;
    subscriber_consumable?: boolean;
    betting_consumable?: boolean;
    production_consumable?: boolean;
    env_bypass_honored?: boolean;
    cacheable?: boolean;
    contract_id?: string;
    channel?: string;
  };
};

/** Customer UI must not consume ALLOW_FIXTURE (Alex X1). */
export function assertCustomerFairLinesViewModel(
  board: NflFairLinesResponse,
): void {
  if (board.fixture !== true && board.eligibility?.result !== "ALLOW_FIXTURE") {
    return;
  }
  if (!board.eligibility) {
    throw new FixtureHardRefuse(
      "REFUSE_MISSING",
      "fixture board missing eligibility",
    );
  }
  consumeFixtureEligibility(
    board.eligibility as EligibilityDecisionInput,
    "subscriber",
  );
}

/** Fixture-channel view-model. Spread only; totals/ML/prob stay absent. */
export function projectFixtureFairLinesViewModel(board: {
  eligibility: EligibilityDecision | EligibilityDecisionInput;
  lines: NflFairLineRow[];
  fixture?: boolean;
  chain?: unknown;
}): {
  fixture: true;
  subscriber_consumable: false;
  lines: Array<
    Pick<
      NflFairLineRow,
      "gameId" | "spreadHome" | "handicapSpreadHome" | "modelSpreadHome"
    > & {
      totalMean: null;
      handicapTotal: null;
      modelTotal: null;
      fairHomeMl: null;
      fairAwayMl: null;
      homeWinProb: null;
      awayWinProb: null;
    }
  >;
} {
  if (board.chain !== undefined) {
    assertFixtureChainRecord(board.chain);
  }
  consumeFixtureEligibility(board.eligibility, "fixture");
  return {
    fixture: true,
    subscriber_consumable: false,
    lines: board.lines.map((row) => ({
      gameId: row.gameId,
      spreadHome: row.spreadHome,
      handicapSpreadHome: row.handicapSpreadHome,
      modelSpreadHome: row.modelSpreadHome,
      totalMean: null,
      handicapTotal: null,
      modelTotal: null,
      fairHomeMl: null,
      fairAwayMl: null,
      homeWinProb: null,
      awayWinProb: null,
    })),
  };
}
