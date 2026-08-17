import { describe, expect, it } from "vitest";
import { cfbGameMatchKeys, cfbGamesMatch } from "@/lib/cfb-match-keys";
import { stampCfbEdgeBoardWeek } from "@/lib/cfb-kei-artifacts";
import { getKeiLines } from "@/lib/kei-lines";
import {
  applyCfbTrustedMarketToRows,
  cfbEdgeTag,
  trustCfbMarket,
} from "@/lib/cfb-trusted-market";

describe("cfb trusted market", () => {
  it("rejects the TCU-class junk book so it cannot PLAY", () => {
    const before = trustCfbMarket({
      kei: -20.39,
      best: 8.5,
      open: 7.5,
    });
    expect(before.trusted).toBe(false);
    expect(before.reason).toBe("absurd_vs_kei");
    expect(cfbEdgeTag(Math.abs(-20.39 - 8.5))).toBe("PLAY"); // raw would fire
    expect(cfbEdgeTag(before.market == null ? null : 28)).toBe("PASS");

    const rows = applyCfbTrustedMarketToRows([
      {
        market: "Spread",
        kei: "-20.4",
        best: "+8.5",
        open: "+7.5",
        book: "Hard Rock Bet",
        bookKey: "hardrockbet",
      },
    ]);
    expect(rows[0]?.best).toBeUndefined();
    expect(rows[0]?.book).toBe("untrusted");
  });

  it("keeps a normal multi-book number inside the KEI neighborhood", () => {
    const ok = trustCfbMarket({ kei: -5.3, best: -3.5, open: -3.0, bookCount: 2 });
    expect(ok.trusted).toBe(true);
    expect(ok.market).toBe(-3.5);
    expect(cfbEdgeTag(Math.abs(-5.3 - -3.5))).toBe("PASS");
  });
});

describe("cfb name match", () => {
  it("matches San José / San Jose and Hawaii aliases", () => {
    expect(
      cfbGamesMatch(
        "San José State Spartans @ USC Trojans",
        "San Jose State Spartans @ USC Trojans",
      ),
    ).toBe(true);
    expect(
      cfbGamesMatch(
        "Hawaii Rainbow Warriors @ Stanford Cardinal",
        "Hawai'i Rainbow Warriors @ Stanford Cardinal",
      ),
    ).toBe(true);
    expect(cfbGameMatchKeys("SJSU @ USC").length).toBeGreaterThan(0);
  });

  it("stamps week 0 on accent-mismatched Odds rows", () => {
    const stamped = stampCfbEdgeBoardWeek([
      { game: "San Jose State Spartans @ USC Trojans" },
      { game: "Hawaii Rainbow Warriors @ Stanford Cardinal" },
    ]);
    expect(stamped[0]?.week).toBe(0);
    expect(stamped[1]?.week).toBe(0);
  });
});

describe("cfb kei lines bundle", () => {
  it("publishes every W0 FBS KEI game with names the board can match", () => {
    const w0 = getKeiLines("cfb").filter((g) => g.week === 0);
    const homes = w0.map((g) => g.homeAbbr);
    expect(homes).toEqual(expect.arrayContaining(["TCU", "USC", "STAN", "FSU", "UNLV", "UVA"]));
    expect(w0).toHaveLength(6);
  });
});
