import { describe, expect, it } from "vitest";
import {
  buildHomePreviewRows,
  HOME_PREVIEW_FIXTURES,
} from "@/lib/edge-board-home-preview";
import {
  cfbEdgeTag,
  CFB_PLAY_EDGE_PTS,
  CFB_SPREAD_PLAY_ELIGIBLE,
  CFB_TOTALS_PLAY_ELIGIBLE,
} from "@/lib/cfb-trusted-market";

/**
 * Homepage eye-catcher must not bypass the sat tagger with stamped PLAY.
 * With CFB_*_PLAY_ELIGIBLE=false, trusted ≥4.0 edges → PASS (not PLAY, not
 * demoted to LEAN).
 */
describe("homepage Edge Board homePreviewRows sit-aware tags", () => {
  it("sit flags remain false (do not flip in this PR)", () => {
    expect(CFB_SPREAD_PLAY_ELIGIBLE).toBe(false);
    expect(CFB_TOTALS_PLAY_ELIGIBLE).toBe(false);
    expect(CFB_PLAY_EDGE_PTS).toBe(4.0);
  });

  it("SMU@FSU and UNLV@Hawaii PLAY-band edges tag PASS, not PLAY", () => {
    const rows = buildHomePreviewRows();
    const byId = Object.fromEntries(rows.map((r) => [r.id, r]));

    expect(byId["home-smu-fsu"]?.edgeLineNum).toBe(5.4);
    expect(byId["home-unlv-hawaii"]?.edgeLineNum).toBe(5.5);
    expect(byId["home-smu-fsu"]?.tagLine).toBe("PASS");
    expect(byId["home-unlv-hawaii"]?.tagLine).toBe("PASS");
    expect(byId["home-smu-fsu"]?.tagLine).not.toBe("PLAY");
    expect(byId["home-unlv-hawaii"]?.tagLine).not.toBe("PLAY");
    // PLAY-band must not be remapped to LEAN under sit doctrine.
    expect(byId["home-smu-fsu"]?.tagLine).not.toBe("LEAN");
    expect(byId["home-unlv-hawaii"]?.tagLine).not.toBe("LEAN");
  });

  it("every ≥4.0 fixture edge tags PASS via cfbEdgeTag (homepage path)", () => {
    const playBand = HOME_PREVIEW_FIXTURES.filter(
      (f) => Math.abs(f.edgeLineNum) >= CFB_PLAY_EDGE_PTS,
    );
    expect(playBand.length).toBeGreaterThanOrEqual(2);
    for (const f of playBand) {
      expect(cfbEdgeTag(f.edgeLineNum, "spread"), f.id).toBe("PASS");
    }
    const rows = buildHomePreviewRows();
    for (const r of rows) {
      if (r.edgeLineNum >= CFB_PLAY_EDGE_PTS) {
        expect(r.tagLine, r.id).toBe("PASS");
      }
      // Builder identity: same as sit-aware tagger.
      expect(r.tagLine, r.id).toBe(cfbEdgeTag(r.edgeLineNum, "spread"));
    }
  });

  it("sub-LEAN SJSU@EMU stays PASS", () => {
    const row = buildHomePreviewRows().find((r) => r.id === "home-sjsu-emu");
    expect(row?.edgeLineNum).toBe(1.4);
    expect(row?.tagLine).toBe("PASS");
  });
});
