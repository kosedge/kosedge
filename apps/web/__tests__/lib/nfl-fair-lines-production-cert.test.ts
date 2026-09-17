/**
 * NFL Fair Lines PRODUCTION-CERT — Product track (Ryan 2026-09-17).
 * Source-lock + fail-closed bind. Not a public CLEAR. No remat.
 */
import { readFileSync } from "node:fs";
import path from "node:path";
import { afterEach, describe, expect, it } from "vitest";
import {
  CFB_EDGE_BOARD_PUBLIC_ENABLED,
  NFL_EDGE_BOARD_PUBLIC_ENABLED,
  NFL_FAIR_LINES_CERTIFIED_AT,
  NFL_FAIR_LINES_CERTIFIED_RUN_ID,
  NFL_FAIR_LINES_CERTIFIED_SHA256,
  NFL_FAIR_LINES_CERT_MAX_AGE_HOURS,
  NFL_FAIR_LINES_KELLY_ENABLED,
  NFL_FAIR_LINES_PLAY_ENABLED,
  NFL_FAIR_LINES_PRODUCTION_ARTIFACT_ID,
  NFL_FAIR_LINES_PRODUCTION_ARTIFACT_SHA256,
  NFL_FAIR_LINES_PRODUCTION_ARTIFACT_STATUS,
  NFL_FAIR_LINES_V2_DIAGNOSTIC_ID,
  NFL_FAIR_LINES_V2_DIAGNOSTIC_STATUS,
  NFL_FAIR_LINES_PUBLIC_ML_ENABLED,
  NFL_FAIR_LINES_PUBLIC_SPREAD_ENABLED,
  NFL_FAIR_LINES_PUBLIC_TOTAL_ENABLED,
  NFL_FAIR_LINES_WARROOM_ARTIFACT_ID,
  NFL_FAIR_LINES_WARROOM_ARTIFACT_SHA256,
  NFL_FAIR_LINES_WARROOM_ARTIFACT_STATUS,
  NFL_FAIR_LINES_WARROOM_ARTIFACT_VERSION,
  bindNflFairLinesCertifiedRun,
  isNflFairLinesRejectedPracticeSha,
  nflFairLinesWarroomPracticeArtifact,
  isNflFairLinesAnyMarketPublicEnabled,
  isNflFairLinesCertifiedPublicPaintAllowed,
  isNflFairLinesCustomerSurfaceClosed,
  isNflFairLinesKellyEnabled,
  isNflFairLinesMarketPublicEnabled,
  isNflFairLinesPlayEnabled,
  nflFairLinesCertifiedBinding,
  nflFairLinesPublicEnabledMarkets,
} from "@/lib/cfb-edge-board-public";

const webRoot = path.join(__dirname, "../..");
const repoRoot = path.join(webRoot, "../..");

function readWeb(rel: string): string {
  return readFileSync(path.join(webRoot, rel), "utf8");
}

function readRepo(rel: string): string {
  return readFileSync(path.join(repoRoot, rel), "utf8");
}

const FIXTURE_RUN_ID = "nfl-fair-lines-cert-fixture-not-production";
const FIXTURE_SHA256 = "a".repeat(64);
const FIXTURE_AT = "2026-09-17T12:00:00.000Z";

function fixtureBinding(overrides: Partial<ReturnType<typeof nflFairLinesCertifiedBinding>> = {}) {
  return {
    runId: FIXTURE_RUN_ID,
    sha256: FIXTURE_SHA256,
    certifiedAt: FIXTURE_AT,
    maxAgeHours: 168,
    ...overrides,
  };
}

describe("NFL Fair Lines PRODUCTION-CERT Product harness", () => {
  afterEach(() => {
    delete process.env.NFL_EDGE_BOARD_INTERNAL;
    delete process.env.NEXT_PUBLIC_NFL_EDGE_BOARD_INTERNAL;
    delete process.env.CFB_EDGE_BOARD_INTERNAL;
    delete process.env.NEXT_PUBLIC_CFB_EDGE_BOARD_INTERNAL;
  });

  it("keeps Coming soon ON and every public / market / stake gate false", () => {
    expect(NFL_EDGE_BOARD_PUBLIC_ENABLED).toBe(false);
    expect(CFB_EDGE_BOARD_PUBLIC_ENABLED).toBe(false);
    expect(NFL_FAIR_LINES_PUBLIC_SPREAD_ENABLED).toBe(false);
    expect(NFL_FAIR_LINES_PUBLIC_ML_ENABLED).toBe(false);
    expect(NFL_FAIR_LINES_PUBLIC_TOTAL_ENABLED).toBe(false);
    expect(NFL_FAIR_LINES_PLAY_ENABLED).toBe(false);
    expect(NFL_FAIR_LINES_KELLY_ENABLED).toBe(false);
    expect(isNflFairLinesMarketPublicEnabled("spread")).toBe(false);
    expect(isNflFairLinesMarketPublicEnabled("ml")).toBe(false);
    expect(isNflFairLinesMarketPublicEnabled("total")).toBe(false);
    expect(isNflFairLinesAnyMarketPublicEnabled()).toBe(false);
    expect(nflFairLinesPublicEnabledMarkets()).toEqual([]);
    expect(isNflFairLinesPlayEnabled()).toBe(false);
    expect(isNflFairLinesKellyEnabled()).toBe(false);
    expect(isNflFairLinesCertifiedPublicPaintAllowed()).toBe(false);
    expect(isNflFairLinesCustomerSurfaceClosed()).toBe(true);
  });

  it("leaves the certified run_id + sha256 slot unbound (no invented hash)", () => {
    expect(NFL_FAIR_LINES_CERTIFIED_RUN_ID).toBeNull();
    expect(NFL_FAIR_LINES_CERTIFIED_SHA256).toBeNull();
    expect(NFL_FAIR_LINES_CERTIFIED_AT).toBeNull();
    expect(NFL_FAIR_LINES_CERT_MAX_AGE_HOURS).toBe(168);
    const binding = nflFairLinesCertifiedBinding();
    expect(binding.runId).toBeNull();
    expect(binding.sha256).toBeNull();
    expect(binding.certifiedAt).toBeNull();
    expect(bindNflFairLinesCertifiedRun({}).reason).toBe(
      "unbound_certified_slot",
    );
    expect(bindNflFairLinesCertifiedRun({}).ok).toBe(false);
    expect(NFL_FAIR_LINES_CERTIFIED_SHA256).not.toBe(
      NFL_FAIR_LINES_WARROOM_ARTIFACT_SHA256,
    );
    expect(NFL_FAIR_LINES_PRODUCTION_ARTIFACT_ID).toBeNull();
    expect(NFL_FAIR_LINES_PRODUCTION_ARTIFACT_SHA256).toBeNull();
    expect(NFL_FAIR_LINES_PRODUCTION_ARTIFACT_STATUS).toBe(
      "UNBOUND_AWAIT_CLOCK_PLAY_FREEZE",
    );
    expect(NFL_FAIR_LINES_V2_DIAGNOSTIC_ID).toBe("pe_drive_poss_v2");
    expect(NFL_FAIR_LINES_V2_DIAGNOSTIC_STATUS).toBe("DIAGNOSTIC_STOP");
  });

  it("records pe_drive_poss_v1 as a rejected practice SHA (not a production bind)", () => {
    const warroom = nflFairLinesWarroomPracticeArtifact();
    expect(warroom.artifactId).toBe("pe_drive_poss_v1");
    expect(warroom.version).toBe("1.0.0-warroom-20260917");
    expect(warroom.sha256).toBe(
      "b5ee9d80494bbc13b989174af0676afb1831a4cb11e678f2f243ac469b92d36b",
    );
    expect(warroom.status).toBe("REJECTED_NO_CLEAR");
    expect(warroom.alex).toBe("NO_CLEAR");
    expect(NFL_FAIR_LINES_WARROOM_ARTIFACT_ID).toBe("pe_drive_poss_v1");
    expect(NFL_FAIR_LINES_WARROOM_ARTIFACT_VERSION).toBe(
      "1.0.0-warroom-20260917",
    );
    expect(NFL_FAIR_LINES_WARROOM_ARTIFACT_SHA256).toBe(warroom.sha256);
    expect(NFL_FAIR_LINES_WARROOM_ARTIFACT_STATUS).toBe("REJECTED_NO_CLEAR");
    expect(isNflFairLinesRejectedPracticeSha(warroom.sha256)).toBe(true);
    expect(isNflFairLinesRejectedPracticeSha(FIXTURE_SHA256)).toBe(false);

    const rejectedExpected = fixtureBinding({
      runId: NFL_FAIR_LINES_WARROOM_ARTIFACT_ID,
      sha256: NFL_FAIR_LINES_WARROOM_ARTIFACT_SHA256,
    });
    expect(
      bindNflFairLinesCertifiedRun(
        {
          runId: NFL_FAIR_LINES_WARROOM_ARTIFACT_ID,
          sha256: NFL_FAIR_LINES_WARROOM_ARTIFACT_SHA256,
          at: FIXTURE_AT,
        },
        rejectedExpected,
      ),
    ).toMatchObject({ ok: false, reason: "rejected_practice_sha" });

    expect(
      bindNflFairLinesCertifiedRun(
        {
          runId: FIXTURE_RUN_ID,
          sha256: NFL_FAIR_LINES_WARROOM_ARTIFACT_SHA256,
          at: FIXTURE_AT,
        },
        fixtureBinding(),
      ).reason,
    ).toBe("rejected_practice_sha");

    expect(
      bindNflFairLinesCertifiedRun(
        {
          runId: NFL_FAIR_LINES_V2_DIAGNOSTIC_ID,
          sha256: FIXTURE_SHA256,
          at: FIXTURE_AT,
        },
        fixtureBinding({ runId: NFL_FAIR_LINES_V2_DIAGNOSTIC_ID }),
      ).reason,
    ).toBe("diagnostic_stop");
  });

  it("fail-closes missing / mismatched / stale certified run_id + sha256", () => {
    const expected = fixtureBinding();
    const observedOk = {
      runId: FIXTURE_RUN_ID,
      sha256: FIXTURE_SHA256,
      at: "2026-09-17T13:00:00.000Z",
    };

    expect(bindNflFairLinesCertifiedRun(observedOk, expected)).toMatchObject({
      ok: true,
      reason: "ok",
    });

    expect(
      bindNflFairLinesCertifiedRun(
        { sha256: FIXTURE_SHA256, at: FIXTURE_AT },
        expected,
      ).reason,
    ).toBe("missing_run_id");
    expect(
      bindNflFairLinesCertifiedRun(
        { runId: FIXTURE_RUN_ID, at: FIXTURE_AT },
        expected,
      ).reason,
    ).toBe("missing_sha256");
    expect(
      bindNflFairLinesCertifiedRun(
        { runId: FIXTURE_RUN_ID, sha256: "deadbeef", at: FIXTURE_AT },
        expected,
      ).reason,
    ).toBe("invalid_sha256");
    expect(
      bindNflFairLinesCertifiedRun(
        { runId: "other-run", sha256: FIXTURE_SHA256, at: FIXTURE_AT },
        expected,
      ).reason,
    ).toBe("run_id_mismatch");
    expect(
      bindNflFairLinesCertifiedRun(
        { runId: FIXTURE_RUN_ID, sha256: "b".repeat(64), at: FIXTURE_AT },
        expected,
      ).reason,
    ).toBe("sha256_mismatch");
    expect(
      bindNflFairLinesCertifiedRun(observedOk, {
        ...expected,
        certifiedAt: null,
      }).reason,
    ).toBe("missing_certified_at");
    expect(
      bindNflFairLinesCertifiedRun(
        { ...observedOk, at: "2026-09-25T12:00:01.000Z" },
        expected,
      ).reason,
    ).toBe("stale");
    expect(
      bindNflFairLinesCertifiedRun(
        observedOk,
        fixtureBinding({ sha256: "not-a-sha" }),
      ).reason,
    ).toBe("invalid_sha256");
  });

  it("treats INTERNAL as QA only — not a public CLEAR", () => {
    expect(NFL_EDGE_BOARD_PUBLIC_ENABLED).toBe(false);
    process.env.NFL_EDGE_BOARD_INTERNAL = "1";
    expect(isNflFairLinesCustomerSurfaceClosed()).toBe(false);
    expect(isNflFairLinesCertifiedPublicPaintAllowed()).toBe(false);
    expect(isNflFairLinesAnyMarketPublicEnabled()).toBe(false);
    expect(isNflFairLinesPlayEnabled()).toBe(false);
    expect(isNflFairLinesKellyEnabled()).toBe(false);
  });

  it("wires cert-binding into Fair Lines API + page and keeps Coming soon chrome", () => {
    const api = readWeb("app/api/nfl/fair-lines/route.ts");
    const page = readWeb("app/(pro)/pro/nfl/fair-lines/page.tsx");
    expect(api).toContain("isNflFairLinesCustomerSurfaceClosed");
    expect(api).toContain("nflEdgeBoardAssembleUnavailablePayload");
    expect(api).toContain("status: 503");
    expect(api).not.toContain("isFootballPublicNumbersDisabled");
    expect(page).toContain("isNflFairLinesCustomerSurfaceClosed");
    expect(page).toContain("FootballNumbersUnavailable");
    expect(page).toContain("Coming soon");
    expect(page).not.toContain("isFootballPublicNumbersDisabled");
  });

  it("source-locks constants false / unbound and no env unlock for cert or market gates", () => {
    const pub = readWeb("lib/cfb-edge-board-public.ts");
    expect(pub).toContain("NFL_EDGE_BOARD_PUBLIC_ENABLED = false");
    expect(pub).toContain("CFB_EDGE_BOARD_PUBLIC_ENABLED = false");
    expect(pub).toContain("NFL_FAIR_LINES_PUBLIC_SPREAD_ENABLED = false");
    expect(pub).toContain("NFL_FAIR_LINES_PUBLIC_ML_ENABLED = false");
    expect(pub).toContain("NFL_FAIR_LINES_PUBLIC_TOTAL_ENABLED = false");
    expect(pub).toContain("NFL_FAIR_LINES_PLAY_ENABLED = false");
    expect(pub).toContain("NFL_FAIR_LINES_KELLY_ENABLED = false");
    expect(pub).toContain(
      "NFL_FAIR_LINES_CERTIFIED_RUN_ID: string | null = null",
    );
    expect(pub).toContain(
      "NFL_FAIR_LINES_CERTIFIED_SHA256: string | null = null",
    );
    expect(pub).toContain("NFL_FAIR_LINES_CERTIFIED_AT: string | null = null");
    expect(pub).not.toMatch(
      /NFL_FAIR_LINES_PUBLIC_(SPREAD|ML|TOTAL)_ENABLED\s*=\s*true/,
    );
    expect(pub).not.toMatch(/NFL_FAIR_LINES_(PLAY|KELLY)_ENABLED\s*=\s*true/);
    expect(pub).not.toMatch(
      /NFL_FAIR_LINES_CERTIFIED_(RUN_ID|SHA256|AT).*=\s*process\.env/,
    );
    expect(pub).not.toMatch(
      /NFL_FAIR_LINES_PUBLIC_(SPREAD|ML|TOTAL)_ENABLED\s*=\s*envFlagTrue/,
    );
    expect(pub).toContain("Do not invent a production hash");
    expect(pub).toContain("no DFS / Line Curve / CFB work");
    expect(pub).toContain(
      "b5ee9d80494bbc13b989174af0676afb1831a4cb11e678f2f243ac469b92d36b",
    );
    expect(pub).toContain("pe_drive_poss_v1");
    expect(pub).toContain("pe_drive_poss_v2");
    expect(pub).toContain("REJECTED_NO_CLEAR");
    expect(pub).toContain("DIAGNOSTIC_STOP");
    expect(pub).toContain("UNBOUND_AWAIT_CLOCK_PLAY_FREEZE");
    expect(pub).not.toContain("NFL_FAIR_LINES_PRODUCTION_ARTIFACT_ID = \"pe_drive_poss_v2\"");
    expect(pub).not.toMatch(
      /NFL_FAIR_LINES_CERTIFIED_SHA256: string \| null = "b5ee9d80/,
    );
  });

  it("does not touch DFS / Line Curve / CFB public constants", () => {
    const pub = readWeb("lib/cfb-edge-board-public.ts");
    expect(pub).toContain("CFB_EDGE_BOARD_PUBLIC_ENABLED = false");
    expect(pub).not.toMatch(/CFB_EDGE_BOARD_PUBLIC_ENABLED = true/);

    const dfs = readWeb("lib/nfl-dfs-identity.ts");
    expect(dfs).not.toContain("NFL_FAIR_LINES_CERTIFIED_RUN_ID");
    const lineCurve = readWeb("lib/line-curve/service.ts");
    expect(lineCurve).not.toContain("NFL_FAIR_LINES_CERTIFIED_RUN_ID");
  });

  it("documents rollback + empty CoS/Ryan Product packet slots", () => {
    const packet = readRepo(
      "docs/ops/NFL_FAIR_LINES_PRODUCTION_CERT_PRODUCT_2026-09-17.md",
    );
    const receipt = readRepo(
      "data/ops/nfl-fair-lines-production-cert-product-20260917.md",
    );
    const machine = JSON.parse(
      readRepo(
        "data/ops/nfl-fair-lines-production-cert-product-20260917/packet.json",
      ),
    ) as {
      recommendation: string;
      public_flags: Record<string, boolean>;
      market_gates: Record<string, boolean>;
      certified_run: { run_id: string | null; sha256: string | null };
      approvers: { cos: string; ryan: string };
      release_slots: Array<{ slot: string; cos: string; ryan: string }>;
      warroom_artifact: {
        artifact_id: string;
        artifact_sha256: string;
        alex: string;
        status: string;
      };
      production_binding_target: {
        artifact_id: string | null;
        sha256: string | null;
        status: string;
      };
      v2_diagnostic: { artifact_id: string; status: string };
    };

    expect(packet).toContain("NO CLEAR");
    expect(packet).toContain("Rollback");
    expect(packet).toContain("NFL_EDGE_BOARD_PUBLIC_ENABLED = false");
    expect(packet).toContain("pe_drive_poss_v1");
    expect(packet).toContain(
      "b5ee9d80494bbc13b989174af0676afb1831a4cb11e678f2f243ac469b92d36b",
    );
    expect(packet).toContain("pe_drive_poss_v2");
    expect(packet).toContain("diagnostic STOP");
    expect(packet).toContain("rejected practice SHA");
    expect(packet).toMatch(/CoS:\s*$/m);
    expect(receipt).toContain("Coming soon");
    expect(receipt).toContain("unbound");
    expect(receipt).toContain(
      "b5ee9d80494bbc13b989174af0676afb1831a4cb11e678f2f243ac469b92d36b",
    );
    expect(receipt).toContain("Alex NO CLEAR");
    expect(machine.recommendation).toBe("NO_CLEAR");
    expect(machine.public_flags.NFL_EDGE_BOARD_PUBLIC_ENABLED).toBe(false);
    expect(machine.public_flags.CFB_EDGE_BOARD_PUBLIC_ENABLED).toBe(false);
    expect(machine.market_gates.spread).toBe(false);
    expect(machine.market_gates.ml).toBe(false);
    expect(machine.market_gates.total).toBe(false);
    expect(machine.certified_run.run_id).toBeNull();
    expect(machine.certified_run.sha256).toBeNull();
    expect(machine.approvers.cos).toBe("");
    expect(machine.approvers.ryan).toBe("");
    expect(machine.warroom_artifact.artifact_id).toBe("pe_drive_poss_v1");
    expect(machine.warroom_artifact.artifact_sha256).toBe(
      "b5ee9d80494bbc13b989174af0676afb1831a4cb11e678f2f243ac469b92d36b",
    );
    expect(machine.warroom_artifact.alex).toBe("NO_CLEAR");
    expect(machine.warroom_artifact.status).toBe("REJECTED_PRACTICE_SHA");
    expect(machine.production_binding_target.artifact_id).toBeNull();
    expect(machine.production_binding_target.sha256).toBeNull();
    expect(machine.production_binding_target.status).toBe(
      "UNBOUND_AWAIT_CLOCK_PLAY_FREEZE",
    );
    expect(machine.v2_diagnostic.artifact_id).toBe("pe_drive_poss_v2");
    expect(machine.v2_diagnostic.status).toBe("DIAGNOSTIC_STOP");
    for (const slot of machine.release_slots) {
      expect(slot.cos).toBe("");
      expect(slot.ryan).toBe("");
    }
  });
});
