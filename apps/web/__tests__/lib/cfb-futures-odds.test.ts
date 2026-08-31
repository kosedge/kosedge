import { describe, expect, it } from "vitest";
import { americanImpliedProb } from "@/lib/american-odds";
import {
  formatCfbImpliedPct,
  formatCfbMarketOdds,
  formatCfbOddsAsOf,
} from "@/lib/cfb-futures-odds-format";
import {
  cfbFuturesRosterSize,
  matchCfbFuturesTeamName,
} from "@/lib/cfb-futures-name-match";
import { findCfbFutures, loadCfbFuturesPack } from "@/lib/cfb-kei-artifacts";

describe("cfb futures market name match", () => {
  it("maps Odds API championship names onto our codes", () => {
    expect(matchCfbFuturesTeamName("Ohio State Buckeyes")).toBe("OSU");
    expect(matchCfbFuturesTeamName("Notre Dame Fighting Irish")).toBe("ND");
    expect(matchCfbFuturesTeamName("Miami Hurricanes")).toBe("MIA");
    expect(matchCfbFuturesTeamName("Oregon Ducks")).toBe("ORE");
    expect(matchCfbFuturesTeamName("Ole Miss Rebels")).toBe("MISS");
    expect(matchCfbFuturesTeamName("Texas A&M Aggies")).toBe("TAMU");
    expect(matchCfbFuturesTeamName("Miami (OH) RedHawks")).toBe("M-OH");
    expect(matchCfbFuturesTeamName("Southern Mississippi Golden Eagles")).toBe(
      "USM",
    );
    expect(matchCfbFuturesTeamName("Delaware Blue Hens")).toBe("DEL");
    expect(matchCfbFuturesTeamName("San José State Spartans")).toBe("SJSU");
    expect(matchCfbFuturesTeamName("Hawai'i Rainbow Warriors")).toBe("HAW");
  });

  it("does not invent a code for unknown or transitioning names", () => {
    expect(matchCfbFuturesTeamName("North Dakota State Bison")).toBeNull();
    expect(matchCfbFuturesTeamName("Sacramento State Hornets")).toBeNull();
    expect(matchCfbFuturesTeamName("")).toBeNull();
    expect(matchCfbFuturesTeamName("Tigers")).toBeNull();
  });

  it("covers the 136-team FBS roster", () => {
    expect(cfbFuturesRosterSize()).toBe(136);
  });
});

describe("cfb futures implied % + honesty", () => {
  it("converts American odds with the standard raw formula", () => {
    expect(americanImpliedProb(600)).toBeCloseTo(100 / 700, 6);
    expect(americanImpliedProb(-150)).toBeCloseTo(150 / 250, 6);
    expect(
      formatCfbImpliedPct({
        american: 600,
        impliedPct: 14.3,
        book: "DraftKings",
        asOfUtc: "2026-08-17T12:26:35Z",
      }),
    ).toBe("14.3%");
    expect(
      formatCfbMarketOdds({
        american: 600,
        impliedPct: 14.3,
        book: "DraftKings",
        asOfUtc: null,
      }),
    ).toBe("+600");
    expect(formatCfbMarketOdds(null)).toBe("—");
    expect(formatCfbImpliedPct(null)).toBe("—");
    expect(formatCfbOddsAsOf("2026-08-17T12:26:35Z")).toBe(
      "2026-08-17 12:26:35 UTC",
    );
  });

  it("leaves sim Natty / CFP / conf % unchanged", () => {
    // Honesty: loaders expose artifact sim % as-is (no market blend).
    // Snapshot values move with Week-0 close re-sim; assert against the pack.
    const pack = loadCfbFuturesPack();
    const osuRow = pack.teams.find((t) => t.team === "OSU");
    const ndRow = pack.teams.find((t) => t.team === "ND");
    const osu = findCfbFutures("OSU");
    const nd = findCfbFutures("ND");
    expect(osuRow).toBeTruthy();
    expect(ndRow).toBeTruthy();
    expect(osu?.natty_pct).toBe(osuRow?.natty_pct);
    expect(osu?.cfp_make_pct).toBe(osuRow?.cfp_make_pct);
    expect(osu?.conf_title_pct).toBe(osuRow?.conf_title_pct);
    expect(nd?.natty_pct).toBe(ndRow?.natty_pct);
    expect(nd?.cfp_make_pct).toBe(ndRow?.cfp_make_pct);
    expect(nd?.conf_title_pct ?? null).toBe(ndRow?.conf_title_pct ?? null);
    expect(osu?.natty_pct).toBeGreaterThan(0);
    expect(osu?.cfp_make_pct).toBeGreaterThan(0);
    expect(pack.used_in_spread).toBe(false);
    expect(pack.kei).toBe(false);
  });
});
