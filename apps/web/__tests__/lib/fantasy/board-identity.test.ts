import { describe, expect, it } from "vitest";
import {
  applyBoardNameOverrides,
  expandCollidingBoardNames,
} from "@/lib/fantasy/board-identity";
import { matchAdpToDeskRows } from "@/lib/fantasy/adp-match";
import { loadNfl2026DepthRows } from "@/lib/fantasy/load-schedule";
import type { DepthRow } from "@/lib/fantasy/risk-signals";
import type { FantasyProsAdpEntry } from "@/lib/fantasy/adp-fantasypros";

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

function fp(
  partial: Partial<FantasyProsAdpEntry> & {
    playerName: string;
    team: string;
    position: string;
    adp: number;
  },
): FantasyProsAdpEntry {
  return {
    playerId: partial.playerId ?? partial.playerName,
    shortName: partial.shortName ?? null,
    ecr: partial.ecr ?? null,
    sportsdataId: partial.sportsdataId ?? null,
    ...partial,
  };
}

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

  it("packaged depth loads ATL Robinsons and finishes expand→ADP pipe", () => {
    const packed = loadNfl2026DepthRows();
    expect(packed.length).toBeGreaterThan(0);
    const atlRbs = packed.filter(
      (r) => r.team === "ATL" && r.position === "RB",
    );
    expect(atlRbs.some((r) => r.playerId === "00-0038542")).toBe(true);
    expect(atlRbs.some((r) => r.playerId === "00-0037746")).toBe(true);

    const board = [
      {
        playerId: "00-0038542",
        playerName: "B.Robinson",
        team: "ATL",
        position: "RB",
        rankOverall: 2,
      },
      {
        playerId: "00-0037746",
        playerName: "B.Robinson",
        team: "ATL",
        position: "RB",
        rankOverall: 174,
      },
    ];
    const overrides = expandCollidingBoardNames(board, packed);
    expect(overrides.get("00-0038542")).toBe("Bijan Robinson");
    expect(overrides.get("00-0037746")).toBe("Brian Robinson Jr.");

    const expanded = applyBoardNameOverrides(board, overrides);
    expect(expanded.every((r) => !r.playerName.startsWith("B."))).toBe(true);

    const { byPlayerId } = matchAdpToDeskRows(expanded, [
      fp({
        playerName: "Bijan Robinson",
        shortName: "B. Robinson",
        team: "ATL",
        position: "RB",
        adp: 1.67,
        ecr: 2,
      }),
      fp({
        playerName: "Brian Robinson Jr.",
        shortName: "B. Robinson Jr.",
        team: "ATL",
        position: "RB",
        adp: 142.33,
        ecr: 134,
      }),
    ]);

    expect(byPlayerId.get("00-0038542")?.adp).toBe(1.67);
    expect(byPlayerId.get("00-0038542")?.matchedName).toBe("Bijan Robinson");
    expect(byPlayerId.get("00-0037746")?.adp).toBe(142.33);
    expect(byPlayerId.get("00-0037746")?.matchedName).toBe(
      "Brian Robinson Jr.",
    );
    // Paying-subscriber gate: never re-introduce dual ADP 2.
    expect(byPlayerId.get("00-0037746")?.adp).not.toBe(1.67);
    expect([...byPlayerId.values()].filter((h) => h.adp === 1.67)).toHaveLength(
      1,
    );
  });
});
