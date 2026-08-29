import { describe, expect, it } from "vitest";

import {
  applyPackInjuryToDraftRow,
  type EnrichableDraftRow,
} from "@/lib/fantasy/enrich";
import type { DepthRow } from "@/lib/fantasy/risk-signals";
import { buildRiskFlags } from "@/lib/fantasy/risk-signals";
import {
  applySurfaceIntegrityToPlayerTotals,
  PASS_TD_YARDS_PER,
  REC_TD_YARDS_PER,
} from "@/lib/nfl-surface-integrity";
import {
  readinessBlocksPlay,
  shouldShowNflPreseasonReadinessBanner,
} from "@/lib/nfl-production-readiness";

function baseRow(
  overrides: Partial<EnrichableDraftRow> = {},
): EnrichableDraftRow {
  return {
    season: 2026,
    scoringProfile: "half_ppr",
    modelVersion: "nfl-player-v1",
    playerId: "00-0040130",
    playerUid: null,
    playerName: "Jayden Higgins",
    team: "HOU",
    position: "WR",
    gamesProjected: 17,
    passYardsTotal: 0,
    rushYardsTotal: 0,
    receivingYardsTotal: 491,
    receptionsTotal: 40,
    passTdsTotal: 0,
    rushTdsTotal: 0,
    recTdsTotal: 0,
    totalPoints: 80,
    replacementPoints: 0,
    valueOverReplacement: 10,
    rankOverall: 100,
    rankPosition: 40,
    tier: "5",
    isRookie: true,
    rookieYear: 2025,
    draftNumber: 34,
    updatedAt: null,
    source: "model-service",
    ...overrides,
  };
}

describe("nfl surface integrity — web", () => {
  it("zeros Higgins HOU when pack injury_status=out", () => {
    const depth: DepthRow[] = [
      {
        team: "HOU",
        position: "WR",
        depthOrder: 2,
        playerName: "Jayden Higgins",
        roleConfidence: 0.7,
        playerId: "00-0040130",
        injuryStatus: "out",
      },
    ];
    const patched = applyPackInjuryToDraftRow(baseRow(), depth);
    expect(patched.gamesProjected).toBe(0);
    expect(patched.receivingYardsTotal).toBe(0);
    expect(patched.recTdsTotal).toBe(0);

    const flags = buildRiskFlags({
      playerName: patched.playerName,
      team: patched.team,
      position: patched.position,
      isRookie: true,
      gamesProjected: patched.gamesProjected,
      rushYardsTotal: 0,
      depthRows: depth,
      teammateRushYards: [],
    });
    expect(flags.some((f) => f.kind === "availability")).toBe(true);
  });

  it("CSV fallback recouples TDs to yards; spine pages must not use CSV TDs", () => {
    const rows = applySurfaceIntegrityToPlayerTotals(
      [
        {
          season: 2026,
          playerKey: "00-0033873",
          playerName: "Matthew Stafford",
          team: "LAR",
          position: "QB",
          gamesProjected: 17,
          passYardsTotal: 4252,
          rushYardsTotal: 0,
          receivingYardsTotal: 0,
          receptionsTotal: 0,
          passTdsTotal: 16.5,
          rushTdsTotal: 0,
          recTdsTotal: 0,
          anytimeTdProbTotal: 0,
        },
        {
          season: 2026,
          playerKey: "00-0036322",
          playerName: "Ja'Marr Chase",
          team: "CIN",
          position: "WR",
          gamesProjected: 17,
          passYardsTotal: 0,
          rushYardsTotal: 0,
          receivingYardsTotal: 1791,
          receptionsTotal: 120,
          passTdsTotal: 0,
          rushTdsTotal: 0,
          recTdsTotal: 6.5,
          anytimeTdProbTotal: 0.4,
        },
      ],
      2026,
      { recoupleTds: true },
    );
    const stafford = rows[0];
    const chase = rows[1];
    expect(stafford.passTdsTotal).toBeCloseTo(4252 / PASS_TD_YARDS_PER, 5);
    expect(chase.recTdsTotal).toBeCloseTo(1791 / REC_TD_YARDS_PER, 5);
  });

  it("shows PRESEASON readiness banner when sample 0 / no-go", () => {
    expect(
      shouldShowNflPreseasonReadinessBanner({
        status: "no-go",
        reasons: ["sample_size_ok"],
        sampleSize: 0,
        clvOk: false,
      }),
    ).toBe(true);
    expect(
      readinessBlocksPlay({
        status: "no-go",
        reasons: ["sample_size_ok"],
        sampleSize: 0,
        clvOk: false,
      }),
    ).toBe(true);
    expect(
      shouldShowNflPreseasonReadinessBanner({
        status: "go",
        reasons: [],
        sampleSize: 200,
        clvOk: true,
      }),
    ).toBe(false);
  });
});
