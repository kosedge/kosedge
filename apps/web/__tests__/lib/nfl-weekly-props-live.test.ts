import { describe, expect, it } from "vitest";
import {
  NFL_WEEKLY_PROPS_LIVE,
  NFL_WEEKLY_PROPS_METHODS,
  NFL_WEEKLY_PROPS_PATH_COHERENT,
} from "@/lib/nfl-weekly-props-live";

describe("NFL weekly props path", () => {
  it("is LIVE for research means — not gated, not a stake card", () => {
    expect(NFL_WEEKLY_PROPS_LIVE).toBe(true);
    expect(NFL_WEEKLY_PROPS_PATH_COHERENT).toBe("yes");
    expect(NFL_WEEKLY_PROPS_METHODS.join(" ")).toMatch(/cap 17/i);
    expect(NFL_WEEKLY_PROPS_METHODS.join(" ")).toMatch(/depth chart/i);
    expect(NFL_WEEKLY_PROPS_METHODS.join(" ")).toMatch(/2026 preseason/i);
    expect(NFL_WEEKLY_PROPS_METHODS.join(" ")).toMatch(/No PLAY \/ LEAN stake tags/);
  });
});
