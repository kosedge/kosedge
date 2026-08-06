import { describe, expect, it } from "vitest";
import { valueDelta } from "@/lib/fantasy/adp-proxy";
import {
  bestAvailableByNeedAware,
  bestAvailableByValueAware,
  computeTiming,
  reachPenalty,
  scoreValueAwarePlayer,
  VALUE_AWARE_WEIGHTS,
} from "@/lib/fantasy/value-aware-recs";
import type { FantasyDeskRow } from "@/lib/fantasy/types";

function row(
  partial: Partial<FantasyDeskRow> & {
    playerId: string;
    playerName: string;
    position: string;
    rankOverall: number;
    adp: number;
  },
): FantasyDeskRow {
  const delta = valueDelta(partial.rankOverall, partial.adp);
  return {
    season: 2026,
    scoringProfile: "half_ppr",
    modelVersion: "test",
    playerUid: null,
    team: "KC",
    gamesProjected: 17,
    passYardsTotal: 0,
    rushYardsTotal: 800,
    receivingYardsTotal: 200,
    receptionsTotal: 30,
    passTdsTotal: 0,
    rushTdsTotal: 6,
    recTdsTotal: 2,
    totalPoints: 200,
    floorPoints: 160,
    medianPoints: 200 - partial.rankOverall,
    ceilingPoints: 240,
    replacementPoints: 100,
    valueOverReplacement: 100,
    rankPosition: partial.rankOverall,
    tier: partial.rankOverall <= 12 ? "RB1" : "flex",
    valueDelta: delta,
    adpMatchedName: partial.playerName,
    adpMatchConfidence: "high",
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
    drivers: ["volume"],
    updatedAt: null,
    source: "preseason-fallback",
    ...partial,
  };
}

function emptyCtx(
  available: FantasyDeskRow[],
  roster: FantasyDeskRow[] = [],
  pickOverall?: number,
) {
  return { available, roster, pickOverall };
}

describe("value-aware recommendations", () => {
  describe("philosophy examples", () => {
    it("model 18 / ADP 30 at pick 20 → wait, not forced early take", () => {
      const player = row({
        playerId: "discount",
        playerName: "Discount RB",
        position: "RB",
        rankOverall: 18,
        adp: 30,
      });
      const ctx = emptyCtx([player], [], 20);
      const scored = scoreValueAwarePlayer(player, ctx);
      expect(scored.timing).toBe("wait");
      expect(scored.timingHint).toMatch(/wait|ADP/i);

      const nearAdp = scoreValueAwarePlayer(player, {
        ...ctx,
        pickOverall: 28,
      });
      expect(nearAdp.timing).toBe("take_now");
    });

    it("model 22 / ADP 20 at pick 22 → fair / take-now window", () => {
      const player = row({
        playerId: "fair",
        playerName: "Fair WR",
        position: "WR",
        rankOverall: 22,
        adp: 20,
      });
      const scored = scoreValueAwarePlayer(player, emptyCtx([player], [], 22));
      expect(["fair", "take_now"]).toContain(scored.timing);
      expect(scored.timingHint).toMatch(/fair|ADP window/i);
    });

    it("model 15 / ADP 28 at pick 18 → high-value wait candidate", () => {
      const player = row({
        playerId: "wait",
        playerName: "Wait RB",
        position: "RB",
        rankOverall: 15,
        adp: 28,
      });
      const scored = scoreValueAwarePlayer(player, emptyCtx([player], [], 18));
      expect(scored.timing).toBe("wait");
      expect(player.valueDelta).toBe(13);
    });

    it("elite + cliff + need allows reach with reduced penalty", () => {
      const eliteTe = row({
        playerId: "elite-te",
        playerName: "Elite TE",
        position: "TE",
        rankOverall: 8,
        adp: 28,
        tier: "elite",
      });
      const te2 = row({
        playerId: "te2",
        playerName: "TE Two",
        position: "TE",
        rankOverall: 14,
        adp: 32,
      });
      const te3 = row({
        playerId: "te3",
        playerName: "TE Three",
        position: "TE",
        rankOverall: 20,
        adp: 40,
      });
      const available = [eliteTe, te2, te3];
      const roster: FantasyDeskRow[] = [
        row({
          playerId: "rb1",
          playerName: "RB1",
          position: "RB",
          rankOverall: 5,
          adp: 6,
        }),
        row({
          playerId: "rb2",
          playerName: "RB2",
          position: "RB",
          rankOverall: 12,
          adp: 14,
        }),
        row({
          playerId: "wr1",
          playerName: "WR1",
          position: "WR",
          rankOverall: 10,
          adp: 11,
        }),
        row({
          playerId: "wr2",
          playerName: "WR2",
          position: "WR",
          rankOverall: 16,
          adp: 18,
        }),
      ];
      const pickOverall = 22;
      const scored = scoreValueAwarePlayer(eliteTe, {
        available,
        roster,
        pickOverall,
      });
      expect(scored.timing).toBe("take_now");
      expect(scored.timingHint).toMatch(/need|cliff|take now/i);

      const fullReachPenalty = reachPenalty(
        eliteTe,
        24,
        0,
        0,
      );
      const reducedReach = reachPenalty(
        eliteTe,
        24,
        2,
        VALUE_AWARE_WEIGHTS.reachOverrideScarcityMin,
      );
      expect(fullReachPenalty).toBeGreaterThan(0);
      expect(reducedReach).toBeLessThan(fullReachPenalty);
    });
  });

  describe("early-round reach penalty", () => {
    it("penalizes reaching well ahead of ADP in round 1", () => {
      const reach = row({
        playerId: "reach",
        playerName: "Reach RB",
        position: "RB",
        rankOverall: 30,
        adp: 26,
      });
      const fair = row({
        playerId: "fair",
        playerName: "Fair RB",
        position: "RB",
        rankOverall: 10,
        adp: 11,
      });
      const available = [reach, fair];
      const suggestions = bestAvailableByValueAware(
        available,
        emptyCtx(available, [], 10),
        2,
      );
      expect(suggestions[0]?.row.playerId).toBe("fair");
    });

    it("ranks discount players above pure model rank when pick is early vs ADP", () => {
      const discount = row({
        playerId: "discount",
        playerName: "Later Value",
        position: "WR",
        rankOverall: 24,
        adp: 38,
      });
      const reachCandidate = row({
        playerId: "reach",
        playerName: "Reach Now",
        position: "WR",
        rankOverall: 20,
        adp: 32,
      });
      const available = [discount, reachCandidate];
      const atPick18 = bestAvailableByValueAware(
        available,
        emptyCtx(available, [], 18),
        2,
      );
      expect(atPick18[0]?.row.playerId).toBe("discount");
      expect(atPick18[0]?.timing).toBe("wait");
    });
  });

  describe("ranking helpers", () => {
    it("need-aware fills WR hole before raw model order", () => {
      const wr = row({
        playerId: "wr",
        playerName: "Need WR",
        position: "WR",
        rankOverall: 30,
        adp: 32,
      });
      const rb = row({
        playerId: "rb",
        playerName: "Better RB",
        position: "RB",
        rankOverall: 20,
        adp: 22,
      });
      const roster = [
        row({
          playerId: "rb1",
          playerName: "RB1",
          position: "RB",
          rankOverall: 8,
          adp: 9,
        }),
      ];
      const available = [wr, rb];
      const suggestions = bestAvailableByNeedAware(
        available,
        emptyCtx(available, roster, 25),
        2,
      );
      expect(suggestions[0]?.row.position).toBe("WR");
    });
  });

  describe("computeTiming", () => {
    it("returns wait for strong positive value delta when ADP is later", () => {
      const player = row({
        playerId: "x",
        playerName: "X",
        position: "RB",
        rankOverall: 18,
        adp: 30,
      });
      const timing = computeTiming(player, 20, {}, 0, 0);
      expect(timing.timing).toBe("wait");
    });

    it("returns take_now when ADP within urgency window", () => {
      const player = row({
        playerId: "x",
        playerName: "X",
        position: "RB",
        rankOverall: 22,
        adp: 24,
      });
      const timing = computeTiming(player, 22, {}, 0, 0);
      expect(timing.timing).toBe("take_now");
    });
  });

  describe("VALUE_AWARE_WEIGHTS", () => {
    it("exports tunable knobs", () => {
      expect(VALUE_AWARE_WEIGHTS.reachPenaltyPerPick).toBeGreaterThan(0);
      expect(VALUE_AWARE_WEIGHTS.discountBonusScale).toBeGreaterThan(0);
      expect(VALUE_AWARE_WEIGHTS.eliteRankThreshold).toBe(12);
    });
  });
});
