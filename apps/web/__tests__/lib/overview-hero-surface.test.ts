import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { preferNextDailySlate } from "@/lib/overview-slate-games";
import type { TonightGame } from "@/lib/edge-board-tonight";

const ROOT = join(__dirname, "../..");

const DEDICATED = [
  "nfl",
  "nba",
  "mlb",
  "nhl",
  "wnba",
  "ncaam",
  "cfb",
] as const;

function game(
  slug: string,
  commenceTime: string,
  week?: number,
): TonightGame {
  return {
    slug,
    sport: "nba",
    row: {
      teamA: { name: "A" },
      teamB: { name: "B" },
      commenceTime,
      week,
    } as TonightGame["row"],
  };
}

describe("Overview hero surface (all sports)", () => {
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
    for (const sport of DEDICATED) {
      expect(slate).toMatch(new RegExp(`${sport}:\\s*\\{`));
    }
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

  it("wires every dedicated Overview onto OverviewSportShell", () => {
    for (const sport of DEDICATED) {
      const src = readFileSync(
        join(ROOT, `app/(pro)/pro/${sport}/overview/page.tsx`),
        "utf8",
      );
      expect(src).toMatch(/OverviewSportShell/);
      expect(src).toMatch(/loadOverviewSlateGames/);
    }
  });

  it("preferNextDailySlate keeps opening day when today is empty", () => {
    const todayEt = new Date().toLocaleDateString("en-CA", {
      timeZone: "America/New_York",
    });
    const [y, m, d] = todayEt.split("-").map(Number);
    const opening = new Date(Date.UTC(y, m - 1, d + 14, 23, 0, 0));
    const later = new Date(Date.UTC(y, m - 1, d + 15, 23, 0, 0));
    const picked = preferNextDailySlate([
      game("later", later.toISOString()),
      game("open-a", opening.toISOString()),
      game("open-b", opening.toISOString()),
    ]);
    expect(picked.map((g) => g.slug).sort()).toEqual(["open-a", "open-b"]);
  });
});
