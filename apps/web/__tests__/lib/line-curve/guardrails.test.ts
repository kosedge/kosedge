import { describe, expect, it, vi } from "vitest";
import {
  evaluatePostedAlt,
  priceAlternateSurface,
} from "@/lib/line-curve/alternate-pricing";
import { missouriOklahomaFixture } from "@/lib/line-curve/fixtures/missouri-oklahoma";
import * as oddsAdapter from "@/lib/line-curve/odds-adapter";
import { getLineCurve } from "@/lib/line-curve/service";
import {
  LINE_CURVE_MAX_ALTS_PER_SIDE,
  type ModelMarginInput,
  type OddsAltSnapshot,
} from "@/lib/line-curve/types";

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

  it("does not fetch live odds when the model run is missing", async () => {
    const spy = vi.spyOn(oddsAdapter, "fetchAlternateSpreadSnapshot");
    const result = await getLineCurve("evt", "Missouri", "draftkings", {
      sport: "cfb",
      allowLiveOddsFetch: true,
    });
    expect(spy).not.toHaveBeenCalled();
    expect(result.ok).toBe(false);
    if (result.ok) return;
    expect(result.code).toBe("missing_model_run");
    expect(result.message).toMatch(/not fetched until the model is bound/);
    spy.mockRestore();
  });

  it("does not fetch live odds for a stub model object", async () => {
    const spy = vi.spyOn(oddsAdapter, "fetchAlternateSpreadSnapshot");
    const result = await getLineCurve("evt", "Missouri", "draftkings", {
      sport: "cfb",
      model: {} as ModelMarginInput,
      allowLiveOddsFetch: true,
    });
    expect(spy).not.toHaveBeenCalled();
    expect(result.ok).toBe(false);
    if (result.ok) return;
    expect(result.code).toBe("missing_model_run");
    spy.mockRestore();
  });

  it("does not fetch live odds when the snapshot is omitted", async () => {
    const spy = vi.spyOn(oddsAdapter, "fetchAlternateSpreadSnapshot");
    const model = missouriOklahomaFixture.missouri.model;
    const result = await getLineCurve(model.eventId, "Missouri", "draftkings", {
      sport: "cfb",
      model,
    });
    expect(spy).not.toHaveBeenCalled();
    expect(result.ok).toBe(false);
    if (result.ok) return;
    expect(result.code).toBe("missing_snapshot");
    expect(result.message).toMatch(/Live Odds API fetch is disabled/);
    spy.mockRestore();
  });

  it("fails closed when an alt list exceeds the surface cap", () => {
    const alts = Array.from(
      { length: LINE_CURVE_MAX_ALTS_PER_SIDE + 1 },
      (_, i) => ({
        line: i === 0 ? 1.5 : i + 0.5,
        americanOdds: -110,
        opposingAmericanOdds: -110,
      }),
    );
    const snapshot: OddsAltSnapshot = {
      ...missouriOklahomaFixture.missouri.snapshot,
      altsBySide: {
        ...missouriOklahomaFixture.missouri.snapshot.altsBySide,
        Missouri: alts,
      },
    };
    const result = priceAlternateSurface({
      snapshot,
      model: missouriOklahomaFixture.missouri.model,
      side: "Missouri",
    });
    expect(result.ok).toBe(false);
    if (result.ok) return;
    expect(result.code).toBe("surface_too_large");
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
