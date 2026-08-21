/**
 * Bounded fetch for upstreams (Railway model-service, Odds API, etc.).
 * Never let a stuck TCP connection hold a Next.js render open indefinitely.
 */

export const UPSTREAM_TIMEOUT_MS = {
  /** Odds API / light JSON health probes */
  fast: 8_000,
  /** Fair-lines / board assembly (cold Railway + odds join) */
  board: 12_000,
  /** Rare heavy ops (backfills, compare dumps) — still capped */
  heavy: 20_000,
  /**
   * NFL season-engine Game Boxes / Survivor research-depth runs.
   * Cold ~65s@2k game-boxes; warm cache should be ms. Edge Board list
   * must not use this budget — keep board timeout for slate loads.
   */
  seasonEngine: 180_000,
  /** Planner / helper interactive n (50 paths) — fail honest, don't hang. */
  seasonEngineInteractive: 25_000,
} as const;

export class UpstreamTimeoutError extends Error {
  readonly timeoutMs: number;
  constructor(timeoutMs: number, url?: string) {
    super(
      url
        ? `Upstream timed out after ${timeoutMs}ms (${url})`
        : `Upstream timed out after ${timeoutMs}ms`,
    );
    this.name = "UpstreamTimeoutError";
    this.timeoutMs = timeoutMs;
  }
}

export type UpstreamFetchInit = RequestInit & {
  /** Abort after this many ms (default: board). */
  timeoutMs?: number;
};

/**
 * fetch() with AbortController timeout. Merges with an existing signal if provided.
 */
export async function upstreamFetch(
  input: string | URL,
  init: UpstreamFetchInit = {},
): Promise<Response> {
  const timeoutMs = init.timeoutMs ?? UPSTREAM_TIMEOUT_MS.board;
  const { timeoutMs: _omit, signal: outerSignal, ...rest } = init;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  const onOuterAbort = () => controller.abort();
  if (outerSignal) {
    if (outerSignal.aborted) controller.abort();
    else outerSignal.addEventListener("abort", onOuterAbort, { once: true });
  }

  try {
    return await fetch(input, { ...rest, signal: controller.signal });
  } catch (err) {
    if (controller.signal.aborted && !outerSignal?.aborted) {
      throw new UpstreamTimeoutError(
        timeoutMs,
        typeof input === "string" ? input : input.toString(),
      );
    }
    throw err;
  } finally {
    clearTimeout(timer);
    outerSignal?.removeEventListener("abort", onOuterAbort);
  }
}
