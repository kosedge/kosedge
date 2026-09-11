import { describe, expect, it } from "vitest";
import {
  buildHomePreviewRows,
  HOME_PREVIEW_FIXTURES,
} from "@/lib/edge-board-home-preview";
import {
  cfbCustomerPublishTag,
  CFB_EDGE_BOARD_PUBLIC_ENABLED,
  isCfbEdgeBoardCustomerEnabled,
} from "@/lib/cfb-edge-board-public";
import {
  cfbEdgeTag,
  CFB_PLAY_EDGE_PTS,
  CFB_SPREAD_PLAY_ELIGIBLE,
  CFB_TOTALS_PLAY_ELIGIBLE,
} from "@/lib/cfb-trusted-market";

/**
 * Homepage eye-catcher is a customer CFB Edge Board surface.
 * While the public kill switch is off: no rows, no PLAY/LEAN/PASS.
 * Tagger math (`cfbEdgeTag`) stays sit-aware and unchanged.
 */
describe("homepage Edge Board homePreviewRows sit-aware tags", () => {
  it("sit flags remain false (do not flip in this PR)", () => {
    expect(CFB_SPREAD_PLAY_ELIGIBLE).toBe(false);
    expect(CFB_TOTALS_PLAY_ELIGIBLE).toBe(false);
    expect(CFB_PLAY_EDGE_PTS).toBe(4.0);
  });

  it("hides homepage CFB preview rows while the public kill switch is off", () => {
    expect(CFB_EDGE_BOARD_PUBLIC_ENABLED).toBe(false);
    expect(isCfbEdgeBoardCustomerEnabled()).toBe(false);
    expect(buildHomePreviewRows()).toEqual([]);
  });

  it("customer publish emits no PLAY/LEAN/PASS while disabled", () => {
    for (const f of HOME_PREVIEW_FIXTURES) {
      expect(
        cfbCustomerPublishTag(f.edgeLineNum, cfbEdgeTag, "spread"),
      ).toBeUndefined();
    }
  });

  it("SMU@FSU and UNLV@Hawaii PLAY-band edges still tag PASS in the tagger", () => {
    const smu = HOME_PREVIEW_FIXTURES.find((f) => f.id === "home-smu-fsu");
    const unlv = HOME_PREVIEW_FIXTURES.find((f) => f.id === "home-unlv-hawaii");
    expect(smu?.edgeLineNum).toBe(5.4);
    expect(unlv?.edgeLineNum).toBe(5.5);
    expect(cfbEdgeTag(smu!.edgeLineNum, "spread")).toBe("PASS");
    expect(cfbEdgeTag(unlv!.edgeLineNum, "spread")).toBe("PASS");
    expect(cfbEdgeTag(smu!.edgeLineNum, "spread")).not.toBe("PLAY");
    expect(cfbEdgeTag(unlv!.edgeLineNum, "spread")).not.toBe("PLAY");
    expect(cfbEdgeTag(smu!.edgeLineNum, "spread")).not.toBe("LEAN");
    expect(cfbEdgeTag(unlv!.edgeLineNum, "spread")).not.toBe("LEAN");
  });

  it("every ≥4.0 fixture edge tags PASS via cfbEdgeTag (math path)", () => {
    const playBand = HOME_PREVIEW_FIXTURES.filter(
      (f) => Math.abs(f.edgeLineNum) >= CFB_PLAY_EDGE_PTS,
    );
    expect(playBand.length).toBeGreaterThanOrEqual(2);
    for (const f of playBand) {
      expect(cfbEdgeTag(f.edgeLineNum, "spread"), f.id).toBe("PASS");
    }
  });

  it("sub-LEAN SJSU@EMU stays PASS in the tagger", () => {
    const fixture = HOME_PREVIEW_FIXTURES.find((f) => f.id === "home-sjsu-emu");
    expect(fixture?.edgeLineNum).toBe(1.4);
    expect(cfbEdgeTag(fixture!.edgeLineNum, "spread")).toBe("PASS");
  });
});
