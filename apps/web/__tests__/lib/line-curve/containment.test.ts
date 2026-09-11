import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import {
  CFB_EDGE_BOARD_PUBLIC_ENABLED,
  customerCtaHref,
  isCfbEdgeBoardHref,
} from "@/lib/cfb-edge-board-public";
import {
  impliesCorrelationAdjusted,
  jointCoverColumnLabel,
  jointProbabilityCaption,
} from "@/lib/line-curve/joint-presentation";
import {
  correlationMeta,
  independentJointModel,
} from "@/lib/line-curve/joint-optimizer";
import { applyBestValue } from "@/lib/line-curve/labels";
import { parseOddsEventSnapshot } from "@/lib/line-curve/odds-adapter";
import type { OddsEvent } from "@/lib/odds-api";

function src(rel: string): string {
  return readFileSync(resolve(process.cwd(), rel), "utf8");
}

describe("line-curve Product/Validation containment", () => {
  it("does not leak the Missouri/Oklahoma fixture into production UI or API", () => {
    const ui = src("components/pro/line-curve/LineCurveResearchPanel.tsx");
    const get = src("app/api/line-curve/route.ts");
    const opt = src("app/api/line-curve/optimize/route.ts");
    expect(ui).not.toMatch(/missouri-oklahoma|Missouri \+1\.5/);
    expect(get).not.toMatch(/getMissouriOklahoma|missouriOklahomaFixture/);
    expect(opt).not.toMatch(/getMissouriOklahoma|missouriOklahomaFixture/);
    expect(get).toMatch(/test-only/);
    expect(opt).toMatch(/test-only/);
  });

  it("does not write Edge Board, odds snapshots, PLAY, or Odds Lake", () => {
    const engine = [
      "lib/line-curve/service.ts",
      "lib/line-curve/odds-adapter.ts",
      "lib/line-curve/alternate-pricing.ts",
      "lib/line-curve/joint-optimizer.ts",
      "app/api/line-curve/route.ts",
      "app/api/line-curve/optimize/route.ts",
    ]
      .map(src)
      .join("\n");
    expect(engine).not.toMatch(
      /insert into odds_snapshots|persistOdds|pull_odds_snapshot\(/i,
    );
    expect(engine).not.toMatch(/assembleEdgeBoard|loadAssembledEdgeBoardRows/);
    expect(engine).not.toMatch(/export_odds_lake|exportOddsLake/);
    expect(engine).not.toMatch(/\bPLAY\b|\bLEAN\b|publishTag/);
    expect(engine).toMatch(/researchOnly|Never persist into odds_snapshots/);
  });

  it("keeps the CFB public Edge Board kill switch independent of Line Curve", () => {
    expect(CFB_EDGE_BOARD_PUBLIC_ENABLED).toBe(false);
    expect(isCfbEdgeBoardHref("/pro/cfb/line-curve")).toBe(false);
    expect(customerCtaHref("/edge-board/cfb")).toBeNull();
    expect(customerCtaHref("/pro/cfb/line-curve")).toBe("/pro/cfb/line-curve");
  });

  it("presents independence — never correlation-adjusted when adjustment is null", () => {
    const meta = correlationMeta(independentJointModel());
    expect(meta.adjustment).toBeNull();
    expect(impliesCorrelationAdjusted(meta)).toBe(false);
    const caption = jointProbabilityCaption(meta);
    expect(caption).toMatch(/not correlation-adjusted/i);
    expect(caption).not.toMatch(/correlation-adjusted joint \(/i);
    expect(jointCoverColumnLabel(meta)).toBe("Indep. joint cover");
  });

  it("refuses BEST VALUE on same-game independence rows", () => {
    const rows = applyBestValue(
      [
        { evPerDollar: 0.08, label: "FAIR" as const },
        { evPerDollar: 0.01, label: "FAIR" as const },
      ],
      { sameGame: true, independenceUnadjusted: true },
    );
    expect(rows.every((r) => r.label !== "BEST VALUE")).toBe(true);
  });

  it("fails closed when Odds API omits alternate_spreads", () => {
    const event: OddsEvent = {
      id: "evt-1",
      sport_key: "americanfootball_ncaaf",
      commence_time: "2026-09-12T19:00:00Z",
      home_team: "Kansas",
      away_team: "Missouri",
      bookmakers: [
        {
          key: "draftkings",
          title: "DraftKings",
          last_update: "2026-09-11T01:00:00.000Z",
          markets: [
            {
              key: "spreads",
              last_update: "2026-09-11T01:00:00.000Z",
              outcomes: [
                { name: "Missouri", point: 1.5, price: -110 },
                { name: "Kansas", point: -1.5, price: -110 },
              ],
            },
          ],
        },
      ],
    };
    const parsed = parseOddsEventSnapshot({
      event,
      book: "draftkings",
      sport: "cfb",
    });
    expect("ok" in parsed && parsed.ok === false).toBe(true);
    if ("ok" in parsed && parsed.ok === false) {
      expect(parsed.code).toBe("unavailable_alt_market");
      expect(parsed.label).toBe("INSUFFICIENT");
    }
  });
});
