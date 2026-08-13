import { describe, expect, it } from "vitest";
import {
  NFL_WEEKLY_PROPS_GATE_TITLE,
  NFL_WEEKLY_PROPS_LIVE,
  NFL_WEEKLY_PROPS_PATH_COHERENT,
} from "@/lib/nfl-weekly-props-live";

describe("NFL weekly props path", () => {
  it("is explicitly gated — not partial and not silently live", () => {
    expect(NFL_WEEKLY_PROPS_LIVE).toBe(false);
    expect(NFL_WEEKLY_PROPS_PATH_COHERENT).toBe("gated");
    expect(NFL_WEEKLY_PROPS_GATE_TITLE).toMatch(/not live/i);
    expect(NFL_WEEKLY_PROPS_GATE_TITLE).toMatch(/season desk only/i);
  });
});
