import { describe, expect, it } from "vitest";
import {
  emptySurvivorPlanCacheKey,
  getEmptySurvivorPlan,
  setEmptySurvivorPlan,
} from "@/lib/nfl-survivor-empty-plan-cache";

describe("empty survivor plan cache", () => {
  it("returns a payload inside TTL and misses after overwrite key", () => {
    const key = emptySurvivorPlanCacheKey({
      season: 2026,
      nSims: 50,
      seed: 42,
      topN: 32,
      includeDiagnostics: false,
    });
    setEmptySurvivorPlan(key, { weeks: [{ week: 1 }] }, 60_000);
    expect(getEmptySurvivorPlan(key)).toEqual({ weeks: [{ week: 1 }] });
    expect(
      getEmptySurvivorPlan(
        emptySurvivorPlanCacheKey({
          season: 2026,
          nSims: 51,
          seed: 42,
          topN: 32,
          includeDiagnostics: false,
        }),
      ),
    ).toBeNull();
  });
});
