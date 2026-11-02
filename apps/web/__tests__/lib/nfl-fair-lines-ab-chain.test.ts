/**
 * t5194u A→B chain — consume A's serialized FixtureChainRecord.
 * Real functions only. No invented allow tokens. CERT=0.
 */
import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import {
  assertFixtureChainRecord,
  projectFixtureAbChain,
  writeThenReadFixtureChainCache,
} from "@/lib/nfl-fair-lines-ab-chain";
import {
  CHAIN_CONTRACT_ID,
  CHAIN_SCHEMA_VERSION,
  FixtureHardRefuse,
  consumeFixtureEligibility,
  allowFixtureEligibility,
  ELIGIBILITY_REQUIRED_KEYS,
} from "@/lib/nfl-fixture-assembly-contract";
import {
  invalidateFixtureProjectionCache,
  readFixtureProjectionCache,
} from "@/lib/page-data-cache";
import { projectFixtureFairLinesApiResponse } from "@/lib/nfl-fair-lines-fixture-api";
import { projectFixtureFairLinesViewModel } from "@/lib/nfl-fair-lines-view-types";
import { keiGamesFromFixtureFairLines } from "@/lib/resolve-kei-lines";

const repoRoot = path.join(__dirname, "../../../..");
const PINNED = path.join(
  repoRoot,
  "data/ops/t5194u-wfix-a-chain/positive-output.json",
);
const PINNED_SHA = path.join(
  repoRoot,
  "data/ops/t5194u-wfix-a-chain/positive-output.sha256",
);
const EXPECTED_DIGEST =
  "27f32649050578108720b2ff26eacebadb92c7324f1930661c88b8f1ce6e6124";

function loadPinned(): Record<string, unknown> {
  return JSON.parse(readFileSync(PINNED, "utf8")) as Record<string, unknown>;
}

function clone(base: Record<string, unknown>): Record<string, unknown> {
  return JSON.parse(JSON.stringify(base)) as Record<string, unknown>;
}

describe("t5194u consumeFixtureEligibility (A exact-field gate)", () => {
  it("accepts A's serialized eligibility and refuses bare / rewritten allows", () => {
    const chain = loadPinned();
    const eligibility = chain.eligibility as Record<string, unknown>;
    const ok = consumeFixtureEligibility(eligibility, "fixture");
    expect(ok.result).toBe("ALLOW_FIXTURE");
    expect(ok.schema_version).toBe("nfl-fixture-assembly-v0");
    expect(ok.contract_id).toBe("t5178u-nfl-fixture-assembly-v0");

    expect(() =>
      consumeFixtureEligibility({ result: "ALLOW_FIXTURE" }, "fixture"),
    ).toThrow(FixtureHardRefuse);
    try {
      consumeFixtureEligibility({ result: "ALLOW_FIXTURE" }, "fixture");
    } catch (err) {
      expect((err as FixtureHardRefuse).result).toBe("REFUSE_MISSING");
    }

    const wrong = { ...eligibility, contract_id: "some-other-contract" };
    expect(() => consumeFixtureEligibility(wrong, "fixture")).toThrow(
      /not rewritten/,
    );

    const flipped = { ...eligibility, fixture: false };
    try {
      consumeFixtureEligibility(flipped, "fixture");
      expect.unreachable("fixture=false rewritten");
    } catch (err) {
      expect((err as FixtureHardRefuse).result).toBe("REFUSE_QUALIFICATION");
    }

    const prod = { ...eligibility, channel: "PRODUCTION" };
    try {
      consumeFixtureEligibility(prod, "fixture");
      expect.unreachable("PRODUCTION rewritten");
    } catch (err) {
      expect((err as FixtureHardRefuse).result).toBe("REFUSE_PRODUCTION_CHANNEL");
    }

    expect(ELIGIBILITY_REQUIRED_KEYS).toContain("schema_version");
    const original = allowFixtureEligibility();
    expect(original.schema_version).toBe("nfl-fixture-assembly-v0");
    consumeFixtureEligibility(original, "fixture");
  });
});

describe("t5194u A→B chain consume of pinned A artifact", () => {
  it("pins digest and carries one I/O context through API / VM / export-shape / cache", () => {
    const payload = loadPinned();
    expect(readFileSync(PINNED_SHA, "utf8").trim()).toBe(EXPECTED_DIGEST);
    expect(payload.chain_contract_id).toBe(CHAIN_CONTRACT_ID);
    expect(payload.chain_schema_version).toBe(CHAIN_SCHEMA_VERSION);

    const chain = assertFixtureChainRecord(payload);
    expect(chain.forecast.game_id).toBe(chain.game_id);
    expect(chain.l1_candidate.capture_id).toBe(chain.admitted_capture_id);
    expect(chain.cutoff.decision_ts).toBe(chain.provenance.decision_ts);
    expect(chain.capability.bits).toContain("POINT_MARGIN");

    const projected = projectFixtureAbChain(payload);
    expect(projected.api.status).toBe(200);
    expect(projected.api.board.persistOdds).toBe(false);
    expect(projected.api.board.lines[0].spreadHome).toBe(-3);
    expect(projected.api.board.lines[0].totalMean).toBeNull();
    expect(projected.api.board.lines[0].fairHomeMl).toBeNull();
    expect(projected.view.fixture).toBe(true);
    expect(projected.view.subscriber_consumable).toBe(false);
    expect(projected.view.lines[0].spreadHome).toBe(-3);
    expect(projected.kei[0].projSpreadHome).toBe(-3);
    expect(projected.kei[0].projTotal).toBeNull();
    expect(projected.headers["Cache-Control"]).toBe("private, no-store");

    const cached = writeThenReadFixtureChainCache("t5194u-ab", projected.api.board, 1);
    expect(cached.ok).toBe(true);
    invalidateFixtureProjectionCache("t5194u-ab");
    expect(readFixtureProjectionCache("t5194u-ab", 1)).toEqual({
      ok: false,
      result: "REFUSE_CACHE",
    });
  });

  it.each([
    [
      "identity",
      (p: Record<string, unknown>) => {
        p.admitted_capture_id = "0".repeat(64);
      },
    ],
    [
      "hash",
      (p: Record<string, unknown>) => {
        (p.forecast as Record<string, unknown>).forecast_id = "not-a-sha256";
      },
    ],
    [
      "version",
      (p: Record<string, unknown>) => {
        (p.eligibility as Record<string, unknown>).schema_version = "wrong";
      },
    ],
    [
      "game",
      (p: Record<string, unknown>) => {
        p.game_id = "2026_99_OTHER";
      },
    ],
    [
      "period",
      (p: Record<string, unknown>) => {
        (p.quote as Record<string, unknown>).period = "h1";
      },
    ],
    [
      "line",
      (p: Record<string, unknown>) => {
        (p.quote as Record<string, unknown>).line = 99.5;
      },
    ],
    [
      "sign",
      (p: Record<string, unknown>) => {
        (p.quote as Record<string, unknown>).side = "AWAY";
      },
    ],
    [
      "time",
      (p: Record<string, unknown>) => {
        (p.quote as Record<string, unknown>).time = "2026-11-08T12:00:00Z";
      },
    ],
    [
      "cutoff",
      (p: Record<string, unknown>) => {
        (p.cutoff as Record<string, unknown>).decision_ts = "2026-11-08T10:00:00Z";
      },
    ],
    [
      "capability",
      (p: Record<string, unknown>) => {
        (p.capability as Record<string, unknown>).bits = [];
      },
    ],
    [
      "qualification",
      (p: Record<string, unknown>) => {
        (p.eligibility as Record<string, unknown>).fixture = false;
      },
    ],
    [
      "stale",
      (p: Record<string, unknown>) => {
        (p.cutoff as Record<string, unknown>).as_of_ts = "2026-11-08T19:00:00Z";
      },
    ],
    [
      "partial",
      (p: Record<string, unknown>) => {
        delete p.forecast;
      },
    ],
    [
      "cache",
      (p: Record<string, unknown>) => {
        p.cacheable = true;
      },
    ],
  ] as const)(
    "fault %s refuses on API / view-model / kei / cache before usable output",
    (_name, mutator) => {
      const bad = clone(loadPinned());
      mutator(bad);
      expect(() => projectFixtureAbChain(bad)).toThrow(FixtureHardRefuse);
      expect(() => assertFixtureChainRecord(bad)).toThrow(FixtureHardRefuse);
      try {
        projectFixtureFairLinesApiResponse({
          eligibility: (bad.eligibility ?? {}) as never,
          consumer: "fixture",
          quote: (bad.quote ?? {}) as never,
        });
      } catch (err) {
        expect(err).toBeInstanceOf(FixtureHardRefuse);
        expect((err as FixtureHardRefuse).partial).toBe(false);
        expect((err as FixtureHardRefuse).toDict()).not.toHaveProperty("lines");
      }
      try {
        const chain = assertFixtureChainRecord(bad);
        projectFixtureFairLinesViewModel({
          eligibility: chain.eligibility,
          lines: [],
          fixture: true,
        });
        keiGamesFromFixtureFairLines({
          eligibility: chain.eligibility,
          lines: [],
          fixture: true,
          persistOdds: false,
        } as never);
        expect.unreachable("view/kei accepted mutated chain");
      } catch (err) {
        expect(err).toBeInstanceOf(FixtureHardRefuse);
      }
    },
  );
});
