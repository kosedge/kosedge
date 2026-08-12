import { describe, expect, it } from "vitest";
import {
  formatNflFreshnessPeriod,
  formatNflWeekLabel,
  nflActualRecordColumnLabel,
  nflModelWinsColumnLabel,
  nflTruthCopyClaimsFutureWeek,
  resolveNflTruthLabel,
} from "@/lib/nfl-truth-label";

const AUG_2026 = new Date("2026-08-12T16:00:00Z");
const OCT_2026 = new Date("2026-10-15T16:00:00Z");
const JAN_2027 = new Date("2027-01-08T16:00:00Z");
const MAR_2027 = new Date("2027-03-01T16:00:00Z");

describe("nfl-truth-label", () => {
  it("labels August 2026 + week 18 as PRESEASON, never Week 18 current", () => {
    const truth = resolveNflTruthLabel({
      season: 2026,
      week: 18,
      now: AUG_2026,
    });
    expect(truth.ui_state).toBe("PRESEASON");
    expect(truth.week).toBeNull();
    expect(truth.week_label).toBe("Preseason");
    expect(truth.period_line).toBe("Season 2026 · Preseason");
    expect(truth.is_current).toBe(false);
    expect(truth.source_type).toBe("preseason");
    expect(nflTruthCopyClaimsFutureWeek(truth.period_line)).toBe(false);
    expect(truth.honesty_note).toMatch(/PRESEASON/);
    expect(nflTruthCopyClaimsFutureWeek(truth.honesty_note ?? "")).toBe(false);
  });

  it("labels 2025 W22 fallback as ARCHIVE finals, not current", () => {
    const truth = resolveNflTruthLabel({
      season: 2025,
      week: 22,
      fallbackApplied: true,
      latestSeason: 2025,
      latestWeek: 22,
      now: AUG_2026,
    });
    expect(truth.ui_state).toBe("ARCHIVE");
    expect(truth.week).toBeNull();
    expect(truth.week_label).toBe("2025 finals");
    expect(truth.period_line).toBe("Season 2025 · finals");
    expect(truth.is_current).toBe(false);
    expect(truth.honesty_note).toBe(
      "ARCHIVE · showing 2025 finals (as-of) — not 2026 current",
    );
    expect(nflTruthCopyClaimsFutureWeek(truth.honesty_note ?? "")).toBe(false);
  });

  it("labels in-season week 5 as LIVE", () => {
    const truth = resolveNflTruthLabel({
      season: 2026,
      week: 5,
      inSeason: true,
      now: OCT_2026,
    });
    expect(truth.ui_state).toBe("LIVE");
    expect(truth.week).toBe(5);
    expect(truth.week_label).toBe("Week 5");
    expect(truth.period_line).toBe("Season 2026 · Week 5");
    expect(truth.is_current).toBe(true);
    expect(truth.source_type).toBe("actual");
    expect(truth.honesty_note).toBeNull();
  });

  it("labels January Week 18 as a real week, March as archive finals", () => {
    const jan = resolveNflTruthLabel({
      season: 2026,
      week: 18,
      inSeason: true,
      now: JAN_2027,
    });
    expect(jan.week_label).toBe("Week 18");
    expect(jan.period_line).toBe("Season 2026 · Week 18");

    const mar = resolveNflTruthLabel({
      season: 2026,
      week: 18,
      now: MAR_2027,
    });
    expect(mar.ui_state).toBe("ARCHIVE");
    expect(mar.week_label).toBe("2026 finals");
  });

  it("labels model surfaces MODEL with Preseason week in August", () => {
    const truth = resolveNflTruthLabel({
      season: 2026,
      week: 18,
      isModelSurface: true,
      launchPreseason: true,
      runId: "nfl-preseason-sim-2026-test",
      modelVersion: "v1.24",
      now: AUG_2026,
    });
    expect(truth.ui_state).toBe("MODEL");
    expect(truth.week_label).toBe("Preseason");
    expect(truth.run_id).toBe("nfl-preseason-sim-2026-test");
    expect(truth.model_version).toBe("v1.24");
  });

  it("formats freshness without W18 in August", () => {
    expect(formatNflFreshnessPeriod(2026, 18, AUG_2026)).toBe("S2026 Preseason");
    expect(formatNflWeekLabel(18, { season: 2026, now: AUG_2026 })).toBe(
      "Preseason",
    );
  });

  it("separates 2025 W–L from 2026 E[wins] column labels", () => {
    const archive = resolveNflTruthLabel({
      season: 2025,
      week: 18,
      now: AUG_2026,
    });
    expect(nflActualRecordColumnLabel(archive)).toBe("2025 W–L");
    expect(nflModelWinsColumnLabel()).toBe("2026 E[wins]");
  });
});
