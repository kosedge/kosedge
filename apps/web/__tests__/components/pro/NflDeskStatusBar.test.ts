import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

const webRoot = join(__dirname, "../../..");

function readSrc(rel: string) {
  return readFileSync(join(webRoot, rel), "utf8");
}

describe("NflDeskStatusBar chrome", () => {
  it("SportProShell mounts one slim bar, not two banners", () => {
    const src = readSrc("components/pro/SportProShell.tsx");
    expect(src).toMatch(/import \{ NflDeskStatusBar \}/);
    expect(src.match(/<NflDeskStatusBar\s*\/>/g)?.length).toBe(1);
    expect(src).not.toContain("NflProductionReadinessBanner");
    expect(src).not.toContain("NflDataFreshnessBanner");
  });

  it("edge-board NFL mounts the same single bar outside SportProShell", () => {
    const src = readSrc("app/edge-board/[sport]/page.tsx");
    expect(src.match(/<NflDeskStatusBar\s*\/>/g)?.length).toBe(1);
    expect(src).not.toContain("NflDataFreshnessBanner");
  });

  it("status bar copy stays token-only (no probe essays in the closed row)", () => {
    const src = readSrc("components/pro/NflDeskStatusBar.tsx");
    expect(src).toContain('tokens.push("PRESEASON")');
    expect(src).toContain('tokens.push("data stale")');
    expect(src).toContain('tokens.push("PLAY tags research-only")');
    expect(src).toContain("#desk-status");
    expect(src).toContain("MODEL_TRANSPARENCY_HREF");
    expect(src).not.toContain("production readiness no-go");
    expect(src).not.toContain("Data freshness degraded");
    expect(src).not.toContain("Boards may use last owned");
    expect(src).not.toContain("sample_size_ok");
  });
});
