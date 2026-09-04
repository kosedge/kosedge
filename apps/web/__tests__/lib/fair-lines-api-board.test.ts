import { describe, expect, it } from "vitest";
import {
  FAIR_LINES_DO_NOT_INVENT,
  fairLinesNotConnectedMessage,
  honestEmptyFairLinesBoard,
  toFairLinesApiBoard,
} from "@/lib/fair-lines-api-board";

describe("fair-lines API honesty envelope", () => {
  it("honest empty never invents asOf, oddsAsOf, or lines", () => {
    const board = honestEmptyFairLinesBoard({
      sport: "cfb",
      slateStatus: "not_connected",
      message: fairLinesNotConnectedMessage("CFB"),
    });
    expect(board.count).toBe(0);
    expect(board.lines).toEqual([]);
    expect(board.asOf).toBeNull();
    expect(board.oddsAsOf).toBeNull();
    expect(board.slateStatus).toBe("not_connected");
    expect(board.message).toContain("not connected");
    expect(board.message).toContain(FAIR_LINES_DO_NOT_INVENT);
  });

  it("toFairLinesApiBoard preserves real lines and leaves as-of null when absent", () => {
    const board = toFairLinesApiBoard({
      sport: "nba",
      sportLabel: "NBA",
      lines: [{ gameId: "1" }],
      slateStatus: "ok",
      modelVersion: "nba-v1",
    });
    expect(board.count).toBe(1);
    expect(board.asOf).toBeNull();
    expect(board.oddsAsOf).toBeNull();
    expect(board.slateStatus).toBe("ok");
    expect(board.lines).toHaveLength(1);
  });

  it("empty board defaults to no_slate and do-not-invent message", () => {
    const board = toFairLinesApiBoard({
      sport: "mlb",
      sportLabel: "MLB",
      lines: [],
    });
    expect(board.count).toBe(0);
    expect(board.slateStatus).toBe("no_slate");
    expect(board.message).toContain(FAIR_LINES_DO_NOT_INVENT);
  });
});
