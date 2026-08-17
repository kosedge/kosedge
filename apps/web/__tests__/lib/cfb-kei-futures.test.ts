import { describe, expect, it } from "vitest";
import {
  cfbFuturesByCode,
  cfbKeiGames,
  cfbKeiVersionStrip,
  findCfbFutures,
  findCfbKeiGame,
  loadCfbFuturesPack,
  loadCfbKeiPack,
} from "@/lib/cfb-kei-artifacts";
import { sportHasKeiSource } from "@/lib/edge-board-kei-availability";
import { getKeiLines } from "@/lib/kei-lines";

const W0_FBS = [
  ["TCU", "UNC"],
  ["USC", "SJSU"],
  ["UVA", "NCSU"],
  ["STAN", "HAW"],
  ["FSU", "NMSU"],
  ["UNLV", "MEM"],
] as const;

describe("cfb KEI + futures artifacts", () => {
  it("publishes Model + KEI for every Week 0 FBS–FBS game", () => {
    const pack = loadCfbKeiPack();
    expect(pack.used_in_spread).toBe(true);
    expect(pack.model_used_in_spread).toBe(false);
    expect(pack.n_w0_fbs_with_kei).toBe(6);
    expect(sportHasKeiSource("cfb")).toBe(true);

    const w0 = cfbKeiGames(0).filter((g) => g.fbs_vs_fbs);
    expect(w0).toHaveLength(6);
    for (const [home, away] of W0_FBS) {
      const row = findCfbKeiGame(home, away);
      expect(row?.kei?.kei_spread_home).toEqual(expect.any(Number));
      expect(row?.model_spread_home).toEqual(expect.any(Number));
      expect(row?.kei?.used_in_spread).toBe(true);
      expect(row?.kei?.kei_spread_home).not.toBe(row?.model_spread_home);
    }

    const lines = getKeiLines("cfb");
    expect(lines.length).toBeGreaterThanOrEqual(6);
    const tcu = lines.find((g) => g.homeAbbr === "TCU" && g.awayAbbr === "UNC");
    expect(tcu?.handicapSpreadHome).toBe(-20.39);
    expect(tcu?.modelSpreadHome).toBe(-19.19);
    expect(tcu?.homeTeam).toBe("TCU Horned Frogs");
    expect(tcu?.awayTeam).toBe("North Carolina Tar Heels");
  });

  it("ships sim-derived futures for 136 teams with documented N", () => {
    const pack = loadCfbFuturesPack();
    const version = cfbKeiVersionStrip();
    expect(pack.n_sims).toBeGreaterThanOrEqual(2500);
    expect(version.n_sims).toBeGreaterThanOrEqual(2500);
    expect(pack.cfp_field).toBe(12);
    expect(pack.teams?.length).toBeGreaterThanOrEqual(130);
    expect(cfbFuturesByCode().size).toBeGreaterThanOrEqual(130);

    const topNatty = (pack.top_natty ?? pack.teams ?? []).slice(0, 10);
    expect(topNatty.map((t) => t.team)).toEqual(
      expect.arrayContaining(["OSU", "ND", "MIA", "ORE"]),
    );
    expect(findCfbFutures("OSU")?.natty_pct).toBeGreaterThan(10);
    expect(findCfbFutures("ND")?.cfp_make_pct).toBeGreaterThan(80);
    expect(findCfbFutures("ND")?.conf_title_pct).toBeNull();
  });
});
