import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { honestEmptySlateCopy } from "@/lib/model-service-status";

const ROOT = join(__dirname, "../..");

describe("fair-lines desk honesty copy", () => {
  it("CFB / NHL pending notes are fail-closed (do not invent)", () => {
    const src = readFileSync(
      join(ROOT, "app/(pro)/pro/[sport]/fair-lines/page.tsx"),
      "utf8",
    );
    expect(src).toContain("not connected / no odds yet");
    expect(src).toContain("we do not invent");
    expect(src).toContain("CBB / NCAAM is out of this overnight slice");
  });

  it("honestEmptySlateCopy covers not_connected", () => {
    expect(honestEmptySlateCopy("not_connected")).toContain("do not invent");
    expect(honestEmptySlateCopy("no_odds_yet")).toContain("no odds yet");
  });

  it("ncaaf kei-lines redirects to cfb fair-lines (Alex #5)", () => {
    const cfg = readFileSync(join(ROOT, "next.config.ts"), "utf8");
    expect(cfg).toContain('source: "/pro/ncaaf/kei-lines"');
    expect(cfg).toContain('destination: "/pro/cfb/fair-lines"');
  });
});
