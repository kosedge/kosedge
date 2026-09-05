import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

const ROOT = join(__dirname, "../..");

describe("Overview hero surface (NFL/NBA/MLB)", () => {
  it("keeps header + slate as separate components inside one shell surface", () => {
    const shell = readFileSync(
      join(ROOT, "components/pro/OverviewSportShell.tsx"),
      "utf8",
    );
    expect(shell).toMatch(/OverviewPageHeader/);
    expect(shell).toMatch(/OverviewEdgeBoardSlate/);
    expect(shell).toMatch(/aria-label=\{`\$\{sportLabel\} Overview`\}/);
    // Single outer hero chrome — not two stacked cards.
    expect(shell).toMatch(/rounded-2xl border border-kos-gold\/20/);
  });

  it("uses sport-specific slate titles and one Full Edge Board CTA", () => {
    const slate = readFileSync(
      join(ROOT, "components/pro/OverviewEdgeBoardSlate.tsx"),
      "utf8",
    );
    expect(slate).toMatch(/This Week.?s Slate/);
    expect(slate).toMatch(/Today.?s Slate/);
    expect(slate).toMatch(/Full Edge Board →/);
    // Gold small-caps label (original eyebrow treatment), not a second hero h2.
    expect(slate).toMatch(
      /text-\[11px\] font-semibold uppercase tracking-\[0\.14em\] text-kos-gold/,
    );
    expect(slate).not.toMatch(/title:\s*"Edge Board"/);
    expect(slate).not.toMatch(/<h2/);
  });

  it("header is typography-only (chrome owned by shell)", () => {
    const header = readFileSync(
      join(ROOT, "components/pro/OverviewPageHeader.tsx"),
      "utf8",
    );
    expect(header).toMatch(/OVERVIEW_TAGLINE|SPORT_TAGLINE/);
    expect(header).not.toMatch(/rounded-2xl border/);
    expect(header).not.toMatch(/radial-gradient/);
  });
});
