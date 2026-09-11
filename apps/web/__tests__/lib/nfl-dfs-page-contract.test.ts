import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

describe("DFS page contract", () => {
  const src = readFileSync(
    path.join(__dirname, "../../app/(pro)/pro/nfl/dfs/page.tsx"),
    "utf8",
  );

  it("does not fall back to season-rate spine or invented ceilings", () => {
    expect(src).not.toMatch(/loadPlayerSeasonTotalsSpine/);
    expect(src).not.toMatch(/1\.35/);
    expect(src).not.toMatch(/half.?ppr/i);
    expect(src).not.toMatch(/PLAY|PASS|LEAN/);
    expect(src).toMatch(/fetchNflDfsBoard/);
    expect(src).toMatch(/Ownership/);
  });

  it("clears slate when the site control changes", () => {
    const desk = readFileSync(
      path.join(__dirname, "../../components/pro/nfl/NflDfsDeskClient.tsx"),
      "utf8",
    );
    expect(desk).toMatch(
      /setParams\(\{\s*site:\s*value,\s*slate:\s*null\s*\}\)/,
    );
  });
});
