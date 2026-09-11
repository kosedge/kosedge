/**
 * P0 2026-09-11 — CFB Edge Board public visibility kill switch.
 */
import { existsSync } from "node:fs";
import { readFileSync } from "node:fs";
import path from "node:path";
import { afterEach, describe, expect, it } from "vitest";
import {
  CFB_EDGE_BOARD_PUBLIC_ENABLED,
  CFB_EDGE_BOARD_UNAVAILABLE_CODE,
  CFB_EDGE_BOARD_UNAVAILABLE_MESSAGE,
  cfbCustomerPublishTag,
  cfbEdgeBoardAssembleUnavailablePayload,
  customerCtaHref,
  isCfbEdgeBoardCustomerDisabled,
  isCfbEdgeBoardCustomerEnabled,
  isCfbEdgeBoardHref,
  isCfbSportKey,
  publicEdgeBoardHref,
  publicEdgeBoardSportKeys,
  publicEdgeBoardSports,
  stripCfbCustomerEdgeTags,
  withoutCfbEdgeBoardHrefs,
} from "@/lib/cfb-edge-board-public";
import { EDGE_BOARD_SPORTS } from "@/lib/edge-board-customer-truth";
import { scrubEdgeBoardAssembleCustomerRows } from "@/lib/edge-board-assemble-quarantine";
import { cfbEdgeTag } from "@/lib/cfb-trusted-market";
import { getSportPrimaryNav } from "@/lib/sport-pro-nav";
import { SPORTS } from "@/lib/sports";

const webRoot = path.join(__dirname, "../..");
const repoRoot = path.join(webRoot, "../..");

function readRel(rel: string): string {
  return readFileSync(path.join(webRoot, rel), "utf8");
}

describe("CFB Edge Board public kill switch", () => {
  afterEach(() => {
    delete process.env.CFB_EDGE_BOARD_INTERNAL;
    delete process.env.NEXT_PUBLIC_CFB_EDGE_BOARD_INTERNAL;
  });

  it("is off by default (public constant)", () => {
    expect(CFB_EDGE_BOARD_PUBLIC_ENABLED).toBe(false);
    expect(isCfbEdgeBoardCustomerEnabled()).toBe(false);
    expect(isCfbEdgeBoardCustomerDisabled("cfb")).toBe(true);
    expect(isCfbEdgeBoardCustomerDisabled("CFB")).toBe(true);
    expect(isCfbSportKey("cfb")).toBe(true);
  });

  it("does not disable other sports", () => {
    for (const sport of ["nfl", "nba", "mlb", "nhl", "wnba", "ncaam"]) {
      expect(isCfbEdgeBoardCustomerDisabled(sport)).toBe(false);
      expect(publicEdgeBoardHref(sport)).toBe(`/edge-board/${sport}`);
    }
  });

  it("omits CFB from the public Edge Board selector and keeps other sports", () => {
    const keys = publicEdgeBoardSports(SPORTS).map((s) => s.key);
    expect(keys).not.toContain("cfb");
    expect(keys).toEqual(
      expect.arrayContaining(["nfl", "nba", "mlb", "nhl", "wnba", "ncaam"]),
    );
    expect(publicEdgeBoardSportKeys(EDGE_BOARD_SPORTS)).not.toContain("cfb");
    expect(publicEdgeBoardSportKeys(EDGE_BOARD_SPORTS)).toEqual(
      expect.arrayContaining(["nfl", "nba", "mlb", "nhl", "wnba", "ncaam"]),
    );
    expect(EDGE_BOARD_SPORTS).toContain("cfb");
  });

  it("fail-closes direct CFB Edge Board URLs with the exact customer message", () => {
    expect(CFB_EDGE_BOARD_UNAVAILABLE_MESSAGE).toBe(
      "CFB Edge Board temporarily unavailable while market coverage is being validated.",
    );
    const payload = cfbEdgeBoardAssembleUnavailablePayload();
    expect(payload.error).toBe(CFB_EDGE_BOARD_UNAVAILABLE_CODE);
    expect(payload.message).toBe(CFB_EDGE_BOARD_UNAVAILABLE_MESSAGE);
    expect(payload.rows).toEqual([]);
    expect(payload.games).toBe(0);

    const page = readRel("app/edge-board/[sport]/page.tsx");
    expect(page).toContain("isCfbEdgeBoardCustomerDisabled");
    expect(page).toContain("CfbEdgeBoardUnavailable");
    expect(page).toContain("cfbPublicDisabled");

    const assemble = readRel("app/api/edge-board/[sport]/assemble/route.ts");
    expect(assemble).toContain("isCfbEdgeBoardCustomerDisabled");
    expect(assemble).toContain("cfbEdgeBoardAssembleUnavailablePayload");
    expect(assemble).toContain("status: 503");

    const unavailable = readRel("components/CfbEdgeBoardUnavailable.tsx");
    expect(unavailable).toContain("CFB_EDGE_BOARD_UNAVAILABLE_MESSAGE");
    expect(unavailable).toContain("cfb-edge-board-unavailable-message");
  });

  it("publishes zero CFB PLAY/LEAN/PASS/value tags while disabled", () => {
    expect(cfbCustomerPublishTag(6.0, cfbEdgeTag, "spread")).toBeUndefined();
    expect(cfbCustomerPublishTag(3.0, cfbEdgeTag, "spread")).toBeUndefined();
    expect(cfbCustomerPublishTag(0.5, cfbEdgeTag, "total")).toBeUndefined();

    const tagged = stripCfbCustomerEdgeTags({
      game: "Ball State @ Ohio State",
      market: "Spread",
      publishTag: "PLAY",
      actionLabel: "LEAN",
      tag: "PASS",
      tagLine: "PLAY",
      tagOU: "LEAN",
      actionLabelLine: "PLAY",
      actionLabelOU: "PASS",
      playLine: "Ohio State -20",
      playOU: "Over 55",
      publishTagSpread: "PLAY",
      publishTagTotal: "LEAN",
      publishTagMl: "PASS",
      kei: "-21.5",
      decision: { publishTag: "PLAY", actionLabel: "LEAN", reason: "ok" },
    });
    expect(tagged.publishTag).toBeUndefined();
    expect(tagged.actionLabel).toBeUndefined();
    expect(tagged.tag).toBeUndefined();
    expect(tagged.tagLine).toBeUndefined();
    expect(tagged.tagOU).toBeUndefined();
    expect(tagged.actionLabelLine).toBeUndefined();
    expect(tagged.actionLabelOU).toBeUndefined();
    expect(tagged.playLine).toBeUndefined();
    expect(tagged.playOU).toBeUndefined();
    expect(tagged.publishTagSpread).toBeUndefined();
    expect(tagged.publishTagTotal).toBeUndefined();
    expect(tagged.publishTagMl).toBeUndefined();
    expect(tagged.kei).toBe("-21.5");
    expect(
      (tagged.decision as { publishTag?: string; actionLabel?: string })
        .publishTag,
    ).toBeUndefined();
    expect(
      (tagged.decision as { publishTag?: string; actionLabel?: string })
        .actionLabel,
    ).toBeUndefined();

    const scrubbed = scrubEdgeBoardAssembleCustomerRows(
      [
        {
          game: "A @ B",
          market: "Spread",
          publishTag: "PLAY",
          actionLabel: "LEAN",
        } as never,
      ],
      "cfb",
    );
    expect((scrubbed[0] as { publishTag?: string }).publishTag).toBeUndefined();
    expect(
      (scrubbed[0] as { actionLabel?: string }).actionLabel,
    ).toBeUndefined();

    const nflScrubbed = scrubEdgeBoardAssembleCustomerRows(
      [
        {
          game: "KC @ BUF",
          market: "Spread",
          publishTag: "LEAN",
          actionLabel: "LEAN",
        } as never,
      ],
      "nfl",
    );
    expect((nflScrubbed[0] as { publishTag?: string }).publishTag).toBe("LEAN");
  });

  it("does not change CFB tagger math (sit-aware PASS still exists internally)", () => {
    expect(cfbEdgeTag(6.0, "spread")).toBe("PASS");
    expect(cfbEdgeTag(3.0, "spread")).toBe("LEAN");
    expect(cfbEdgeTag(1.0, "spread")).toBe("PASS");
  });

  it("hides CFB Edge Board from public/pro chrome and keeps other sports listed", () => {
    const cfbPrimary = getSportPrimaryNav("cfb").map((i) => i.label);
    expect(cfbPrimary).not.toContain("Edge Board");
    expect(cfbPrimary).toContain("Overview");
    expect(cfbPrimary).toContain("Model");

    expect(getSportPrimaryNav("nfl").map((i) => i.label)).toContain(
      "Edge Board",
    );
    expect(getSportPrimaryNav("nba").map((i) => i.label)).toContain(
      "Edge Board",
    );
    expect(getSportPrimaryNav("ncaam").map((i) => i.label)).toContain(
      "Edge Board",
    );

    expect(publicEdgeBoardHref("cfb")).toBeNull();
    expect(customerCtaHref("/edge-board/cfb")).toBeNull();
    expect(customerCtaHref("/edge-board/cfb?week=1")).toBeNull();
    expect(customerCtaHref("/edge-board/nfl")).toBe("/edge-board/nfl");
    expect(isCfbEdgeBoardHref("/edge-board/cfb?week=2")).toBe(true);
    expect(isCfbEdgeBoardHref("/edge-board/nfl")).toBe(false);

    const filtered = withoutCfbEdgeBoardHrefs([
      { href: "/edge-board/cfb?week=1", label: "CFB" },
      { href: "/edge-board/nfl", label: "NFL" },
      { href: "/pro/cfb/model", label: "Model" },
    ]);
    expect(filtered.map((i) => i.label)).toEqual(["NFL", "Model"]);
  });

  it("leaves underlying CFB lib/API/research modules in place (not deleted)", () => {
    const present = [
      "lib/cfb-trusted-market.ts",
      "lib/cfb-edge-board-week.ts",
      "lib/cfb-kei-artifacts.ts",
      "lib/cfb-season-engine.ts",
      "lib/build-edge-board-rows.ts",
      "app/api/edge-board/[sport]/assemble/route.ts",
      "app/api/edge-board/[sport]/today/route.ts",
      "app/edge-board/[sport]/page.tsx",
      "data/processed/edge_board_fallback_cfb.json",
    ];
    for (const rel of present) {
      expect(existsSync(path.join(webRoot, rel)), rel).toBe(true);
    }
    expect(
      existsSync(
        path.join(repoRoot, "services/model-service/src/routes/edge_board.py"),
      ),
    ).toBe(true);
    const today = readRel("app/api/edge-board/[sport]/today/route.ts");
    expect(today).not.toContain("isCfbEdgeBoardCustomerDisabled");
    expect(today).toContain("x-kosedge-secret");
  });

  it("documents the kill-switch flip and internal override", () => {
    const src = readRel("lib/cfb-edge-board-public.ts");
    expect(src).toContain("CFB_EDGE_BOARD_PUBLIC_ENABLED");
    expect(src).toContain("CFB_EDGE_BOARD_INTERNAL");
    expect(src).toContain("re-enable");
    expect(src).toContain("canonical game joins");
  });

  it("internal env override re-enables customer surfaces without flipping the constant", () => {
    expect(CFB_EDGE_BOARD_PUBLIC_ENABLED).toBe(false);
    process.env.CFB_EDGE_BOARD_INTERNAL = "1";
    expect(isCfbEdgeBoardCustomerEnabled()).toBe(true);
    expect(isCfbEdgeBoardCustomerDisabled("cfb")).toBe(false);
    expect(publicEdgeBoardHref("cfb")).toBe("/edge-board/cfb");
    expect(publicEdgeBoardSports(SPORTS).map((s) => s.key)).toContain("cfb");
    expect(cfbCustomerPublishTag(3.0, cfbEdgeTag, "spread")).toBe("LEAN");
  });

  it("Edge Board sport client selector uses the public helper", () => {
    const client = readRel("components/EdgeBoardSportClient.tsx");
    expect(client).toContain("publicEdgeBoardSports");
    expect(client).not.toMatch(/SPORTS\.map\(\(s\) => \(/);
  });
});
