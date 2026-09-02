import { describe, expect, it } from "vitest";
import { getSportDeskConfig } from "@/lib/pro-sport-desk";
import { getSportGlance } from "@/lib/sport-overview";
import { getSportToolNav } from "@/lib/sport-pro-nav";

describe("NHL Ch7 fantasy desk wiring", () => {
  it("glance and desk link Edge Board / Fantasy / Props dark", () => {
    const glance = getSportGlance("nhl");
    const hrefs = glance.map((g) => g.href);
    expect(hrefs).toContain("/edge-board/nhl");
    expect(hrefs).toContain("/pro/nhl/fantasy");
    expect(hrefs).toContain("/pro/nhl/props");

    const desk = getSportDeskConfig("nhl");
    expect(desk.pathLabel).toContain("Fantasy");
    const cardHrefs = desk.cards.map((c) => c.href);
    expect(cardHrefs).toContain("/edge-board/nhl");
    expect(cardHrefs).toContain("/pro/nhl/fantasy");
    expect(cardHrefs).toContain("/pro/nhl/props");

    expect(getSportToolNav("nhl").map((i) => i.label)).toContain("Fantasy");
  });
});
