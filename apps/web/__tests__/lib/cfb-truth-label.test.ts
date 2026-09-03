import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import path from "node:path";
import {
  CFB_PRODUCT_SEASON,
  cfbModelDeskHonestyNote,
  cfbModelDeskTruthStates,
  isCfbCalendarPreseason,
} from "@/lib/cfb-truth-label";

const AUG_2026 = new Date("2026-08-12T16:00:00Z");
const SEP_2026 = new Date("2026-09-05T16:00:00Z");

describe("cfb-truth-label", () => {
  it("labels August 2026 as PRESEASON + MODEL, never LIVE", () => {
    expect(isCfbCalendarPreseason(CFB_PRODUCT_SEASON, AUG_2026)).toBe(true);
    expect(cfbModelDeskTruthStates(AUG_2026)).toEqual(["PRESEASON", "MODEL"]);
    expect(cfbModelDeskHonestyNote(AUG_2026)).toMatch(/PRESEASON/);
    expect(cfbModelDeskHonestyNote(AUG_2026)).toMatch(/MODEL research/);
    expect(cfbModelDeskHonestyNote(AUG_2026)).toMatch(
      /KEI is the published line/,
    );
    expect(cfbModelDeskTruthStates(AUG_2026)).not.toContain("LIVE");
  });

  it("drops PRESEASON after Week 0 and keeps MODEL only", () => {
    expect(isCfbCalendarPreseason(CFB_PRODUCT_SEASON, SEP_2026)).toBe(false);
    expect(cfbModelDeskTruthStates(SEP_2026)).toEqual(["MODEL"]);
    expect(cfbModelDeskHonestyNote(SEP_2026)).toMatch(/^MODEL research/);
    expect(cfbModelDeskHonestyNote(SEP_2026)).not.toMatch(/PRESEASON/);
  });
});

describe("cfb truth-label wiring", () => {
  it("Season Model and Project Game pages mount PRESEASON/MODEL badges", () => {
    const model = readFileSync(
      path.join(__dirname, "../../app/(pro)/pro/cfb/model/page.tsx"),
      "utf8",
    );
    const project = readFileSync(
      path.join(__dirname, "../../app/(pro)/pro/cfb/project-game/page.tsx"),
      "utf8",
    );
    for (const src of [model, project]) {
      expect(src).toContain("cfbModelDeskTruthStates");
      expect(src).toContain("cfb-truth-state");
      expect(src).toContain("cfbModelDeskHonestyNote");
    }
  });

  it("CFB Edge Board publishes KEI vs market with Week 0/1 tabs defaulting to Week 1", () => {
    // Board build moved off the SSR page (Alex waterfall) — stamp lives on
    // the assemble API; Week 0/1 tabs stay on the client shell.
    const page = readFileSync(
      path.join(__dirname, "../../app/edge-board/[sport]/page.tsx"),
      "utf8",
    );
    const assemble = readFileSync(
      path.join(
        __dirname,
        "../../app/api/edge-board/[sport]/assemble/route.ts",
      ),
      "utf8",
    );
    const client = readFileSync(
      path.join(__dirname, "../../components/EdgeBoardSportClient.tsx"),
      "utf8",
    );

    expect(assemble).toContain("stampCfbEdgeBoardWeek");
    expect(assemble).toMatch(
      /week === ["']0["'] \? 0 : 1|get\("week"\) === "0" \? 0 : 1/,
    );

    expect(page).toContain("EdgeBoardSportClient");
    expect(page).toMatch(/cfbWeekRaw === "0" \? 0 : 1/);
    expect(page).not.toContain("loadAssembledEdgeBoardRows");

    expect(client).toContain("Tag = KEI vs trusted market");
    expect(client).toContain("/edge-board/cfb?week=0");
    expect(client).toContain("/edge-board/cfb?week=1");
    expect(client).toContain("week0Count");
    expect(client).toContain("waiting on Odds API");
  });
});
