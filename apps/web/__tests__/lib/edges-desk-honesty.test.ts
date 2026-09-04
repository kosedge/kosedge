import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import {
  EDGE_BOARD_RESEARCH_FAIR_HONESTY,
  EDGES_DESK_SEPARATIONS_PENDING_TITLE,
  edgesDeskQuantifiedLine,
  edgesDeskSummary,
  NFL_EDGES_DESK_SUMMARY,
  NFL_EDGES_DESK_TITLE,
} from "@/lib/edges-desk-honesty";

const webRoot = path.join(__dirname, "../..");

function readRel(rel: string): string {
  return readFileSync(path.join(webRoot, rel), "utf8");
}

/**
 * #8 Phase C last slice — desk fork honesty (Phase B #5 · #4 E4).
 * `/pro/{sport}/edges` stays live; must not ship model-vs-market as competing
 * decision-center truth vs Edge Board research-fair honesty.
 */
describe("edges desk honesty fork (#8 Phase C / #4 E4)", () => {
  it("shared constants demote desk and ban model-vs-market decision framing", () => {
    expect(EDGE_BOARD_RESEARCH_FAIR_HONESTY).toContain("KEI vs market");
    expect(EDGE_BOARD_RESEARCH_FAIR_HONESTY).toContain("research-fair");
    expect(EDGE_BOARD_RESEARCH_FAIR_HONESTY).toContain(
      "Tags never use Model vs market",
    );

    const summary = edgesDeskSummary("Edge Board → Project Game");
    expect(summary).toMatch(/Demoted desk/i);
    expect(summary).toMatch(/Edge Board is the decision center/i);
    expect(summary).toMatch(/KEI vs market/i);
    expect(summary).toMatch(/research-fair/i);
    expect(summary.toLowerCase()).not.toContain("model-vs-market");
    expect(summary).toContain("Edge Board → Project Game");

    expect(edgesDeskQuantifiedLine(38)).toBe(
      "38 matchups with KEI vs market separation on the current board.",
    );
    expect(edgesDeskQuantifiedLine(38).toLowerCase()).not.toContain(
      "model-vs-market",
    );
    expect(EDGES_DESK_SEPARATIONS_PENDING_TITLE).toContain("KEI separations");
    expect(EDGES_DESK_SEPARATIONS_PENDING_TITLE.toLowerCase()).not.toContain(
      "model separations",
    );

    expect(NFL_EDGES_DESK_TITLE).toBe("Edges desk");
    expect(NFL_EDGES_DESK_TITLE.toLowerCase()).not.toContain("model vs market");
    expect(NFL_EDGES_DESK_SUMMARY.toLowerCase()).not.toContain(
      "model vs market edges",
    );
    expect(NFL_EDGES_DESK_SUMMARY).toMatch(
      /Edge Board is the decision center/i,
    );
  });

  it("source-locks shared sport edges page through honesty helpers (no model-vs-market)", () => {
    const src = readRel("app/(pro)/pro/[sport]/edges/page.tsx");
    expect(src).toMatch(/from\s+["']@\/lib\/edges-desk-honesty["']/);
    expect(src).toContain("edgesDeskSummary");
    expect(src).toContain("edgesDeskQuantifiedLine");
    expect(src).toContain("EDGES_DESK_SEPARATIONS_PENDING_TITLE");
    expect(src.toLowerCase()).not.toContain("model-vs-market");
    expect(src).not.toContain("Thresholded model-vs-market");
    // #4 E4 — desk stays live (no redirect-away of the edges surface itself).
    expect(src).not.toMatch(/redirect\(["'`]\/edge-board\//);
    expect(src).not.toMatch(/permanentRedirect/);
  });

  it("source-locks NFL edges desk client off Model vs Market H1", () => {
    const src = readRel("components/pro/nfl/NflEdgesDeskClient.tsx");
    expect(src).toMatch(/from\s+["']@\/lib\/edges-desk-honesty["']/);
    expect(src).toContain("NFL_EDGES_DESK_TITLE");
    expect(src).toContain("NFL_EDGES_DESK_SUMMARY");
    expect(src).not.toContain("Model vs Market Edges");
  });

  it("does not 308 /pro/{sport}/edges away from the desk", () => {
    const nextConfig = readRel("next.config.ts");
    expect(nextConfig).not.toMatch(
      /source:\s*["']\/pro\/:sport[^"']*\/edges["']/,
    );
    // Canonical Edge Board aliases still 308 — edges desk must remain distinct.
    expect(nextConfig).toContain('destination: "/edge-board/:sport"');
  });
});
