import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

/**
 * Alex diagnosis (live GET):
 * - /odds/nfl: RSC ~22k className nodes — client-fetch board (not model JSON)
 * - Edge Board / Edges / Fair-lines: small HTML, SSR wait on model-service —
 *   do not block document on serial page fetches
 */
describe("NFL market page waterfall / RSC fat payload (Alex)", () => {
  it("Compare Odds page does not SSR the multi-book table (cuts className explosion)", () => {
    const page = readFileSync(
      path.join(process.cwd(), "app/odds/[sport]/page.tsx"),
      "utf8",
    );
    const board = readFileSync(
      path.join(process.cwd(), "components/OddsCompareBoard.tsx"),
      "utf8",
    );
    expect(page).toContain("OddsCompareBoard");
    expect(page).not.toMatch(/fetch\s*\(/);
    expect(page).not.toMatch(/\brows\.map\b/);
    expect(board).toContain('"use client"');
    expect(board).toContain("/api/odds/${sportKey}/compare");
  });

  it("Edge Board / Edges / Fair-lines shells do not await model-service before HTML", () => {
    const edgePage = readFileSync(
      path.join(process.cwd(), "app/edge-board/[sport]/page.tsx"),
      "utf8",
    );
    const edgesPage = readFileSync(
      path.join(process.cwd(), "app/(pro)/pro/nfl/edges/page.tsx"),
      "utf8",
    );
    const fairPage = readFileSync(
      path.join(process.cwd(), "app/(pro)/pro/nfl/fair-lines/page.tsx"),
      "utf8",
    );

    expect(edgePage).toContain("EdgeBoardSportClient");
    expect(edgePage).toContain("Promise.all");
    expect(edgePage).not.toContain("loadAssembledEdgeBoardRows");
    expect(edgePage).not.toContain("fetchNflFairLines");

    expect(edgesPage).toContain("NflEdgesDeskClient");
    expect(edgesPage).not.toContain("fetchNflEdgesDesk");

    expect(fairPage).toContain("NflFairLinesClient");
    expect(fairPage).not.toContain("fetchNflFairLines");
  });

  it("page-data APIs exist and desk keeps parallel fair∥today∥props", () => {
    const assemble = readFileSync(
      path.join(process.cwd(), "app/api/edge-board/[sport]/assemble/route.ts"),
      "utf8",
    );
    const edgesApi = readFileSync(
      path.join(process.cwd(), "app/api/nfl/edges-desk/route.ts"),
      "utf8",
    );
    const fairApi = readFileSync(
      path.join(process.cwd(), "app/api/nfl/fair-lines/route.ts"),
      "utf8",
    );
    const deskLib = readFileSync(
      path.join(process.cwd(), "lib/nfl-edges.ts"),
      "utf8",
    );

    expect(assemble).toContain("loadAssembledEdgeBoardRows");
    expect(assemble).toContain("resolveEdgeBoardBoardLinesAsOf");
    expect(edgesApi).toContain("fetchNflEdgesDesk");
    expect(fairApi).toContain("fetchNflFairLines");
    expect(deskLib).toMatch(
      /await Promise\.all\(\[\s*fetchNflFairLines[\s\S]*fetchNflEdgesToday[\s\S]*fetchNflPropsBoard/,
    );
  });

  it("as-of stamps stay wired on client boards (PR 416)", () => {
    const odds = readFileSync(
      path.join(process.cwd(), "components/OddsCompareBoard.tsx"),
      "utf8",
    );
    const edge = readFileSync(
      path.join(process.cwd(), "components/EdgeBoardSportClient.tsx"),
      "utf8",
    );
    const edges = readFileSync(
      path.join(process.cwd(), "components/pro/nfl/NflEdgesDeskClient.tsx"),
      "utf8",
    );
    const fair = readFileSync(
      path.join(process.cwd(), "components/pro/nfl/NflFairLinesClient.tsx"),
      "utf8",
    );

    expect(odds).toContain("compare-odds-asof");
    expect(edge).toContain("edge-board-asof");
    expect(edges).toContain("edges-desk-asof");
    expect(fair).toContain("kei-lines-asof");
    expect(fair).toContain("oddsAsOf");
    expect(fair).not.toMatch(/pickLatestIso\(board\.oddsAsOf,\s*board\.asOf\)/);
  });
});
