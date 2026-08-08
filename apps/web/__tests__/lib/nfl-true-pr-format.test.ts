import { describe, expect, it } from "vitest";
import {
  blendChip,
  continuityChip,
  driverChipsForTeam,
  projectedSosChip,
  qbPremiumChip,
} from "@/lib/nfl-true-pr-format";

describe("nfl-true-pr-format", () => {
  it("hides unavailable continuity instead of inventing high", () => {
    expect(continuityChip({ available: false })).toBeNull();
  });

  it("labels approximate continuity bands", () => {
    const chip = continuityChip({
      available: true,
      band: "low",
      reason: "new staff",
      approximate: true,
    });
    expect(chip?.value).toBe("Low");
    expect(chip?.approximate).toBe(true);
  });

  it("shows QB starter context without elite lift when band missing", () => {
    const chip = qbPremiumChip({
      available: true,
      starter_name: "Jaxson Dart",
      reason: "Jaxson Dart · quality sample missing",
      approximate: true,
      fidelity: "missing",
    });
    expect(chip?.value).toBe("Context only");
    expect(chip?.muted).toBe(true);
  });

  it("frames projected SOS as outlook", () => {
    const chip = projectedSosChip({
      available: true,
      band: "hard",
      reason: "2026 slate hard",
      framing: "Schedule outlook only — does not change intrinsic PR",
    });
    expect(chip?.framing).toMatch(/does not change intrinsic PR/);
  });

  it("keeps preseason blend prior-heavy", () => {
    const chip = blendChip({
      available: true,
      label: "Prior-heavy",
      state: "prior_heavy",
      reason: "Preseason / 0 REG games — prior only (no current sample)",
      preseason: true,
    });
    expect(chip?.value).toBe("Prior-heavy");
    expect(chip?.muted).toBe(true);
  });

  it("keeps games 1–2 blend prior-heavy (no Week-1 cliff copy)", () => {
    const chip = blendChip({
      available: true,
      label: "Prior-heavy",
      state: "prior_heavy",
      reason: "Games 1/8 — prior-heavy early season (no Week-1 cliff)",
      early_season: true,
      preseason: false,
    });
    expect(chip?.value).toBe("Prior-heavy");
    expect(chip?.muted).toBe(true);
  });

  it("builds a scannable chip list", () => {
    const chips = driverChipsForTeam({
      continuity: { available: true, band: "high", reason: "same QB" },
      qb_premium: {
        available: true,
        band: "elite_lift",
        band_label: "Elite lift",
        starter_name: "Patrick Mahomes",
      },
      past_sos: { available: true, band: "soft", reason: "Prior slate soft" },
      projected_sos_2026: {
        available: true,
        band: "average",
        framing: "Schedule outlook only — does not change intrinsic PR",
      },
      blend: {
        available: true,
        label: "Prior-heavy",
        preseason: true,
        reason: "Preseason",
      },
    });
    expect(chips.map((c) => c.key)).toEqual([
      "continuity",
      "qb",
      "past_sos",
      "proj_sos",
      "blend",
    ]);
  });
});
