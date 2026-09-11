import { describe, expect, it } from "vitest";
import { priceAlternateSurface } from "@/lib/line-curve/alternate-pricing";
import { missouriOklahomaFixture } from "@/lib/line-curve/fixtures/missouri-oklahoma";

describe("line-curve alternate pricing", () => {
  it("prices every posted Missouri alt and never interpolates", () => {
    const curve = priceAlternateSurface({
      snapshot: missouriOklahomaFixture.missouri.snapshot,
      model: missouriOklahomaFixture.missouri.model,
      side: "Missouri",
    });
    expect(curve.ok).toBe(true);
    if (!curve.ok) return;
    expect(curve.baseLine).toBe(1.5);
    expect(curve.points.map((p) => p.altLine)).toEqual([
      -2.5, -1.5, 1.5, 2.5, 3.5, 4.5, 6.5, 7.5,
    ]);
    expect(curve.points.every((p) => p.oddsSnapshotId && p.modelRunId)).toBe(
      true,
    );
    expect(curve.points.every((p) => p.timestamp)).toBe(true);
  });

  it("cover rises as Missouri buys points, not linearly", () => {
    const curve = priceAlternateSurface({
      snapshot: missouriOklahomaFixture.missouri.snapshot,
      model: missouriOklahomaFixture.missouri.model,
      side: "Missouri",
    });
    if (!curve.ok) throw new Error(curve.message);
    const by = Object.fromEntries(
      curve.points.map((p) => [p.altLine, p.modelCoverProbability]),
    );
    expect(by[2.5]).toBeGreaterThan(by[1.5]);
    expect(by[3.5]).toBeGreaterThan(by[2.5]);
    expect(by[7.5]).toBeGreaterThan(by[3.5]);
    const d1 = by[2.5] - by[1.5];
    const d2 = by[3.5] - by[2.5];
    expect(d2).not.toBeCloseTo(d1, 4);
  });

  it("uses research labels only", () => {
    const curve = priceAlternateSurface({
      snapshot: missouriOklahomaFixture.missouri.snapshot,
      model: missouriOklahomaFixture.missouri.model,
      side: "Missouri",
    });
    if (!curve.ok) throw new Error(curve.message);
    const labels = new Set(curve.points.map((p) => p.label));
    for (const label of labels) {
      expect(["BEST VALUE", "FAIR", "OVERPRICED", "INSUFFICIENT"]).toContain(
        label,
      );
    }
    expect([...labels].join(" ")).not.toMatch(/\b(PLAY|LEAN|teaser)\b/i);
  });
});
