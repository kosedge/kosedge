import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

const webRoot = path.join(__dirname, "../..");

/**
 * #8 honesty slice 13a / KOS-20 — Conf% kill on NFL props customer UI.
 * KOS-15 LOCKED: confidence dark until Lab validates the family.
 * Not a Lab unlock; do not invent Conf% chrome elsewhere.
 */
describe("NFL props Conf% dark until Lab (13a)", () => {
  it("customer /pro/nfl/props page has no Conf % / Conf: chrome", () => {
    const page = readFileSync(
      path.join(webRoot, "app/(pro)/pro/nfl/props/page.tsx"),
      "utf8",
    );

    expect(page).not.toContain("formatConfidence");
    expect(page).not.toMatch(/\bConf:\s*/);
    expect(page).not.toMatch(/>Confidence</);
    expect(page).not.toMatch(/Conf\s*%/);
    // Reliability field may still exist on the board type — UI must not paint it.
    expect(page).not.toMatch(/row\.confidence/);
  });
});
