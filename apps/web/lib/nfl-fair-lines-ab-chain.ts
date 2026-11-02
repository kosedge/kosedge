/**
 * t5194u A→B chain consume. Loads A's serialized FixtureChainRecord.
 * Does not invent allow tokens. CERT=0.
 */
import { projectFixtureFairLinesApiResponse } from "@/lib/nfl-fair-lines-fixture-api";
import { projectFixtureFairLinesViewModel } from "@/lib/nfl-fair-lines-view-types";
import { keiGamesFromFixtureFairLines } from "@/lib/resolve-kei-lines";
import {
  pageDataCacheHeadersForFixture,
  readFixtureProjectionCache,
  writeFixtureProjectionCache,
} from "@/lib/page-data-cache";
import { assertFixtureChainRecord } from "@/lib/nfl-fixture-chain-consume";

export { assertFixtureChainRecord } from "@/lib/nfl-fixture-chain-consume";

export function projectFixtureAbChain(raw: unknown): {
  api: ReturnType<typeof projectFixtureFairLinesApiResponse>;
  view: ReturnType<typeof projectFixtureFairLinesViewModel>;
  kei: ReturnType<typeof keiGamesFromFixtureFairLines>;
  headers: Record<string, string>;
} {
  const chain = assertFixtureChainRecord(raw);
  const input = {
    eligibility: chain.eligibility,
    consumer: "fixture" as const,
    quote: chain.quote,
    requestedOutput: chain.requested_output,
    chain: raw,
  };
  const api = projectFixtureFairLinesApiResponse(input);
  const view = projectFixtureFairLinesViewModel({ ...api.board, chain: raw });
  const kei = keiGamesFromFixtureFairLines({ ...api.board, chain: raw });
  const headers = pageDataCacheHeadersForFixture(api.board.eligibility);
  return { api, view, kei, headers };
}

export function writeThenReadFixtureChainCache(
  key: string,
  body: unknown,
  generation: number,
  chain: unknown,
) {
  assertFixtureChainRecord(chain);
  writeFixtureProjectionCache(key, body, generation);
  return readFixtureProjectionCache(key, generation);
}
