import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

const root = join(process.cwd());

function readRel(rel: string): string {
  return readFileSync(join(root, rel), "utf8");
}

/**
 * Historical crash (~2026-09-01 digests): `/pro/[sport]/edges` RSC imported
 * `flatRowsToLegacy` via the client EdgeBoard module. Guard: server paths use
 * the shared lib; EdgeBoard must not re-export the converter.
 */
describe("edges RSC client-boundary regression", () => {
  it("flat-rows-to-legacy stays server-safe (no use client)", () => {
    const src = readRel("lib/flat-rows-to-legacy.ts");
    expect(src).not.toMatch(/^["']use client["']/m);
    expect(src).toMatch(/Server-safe Edge Board flat/);
  });

  it("edge-board-tonight imports converter from lib, not EdgeBoard", () => {
    const src = readRel("lib/edge-board-tonight.ts");
    expect(src).toMatch(/from\s+["']@\/lib\/flat-rows-to-legacy["']/);
    expect(src).not.toMatch(
      /flatRowsToLegacy[^;]*from\s+["']@\/components\/EdgeBoard["']/,
    );
  });

  it("sport edges page uses getTonightGames (lib path), not EdgeBoard value import", () => {
    const src = readRel("app/(pro)/pro/[sport]/edges/page.tsx");
    expect(src).toMatch(/getTonightGames/);
    expect(src).toMatch(/from\s+["']@\/lib\/edge-board-tonight["']/);
    expect(src).not.toMatch(/from\s+["']@\/components\/EdgeBoard["']/);
    expect(src).not.toMatch(/flatRowsToLegacy/);
  });

  it("client EdgeBoard does not re-export flatRowsToLegacy", () => {
    const src = readRel("components/EdgeBoard.tsx");
    expect(src).toMatch(/^["']use client["']/m);
    expect(src).not.toMatch(/export\s*\{\s*flatRowsToLegacy\s*\}/);
  });
});

describe("odds-api-keys env-only (no embedded backup)", () => {
  it("does not embed a backup API key constant", () => {
    const src = readRel("lib/odds-api-keys.ts");
    expect(src).toMatch(/server-only/);
    expect(src).not.toMatch(/EMBEDDED_ODDS/);
    expect(src).toMatch(/ODDS_API_KEY_BACKUP/);
    // No long hex literal masquerading as a key.
    expect(src).not.toMatch(/["'][0-9a-f]{32}["']/i);
  });
});
