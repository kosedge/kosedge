import { describe, expect, it } from "vitest";
import { optimizeMissouriOklahomaLineCurve } from "@/lib/line-curve/service";

describe("Missouri +1.5 / Oklahoma +1.5 research fixture", () => {
  it("ranks the quoted -103 combo against every posted alt pair", () => {
    const result = optimizeMissouriOklahomaLineCurve();
    expect(result.ok).toBe(true);
    if (!result.ok) return;

    const ticket = result.combos.find(
      (c) => c.lineA === 1.5 && c.lineB === 1.5,
    );
    expect(ticket?.bookParlayAmerican).toBe(-103);
    expect(result.combos.length).toBeGreaterThan(1);

    // The fixture must not encode the winner. Only prove comparison happened.
    const winner = result.combos[0];
    expect(winner.rank).toBe(1);
    expect(Number.isFinite(winner.evPerDollar)).toBe(true);
    expect(ticket?.rank).toBeGreaterThanOrEqual(1);
    expect(winner.correlation.assumption).toBe("independent");
  });
});
