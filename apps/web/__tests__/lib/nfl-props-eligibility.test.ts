import { describe, expect, it } from "vitest";
import {
  isInvestableProp,
  PRIMARY_BOARD_MARKETS,
  PROPS_ELIGIBILITY_NOTE,
} from "@/lib/nfl-props-eligibility";

describe("NFL props eligibility", () => {
  it("drops OL/DL/K anytime TD and 0.0 model junk", () => {
    expect(
      isInvestableProp({
        marketKey: "anytime_td",
        position: "G",
        modelMean: 0,
        confidence: 0.05,
      }),
    ).toBe(false);
    expect(
      isInvestableProp({
        marketKey: "anytime_td",
        position: "K",
        modelMean: 0.2,
      }),
    ).toBe(false);
    expect(
      isInvestableProp({
        marketKey: "rec_yds",
        position: "DE",
        modelMean: 12,
      }),
    ).toBe(false);
  });

  it("keeps QB/RB/WR desk rows that clear involvement floors", () => {
    expect(
      isInvestableProp({
        marketKey: "pass_yds",
        position: "QB",
        modelMean: 248,
        line: 245.5,
      }),
    ).toBe(true);
    expect(
      isInvestableProp({
        marketKey: "rush_yds",
        position: "RB",
        modelMean: 71,
        line: 66.5,
      }),
    ).toBe(true);
    expect(
      isInvestableProp({
        marketKey: "anytime_td",
        position: "WR",
        modelMean: 0.18,
      }),
    ).toBe(true);
  });

  it("does not treat ATD 0.5 line as volume", () => {
    expect(
      isInvestableProp({
        marketKey: "anytime_td",
        position: "WR",
        modelMean: 0,
        line: 0.5,
      }),
    ).toBe(false);
  });

  it("primary board markets are the investable v1 set", () => {
    expect([...PRIMARY_BOARD_MARKETS]).toEqual([
      "pass_yds",
      "rush_yds",
      "rec_yds",
      "receptions",
      "anytime_td",
    ]);
    expect(PROPS_ELIGIBILITY_NOTE.toLowerCase()).toContain("skill");
    expect(PROPS_ELIGIBILITY_NOTE.toLowerCase()).not.toContain("2025");
  });
});
