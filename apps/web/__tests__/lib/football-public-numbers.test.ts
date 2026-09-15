/**
 * Ryan 2026-09-15 — NFL+CFB public number kill switch (Coming soon).
 * Extends the CFB Edge Board pattern (#529) to NFL. Fail closed.
 */
import { readFileSync } from "node:fs";
import path from "node:path";
import { afterEach, describe, expect, it } from "vitest";
import {
  FOOTBALL_PUBLIC_NUMBERS_HEADING,
  NFL_EDGE_BOARD_PUBLIC_ENABLED,
  NFL_EDGE_BOARD_UNAVAILABLE_CODE,
  NFL_EDGE_BOARD_UNAVAILABLE_MESSAGE,
  customerCtaHref,
  footballPublicNumbersAssembleUnavailablePayload,
  isFootballPublicNumbersDisabled,
  isNflEdgeBoardCustomerDisabled,
  isNflEdgeBoardCustomerEnabled,
  isNflSportKey,
  publicEdgeBoardHref,
  publicEdgeBoardSports,
} from "@/lib/cfb-edge-board-public";
import { getSportPrimaryNav, getSportToolNav } from "@/lib/sport-pro-nav";
import { SPORTS } from "@/lib/sports";

const webRoot = path.join(__dirname, "../..");

function readRel(rel: string): string {
  return readFileSync(path.join(webRoot, rel), "utf8");
}

describe("football public numbers kill switch", () => {
  afterEach(() => {
    delete process.env.NFL_EDGE_BOARD_INTERNAL;
    delete process.env.NEXT_PUBLIC_NFL_EDGE_BOARD_INTERNAL;
    delete process.env.CFB_EDGE_BOARD_INTERNAL;
    delete process.env.NEXT_PUBLIC_CFB_EDGE_BOARD_INTERNAL;
  });

  it("is off by default for NFL and CFB", () => {
    expect(NFL_EDGE_BOARD_PUBLIC_ENABLED).toBe(false);
    expect(isNflEdgeBoardCustomerEnabled()).toBe(false);
    expect(isNflEdgeBoardCustomerDisabled("nfl")).toBe(true);
    expect(isNflEdgeBoardCustomerDisabled("NFL")).toBe(true);
    expect(isNflSportKey("nfl")).toBe(true);
    expect(isFootballPublicNumbersDisabled("nfl")).toBe(true);
    expect(isFootballPublicNumbersDisabled("cfb")).toBe(true);
    expect(FOOTBALL_PUBLIC_NUMBERS_HEADING).toBe("Coming soon");
  });

  it("does not park other sports", () => {
    for (const sport of ["nba", "mlb", "nhl", "wnba", "ncaam"]) {
      expect(isFootballPublicNumbersDisabled(sport)).toBe(false);
      expect(publicEdgeBoardHref(sport)).toBe(`/edge-board/${sport}`);
    }
  });

  it("fail-closes NFL assemble with empty rows and the validation message", () => {
    const payload = footballPublicNumbersAssembleUnavailablePayload("nfl");
    expect(payload.error).toBe(NFL_EDGE_BOARD_UNAVAILABLE_CODE);
    expect(payload.message).toBe(NFL_EDGE_BOARD_UNAVAILABLE_MESSAGE);
    expect(payload.rows).toEqual([]);
    expect(payload.games).toBe(0);
  });

  it("hides NFL Edge Board from chrome and keeps other sports listed", () => {
    expect(getSportPrimaryNav("nfl").map((i) => i.label)).not.toContain(
      "Edge Board",
    );
    expect(getSportPrimaryNav("nfl").map((i) => i.label)).toContain("Overview");
    expect(getSportPrimaryNav("nfl").map((i) => i.label)).toContain("Fantasy");
    expect(getSportPrimaryNav("nfl").map((i) => i.label)).toContain("Camp Desk");
    expect(getSportToolNav("nba").map((i) => i.label)).toContain("Edges desk");
    expect(publicEdgeBoardHref("nfl")).toBeNull();
    expect(customerCtaHref("/edge-board/nfl")).toBeNull();
    expect(publicEdgeBoardSports(SPORTS).map((s) => s.key)).not.toContain("nfl");
  });

  it("customer pages render Coming soon and do not bootstrap house numbers", () => {
    const surfaces = [
      "app/edge-board/[sport]/page.tsx",
      "app/(pro)/pro/nfl/edges/page.tsx",
      "app/(pro)/pro/nfl/fair-lines/page.tsx",
      "app/(pro)/pro/power-ratings/[sport]/page.tsx",
      "app/(pro)/pro/nfl/slate/[date]/page.tsx",
      "app/(pro)/pro/cfb/teams/page.tsx",
      "app/(pro)/pro/[sport]/edges/page.tsx",
      "app/(pro)/pro/[sport]/fair-lines/page.tsx",
      "components/FootballNumbersUnavailable.tsx",
    ];
    const unavailable = readRel("components/FootballNumbersUnavailable.tsx");
    expect(unavailable).toContain("FOOTBALL_PUBLIC_NUMBERS_HEADING");
    expect(unavailable).toContain("Coming soon");

    for (const rel of surfaces) {
      expect(readRel(rel), rel).toContain("FootballNumbersUnavailable");
    }
  });

  it("internal env override re-enables NFL without flipping the constant", () => {
    expect(NFL_EDGE_BOARD_PUBLIC_ENABLED).toBe(false);
    process.env.NFL_EDGE_BOARD_INTERNAL = "1";
    expect(isNflEdgeBoardCustomerEnabled()).toBe(true);
    expect(isNflEdgeBoardCustomerDisabled("nfl")).toBe(false);
    expect(isFootballPublicNumbersDisabled("nfl")).toBe(false);
    expect(publicEdgeBoardHref("nfl")).toBe("/edge-board/nfl");
    expect(publicEdgeBoardSports(SPORTS).map((s) => s.key)).toContain("nfl");
    expect(isFootballPublicNumbersDisabled("cfb")).toBe(true);
  });

  it("does not touch secret today assemble or research libs", () => {
    const today = readRel("app/api/edge-board/[sport]/today/route.ts");
    expect(today).not.toContain("isFootballPublicNumbersDisabled");
    expect(today).toContain("x-kosedge-secret");
    const pub = readRel("lib/cfb-edge-board-public.ts");
    expect(pub).toContain("NFL_EDGE_BOARD_PUBLIC_ENABLED = false");
    expect(pub).toContain("CFB_EDGE_BOARD_PUBLIC_ENABLED = false");
    expect(pub).toContain("CoS CLEAR");
  });
});
