/**
 * Durable NFL inactive suppress file-store path resolution (Vercel NFT).
 * Product SoT: data/ops/nfl-inactive-suppress.json
 * Packaged copy: apps/web/lib/ops/nfl-inactive-suppress.json
 */
import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import {
  lookupNflInactiveSuppressFlag,
  NFL_INACTIVE_SUPPRESS_REASON_MAJOR,
} from "@/lib/nfl-inactive-fair-suppress";
import {
  loadNflInactiveSuppressStore,
  NFL_INACTIVE_SUPPRESS_IN_APP_REL,
  NFL_INACTIVE_SUPPRESS_REPO_REL,
  parseNflInactiveSuppressStore,
  resolveNflInactiveSuppressStoreCandidates,
  resolveNflInactiveSuppressStorePath,
} from "@/lib/nfl-inactive-suppress-store";
import { CFB_EDGE_BOARD_PUBLIC_ENABLED } from "@/lib/cfb-edge-board-public";

const webRoot = path.join(__dirname, "../..");
const repoRoot = path.join(webRoot, "../..");
const ATL_PIT_ID = "2026-W01-ATL@PIT";

const IN_APP_ABS = path.join(webRoot, NFL_INACTIVE_SUPPRESS_IN_APP_REL);
const REPO_ABS = path.join(repoRoot, NFL_INACTIVE_SUPPRESS_REPO_REL);

function existsSet(paths: string[]) {
  const allowed = new Set(paths.map((p) => path.resolve(p)));
  return (filePath: string) => allowed.has(path.resolve(filePath));
}

describe("nfl inactive suppress store paths", () => {
  it("prefers the in-app packaged copy when cwd is /var/task (Vercel)", () => {
    const vercelCwd = "/var/task";
    const inApp = path.join(vercelCwd, NFL_INACTIVE_SUPPRESS_IN_APP_REL);
    const repoOps = path.join(vercelCwd, NFL_INACTIVE_SUPPRESS_REPO_REL);
    const chosen = resolveNflInactiveSuppressStorePath({
      cwd: vercelCwd,
      exists: existsSet([inApp]),
    });
    expect(chosen).toBe(path.resolve(inApp));
    expect(chosen).not.toBe(path.resolve(repoOps));
  });

  it("does not treat missing ../../data/ops as a hit from /var/task", () => {
    const chosen = resolveNflInactiveSuppressStorePath({
      cwd: "/var/task",
      exists: () => false,
    });
    expect(chosen).toBeNull();
  });

  it("falls back to repo-root data/ops for local monorepo cwd=apps/web", () => {
    const cwd = webRoot;
    const repoFile = path.join(cwd, "..", "..", NFL_INACTIVE_SUPPRESS_REPO_REL);
    const chosen = resolveNflInactiveSuppressStorePath({
      cwd,
      exists: existsSet([repoFile]),
    });
    expect(chosen).toBe(path.resolve(repoFile));
  });

  it("lists in-app candidates before repo-root ops", () => {
    const cwd = "/var/task";
    const candidates = resolveNflInactiveSuppressStoreCandidates(cwd);
    const inAppAt = candidates.indexOf(
      path.resolve(cwd, NFL_INACTIVE_SUPPRESS_IN_APP_REL),
    );
    const repoAt = candidates.indexOf(
      path.resolve(cwd, NFL_INACTIVE_SUPPRESS_REPO_REL),
    );
    expect(inAppAt).toBeGreaterThanOrEqual(0);
    expect(repoAt).toBeGreaterThan(inAppAt);
  });

  it("env PATH override wins over discovered files", () => {
    const override = "/tmp/custom-suppress.json";
    const store = loadNflInactiveSuppressStore({
      env: { NFL_INACTIVE_SUPPRESS_PATH: override },
      exists: existsSet([override]),
      readJson: (p) =>
        p === override
          ? {
              version: 1,
              games: {
                "KC@BAL": {
                  reason: NFL_INACTIVE_SUPPRESS_REASON_MAJOR,
                  classes: ["MAJOR"],
                  rematRunId: null,
                },
              },
            }
          : null,
    });
    expect(store.games?.["KC@BAL"]?.classes).toEqual(["MAJOR"]);
    expect(store.games?.["ATL@PIT"]).toBeUndefined();
  });

  it("env comma-id list wins over files", () => {
    const store = loadNflInactiveSuppressStore({
      env: { NFL_INACTIVE_SUPPRESS: "SEA@SF" },
      exists: () => true,
      readJson: () => {
        throw new Error("file store must not be read when csv env is set");
      },
    });
    expect(store.games?.["SEA@SF"]?.reason).toBe(
      NFL_INACTIVE_SUPPRESS_REASON_MAJOR,
    );
    expect(store.games?.["ATL@PIT"]).toBeUndefined();
  });

  it("invalid inline JSON env fail-closes to empty (does not fall through)", () => {
    const store = loadNflInactiveSuppressStore({
      env: { NFL_INACTIVE_SUPPRESS_JSON: "{not-json" },
      exists: () => true,
      readJson: () => ({ games: { "ATL@PIT": { classes: ["MAJOR"] } } }),
    });
    expect(store.games).toEqual({});
  });

  it("bundled import still arms ATL@PIT when no file is on disk", () => {
    const store = loadNflInactiveSuppressStore({
      env: {},
      cwd: "/var/task",
      exists: () => false,
      readJson: () => null,
    });
    const flag = lookupNflInactiveSuppressFlag(store, ATL_PIT_ID, ["ATL@PIT"]);
    expect(flag?.reason).toBe(NFL_INACTIVE_SUPPRESS_REASON_MAJOR);
    expect(flag?.classes).toContain("MAJOR");
    expect(flag?.rematRunId ?? null).toBeNull();
  });
});

describe("nfl inactive suppress dual-file SoT", () => {
  it("keeps ATL@PIT armed in both JSON copies", () => {
    const repo = parseNflInactiveSuppressStore(
      JSON.parse(readFileSync(REPO_ABS, "utf8")),
    );
    const inApp = parseNflInactiveSuppressStore(
      JSON.parse(readFileSync(IN_APP_ABS, "utf8")),
    );
    expect(repo.games?.["ATL@PIT"]?.reason).toBe(
      NFL_INACTIVE_SUPPRESS_REASON_MAJOR,
    );
    expect(inApp.games?.["ATL@PIT"]?.reason).toBe(
      NFL_INACTIVE_SUPPRESS_REASON_MAJOR,
    );
    expect(repo.games?.["ATL@PIT"]?.rematRunId ?? null).toBeNull();
    expect(inApp.games?.["ATL@PIT"]?.rematRunId ?? null).toBeNull();
    expect(repo.games).toEqual(inApp.games);
    expect(repo.kickoffBufferMs).toBe(inApp.kickoffBufferMs);
    expect(repo.version).toBe(inApp.version);
  });

  it("NFT-includes the in-app file on assemble / today / overview", () => {
    const cfg = readFileSync(path.join(webRoot, "next.config.ts"), "utf8");
    expect(cfg).toContain("./lib/ops/nfl-inactive-suppress.json");
    expect(cfg).toContain('"/api/edge-board/[sport]/assemble"');
    expect(cfg).toContain('"/api/edge-board/[sport]/today"');
    expect(cfg).toContain('"/pro/nfl/overview"');
    expect(cfg).not.toContain('"./data/ops/');
    expect(cfg).not.toContain('"./data/ops/**/*"');
  });

  it("does not flip the CFB public board kill switch", () => {
    expect(CFB_EDGE_BOARD_PUBLIC_ENABLED).toBe(false);
  });
});
