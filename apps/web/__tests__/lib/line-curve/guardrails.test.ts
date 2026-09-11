import { describe, expect, it } from "vitest";
import {
  evaluatePostedAlt,
  priceAlternateSurface,
} from "@/lib/line-curve/alternate-pricing";
import { missouriOklahomaFixture } from "@/lib/line-curve/fixtures/missouri-oklahoma";
import type { ModelMarginInput, OddsAltSnapshot } from "@/lib/line-curve/types";

const freshNow = Date.parse("2026-09-11T01:05:00.000Z");

function liveSnap(): OddsAltSnapshot {
  return {
    ...missouriOklahomaFixture.missouri.snapshot,
    source: "odds_api",
  };
}

describe("line-curve guardrails", () => {
  it("rejects stale odds", () => {
    const result = priceAlternateSurface({
      snapshot: liveSnap(),
      model: missouriOklahomaFixture.missouri.model,
      side: "Missouri",
      nowMs: Date.parse("2026-09-11T04:00:00.000Z"),
    });
    expect(result.ok).toBe(false);
    if (result.ok) return;
    expect(result.code).toBe("stale_odds");
    expect(result.label).toBe("INSUFFICIENT");
  });

  it("rejects a missing model run", () => {
    const model: ModelMarginInput = {
      ...missouriOklahomaFixture.missouri.model,
      modelRunId: "",
    };
    const result = priceAlternateSurface({
      snapshot: missouriOklahomaFixture.missouri.snapshot,
      model,
      side: "Missouri",
    });
    expect(result.ok).toBe(false);
    if (result.ok) return;
    expect(result.code).toBe("missing_model_run");
  });

  it("rejects a model run tied to a different event", () => {
    const model: ModelMarginInput = {
      ...missouriOklahomaFixture.missouri.model,
      eventId: "some-other-event",
    };
    const result = priceAlternateSurface({
      snapshot: missouriOklahomaFixture.missouri.snapshot,
      model,
      side: "Missouri",
    });
    expect(result.ok).toBe(false);
    if (result.ok) return;
    expect(result.code).toBe("unbound_model_event");
  });

  it("rejects duplicate disagreeing prices", () => {
    const snapshot: OddsAltSnapshot = {
      ...missouriOklahomaFixture.missouri.snapshot,
      altsBySide: {
        ...missouriOklahomaFixture.missouri.snapshot.altsBySide,
        Missouri: [
          ...missouriOklahomaFixture.missouri.snapshot.altsBySide.Missouri,
          { line: 1.5, americanOdds: -130, opposingAmericanOdds: -110 },
        ],
      },
    };
    const result = priceAlternateSurface({
      snapshot,
      model: missouriOklahomaFixture.missouri.model,
      side: "Missouri",
    });
    expect(result.ok).toBe(false);
    if (result.ok) return;
    expect(result.code).toBe("duplicate_odds");
  });

  it("refuses to interpolate a missing alt price", () => {
    const result = evaluatePostedAlt({
      snapshot: missouriOklahomaFixture.missouri.snapshot,
      model: missouriOklahomaFixture.missouri.model,
      side: "Missouri",
      altLine: 5.5,
    });
    expect(result.ok).toBe(false);
    if (result.ok) return;
    expect(result.code).toBe("missing_alt_price");
  });

  it("fails closed when the alternate market is only the mainline", () => {
    const snapshot: OddsAltSnapshot = {
      ...missouriOklahomaFixture.missouri.snapshot,
      altsBySide: {
        Missouri: [
          { line: 1.5, americanOdds: -110, opposingAmericanOdds: -110 },
        ],
        Kansas: [
          { line: -1.5, americanOdds: -110, opposingAmericanOdds: -110 },
        ],
      },
    };
    const result = priceAlternateSurface({
      snapshot,
      model: missouriOklahomaFixture.missouri.model,
      side: "Missouri",
    });
    expect(result.ok).toBe(false);
    if (result.ok) return;
    expect(result.code).toBe("unavailable_alt_market");
    expect(result.label).toBe("INSUFFICIENT");
  });

  it("accepts a live snapshot inside the freshness window", () => {
    const result = priceAlternateSurface({
      snapshot: liveSnap(),
      model: missouriOklahomaFixture.missouri.model,
      side: "Missouri",
      nowMs: freshNow,
    });
    expect(result.ok).toBe(true);
  });
});
