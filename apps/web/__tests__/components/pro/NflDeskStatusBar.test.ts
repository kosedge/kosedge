import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

const webRoot = join(__dirname, "../../..");

function readSrc(rel: string) {
  return readFileSync(join(webRoot, rel), "utf8");
}

describe("NflDeskStatusBar chrome", () => {
  it("is not mounted on SportProShell product layouts", () => {
    const src = readSrc("components/pro/SportProShell.tsx");
    expect(src).not.toContain("NflDeskStatusBar");
    expect(src).not.toContain("nfl-desk-status-bar");
    expect(src).not.toContain("NflProductionReadinessBanner");
    expect(src).not.toContain("NflDataFreshnessBanner");
  });

  it("is not mounted on edge-board", () => {
    const src = readSrc("app/edge-board/[sport]/page.tsx");
    expect(src).not.toContain("NflDeskStatusBar");
    expect(src).not.toContain("nfl-desk-status-bar");
    expect(src).not.toContain("NflDataFreshnessBanner");
  });

  it("component still exists for ops probes but is not a customer mount", () => {
    const src = readSrc("components/pro/NflDeskStatusBar.tsx");
    expect(src).toContain("fetchNflProductionReadiness");
    expect(src).toContain("fetchNflDataFreshness");
    expect(src).toContain("#desk-status");
  });
});
