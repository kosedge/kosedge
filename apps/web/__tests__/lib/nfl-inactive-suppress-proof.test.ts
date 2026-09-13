/**
 * Preview-only synthetic inactive-suppress proof (Proof A).
 * Never paints ATL@PIT. Never enabled on VERCEL_ENV=production.
 */
import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { CFB_EDGE_BOARD_PUBLIC_ENABLED } from "@/lib/cfb-edge-board-public";
import {
  appendNflInactiveSuppressProofRows,
  buildNflInactiveSuppressProofAssembleBody,
  buildNflInactiveSuppressProofRows,
  isNflInactiveSuppressProofEnv,
  isNflInactiveSuppressProofRequest,
  NFL_INACTIVE_SUPPRESS_PROOF_COMMENCE,
  NFL_INACTIVE_SUPPRESS_PROOF_GAME_KEY,
  NFL_INACTIVE_SUPPRESS_PROOF_GAME_LABEL,
  NFL_INACTIVE_SUPPRESS_PROOF_UUID,
} from "@/lib/nfl-inactive-suppress-proof";
import { NFL_INACTIVE_SUPPRESS_REASON_MAJOR } from "@/lib/nfl-inactive-fair-suppress";

const webRoot = path.join(__dirname, "../..");

const PREVIEW_URL = new URL(
  "https://preview.example/api/edge-board/nfl/assemble?slate=week1&inactiveProof=1",
);
const WEEK1_URL = new URL(
  "https://preview.example/api/edge-board/nfl/assemble?slate=week1",
);

describe("nfl inactive suppress proof gate", () => {
  it("enables on Vercel preview", () => {
    expect(isNflInactiveSuppressProofEnv({ VERCEL_ENV: "preview" })).toBe(true);
  });

  it("enables on local INACTIVE_SUPPRESS_PROOF=1 when not production", () => {
    expect(
      isNflInactiveSuppressProofEnv({ INACTIVE_SUPPRESS_PROOF: "1" }),
    ).toBe(true);
  });

  it("never enables on VERCEL_ENV=production even with proof env + query", () => {
    const env = {
      VERCEL_ENV: "production",
      INACTIVE_SUPPRESS_PROOF: "1",
    };
    expect(isNflInactiveSuppressProofEnv(env)).toBe(false);
    expect(isNflInactiveSuppressProofRequest(PREVIEW_URL, env)).toBe(false);
    const rows = appendNflInactiveSuppressProofRows([], PREVIEW_URL, env);
    expect(rows).toEqual([]);
  });

  it("requires inactiveProof=1 even on preview", () => {
    expect(
      isNflInactiveSuppressProofRequest(WEEK1_URL, { VERCEL_ENV: "preview" }),
    ).toBe(false);
    expect(
      appendNflInactiveSuppressProofRows([], WEEK1_URL, {
        VERCEL_ENV: "preview",
      }),
    ).toEqual([]);
  });

  it("appends SUPPRESSED Spread+Total rows from the packaged store (no env)", () => {
    const rows = appendNflInactiveSuppressProofRows(
      [],
      PREVIEW_URL,
      { VERCEL_ENV: "preview" },
      { nowMs: Date.parse("2026-09-13T22:43:00Z") },
    );
    expect(rows).toHaveLength(2);
    expect(rows.map((r) => r.market)).toEqual(["Spread", "Total"]);
    for (const row of rows) {
      expect(row.gameId).toBe(NFL_INACTIVE_SUPPRESS_PROOF_GAME_KEY);
      expect(row.game).toBe(NFL_INACTIVE_SUPPRESS_PROOF_GAME_LABEL);
      expect(row.commenceTime).toBe(NFL_INACTIVE_SUPPRESS_PROOF_COMMENCE);
      expect(row.inactiveSuppress?.state).toBe("SUPPRESSED");
      expect(row.inactiveSuppress?.reason).toBe(
        NFL_INACTIVE_SUPPRESS_REASON_MAJOR,
      );
      expect(row.inactiveSuppress?.classes).toEqual(["MAJOR"]);
      expect(row.inactiveSuppress?.ttlUntil).toBeTruthy();
      expect(row.fairCompareEligible).toBe(false);
      expect(row.kei).toBeUndefined();
      expect(row.publishTag).toBeUndefined();
      expect(row.best).toBeTruthy();
    }
    expect(rows[0]?.id).toContain(NFL_INACTIVE_SUPPRESS_PROOF_UUID);
  });

  it("natural CLEAR after packaged ttlUntil (no remat / no env)", () => {
    const rows = appendNflInactiveSuppressProofRows(
      [],
      PREVIEW_URL,
      { VERCEL_ENV: "preview" },
      { nowMs: Date.parse("2099-01-01T00:00:00Z") },
    );
    expect(rows).toHaveLength(2);
    for (const row of rows) {
      expect(row.inactiveSuppress?.state).toBe("CLEAR");
      expect(row.kei).toBeTruthy();
    }
  });

  it("raw proof rows never use a customer ATL@PIT id or label", () => {
    for (const row of buildNflInactiveSuppressProofRows()) {
      expect(String(row.gameId)).not.toMatch(/ATL/i);
      expect(String(row.game)).not.toMatch(/ATL|PIT|Falcons|Steelers/i);
      expect(String(row.awayAbbr)).not.toBe("ATL");
      expect(String(row.homeAbbr)).not.toBe("PIT");
    }
  });

  it("does not flip the CFB public board kill switch", () => {
    expect(CFB_EDGE_BOARD_PUBLIC_ENABLED).toBe(false);
  });

  it("proof assemble body does not require model-service", () => {
    const body = buildNflInactiveSuppressProofAssembleBody(
      PREVIEW_URL,
      { VERCEL_ENV: "preview" },
      { nowMs: Date.parse("2026-09-13T22:43:00Z") },
    );
    expect(body).not.toBeNull();
    expect(body!.proofOnly).toBe(true);
    expect(body!.rows).toHaveLength(2);
    expect(body!.games).toBe(1);
    expect(body!.week1Count).toBe(1);
    expect(body!.rows[0]?.inactiveSuppress?.state).toBe("SUPPRESSED");
    const helper = readFileSync(
      path.join(webRoot, "lib/nfl-inactive-suppress-proof.ts"),
      "utf8",
    );
    expect(helper).not.toContain("loadAssembledEdgeBoardRows");
    expect(helper).not.toContain("requireGovernedNflFullSlate");
    expect(helper).not.toContain("from \"@/lib/build-edge-board-rows\"");
  });

  it("production cannot build a proof assemble body", () => {
    expect(
      buildNflInactiveSuppressProofAssembleBody(PREVIEW_URL, {
        VERCEL_ENV: "production",
        INACTIVE_SUPPRESS_PROOF: "1",
      }),
    ).toBeNull();
  });

  it("assemble route short-circuits proof before model fetch", () => {
    const src = readFileSync(
      path.join(webRoot, "app/api/edge-board/[sport]/assemble/route.ts"),
      "utf8",
    );
    const proofAt = src.indexOf("buildNflInactiveSuppressProofAssembleBody(url)");
    const loadAt = src.indexOf('await loadAssembledEdgeBoardRows("nfl"');
    const tryAt = src.indexOf("try {\n    if (sport === \"nfl\")");
    expect(proofAt).toBeGreaterThanOrEqual(0);
    expect(loadAt).toBeGreaterThan(proofAt);
    expect(tryAt).toBeGreaterThan(proofAt);
    expect(src.indexOf("if (proofBody)")).toBeGreaterThan(proofAt);
    expect(src.indexOf("if (proofBody)")).toBeLessThan(loadAt);
  });
});
