import { describe, expect, it } from "vitest";
import {
  formatGoalieCell,
  matchGoalieConfirmation,
  type NhlGoalieMatchup,
} from "@/lib/nhl-goalie-confirmation";

const sample: NhlGoalieMatchup[] = [
  {
    eventId: "1",
    name: "Florida Panthers at Carolina Hurricanes",
    commenceTime: "2026-09-29T21:00Z",
    away: {
      teamAbbr: "FLA",
      teamName: "Florida Panthers",
      goalieName: null,
      status: "pending",
      source: "espn-scoreboard",
    },
    home: {
      teamAbbr: "CAR",
      teamName: "Carolina Hurricanes",
      goalieName: "Fredrik Andersen",
      status: "expected",
      source: "espn-scoreboard",
    },
  },
];

describe("nhl-goalie-confirmation", () => {
  it("formats pending without inventing names", () => {
    expect(formatGoalieCell(sample[0]!.away)).toBe("Confirmation pending");
    expect(formatGoalieCell(sample[0]!.home)).toBe(
      "Fredrik Andersen · Expected",
    );
    expect(formatGoalieCell(null)).toBe("Confirmation pending");
  });

  it("matches board team names to ESPN rows", () => {
    const hit = matchGoalieConfirmation(
      "Florida Panthers",
      "Carolina Hurricanes",
      sample,
    );
    expect(hit?.eventId).toBe("1");
    expect(
      matchGoalieConfirmation("Seattle Kraken", "Vegas Golden Knights", sample),
    ).toBeNull();
  });
});
