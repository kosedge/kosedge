import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import {
  AWARD_SCORE_LABEL,
  AWARD_SCORE_TITLE,
  awardScoreIndex,
  formatAwardScore,
} from "@/lib/nfl-award-score";

describe("award score is not a probability", () => {
  it("labels the field Award Score, never percent or probability", () => {
    expect(AWARD_SCORE_LABEL).toBe("Award Score");
    expect(AWARD_SCORE_LABEL).not.toMatch(/%|probability/i);
    expect(AWARD_SCORE_TITLE).not.toMatch(/%/);
    expect(AWARD_SCORE_TITLE.toLowerCase()).toContain("not a probability");
  });

  it("formats 0–1 scores as a 0–100 index without a percent sign", () => {
    expect(formatAwardScore(0.877)).toBe("87.7");
    expect(formatAwardScore(0.877)).not.toContain("%");
    expect(formatAwardScore(0.858)).toBe("85.8");
    expect(formatAwardScore(null)).toBe("—");
    expect(awardScoreIndex(0.81)).toBeCloseTo(81.0);
  });

  it("award surfaces do not render Model % or projectedPercent on scores", () => {
    const root = path.join(__dirname, "../..");
    const files = [
      "app/(pro)/pro/nfl/awards/page.tsx",
      "app/(pro)/pro/nfl/player-previews/page.tsx",
    ];
    for (const rel of files) {
      const src = readFileSync(path.join(root, rel), "utf8");
      expect(src, rel).not.toContain("Model %");
      expect(src, rel).not.toContain("projectedPercent");
      expect(src, rel).toContain("AWARD_SCORE_LABEL");
    }
  });
});
