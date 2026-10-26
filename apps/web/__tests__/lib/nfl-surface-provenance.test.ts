/**
 * NFL Enterprise Green — Edges cert-bind + cross-surface provenance.
 * Paper: PE addendum v1.1 (E-1..E-3, X-1..X-5, Q1/Q2, N-1). Draft only.
 */
import { readFileSync } from "node:fs";
import path from "path";
import { afterEach, describe, expect, it } from "vitest";
import {
  NFL_EDGE_BOARD_PUBLIC_ENABLED,
  NFL_EDGES_CERTIFIED_AT,
  NFL_EDGES_CERTIFIED_RUN_ID,
  NFL_EDGES_CERTIFIED_SHA256,
  NFL_EDGES_CERT_MAX_AGE_HOURS,
  NFL_EDGES_PUBLIC_ML_ENABLED,
  NFL_EDGES_PUBLIC_SPREAD_ENABLED,
  NFL_EDGES_PUBLIC_TOTAL_ENABLED,
  NFL_FAIR_LINES_CERTIFIED_AT,
  NFL_FAIR_LINES_CERTIFIED_RUN_ID,
  NFL_FAIR_LINES_CERTIFIED_SHA256,
  NFL_FAIR_LINES_CERT_MAX_AGE_HOURS,
  NFL_FAIR_LINES_PUBLIC_ML_ENABLED,
  NFL_FAIR_LINES_PUBLIC_SPREAD_ENABLED,
  NFL_FAIR_LINES_PUBLIC_TOTAL_ENABLED,
  NFL_FAIR_LINES_WARROOM_ARTIFACT_SHA256,
  bindNflFairLinesCertifiedRun,
  isNflFairLinesCertifiedPublicPaintAllowed,
} from "@/lib/cfb-edge-board-public";
import { TOTAL_PLAY_ENABLED } from "@/lib/nfl-spread-play-lock";
import {
  NFL_EDGES_EDGE_LANGUAGE_ADOPTED,
  NFL_EDGES_PROPS_STATUS,
  assertNflSurfacesAgree,
  bindNflEdgesToFairLinesCertifiedRun,
  checkNflObservedAgainstCertifiedSlot,
  compareNflSurfaceProvenance,
  emptyNflSurfaceProvenance,
  isNflEdgesCertifiedPublicPaintAllowed,
  isNflEdgesCustomerSurfaceClosed,
  isNflEdgesMarketRestrictEnabled,
  isNflMarketCustomerPaintAllowed,
  isNflMarketHardBlocked,
  linesAsOfFromAssemble,
  linesAsOfFromEdgesMarketAsOf,
  linesAsOfFromFairLinesOddsAsOf,
  nflCertifiedSlotIdentity,
  nflEdgesOwnCertifiedSlots,
  nflLinesAsOfLeakageReason,
  nflSurfaceProvenanceFromAssemble,
  nflSurfaceProvenanceFromEdgesDesk,
  nflSurfaceProvenanceFromFairLines,
  resolveNflAssembleLinesAsOfFromCapture,
  resolveNflCertStatus,
  resolveNflCertStatusField,
  resolveNflRowLinesAsOf,
  selectNflEdgesCustomerPaintRows,
  unboundNflCertStatus,
  type NflSurfaceProvenance,
} from "@/lib/nfl-surface-provenance";
import { assembleNflEdgesDeskPayload } from "@/lib/nfl-edges";
import type { DeskEdgeRow } from "@/lib/nfl-edges-desk-types";

const webRoot = path.join(__dirname, "../..");

function readWeb(rel: string): string {
  return readFileSync(path.join(webRoot, rel), "utf8");
}

const FIXTURE_RUN_ID = "nfl-fair-lines-cert-fixture-not-production";
const FIXTURE_SHA256 = "a".repeat(64);
const FIXTURE_AT = "2026-09-17T12:00:00.000Z";
const FIXTURE_LINES = "2026-09-10T16:41:00.000Z";

function fixtureObserved(
  overrides: Partial<NflSurfaceProvenance> = {},
): NflSurfaceProvenance {
  return {
    runId: FIXTURE_RUN_ID,
    sha256: FIXTURE_SHA256,
    linesAsOf: FIXTURE_LINES,
    source: "fair",
    certStatus: unboundNflCertStatus(),
    ...overrides,
  };
}

function deskRow(
  partial: Partial<DeskEdgeRow> &
    Pick<DeskEdgeRow, "id" | "marketType" | "source">,
): DeskEdgeRow {
  return {
    matchupOrPlayer: "NE @ SEA",
    detail: partial.marketType,
    kosedgeLine: "-3.5",
    marketLine: "-3.0",
    edge: 1.2,
    edgeDisplay: "+1.2 pts",
    side: "Home",
    confidence: null,
    kickoff: "2026-09-10T00:20:00.000Z",
    linesAsOf: FIXTURE_LINES,
    ...partial,
  };
}

describe("NFL Edges cert slots + shared Fair Lines bind", () => {
  afterEach(() => {
    delete process.env.NFL_EDGE_BOARD_INTERNAL;
    delete process.env.NEXT_PUBLIC_NFL_EDGE_BOARD_INTERNAL;
  });

  it("keeps Coming soon ON, public flag false, and Edges slots unbound", () => {
    expect(NFL_EDGE_BOARD_PUBLIC_ENABLED).toBe(false);
    expect(NFL_EDGES_CERTIFIED_RUN_ID).toBeNull();
    expect(NFL_EDGES_CERTIFIED_SHA256).toBeNull();
    expect(NFL_EDGES_CERTIFIED_AT).toBeNull();
    expect(NFL_EDGES_CERT_MAX_AGE_HOURS).toBe(
      NFL_FAIR_LINES_CERT_MAX_AGE_HOURS,
    );
    expect(NFL_EDGES_PUBLIC_SPREAD_ENABLED).toBe(false);
    expect(NFL_EDGES_PUBLIC_ML_ENABLED).toBe(false);
    expect(NFL_EDGES_PUBLIC_TOTAL_ENABLED).toBe(false);
    expect(NFL_FAIR_LINES_CERTIFIED_RUN_ID).toBeNull();
    expect(NFL_FAIR_LINES_CERTIFIED_SHA256).toBeNull();
    expect(NFL_FAIR_LINES_CERTIFIED_AT).toBeNull();
    expect(nflCertifiedSlotIdentity()).toEqual({
      runId: null,
      sha256: null,
      certifiedAt: null,
    });
    expect(nflEdgesOwnCertifiedSlots()).toEqual({
      runId: null,
      sha256: null,
      certifiedAt: null,
    });
    expect(NFL_EDGES_EDGE_LANGUAGE_ADOPTED).toBe(false);
    expect(TOTAL_PLAY_ENABLED).toBe(false);
  });

  it("does not invent or bind a production / practice / diagnostic hash", () => {
    expect(NFL_EDGES_CERTIFIED_SHA256).not.toBe(
      NFL_FAIR_LINES_WARROOM_ARTIFACT_SHA256,
    );
    expect(NFL_FAIR_LINES_CERTIFIED_SHA256).not.toBe(
      NFL_FAIR_LINES_WARROOM_ARTIFACT_SHA256,
    );
    expect(bindNflEdgesToFairLinesCertifiedRun({}).reason).toBe(
      "unbound_certified_slot",
    );
    expect(bindNflEdgesToFairLinesCertifiedRun({}).ok).toBe(false);
    expect(
      bindNflFairLinesCertifiedRun({
        runId: FIXTURE_RUN_ID,
        sha256: FIXTURE_SHA256,
      }).reason,
    ).toBe("unbound_certified_slot");
  });

  it("reuses bindNflFairLinesCertifiedRun — no dedicated Edges bind path", () => {
    const pub = readWeb("lib/cfb-edge-board-public.ts");
    const provenance = readWeb("lib/nfl-surface-provenance.ts");
    expect(pub).toContain("NFL_EDGES_CERTIFIED_RUN_ID: string | null = null");
    expect(pub).toContain("NFL_EDGES_CERTIFIED_SHA256: string | null = null");
    expect(pub).toContain("NFL_EDGES_CERTIFIED_AT: string | null = null");
    expect(pub).not.toMatch(
      /NFL_EDGES_CERTIFIED_(RUN_ID|SHA256|AT).*=\s*process\.env/,
    );
    expect(pub).not.toContain("bindNflEdgesCertifiedRun");
    expect(provenance).not.toContain("function bindNflEdgesCertifiedRun");
    expect(provenance).toContain("bindNflFairLinesCertifiedRun");
    expect(provenance).toContain("SAME Fair Lines certified run");
  });

  it("fail-closes unbound / missing / mismatched identity (shared bind)", () => {
    const expected = {
      runId: FIXTURE_RUN_ID,
      sha256: FIXTURE_SHA256,
      certifiedAt: FIXTURE_AT,
      maxAgeHours: 168,
    };
    const observedOk = {
      runId: FIXTURE_RUN_ID,
      sha256: FIXTURE_SHA256,
      at: "2026-09-17T13:00:00.000Z",
    };
    expect(
      bindNflFairLinesCertifiedRun(observedOk, expected),
    ).toMatchObject({ ok: true, reason: "ok" });
    expect(
      bindNflEdgesToFairLinesCertifiedRun({
        runId: "other",
        sha256: FIXTURE_SHA256,
      }).reason,
    ).toBe("unbound_certified_slot");
    expect(
      bindNflFairLinesCertifiedRun(
        { runId: "other", sha256: FIXTURE_SHA256, at: FIXTURE_AT },
        expected,
      ).reason,
    ).toBe("run_id_mismatch");
    expect(
      bindNflFairLinesCertifiedRun(
        { runId: FIXTURE_RUN_ID, sha256: "b".repeat(64), at: FIXTURE_AT },
        expected,
      ).reason,
    ).toBe("sha256_mismatch");
  });

  it("hard-blocks total/ML as NOT_CERTIFIABLE irrespective of switches", () => {
    expect(isNflMarketHardBlocked("total")).toBe(true);
    expect(isNflMarketHardBlocked("ml")).toBe(true);
    expect(isNflMarketHardBlocked("spread")).toBe(false);
    expect(unboundNflCertStatus()).toEqual({
      spread: "NOT_CERTIFIED",
      total: "NOT_CERTIFIABLE",
      ml: "NOT_CERTIFIABLE",
    });
    expect(resolveNflCertStatusField("CERTIFIED", "total")).toBe(
      "NOT_CERTIFIABLE",
    );
    expect(resolveNflCertStatusField("CERTIFIED", "ml")).toBe(
      "NOT_CERTIFIABLE",
    );
    expect(resolveNflCertStatusField(undefined, "spread")).toBe(
      "NOT_CERTIFIED",
    );
    expect(resolveNflCertStatus({ spread: "CERTIFIED" }).spread).toBe(
      "CERTIFIED",
    );
    expect(resolveNflCertStatus({ total: "CERTIFIED" }).total).toBe(
      "NOT_CERTIFIABLE",
    );
    expect(isNflFairLinesCertifiedPublicPaintAllowed({}, "total")).toBe(
      false,
    );
    expect(isNflFairLinesCertifiedPublicPaintAllowed({}, "ml")).toBe(false);
    expect(isNflMarketCustomerPaintAllowed("total")).toBe(false);
    expect(isNflMarketCustomerPaintAllowed("ml")).toBe(false);
    expect(isNflMarketCustomerPaintAllowed("spread")).toBe(false);
    expect(isNflEdgesCertifiedPublicPaintAllowed({}, "spread")).toBe(false);
    expect(isNflEdgesMarketRestrictEnabled("spread")).toBe(false);
    expect(NFL_FAIR_LINES_PUBLIC_SPREAD_ENABLED).toBe(false);
    expect(NFL_FAIR_LINES_PUBLIC_ML_ENABLED).toBe(false);
    expect(NFL_FAIR_LINES_PUBLIC_TOTAL_ENABLED).toBe(false);
  });

  it("Coming Soon is the first Edges gate; INTERNAL is not a CLEAR", () => {
    expect(isNflEdgesCustomerSurfaceClosed()).toBe(true);
    process.env.NFL_EDGE_BOARD_INTERNAL = "1";
    expect(isNflEdgesCustomerSurfaceClosed()).toBe(false);
    expect(isNflEdgesCertifiedPublicPaintAllowed()).toBe(false);
    expect(NFL_EDGE_BOARD_PUBLIC_ENABLED).toBe(false);
  });
});

describe("NflSurfaceProvenance envelope + fail-closed equality", () => {
  it("maps legacy as-of names onto canonical linesAsOf (never clock)", () => {
    expect(linesAsOfFromFairLinesOddsAsOf(" 2026-09-10T16:41:00Z ")).toBe(
      "2026-09-10T16:41:00Z",
    );
    expect(linesAsOfFromEdgesMarketAsOf("2026-09-10T16:41:00Z")).toBe(
      "2026-09-10T16:41:00Z",
    );
    expect(linesAsOfFromAssemble("2026-09-10T16:41:00Z")).toBe(
      "2026-09-10T16:41:00Z",
    );
    expect(linesAsOfFromFairLinesOddsAsOf("")).toBeNull();
    expect(linesAsOfFromFairLinesOddsAsOf(null)).toBeNull();
    const fair = nflSurfaceProvenanceFromFairLines({
      oddsAsOf: "2026-09-10T16:41:00Z",
    });
    const desk = nflSurfaceProvenanceFromEdgesDesk({
      marketAsOf: "2026-09-10T16:41:00Z",
    });
    const assemble = nflSurfaceProvenanceFromAssemble({
      linesAsOf: "2026-09-10T16:41:00Z",
    });
    expect(fair).toMatchObject({
      runId: null,
      sha256: null,
      linesAsOf: "2026-09-10T16:41:00Z",
      source: "fair",
      certStatus: unboundNflCertStatus(),
    });
    expect(desk.linesAsOf).toBe(fair.linesAsOf);
    expect(assemble.linesAsOf).toBe(fair.linesAsOf);
    expect(emptyNflSurfaceProvenance("desk")).toMatchObject({
      runId: null,
      sha256: null,
      linesAsOf: null,
      source: "desk",
    });
  });

  it("fail-closes exact-equality mismatches and missing provenance (X-1)", () => {
    const a = fixtureObserved();
    const b = fixtureObserved({ source: "desk" });
    expect(compareNflSurfaceProvenance(a, b)).toEqual({
      ok: true,
      reason: "ok",
    });
    expect(assertNflSurfacesAgree([a, b, fixtureObserved()])).toEqual({
      ok: true,
      reason: "ok",
    });
    expect(
      compareNflSurfaceProvenance(a, fixtureObserved({ runId: "other" })),
    ).toEqual({ ok: false, reason: "run_id_mismatch" });
    expect(
      compareNflSurfaceProvenance(
        a,
        fixtureObserved({ sha256: "b".repeat(64) }),
      ),
    ).toEqual({ ok: false, reason: "sha256_mismatch" });
    expect(
      compareNflSurfaceProvenance(
        a,
        fixtureObserved({ linesAsOf: "2026-09-10T16:40:00.000Z" }),
      ),
    ).toEqual({ ok: false, reason: "lines_as_of_mismatch" });
    expect(
      compareNflSurfaceProvenance(emptyNflSurfaceProvenance("fair"), a),
    ).toEqual({ ok: false, reason: "missing_provenance" });
    expect(assertNflSurfacesAgree([])).toEqual({
      ok: false,
      reason: "missing_provenance",
    });
  });

  it("fail-closes unbound certified slot and missing/older row linesAsOf", () => {
    expect(
      checkNflObservedAgainstCertifiedSlot({
        observed: fixtureObserved(),
      }).reason,
    ).toBe("unbound_certified_slot");
    expect(
      resolveNflRowLinesAsOf({ rowLinesAsOf: null }).reason,
    ).toBe("missing_lines_as_of");
    expect(
      resolveNflRowLinesAsOf({
        rowLinesAsOf: "2026-09-10T16:00:00.000Z",
        deskLinesAsOf: "2026-09-10T16:41:00.000Z",
      }).reason,
    ).toBe("lines_as_of_mismatch");
    expect(
      resolveNflRowLinesAsOf({
        rowLinesAsOf: FIXTURE_LINES,
        deskLinesAsOf: FIXTURE_LINES,
      }),
    ).toEqual({ linesAsOf: FIXTURE_LINES, reason: "ok" });
  });

  it("never substitutes governed.linesAsOf (X-3)", () => {
    expect(
      resolveNflAssembleLinesAsOfFromCapture(null, "2026-09-10T16:41:00Z"),
    ).toEqual({
      linesAsOf: null,
      reason: "governed_lines_as_of_forbidden",
    });
    expect(resolveNflAssembleLinesAsOfFromCapture(null, null)).toEqual({
      linesAsOf: null,
      reason: "missing_lines_as_of",
    });
    expect(
      resolveNflAssembleLinesAsOfFromCapture(
        "2026-09-10T16:41:00Z",
        "2099-01-01T00:00:00Z",
      ),
    ).toEqual({
      linesAsOf: "2026-09-10T16:41:00Z",
      reason: "ok",
    });
    const assemble = readWeb("app/api/edge-board/[sport]/assemble/route.ts");
    expect(assemble).toContain("resolveNflAssembleLinesAsOfFromCapture");
    expect(assemble).not.toContain(
      "resolveEdgeBoardBoardLinesAsOf(assembled) ?? governed.linesAsOf",
    );
    expect(assemble).toContain("NEVER substitute governed.linesAsOf");
  });

  it("rejects post-kickoff / post-model linesAsOf (X-3 leakage)", () => {
    expect(
      nflLinesAsOfLeakageReason({
        linesAsOf: "2026-09-10T00:30:00.000Z",
        kickoff: "2026-09-10T00:20:00.000Z",
      }),
    ).toBe("lines_as_of_mismatch");
    expect(
      nflLinesAsOfLeakageReason({
        linesAsOf: "2026-09-10T16:50:00.000Z",
        modelAsOf: "2026-09-10T16:41:00.000Z",
      }),
    ).toBe("lines_as_of_mismatch");
    expect(
      nflLinesAsOfLeakageReason({
        linesAsOf: "2026-09-10T16:40:00.000Z",
        modelAsOf: "2026-09-10T16:41:00.000Z",
        kickoff: "2026-09-10T20:00:00.000Z",
      }),
    ).toBe("ok");
    expect(nflLinesAsOfLeakageReason({})).toBe("missing_lines_as_of");
  });
});

describe("Edges desk omit-props + E-2 edge-row block", () => {
  it("omits props from the first build and marks the desk incomplete (N-1)", () => {
    expect(NFL_EDGES_PROPS_STATUS).toBe("unavailable");
    const payload = assembleNflEdgesDeskPayload({
      season: 2026,
      week: 1,
      market: "all",
      minProbEdge: 0.02,
      minLineEdge: 1,
      minConfidence: 0,
      fairOddsAsOf: FIXTURE_LINES,
      fairBooks: ["fanduel"],
      fairEdges: [
        deskRow({ id: "g-spread", marketType: "spread", source: "fair-lines" }),
        deskRow({ id: "g-total", marketType: "total", source: "fair-lines" }),
        deskRow({ id: "g-ml", marketType: "ml", source: "fair-lines" }),
      ],
      todayEdges: [
        deskRow({
          id: "g-today-ml",
          marketType: "ml",
          source: "edges-today",
        }),
      ],
      propEdges: [
        deskRow({
          id: "player-rec",
          marketType: "props",
          source: "props",
          matchupOrPlayer: "Demo Player",
        }),
      ],
    });
    expect(payload.propsStatus).toBe("unavailable");
    expect(payload.deskComplete).toBe(false);
    expect(payload.rows).toEqual([]);
    expect(payload.count).toBe(0);
    expect(payload.observed.runId).toBeNull();
    expect(payload.observed.sha256).toBeNull();
    expect(payload.observed.linesAsOf).toBe(FIXTURE_LINES);
    expect(payload.observed.certStatus).toEqual(unboundNflCertStatus());
    expect(payload.diagnostics.propsOmitted).toBe(true);
    expect(payload.diagnostics.edgeRowsBlocked).toBe(true);
    expect(payload.diagnostics.bindReason).toBe("unbound_certified_slot");
    expect(payload.diagnostics.propCandidates).toBe(0);
    expect(payload.rows.some((row) => row.marketType === "props")).toBe(false);
  });

  it("keeps edge rows blocked even after a Fair Lines bind succeeds (E-2)", () => {
    const bindOk = bindNflFairLinesCertifiedRun(
      {
        runId: FIXTURE_RUN_ID,
        sha256: FIXTURE_SHA256,
        at: FIXTURE_AT,
      },
      {
        runId: FIXTURE_RUN_ID,
        sha256: FIXTURE_SHA256,
        certifiedAt: FIXTURE_AT,
        maxAgeHours: 168,
      },
    );
    expect(bindOk.ok).toBe(true);
    const painted = selectNflEdgesCustomerPaintRows(
      [
        deskRow({ id: "g-spread", marketType: "spread", source: "fair-lines" }),
        deskRow({
          id: "g-today",
          marketType: "ml",
          source: "edges-today",
        }),
        deskRow({ id: "g-prop", marketType: "props", source: "props" }),
      ],
      {
        bindOk: true,
        observed: fixtureObserved({ source: "desk" }),
      },
    );
    expect(painted).toEqual([]);
    expect(NFL_EDGES_EDGE_LANGUAGE_ADOPTED).toBe(false);
  });

  it("source-locks page + API + fetch off props fan-out and dedicated Edges bind", () => {
    const edgesLib = readWeb("lib/nfl-edges.ts");
    const page = readWeb("app/(pro)/pro/nfl/edges/page.tsx");
    const api = readWeb("app/api/nfl/edges-desk/route.ts");
    const client = readWeb("components/pro/nfl/NflEdgesDeskClient.tsx");
    expect(edgesLib).toContain("assembleNflEdgesDeskPayload");
    expect(edgesLib).not.toContain("fetchNflPropsBoard");
    expect(edgesLib).not.toContain("fetchNflEdgesToday");
    expect(edgesLib).not.toContain("edgesMayShowPropRows");
    expect(page).toContain("isNflEdgesCustomerSurfaceClosed");
    expect(page).toContain("FootballNumbersUnavailable");
    expect(page).not.toContain("isFootballPublicNumbersDisabled");
    expect(api).toContain("isNflEdgesCustomerSurfaceClosed");
    expect(api).toContain('propsStatus: NFL_EDGES_PROPS_STATUS');
    expect(api).toContain("deskComplete: false");
    expect(client).toContain("edges-desk-incomplete");
    expect(client).toContain("nflEdgesDeskIncompleteCopy");
    expect(client).toContain('["all", "ml", "spread", "total"]');
    expect(client).not.toContain('["all", "ml", "spread", "total", "props"]');
    expect(client.toLowerCase()).not.toContain("full boards");
    expect(client.toLowerCase()).not.toContain("clv");
  });
});
