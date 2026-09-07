import { describe, expect, it } from "vitest";
import {
  NHL_GAME_MONEYLINE_LABEL,
  NHL_MODEL_DISAGREEMENT_LABEL,
  NHL_PUCK_LINE_EDGE_LABEL,
  NHL_PUCK_LINE_LABEL,
  NHL_RESEARCH_SIGNAL_LABEL,
  nhlDisplayMarketLabel,
  nhlEdgeBoardTagFooter,
} from "@/lib/nhl-edge-board-display";
import { NHL_LEAN_EDGE_PTS, NHL_PLAY_EDGE_PTS } from "@/lib/nhl-trusted-market";

describe("nhl-edge-board-display (honesty naming + footer cuts)", () => {
  it("footer cuts match trusted-market constants (not legacy 1 / 2.5)", () => {
    expect(NHL_LEAN_EDGE_PTS).toBe(2.5);
    expect(NHL_PLAY_EDGE_PTS).toBe(4.0);
    const footer = nhlEdgeBoardTagFooter();
    expect(footer).toContain(`LEAN (≥${NHL_LEAN_EDGE_PTS})`);
    expect(footer).toContain(`PLAY (≥${NHL_PLAY_EDGE_PTS})`);
    expect(footer).toContain("goal units");
    expect(footer).toContain("trusted Best");
    expect(footer).toMatch(/research-fair/i);
    expect(footer).not.toMatch(/LEAN \(≥1\)/);
    expect(footer).not.toMatch(/PLAY \(≥2\.5\)/);
  });

  it("renames Spread → Puck Line for customer display", () => {
    expect(NHL_PUCK_LINE_LABEL).toBe("Puck Line");
    expect(NHL_PUCK_LINE_EDGE_LABEL).toBe("Puck Line edge");
    expect(nhlDisplayMarketLabel("Spread")).toBe("Puck Line");
    expect(nhlDisplayMarketLabel("Total")).toBe("Total");
  });

  it("labels two-way ML as Game Moneyline — Includes OT/Shootout", () => {
    expect(NHL_GAME_MONEYLINE_LABEL).toBe(
      "Game Moneyline — Includes OT/Shootout",
    );
    expect(nhlDisplayMarketLabel("Moneyline")).toBe(NHL_GAME_MONEYLINE_LABEL);
    expect(NHL_GAME_MONEYLINE_LABEL).not.toMatch(/Regulation/i);
  });

  it("research-only chrome prefers MODEL DISAGREEMENT / RESEARCH SIGNAL", () => {
    expect(NHL_MODEL_DISAGREEMENT_LABEL).toBe("MODEL DISAGREEMENT");
    expect(NHL_RESEARCH_SIGNAL_LABEL).toBe("RESEARCH SIGNAL");
  });
});
