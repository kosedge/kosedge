import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { marketAsOfHeaderSuffix } from "@/lib/market-asof-stamp";

const webRoot = path.join(__dirname, "../..");

/**
 * #8 Phase C1 — Edge Board SSR as-of first paint.
 * Contract (#4 E8): real assemble linesAsOf OR honest “as-of unavailable”.
 * Never mint “as of now”; prefer fail-closed loading stamp over blank “…”.
 * Keep Alex waterfall: page shell must not await assemble / model-service.
 */
describe("Edge Board SSR as-of first paint (C1)", () => {
  it("loading paint stamps unavailable — never blank ellipsis or invent-now", () => {
    const client = readFileSync(
      path.join(webRoot, "components/EdgeBoardSportClient.tsx"),
      "utf8",
    );

    // Stamp always mounted (not gated off loading).
    expect(client).toContain('data-testid="edge-board-asof"');
    expect(client).toContain("MarketAsOfStamp");
    expect(client).not.toMatch(
      /status === "ready" \|\|\s*state\.status === "error" \|\|\s*state\.status === "slow" \? \(\s*<MarketAsOfStamp/,
    );

    // Header uses honest suffix for every status (incl. loading).
    expect(client).toContain("marketAsOfHeaderSuffix({");
    expect(client).toContain("asOf: boardLinesAsOf");
    expect(client).toContain('kind: "lines"');
    expect(client).not.toMatch(/status === "loading"\s*\?\s*"…"/);
    expect(client).not.toMatch(/Date\.now\(\)/);
    expect(client).not.toMatch(/new Date\(\)\.toISOString/);

    // Loading chrome still present; rows not invented.
    expect(client).toContain('data-testid="edge-board-loading"');
    expect(client).toContain("Loading board…");
  });

  it("blank stamp resolves to unavailable copy (contract)", () => {
    expect(marketAsOfHeaderSuffix({ asOf: null, kind: "lines" })).toBe(
      "as-of unavailable",
    );
    expect(marketAsOfHeaderSuffix({ asOf: "", kind: "lines" })).toBe(
      "as-of unavailable",
    );
  });

  it("SSR shell stays waterfall-safe (no assemble await on page)", () => {
    const page = readFileSync(
      path.join(webRoot, "app/edge-board/[sport]/page.tsx"),
      "utf8",
    );
    expect(page).toContain("EdgeBoardSportClient");
    expect(page).not.toContain("loadAssembledEdgeBoardRows");
    // #12 GO-1: inline bootstrap may call fetch() — must not await assemble.
    expect(page).toContain("edgeBoardAssembleBootstrapScript");
    expect(page).not.toMatch(/await\s+loadAssembled/);
    expect(page).not.toMatch(/await\s+fetch\s*\(/);
    expect(page).not.toMatch(/\blinesAsOf\b/);
  });
});
