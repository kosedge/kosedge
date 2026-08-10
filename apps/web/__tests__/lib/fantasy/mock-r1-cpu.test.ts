import { describe, expect, it } from "vitest";
import {
  autoCompleteDraft,
  createMockDraftState,
  defaultMockConfig,
  isDraftComplete,
} from "@/lib/fantasy/mock-draft-engine";
import type { FantasyDeskRow } from "@/lib/fantasy/types";

function row(
  partial: Partial<FantasyDeskRow> & {
    playerId: string;
    playerName: string;
    position: string;
    rankOverall: number;
    adp: number | null;
    valueDelta: number | null;
  },
): FantasyDeskRow {
  return {
    season: 2026,
    scoringProfile: "half_ppr",
    modelVersion: "test",
    playerUid: null,
    team: "KC",
    gamesProjected: 17,
    passYardsTotal: partial.position === "QB" ? 4200 : 0,
    rushYardsTotal: partial.position === "RB" ? 1100 : 200,
    receivingYardsTotal: ["WR", "TE"].includes(partial.position) ? 1000 : 200,
    receptionsTotal: 50,
    passTdsTotal: partial.position === "QB" ? 30 : 0,
    rushTdsTotal: 6,
    recTdsTotal: 4,
    totalPoints: 250 - partial.rankOverall,
    floorPoints: 180,
    medianPoints: 220 - partial.rankOverall * 0.3,
    ceilingPoints: 280,
    replacementPoints: 100,
    valueOverReplacement: 80,
    rankPosition: 1,
    tier: "elite",
    adpMatchedName: partial.playerName,
    adpMatchConfidence: partial.adp != null ? "high" : null,
    isRookie: false,
    rookieYear: null,
    draftNumber: null,
    schedule: {
      early: "neutral",
      playoff: "neutral",
      label: "Neutral",
      detail: "",
    },
    riskFlags: [],
    expertBlurb: "",
    drivers: [],
    updatedAt: null,
    source: "preseason-fallback",
    ...partial,
  };
}

/**
 * Stress board: elite model QBs with late ADP (the pre-hotfix failure mode).
 * Skill studs have early ADP.
 */
function stressBoard(): FantasyDeskRow[] {
  const qbs = [
    row({
      playerId: "qb1",
      playerName: "Model QB1",
      position: "QB",
      rankOverall: 1,
      adp: 85,
      valueDelta: 84,
    }),
    row({
      playerId: "qb2",
      playerName: "Model QB2",
      position: "QB",
      rankOverall: 3,
      adp: 55,
      valueDelta: 52,
    }),
    row({
      playerId: "qb3",
      playerName: "Model QB3",
      position: "QB",
      rankOverall: 5,
      adp: 70,
      valueDelta: 65,
    }),
  ];
  const skills = Array.from({ length: 40 }, (_, i) => {
    const positions = ["RB", "WR", "RB", "WR", "TE"] as const;
    const position = positions[i % positions.length]!;
    return row({
      playerId: `sk${i}`,
      playerName: `Skill ${i}`,
      position,
      rankOverall: i + 6,
      adp: i + 1,
      valueDelta: (i + 1) - (i + 6),
      medianPoints: 210 - i,
    });
  });
  const depth = Array.from({ length: 200 }, (_, i) =>
    row({
      playerId: `d${i}`,
      playerName: `Depth ${i}`,
      position: (["RB", "WR", "TE", "QB"] as const)[i % 4]!,
      rankOverall: 50 + i,
      adp: 60 + i,
      valueDelta: 5,
      medianPoints: 140,
    }),
  );
  return [...qbs, ...skills, ...depth].sort(
    (a, b) => a.rankOverall - b.rankOverall,
  );
}

describe("mock R1 CPU after QB hotfix", () => {
  it("does not flood Round 1 with QBs despite huge model-vs-ADP value", () => {
    const board = stressBoard();
    // Slot 12 so CPU takes all of R1 first when we auto-complete from start…
    // Better: start draft and auto-complete from pick 1 with user as slot 12.
    let state = createMockDraftState({
      config: defaultMockConfig(12, "half_ppr", 12),
      board,
    });
    state = autoCompleteDraft(board, state);
    expect(isDraftComplete(state)).toBe(true);

    const round1 = state.picks.filter((p) => p.round === 1);
    expect(round1).toHaveLength(12);
    const r1Qbs = round1.filter((p) => p.position.toUpperCase() === "QB");
    // Personas intact, but 1QB market structure: at most one early QB.
    expect(r1Qbs.length).toBeLessThanOrEqual(1);
    const skillEarly = round1.filter((p) =>
      ["RB", "WR", "TE"].includes(p.position.toUpperCase()),
    );
    expect(skillEarly.length).toBeGreaterThanOrEqual(10);
  });

  it("auto-pick to end lands on results with full pick count", () => {
    const board = stressBoard();
    let state = createMockDraftState({
      config: defaultMockConfig(10, "half_ppr", 1),
      board,
    });
    // User would be on the clock — auto-complete uses CPU for all seats.
    state = autoCompleteDraft(board, state);
    expect(state.phase).toBe("results");
    expect(state.picks).toHaveLength(10 * 15);
  });

  it("limits late-bench QB stacking once a starter QB is rostered", () => {
    const board = stressBoard();
    let state = createMockDraftState({
      config: defaultMockConfig(12, "half_ppr", 6),
      board,
    });
    state = autoCompleteDraft(board, state);
    // Average QBs per CPU roster should stay near 1–2, not 5+.
    const byTeam = new Map<number, number>();
    for (const pick of state.picks) {
      if (pick.position.toUpperCase() !== "QB") continue;
      byTeam.set(pick.teamIndex, (byTeam.get(pick.teamIndex) ?? 0) + 1);
    }
    const maxQb = Math.max(...byTeam.values(), 0);
    expect(maxQb).toBeLessThanOrEqual(3);
  });

  it("never lets ADP-269 fringe TE steal a top-5 overall pick", () => {
    const fringeTe = row({
      playerId: "gesicki",
      playerName: "Mike Gesicki",
      position: "TE",
      rankOverall: 40,
      adp: 269,
      valueDelta: 229,
      valueOverReplacement: 30,
      medianPoints: 140,
    });
    const board = [fringeTe, ...stressBoard()]
      .filter(
        (r, i, arr) => arr.findIndex((x) => x.playerId === r.playerId) === i,
      )
      .sort((a, b) => a.rankOverall - b.rankOverall);

    let state = createMockDraftState({
      config: defaultMockConfig(12, "half_ppr", 12),
      board,
    });
    state = autoCompleteDraft(board, state);

    const top5 = state.picks.filter((p) => p.overall <= 5);
    expect(top5).toHaveLength(5);
    expect(top5.every((p) => p.playerId !== "gesicki")).toBe(true);
    expect(
      top5.every((p) => {
        const adp = board.find((r) => r.playerId === p.playerId)?.adp;
        return adp == null || adp < 40;
      }),
    ).toBe(true);

    const gesickiPick = state.picks.find((p) => p.playerId === "gesicki");
    if (gesickiPick) {
      expect(gesickiPick.round).toBeGreaterThan(1);
    }
  });
});
