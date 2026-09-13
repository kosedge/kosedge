/**
 * Preview / local proof-only synthetic NFL inactive-suppress row.
 *
 * Never paints a customer matchup (no ATL@PIT). Never enabled when
 * VERCEL_ENV === "production". Preview assemble:
 *   /api/edge-board/nfl/assemble?slate=week1&inactiveProof=1
 *
 * Local (non-production) also accepts INACTIVE_SUPPRESS_PROOF=1 + the same query.
 */

import type { EdgeBoardRow } from "@kosedge/contracts";
import { applyNflInactiveFairSuppressToRows } from "@/lib/nfl-inactive-fair-suppress";
import { loadNflInactiveSuppressStore } from "@/lib/nfl-inactive-suppress-store";

export const NFL_INACTIVE_SUPPRESS_PROOF_GAME_KEY = "PROOF@SYNTH";
export const NFL_INACTIVE_SUPPRESS_PROOF_UUID =
  "c0de0000-5e17-4000-8000-00000000f00f";
export const NFL_INACTIVE_SUPPRESS_PROOF_GAME_LABEL =
  "PROOF SYNTH @ PROOF SYNTH";
/** Far-future kickoff so kickoff+buffer cannot expire the proof arm. */
export const NFL_INACTIVE_SUPPRESS_PROOF_COMMENCE = "2099-12-31T18:00:00Z";

export function isNflInactiveSuppressProofEnv(
  env: NodeJS.ProcessEnv = process.env,
): boolean {
  if (env.VERCEL_ENV === "production") return false;
  return env.VERCEL_ENV === "preview" || env.INACTIVE_SUPPRESS_PROOF === "1";
}

export function isNflInactiveSuppressProofRequest(
  url: URL,
  env: NodeJS.ProcessEnv = process.env,
): boolean {
  if (!isNflInactiveSuppressProofEnv(env)) return false;
  return url.searchParams.get("inactiveProof") === "1";
}

function proofRow(market: "Spread" | "Total"): EdgeBoardRow {
  const suffix = market === "Spread" ? "spread" : "total";
  return {
    id: `${NFL_INACTIVE_SUPPRESS_PROOF_UUID}-${suffix}`,
    gameId: NFL_INACTIVE_SUPPRESS_PROOF_GAME_KEY,
    aliases: [
      NFL_INACTIVE_SUPPRESS_PROOF_GAME_KEY,
      NFL_INACTIVE_SUPPRESS_PROOF_UUID,
    ],
    game: NFL_INACTIVE_SUPPRESS_PROOF_GAME_LABEL,
    market,
    awayAbbr: "SYN",
    homeAbbr: "PRF",
    commenceTime: NFL_INACTIVE_SUPPRESS_PROOF_COMMENCE,
    week: 1,
    seasonType: "REG",
    open: market === "Spread" ? "+3.5" : "44.5",
    best: market === "Spread" ? "+3.5" : "44.5",
    book: "proof",
    bookKey: "proof",
    kei: market === "Spread" ? "-3.0" : "43.5",
    fairLine: market === "Spread" ? -3 : 43.5,
    publishTag: "PASS",
    actionLabel: "PASS",
    edgeMagnitude: 6.5,
    period: market === "Total" ? "fg" : undefined,
    modelPeriod: market === "Total" ? "fg" : undefined,
  } as EdgeBoardRow;
}

/** Unstamped Spread+Total rows keyed to the packaged synthetic store. */
export function buildNflInactiveSuppressProofRows(): EdgeBoardRow[] {
  return [proofRow("Spread"), proofRow("Total")];
}

/**
 * Append synthetic proof rows and run them through the packaged store
 * (no env). Production and missing `inactiveProof=1` are no-ops.
 */
export function appendNflInactiveSuppressProofRows(
  rows: EdgeBoardRow[],
  url: URL,
  env: NodeJS.ProcessEnv = process.env,
  opts?: { nowMs?: number },
): EdgeBoardRow[] {
  if (!isNflInactiveSuppressProofRequest(url, env)) return rows;
  const stamped = applyNflInactiveFairSuppressToRows(
    buildNflInactiveSuppressProofRows(),
    "nfl",
    { store: loadNflInactiveSuppressStore(), nowMs: opts?.nowMs },
  );
  return [...rows, ...stamped];
}
