/**
 * Process-local TTL cache for empty-picks survivor plans (already_used = []).
 * Vercel instances still skip a Railway round-trip on warm repeats.
 */

type CacheEntry = { expires: number; payload: unknown };

const globalForCache = globalThis as typeof globalThis & {
  __kosSurvivorEmptyPlanCache?: Map<string, CacheEntry>;
};

function store(): Map<string, CacheEntry> {
  if (!globalForCache.__kosSurvivorEmptyPlanCache) {
    globalForCache.__kosSurvivorEmptyPlanCache = new Map();
  }
  return globalForCache.__kosSurvivorEmptyPlanCache;
}

export const EMPTY_SURVIVOR_PLAN_TTL_MS = 5 * 60 * 1000;

export function emptySurvivorPlanCacheKey(input: {
  season: number;
  nSims: number;
  seed: number;
  topN: number;
  includeDiagnostics: boolean;
}): string {
  return [
    "empty",
    input.season,
    `n=${input.nSims}`,
    `seed=${input.seed}`,
    `top=${input.topN}`,
    `diag=${input.includeDiagnostics ? 1 : 0}`,
    "slim=1",
  ].join("|");
}

export function getEmptySurvivorPlan(key: string): unknown | null {
  const hit = store().get(key);
  if (!hit) return null;
  if (hit.expires < Date.now()) {
    store().delete(key);
    return null;
  }
  return hit.payload;
}

export function setEmptySurvivorPlan(
  key: string,
  payload: unknown,
  ttlMs = EMPTY_SURVIVOR_PLAN_TTL_MS,
): void {
  store().set(key, { expires: Date.now() + ttlMs, payload });
}
