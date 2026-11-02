import { NextResponse } from "next/server";
import {
  projectFixtureFairLinesBoard,
  type FixtureFairLinesBoard,
  type FixtureFairLinesProjectionInput,
} from "@/lib/nfl-fair-lines";
import {
  pageDataCacheHeaders,
  pageDataCacheHeadersForFixture,
} from "@/lib/page-data-cache";
import { nflEdgeBoardAssembleUnavailablePayload } from "@/lib/cfb-edge-board-public";
import { consumeFixtureEligibility } from "@/lib/nfl-fixture-assembly-contract";
import { assertFixtureChainRecord } from "@/lib/nfl-fixture-chain-consume";

/** Closed customer surface — 503 unavailable, never 200 empty-success. */
export function nflFairLinesCustomerUnavailableResponse(): NextResponse {
  return NextResponse.json(nflEdgeBoardAssembleUnavailablePayload(), {
    status: 503,
    headers: pageDataCacheHeaders({ cacheable: false }),
  });
}

/**
 * Fixture-channel API projection of the SAME t5178u contract.
 * Isolated from customer GET. ALLOW_FIXTURE is not subscriber-consumable.
 */
export function projectFixtureFairLinesApiResponse(
  input: FixtureFairLinesProjectionInput,
): {
  status: number;
  board: FixtureFairLinesBoard;
  headers: Record<string, string>;
} {
  if (input.chain !== undefined) {
    assertFixtureChainRecord(input.chain);
  }
  consumeFixtureEligibility(input.eligibility, input.consumer);
  const board = projectFixtureFairLinesBoard(input);
  return {
    status: 200,
    board,
    headers: pageDataCacheHeadersForFixture(board.eligibility),
  };
}
