import { describe, expect, it } from "vitest";
import {
  applyBoardNameOverrides,
  expandCollidingBoardNames,
} from "@/lib/fantasy/board-identity";
import type { DepthRow } from "@/lib/fantasy/risk-signals";

const depth: DepthRow[] = [
  {
    team: "ATL",
    position: "RB",
    depthOrder: 1,
    playerName: "Bijan Robinson",
    roleConfidence: 0.9,
    playerId: "00-0038542",
  },
  {
    team: "ATL",
    position: "RB",
    depthOrder: 2,
    playerName: "Brian Robinson Jr.",
    roleConfidence: 0.7,
    playerId: "00-0037746",
  },
  {
    team: "SF",
    position: "RB",
    depthOrder: 1,
    playerName: "Christian McCaffrey",
    roleConfidence: 0.95,
    playerId: "00-0033280",
  },
];

describe("expandCollidingBoardNames", () => {
  it("expands two ATL B.Robinson rows via depth player_id", () => {
    const overrides = expandCollidingBoardNames(
      [
        {
          playerId: "00-0038542",
          playerName: "B.Robinson",
          team: "ATL",
          position: "RB",
        },
        {
          playerId: "00-0037746",
          playerName: "B.Robinson",
          team: "ATL",
          position: "RB",
        },
        {
          playerId: "00-0033280",
          playerName: "C.McCaffrey",
          team: "SF",
          position: "RB",
        },
      ],
      depth,
    );
    expect(overrides.get("00-0038542")).toBe("Bijan Robinson");
    expect(overrides.get("00-0037746")).toBe("Brian Robinson Jr.");
    // Non-colliding abbrevs stay abbreviated.
    expect(overrides.has("00-0033280")).toBe(false);

    const applied = applyBoardNameOverrides(
      [
        {
          playerId: "00-0038542",
          playerName: "B.Robinson",
          team: "ATL",
          position: "RB",
        },
        {
          playerId: "00-0037746",
          playerName: "B.Robinson",
          team: "ATL",
          position: "RB",
        },
      ],
      overrides,
    );
    expect(applied.map((r) => r.playerName)).toEqual([
      "Bijan Robinson",
      "Brian Robinson Jr.",
    ]);
  });

  it("does not expand a lone B.Robinson", () => {
    const overrides = expandCollidingBoardNames(
      [
        {
          playerId: "00-0038542",
          playerName: "B.Robinson",
          team: "ATL",
          position: "RB",
        },
      ],
      depth,
    );
    expect(overrides.size).toBe(0);
  });
});
