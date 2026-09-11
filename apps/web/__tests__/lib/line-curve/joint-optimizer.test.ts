import { describe, expect, it } from "vitest";
import { optimizeTwoLegLineCurve } from "@/lib/line-curve/service";
import { missouriOklahomaFixture } from "@/lib/line-curve/fixtures/missouri-oklahoma";
import { INDEPENDENT_JOINT_NOTE } from "@/lib/line-curve/types";

function legs() {
  const fx = missouriOklahomaFixture;
  return {
    a: {
      eventId: fx.missouri.snapshot.eventId,
      side: fx.missouri.side,
      snapshot: fx.missouri.snapshot,
      model: fx.missouri.model,
    },
    b: {
      eventId: fx.oklahoma.snapshot.eventId,
      side: fx.oklahoma.side,
      snapshot: fx.oklahoma.snapshot,
      model: fx.oklahoma.model,
    },
  };
}

describe("line-curve joint optimizer", () => {
  it("documents the independence assumption on every combo", () => {
    const { a, b } = legs();
    const result = optimizeTwoLegLineCurve(a, b, missouriOklahomaFixture.book, {
      quotedParlays: missouriOklahomaFixture.quotedParlays,
    });
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.correlation.assumption).toBe("independent");
    expect(result.correlation.documented).toBe(true);
    expect(result.correlation.note).toBe(INDEPENDENT_JOINT_NOTE);
    expect(
      result.combos.every(
        (c) =>
          c.correlation.assumption === "independent" &&
          c.correlation.documented === true,
      ),
    ).toBe(true);
  });

  it("allows asymmetric line combinations", () => {
    const { a, b } = legs();
    const result = optimizeTwoLegLineCurve(a, b, missouriOklahomaFixture.book, {
      quotedParlays: missouriOklahomaFixture.quotedParlays,
    });
    if (!result.ok) throw new Error(result.message);
    const asymmetric = result.combos.filter((c) => c.lineA !== c.lineB);
    expect(asymmetric.length).toBeGreaterThan(0);
    expect(result.combos.some((c) => c.lineA === 1.5 && c.lineB === 3.5)).toBe(
      true,
    );
  });

  it("compares Missouri +1.5 / Oklahoma +1.5 @ -103 against all posted pairs", () => {
    const { a, b } = legs();
    const result = optimizeTwoLegLineCurve(a, b, missouriOklahomaFixture.book, {
      quotedParlays: missouriOklahomaFixture.quotedParlays,
    });
    if (!result.ok) throw new Error(result.message);

    const ticket = result.combos.find(
      (c) => c.lineA === 1.5 && c.lineB === 1.5,
    );
    expect(ticket).toBeDefined();
    expect(ticket?.bookParlayAmerican).toBe(-103);
    expect(ticket?.parlayPriceSource).toBe("book_quoted");

    const altCount =
      missouriOklahomaFixture.missouri.snapshot.altsBySide.Missouri.length *
      missouriOklahomaFixture.oklahoma.snapshot.altsBySide.Oklahoma.length;
    expect(result.combos.length).toBe(altCount);

    const best = result.combos[0];
    expect(best.rank).toBe(1);
    expect(result.combos.every((c, i) => c.rank === i + 1)).toBe(true);
    expect(
      result.combos.every(
        (c, i) => i === 0 || c.evPerDollar <= result.combos[i - 1].evPerDollar,
      ),
    ).toBe(true);

    // Do not hardcode whether +1.5/+1.5 wins — only that it was ranked.
    expect(ticket?.rank).toBeGreaterThanOrEqual(1);
    if (ticket && ticket.rank > 1) {
      expect(best.lineA !== 1.5 || best.lineB !== 1.5).toBe(true);
    }
  });

  it("fails closed on same-game legs — never BEST VALUE under independence", () => {
    const { a } = legs();
    const result = optimizeTwoLegLineCurve(
      a,
      { ...a, side: "Kansas" },
      missouriOklahomaFixture.book,
    );
    expect(result.ok).toBe(false);
    if (result.ok) return;
    expect(result.code).toBe("same_game");
    expect(result.label).toBe("INSUFFICIENT");
  });
});
