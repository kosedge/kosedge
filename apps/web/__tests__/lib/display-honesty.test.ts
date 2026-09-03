import { describe, expect, it } from "vitest";
import { formatConfidence } from "@/lib/nfl-props-board";
import { deskEdgeFromPropRow } from "@/lib/nfl-edges";
import type { NflPropBoardRow } from "@/lib/nfl-props-board";
import {
  displayConfidenceForProps,
  displaySuppressionNoteForUi,
  failOpenDisplayHonestyFlags,
  formatGameConfidenceLabel,
  loadDisplayHonestyFlags,
  parseDisplayHonestyFlags,
  shouldSuppressPropsConfidence,
} from "@/lib/display-honesty";

function propRow(
  partial: Partial<NflPropBoardRow> &
    Pick<NflPropBoardRow, "marketKey" | "confidence">,
): NflPropBoardRow {
  return {
    season: 2026,
    week: 1,
    modelVersion: "test",
    gameId: "g1",
    playerId: "p1",
    playerUid: null,
    playerName: "Test Player",
    team: "SEA",
    marketKey: partial.marketKey,
    line: 0.5,
    modelMean: 0.4,
    modelStd: null,
    modelFloor: null,
    modelMedian: null,
    modelCeiling: null,
    overProb: 0.55,
    underProb: 0.45,
    fairOverPrice: -120,
    fairUnderPrice: 100,
    marketOverPrice: -110,
    marketUnderPrice: -110,
    edgeOver: 0.08,
    edgeUnder: -0.02,
    confidence: partial.confidence,
    updatedAt: null,
    marketJoined: true,
    tag: null,
    tagSide: null,
    tagAction: null,
    sizeDown: false,
    stakeEligible: false,
    projectionSource: null,
    zOver: null,
    position: "WR",
    roleConfidence: null,
    ...partial,
  };
}

describe("display honesty kill switch", () => {
  it("formatConfidence: null → em dash; 0 → 0%", () => {
    expect(formatConfidence(null)).toBe("—");
    expect(formatConfidence(0)).toBe("0%");
    expect(formatConfidence(0.72)).toBe("72%");
  });

  it("off state renders em dash via null display confidence (never 0)", () => {
    const flags = parseDisplayHonestyFlags(
      { nfl_props_confidence_display: "off" },
      "global-config",
    );
    const suppressed = displayConfidenceForProps(0.81, "rush_yds", flags);
    expect(suppressed).toBeNull();
    expect(formatConfidence(suppressed)).toBe("—");
    expect(formatConfidence(suppressed)).not.toBe("0%");
  });

  it("suppressed row still renders and is counted", () => {
    const flags = parseDisplayHonestyFlags(
      { nfl_props_confidence_display: "off" },
      "global-config",
    );
    const rows = [
      propRow({ marketKey: "rush_yds", confidence: 0.2 }),
      propRow({ marketKey: "anytime_td", confidence: 0.9 }),
    ];
    const displayed = rows.map((row) => ({
      ...row,
      confidence: displayConfidenceForProps(
        row.confidence,
        row.marketKey,
        flags,
      ),
    }));
    expect(displayed).toHaveLength(2);
    expect(displayed.every((r) => r.confidence === null)).toBe(true);
    expect(displayed.map((r) => formatConfidence(r.confidence))).toEqual([
      "—",
      "—",
    ]);
  });

  it("market-subset off blanks anytime_td only", () => {
    const flags = parseDisplayHonestyFlags(
      {
        nfl_props_confidence_display: "on",
        nfl_props_confidence_display_off_markets: ["anytime_td"],
      },
      "global-config",
    );
    expect(shouldSuppressPropsConfidence("anytime_td", flags)).toBe(true);
    expect(shouldSuppressPropsConfidence("rush_yds", flags)).toBe(false);
    expect(displayConfidenceForProps(0.77, "anytime_td", flags)).toBeNull();
    expect(displayConfidenceForProps(0.77, "rush_yds", flags)).toBe(0.77);
    expect(
      formatConfidence(displayConfidenceForProps(0.77, "rush_yds", flags)),
    ).toBe("77%");
  });

  it("edges desk minConfidence keeps suppressed null rows", () => {
    const flags = parseDisplayHonestyFlags(
      {
        nfl_props_confidence_display: "on",
        nfl_props_confidence_display_off_markets: ["anytime_td"],
      },
      "global-config",
    );
    const lowConfAtd = propRow({
      marketKey: "anytime_td",
      confidence: 0.1,
      edgeOver: 0.08,
      marketJoined: true,
    });
    const suppressed = {
      ...lowConfAtd,
      confidence: displayConfidenceForProps(
        lowConfAtd.confidence,
        lowConfAtd.marketKey,
        flags,
      ),
    };
    const kept = deskEdgeFromPropRow(suppressed, {
      minProbEdge: 0.05,
      minConfidence: 0.5,
    });
    expect(kept).not.toBeNull();
    expect(kept?.confidence).toBeNull();

    const dropped = deskEdgeFromPropRow(lowConfAtd, {
      minProbEdge: 0.05,
      minConfidence: 0.5,
    });
    expect(dropped).toBeNull();
  });

  it("game band off shows Conf — instead of vanishing", () => {
    expect(formatGameConfidenceLabel(undefined, 0.72, false)).toBeNull();
    expect(
      formatGameConfidenceLabel("HIGH", 0.81, false, { suppressed: true }),
    ).toBe("Conf —");
    expect(
      formatGameConfidenceLabel(undefined, undefined, false, {
        suppressed: true,
      }),
    ).toBe("Conf —");
    expect(formatGameConfidenceLabel("MEDIUM", 0.72, true)).toBe("Conf MEDIUM");
  });

  it("fail-open on missing store / read error", async () => {
    const flags = await loadDisplayHonestyFlags({
      getFn: async () => {
        throw new Error("No connection string");
      },
    });
    expect(flags).toEqual(failOpenDisplayHonestyFlags());
    expect(flags.source).toBe("fallback");
    expect(flags.nfl_props_confidence_display).toBe("on");
    expect(flags.nfl_game_confidence_band_display).toBe("on");
    expect(displaySuppressionNoteForUi(flags)).toBeNull();
  });

  it("parseOnOff treats anything but exact off as on", () => {
    const flags = parseDisplayHonestyFlags(
      {
        nfl_props_confidence_display: "OFF",
        nfl_game_confidence_band_display: false,
      },
      "global-config",
    );
    expect(flags.nfl_props_confidence_display).toBe("on");
    expect(flags.nfl_game_confidence_band_display).toBe("on");
  });

  it("exposes subscriber-safe note when any flag is off", () => {
    const withCustom = parseDisplayHonestyFlags(
      {
        nfl_props_confidence_display: "off",
        display_suppression_note: "Confidence paused for cal check.",
      },
      "global-config",
    );
    expect(displaySuppressionNoteForUi(withCustom)).toBe(
      "Confidence paused for cal check.",
    );
    const withDefault = parseDisplayHonestyFlags(
      { nfl_game_confidence_band_display: "off" },
      "global-config",
    );
    expect(displaySuppressionNoteForUi(withDefault)).toMatch(/hidden/i);
  });
});
