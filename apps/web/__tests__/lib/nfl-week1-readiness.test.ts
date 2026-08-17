import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import {
  NFL_DEPTH_PACK_AS_OF,
  nflCurrentPathUsesPackaged,
  nflDepthPackagedBanner,
} from "@/lib/nfl-week1-current-path";

function repoRoot(): string {
  const here = path.join(__dirname, "../../../..");
  return path.resolve(here);
}

describe("nfl week-1 readiness", () => {
  it("aliases /pro/nfl/weekly-slate to the live slate", () => {
    const page = readFileSync(
      path.join(
        __dirname,
        "../../app/(pro)/pro/nfl/weekly-slate/page.tsx",
      ),
      "utf8",
    );
    expect(page).toContain('redirect("/pro/nfl/slate/today")');
    const cfg = readFileSync(
      path.join(__dirname, "../../next.config.ts"),
      "utf8",
    );
    expect(cfg).toContain('source: "/pro/nfl/weekly-slate"');
    expect(cfg).toContain('destination: "/pro/nfl/slate/today"');
  });

  it("banners packaged depth as not a live injury feed", () => {
    expect(nflDepthPackagedBanner("2026-08-13")).toBe(
      "Depth as_of 2026-08-13 — not live injury feed",
    );
    expect(nflDepthPackagedBanner()).toContain(NFL_DEPTH_PACK_AS_OF);
    expect(nflCurrentPathUsesPackaged(0)).toBe(true);
    expect(nflCurrentPathUsesPackaged(2)).toBe(false);
  });

  it("keeps ARI/MIN QB1 on the depth pack and named-starter copy", () => {
    const pack = JSON.parse(
      readFileSync(
        path.join(
          repoRoot(),
          "services/model-service/src/services/nfl_season_engine/data/nfl_depth_chart_2026_w1.json",
        ),
        "utf8",
      ),
    ) as {
      as_of?: string;
      rows: Array<{
        team?: string;
        position?: string;
        depth_order?: number;
        player_name?: string;
      }>;
    };
    expect(pack.as_of).toBe("2026-08-13");
    const qb1 = new Map(
      (pack.rows ?? [])
        .filter((r) => r.position === "QB" && r.depth_order === 1)
        .map((r) => [r.team, r.player_name]),
    );
    expect(qb1.size).toBe(32);
    expect(qb1.get("MIN")).toBe("Kyler Murray");
    expect(qb1.get("ARI")).toBe("Jacoby Brissett");
    const minPreview = readFileSync(
      path.join(repoRoot(), "content/writers/season-previews-2026/MIN.md"),
      "utf8",
    );
    expect(minPreview).toMatch(/named starter/i);
    expect(minPreview).not.toMatch(/are competing in camp/i);
    const ariPreview = readFileSync(
      path.join(repoRoot(), "content/writers/season-previews-2026/ARI.md"),
      "utf8",
    );
    expect(ariPreview).toMatch(/Murray is Minnesota/i);
    expect(ariPreview).toMatch(/Jacoby Brissett as ARI QB1/i);
  });

  it("documents the injury → current path on launch notes", () => {
    const notes = readFileSync(
      path.join(
        __dirname,
        "../../app/(pro)/pro/nfl/launch-notes/page.tsx",
      ),
      "utf8",
    );
    expect(notes).toMatch(/Injury → current/);
    expect(notes).toMatch(/not live injury feed/);
    expect(notes).toMatch(/Gameday inactives/);
    expect(notes).toContain("/pro/nfl/weekly-slate");
  });
});
