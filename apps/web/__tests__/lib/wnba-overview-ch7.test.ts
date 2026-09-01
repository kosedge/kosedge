import { describe, expect, it } from "vitest";
import { getSportDeskConfig } from "@/lib/pro-sport-desk";
import { getSportGlance } from "@/lib/sport-overview";
import { getSportToolNav } from "@/lib/sport-pro-nav";

describe("WNBA Ch7 fantasy desk wiring", () => {
  it("glance and desk link Edge Board / Fantasy / Props dark", () => {
    const glance = getSportGlance("wnba");
    const hrefs = glance.map((g) => g.href);
    expect(hrefs).toContain("/edge-board/wnba");
    expect(hrefs).toContain("/pro/wnba/fantasy");
    expect(hrefs).toContain("/pro/wnba/props");

    const desk = getSportDeskConfig("wnba");
    expect(desk.pathLabel).toContain("Fantasy");
    const cardHrefs = desk.cards.map((c) => c.href);
    expect(cardHrefs).toContain("/edge-board/wnba");
    expect(cardHrefs).toContain("/pro/wnba/fantasy");
    expect(cardHrefs).toContain("/pro/wnba/props");

    expect(getSportToolNav("wnba").map((i) => i.label)).toContain("Fantasy");
  });
});
