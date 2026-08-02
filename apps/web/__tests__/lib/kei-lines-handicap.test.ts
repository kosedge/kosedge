import { describe, expect, it } from "vitest";
import {
  applyHandicapIdentity,
  resolveHandicapFields,
  type KeiLineGame,
} from "@/lib/kei-lines";

describe("kei handicap identity", () => {
  it("resolveHandicapFields prefers handicap over proj and model", () => {
    const game: KeiLineGame = {
      homeTeam: "H",
      awayTeam: "A",
      projSpreadHome: -3,
      projTotal: 40,
      handicapSpreadHome: -4,
      handicapTotal: 42,
      modelSpreadHome: -2,
      modelTotal: 39,
    };
    expect(resolveHandicapFields(game)).toEqual({
      spreadHome: -4,
      total: 42,
      homeMl: null,
      awayMl: null,
      homeWinProb: null,
    });
  });

  it("applyHandicapIdentity fills proj from model when handicap absent", () => {
    const game = applyHandicapIdentity({
      homeTeam: "H",
      awayTeam: "A",
      projSpreadHome: null,
      projTotal: null,
      modelSpreadHome: -5.5,
      modelTotal: 45.5,
      modelHomeMl: -110,
      modelAwayMl: -110,
      modelHomeWinProb: 0.52,
    });
    expect(game.handicapSpreadHome).toBe(-5.5);
    expect(game.projSpreadHome).toBe(-5.5);
    expect(game.projTotal).toBe(45.5);
    expect(game.homeWinProb).toBe(0.52);
    expect(game.modelSpreadHome).toBe(-5.5);
  });
});
