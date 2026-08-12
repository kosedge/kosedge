import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import {
  NFL_CLV_BEAT_CLOSE_LABEL,
  NFL_CLV_DEFINITION,
  NFL_CLV_LIVE_INCOMPLETE_NOTE,
  formatClvRate,
  liveClvHeroAllowed,
} from "@/lib/nfl-clv-semantics";

describe("NFL CLV semantics copy", () => {
  it("defines CLV as beating the later line on our recommended side", () => {
    expect(NFL_CLV_DEFINITION.toLowerCase()).toContain("beat the close");
    expect(NFL_CLV_DEFINITION.toLowerCase()).toContain("recommended side");
    expect(NFL_CLV_BEAT_CLOSE_LABEL).toBe("Beat later snapshot");
    expect(NFL_CLV_BEAT_CLOSE_LABEL.toLowerCase()).not.toBe("positive clv rate");
  });

  it("does not treat a push-heavy sample as a hero beat-close rate", () => {
    expect(
      liveClvHeroAllowed({
        trustworthy: false,
        reasons: ["preseason_no_reg_closes", "majority_identical_open_close"],
        decided_n: 2,
      }),
    ).toBe(false);
    expect(formatClvRate(0.089, 0)).toBe("—");
    expect(formatClvRate(0.5, 2)).toBe("50.0%");
  });

  it("allows a hero rate only when live CLV is marked trustworthy", () => {
    expect(
      liveClvHeroAllowed({ trustworthy: true, decided_n: 80 }),
    ).toBe(true);
    expect(liveClvHeroAllowed({ trustworthy: true, decided_n: 0 })).toBe(false);
  });

  it("Tracking page uses the shared definition and never heroes unlabeled Positive CLV rate", () => {
    const src = readFileSync(
      path.join(__dirname, "../../app/(pro)/pro/[sport]/tracking/page.tsx"),
      "utf8",
    );
    expect(src).toContain("NFL_CLV_DEFINITION");
    expect(src).toContain("NFL_CLV_BEAT_CLOSE_LABEL");
    expect(src).toContain("liveClvHeroAllowed");
    expect(src).toContain("NFL_CLV_LIVE_INCOMPLETE_NOTE");
    expect(src).not.toMatch(/Positive CLV rate/);
    expect(src).toContain("PRESEASON");
    expect(src).toContain("ARCHIVE");
  });

  it("incomplete note explains pushes are not beat-close misses", () => {
    expect(NFL_CLV_LIVE_INCOMPLETE_NOTE.toLowerCase()).toContain("pushes");
    expect(NFL_CLV_LIVE_INCOMPLETE_NOTE.toLowerCase()).toContain(
      "beat the close",
    );
  });
});
